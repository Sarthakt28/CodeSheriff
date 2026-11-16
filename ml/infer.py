"""
ml/infer.py — Standalone inference CLI for the CodeSheriff ML reviewer.

Two modes:
  1. --mode embedding  (default): uses MLReviewer (SentenceTransformer anchors)
     - No training required, works out of the box
     - Analyses a code file or snippet and prints findings

  2. --mode classifier: uses fine-tuned CodeT5 severity classifier
     - Requires a trained model at --model-dir (produced by train.py)
     - Classifies the whole snippet as error / warning / info

Usage
-----
  # Embedding mode (zero-shot)
  python ml/infer.py --file path/to/file.py

  # Classifier mode (needs trained model)
  python ml/infer.py --file path/to/file.py --mode classifier --model-dir ml/models/severity_classifier

  # Inline snippet
  python ml/infer.py --code "password = 'hunter2'"
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# Embedding-mode inference (uses MLReviewer directly)
# ---------------------------------------------------------------------------

def run_embedding_mode(code: str, filename: str = "snippet.py") -> None:
    """
    Wraps the production MLReviewer so infer.py tests the exact same path
    that webhook.py uses.  Constructs a fake FileDiff, calls review_file(),
    and pretty-prints the results.
    """
    # Add backend/ to sys.path so we can import the app package
    backend_dir = Path(__file__).parent.parent / "backend"
    sys.path.insert(0, str(backend_dir))

    from app.reviewer.ml_reviewer import MLReviewer
    from app.reviewer.models import FileDiff

    lines = code.splitlines()
    added_lines = [(i + 1, line) for i, line in enumerate(lines)]

    file_diff = FileDiff(
        filename=filename,
        added_lines=added_lines,
        raw_diff=code,
    )

    reviewer = MLReviewer()
    comments = reviewer.review_file(file_diff)

    if not comments:
        print("✅  No issues detected (embedding similarity below all thresholds).")
        return

    print(f"\n🔍  Found {len(comments)} issue(s) in '{filename}':\n")
    for i, c in enumerate(comments, 1):
        icon = {"error": "🔴", "warning": "🟡", "info": "🔵"}.get(c.severity, "⚪")
        print(f"  {i}. {icon} [{c.severity.upper()}] {c.category}")
        print(f"     Line {c.line_number}: {c.message}")
        if c.suggestion:
            print(f"     💡 {c.suggestion}")
        print()


# ---------------------------------------------------------------------------
# Classifier-mode inference (fine-tuned CodeT5)
# ---------------------------------------------------------------------------

def run_classifier_mode(code: str, model_dir: str) -> None:
    """
    Loads the fine-tuned AutoModelForSequenceClassification from model_dir
    and runs a single forward pass to predict severity.
    """
    try:
        import torch
        from transformers import AutoModelForSequenceClassification, AutoTokenizer
    except ImportError:
        print("ERROR: torch and transformers must be installed. Run: pip install torch transformers")
        sys.exit(1)

    model_path = Path(model_dir)
    if not model_path.exists():
        print(f"ERROR: model directory not found: {model_dir}")
        print("Run ml/train.py first to produce a fine-tuned model.")
        sys.exit(1)

    # Load label map
    label_map_file = model_path / "label_map.json"
    if label_map_file.exists():
        label_map: dict[str, int] = json.loads(label_map_file.read_text())
        id2label = {v: k for k, v in label_map.items()}
    else:
        id2label = {0: "error", 1: "warning", 2: "info"}

    print(f"Loading model from {model_dir} …")
    tokenizer = AutoTokenizer.from_pretrained(model_dir)
    model = AutoModelForSequenceClassification.from_pretrained(model_dir)
    model.eval()

    # Tokenise
    enc = tokenizer(
        code,
        max_length=512,
        padding="max_length",
        truncation=True,
        return_tensors="pt",
    )

    with torch.no_grad():
        outputs = model(**enc)
        logits = outputs.logits
        probs = torch.softmax(logits, dim=-1).squeeze().tolist()
        pred_id = int(logits.argmax(dim=-1))

    label = id2label[pred_id]
    icon = {"error": "🔴", "warning": "🟡", "info": "🔵"}.get(label, "⚪")

    print(f"\n{icon}  Predicted severity: {label.upper()}\n")
    print("  Probability breakdown:")
    for label_id, prob in enumerate(probs):
        lname = id2label.get(label_id, str(label_id))
        bar = "█" * int(prob * 30)
        print(f"    {lname:<10}  {bar:<30}  {prob:.3f}")
    print()


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="CodeSheriff ML inference — analyse code for issues",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    source = p.add_mutually_exclusive_group(required=True)
    source.add_argument("--file", help="Path to a source file to analyse")
    source.add_argument("--code", help="Inline code snippet (use quotes)")

    p.add_argument(
        "--mode",
        choices=["embedding", "classifier"],
        default="embedding",
        help="'embedding' = zero-shot anchor similarity (default); 'classifier' = fine-tuned model",
    )
    p.add_argument(
        "--model-dir",
        default="ml/models/severity_classifier",
        help="Path to fine-tuned model directory (classifier mode only)",
    )
    return p.parse_args()


def main() -> None:
    args = parse_args()

    if args.file:
        path = Path(args.file)
        if not path.exists():
            print(f"ERROR: file not found: {args.file}")
            sys.exit(1)
        code = path.read_text(encoding="utf-8", errors="replace")
        filename = path.name
    else:
        code = args.code
        filename = "snippet.py"

    print(f"\n{'='*60}")
    print(f"  CodeSheriff ML Inference")
    print(f"  Mode    : {args.mode}")
    print(f"  File    : {filename}")
    print(f"  Lines   : {len(code.splitlines())}")
    print(f"{'='*60}")

    if args.mode == "embedding":
        run_embedding_mode(code, filename)
    else:
        run_classifier_mode(code, args.model_dir)


if __name__ == "__main__":
    main()
