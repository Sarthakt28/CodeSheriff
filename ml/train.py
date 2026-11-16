"""
ml/train.py — Fine-tune a code review severity classifier.

Usage
-----
  python ml/train.py \
      --data ml/data/labeled_data.jsonl \
      --output ml/models/severity_classifier \
      --epochs 5 \
      --batch-size 8

Data format (one JSON object per line)
---------------------------------------
  {"code": "password = 'hunter2'", "label": "error"}
  {"code": "x = x + 1  # TODO fix", "label": "warning"}
  {"code": "def foo(a,b,c,d,e,f): ...", "label": "info"}

Labels: "error" | "warning" | "info"

Model: Salesforce/codet5-base used as a sequence classifier.
  - codet5-base encoder produces 768-d representations
  - A linear head maps 768 → 3 (error / warning / info)
  - We fine-tune the whole model (encoder + head) with AdamW

Output
------
  ml/models/severity_classifier/
      config.json
      pytorch_model.bin   (or model.safetensors)
      tokenizer_config.json
      label_map.json      ({"error":0,"warning":1,"info":2})
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import random
from pathlib import Path

import numpy as np
import torch
from torch.utils.data import DataLoader, Dataset
from transformers import (
    AutoModelForSequenceClassification,
    AutoTokenizer,
    get_linear_schedule_with_warmup,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

BASE_MODEL = "Salesforce/codet5-base"
LABEL_MAP: dict[str, int] = {"error": 0, "warning": 1, "info": 2}
ID2LABEL: dict[int, str] = {v: k for k, v in LABEL_MAP.items()}
MAX_LENGTH = 512
SEED = 42


# ---------------------------------------------------------------------------
# Reproducibility
# ---------------------------------------------------------------------------

def set_seed(seed: int) -> None:
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)


# ---------------------------------------------------------------------------
# Dataset
# ---------------------------------------------------------------------------

class CodeReviewDataset(Dataset):
    """
    Wraps a list of (code, label_id) pairs.

    __getitem__ returns a dict of tensors ready for the model:
      input_ids, attention_mask, labels
    """

    def __init__(self, examples: list[dict], tokenizer, max_length: int = MAX_LENGTH):
        self.examples = examples
        self.tokenizer = tokenizer
        self.max_length = max_length

    def __len__(self) -> int:
        return len(self.examples)

    def __getitem__(self, idx: int) -> dict[str, torch.Tensor]:
        ex = self.examples[idx]
        enc = self.tokenizer(
            ex["code"],
            max_length=self.max_length,
            padding="max_length",
            truncation=True,
            return_tensors="pt",
        )
        return {
            "input_ids": enc["input_ids"].squeeze(0),
            "attention_mask": enc["attention_mask"].squeeze(0),
            "labels": torch.tensor(ex["label_id"], dtype=torch.long),
        }


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------

def load_jsonl(path: str) -> list[dict]:
    """Load labeled_data.jsonl → list of {code, label_id}."""
    examples = []
    with open(path, encoding="utf-8") as f:
        for lineno, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
                code = obj["code"]
                label = obj["label"].lower()
                if label not in LABEL_MAP:
                    logger.warning("Line %d: unknown label '%s' — skipping", lineno, label)
                    continue
                examples.append({"code": code, "label_id": LABEL_MAP[label]})
            except (json.JSONDecodeError, KeyError) as exc:
                logger.warning("Line %d: parse error — %s", lineno, exc)
    logger.info("Loaded %d examples from %s", len(examples), path)
    return examples


def train_val_split(examples: list[dict], val_ratio: float = 0.1) -> tuple[list[dict], list[dict]]:
    """Stratified train/val split (by label_id)."""
    random.shuffle(examples)
    split = int(len(examples) * (1 - val_ratio))
    return examples[:split], examples[split:]


# ---------------------------------------------------------------------------
# Training loop
# ---------------------------------------------------------------------------

def train(
    data_path: str,
    output_dir: str,
    epochs: int = 5,
    batch_size: int = 8,
    learning_rate: float = 2e-5,
    warmup_ratio: float = 0.1,
) -> None:
    set_seed(SEED)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    logger.info("Using device: %s", device)

    # --- data ---
    all_examples = load_jsonl(data_path)
    if len(all_examples) < 10:
        raise ValueError("Need at least 10 labeled examples to train.")
    train_data, val_data = train_val_split(all_examples)
    logger.info("Train: %d  Val: %d", len(train_data), len(val_data))

    # --- tokenizer + model ---
    logger.info("Loading tokenizer and model from '%s' …", BASE_MODEL)
    tokenizer = AutoTokenizer.from_pretrained(BASE_MODEL)
    model = AutoModelForSequenceClassification.from_pretrained(
        BASE_MODEL,
        num_labels=len(LABEL_MAP),
        id2label=ID2LABEL,
        label2id=LABEL_MAP,
    )
    model.to(device)

    # --- dataloaders ---
    train_ds = CodeReviewDataset(train_data, tokenizer)
    val_ds = CodeReviewDataset(val_data, tokenizer)
    train_loader = DataLoader(train_ds, batch_size=batch_size, shuffle=True, num_workers=0)
    val_loader = DataLoader(val_ds, batch_size=batch_size, shuffle=False, num_workers=0)

    # --- optimizer + scheduler ---
    optimizer = torch.optim.AdamW(model.parameters(), lr=learning_rate, weight_decay=0.01)
    total_steps = len(train_loader) * epochs
    warmup_steps = int(total_steps * warmup_ratio)
    scheduler = get_linear_schedule_with_warmup(optimizer, warmup_steps, total_steps)

    # --- training loop ---
    best_val_acc = 0.0
    for epoch in range(1, epochs + 1):
        # -- train --
        model.train()
        total_loss = 0.0
        for step, batch in enumerate(train_loader, 1):
            input_ids = batch["input_ids"].to(device)
            attention_mask = batch["attention_mask"].to(device)
            labels = batch["labels"].to(device)

            outputs = model(input_ids=input_ids, attention_mask=attention_mask, labels=labels)
            loss = outputs.loss
            loss.backward()

            torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            optimizer.step()
            scheduler.step()
            optimizer.zero_grad()

            total_loss += loss.item()
            if step % 10 == 0:
                logger.info("Epoch %d  Step %d/%d  Loss=%.4f", epoch, step, len(train_loader), loss.item())

        avg_loss = total_loss / len(train_loader)

        # -- validate --
        model.eval()
        correct = total = 0
        with torch.no_grad():
            for batch in val_loader:
                input_ids = batch["input_ids"].to(device)
                attention_mask = batch["attention_mask"].to(device)
                labels = batch["labels"].to(device)
                outputs = model(input_ids=input_ids, attention_mask=attention_mask)
                preds = outputs.logits.argmax(dim=-1)
                correct += (preds == labels).sum().item()
                total += labels.size(0)
        val_acc = correct / total if total > 0 else 0.0
        logger.info("Epoch %d  avg_loss=%.4f  val_acc=%.4f", epoch, avg_loss, val_acc)

        # -- checkpoint best model --
        if val_acc > best_val_acc:
            best_val_acc = val_acc
            logger.info("  → New best val_acc=%.4f — saving checkpoint", val_acc)
            os.makedirs(output_dir, exist_ok=True)
            model.save_pretrained(output_dir)
            tokenizer.save_pretrained(output_dir)
            label_map_path = Path(output_dir) / "label_map.json"
            label_map_path.write_text(json.dumps(LABEL_MAP, indent=2))

    logger.info("Training complete. Best val_acc=%.4f", best_val_acc)
    logger.info("Model saved to %s", output_dir)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Fine-tune CodeT5 for code review severity classification")
    p.add_argument("--data", required=True, help="Path to labeled_data.jsonl")
    p.add_argument("--output", default="ml/models/severity_classifier", help="Output directory")
    p.add_argument("--epochs", type=int, default=5)
    p.add_argument("--batch-size", type=int, default=8)
    p.add_argument("--lr", type=float, default=2e-5, help="Learning rate")
    return p.parse_args()


if __name__ == "__main__":
    args = parse_args()
    train(
        data_path=args.data,
        output_dir=args.output,
        epochs=args.epochs,
        batch_size=args.batch_size,
        learning_rate=args.lr,
    )
