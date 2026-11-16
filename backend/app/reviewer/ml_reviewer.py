"""
ml_reviewer.py — Semantic ML-based code reviewer using SentenceTransformers.

Strategy:
  1. Chunk each file's added lines into overlapping windows (~20 lines each).
  2. Embed every chunk with SentenceTransformer (all-MiniLM-L6-v2).
  3. Compare each chunk embedding against a set of "bad pattern" anchor
     embeddings using cosine similarity.
  4. If similarity > threshold, emit a ReviewComment with the matched
     category and a generated suggestion.

The model is loaded lazily on first use so the API server starts instantly
even when USE_ML_REVIEWER=false.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import ClassVar

import numpy as np

from app.reviewer.base import BaseReviewer
from app.reviewer.models import FileDiff, FileComment

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Anchor patterns — plain-English descriptions of "bad code" patterns.
# The embedder encodes these once; then each code chunk is compared against
# every anchor.  When similarity >= anchor threshold, we raise an issue.
# ---------------------------------------------------------------------------

@dataclass
class AnchorPattern:
    name: str          # human-readable category
    description: str   # embedded to produce anchor vector
    severity: str      # "error" | "warning" | "info"
    suggestion: str    # shown to the developer
    threshold: float = 0.45   # cosine similarity cutoff (tuned empirically)


ANCHORS: list[AnchorPattern] = [
    AnchorPattern(
        name="hardcoded_secret",
        description="hardcoded password api key secret token credential in source code string literal",
        severity="error",
        suggestion="Move secrets to environment variables or a secrets manager. Never commit credentials to source control.",
        threshold=0.42,
    ),
    AnchorPattern(
        name="sql_injection",
        description="sql injection vulnerability string concatenation in database query user input unsanitized",
        severity="error",
        suggestion="Use parameterised queries or an ORM. Never interpolate user input directly into SQL strings.",
        threshold=0.40,
    ),
    AnchorPattern(
        name="broad_exception",
        description="bare except catching all exceptions swallowing errors silent failure exception handling",
        severity="warning",
        suggestion="Catch specific exception types. Swallowing all exceptions hides bugs and makes debugging difficult.",
        threshold=0.44,
    ),
    AnchorPattern(
        name="god_function",
        description="very long function doing too many things single responsibility principle violation complex logic",
        severity="warning",
        suggestion="Break this function into smaller, focused units. Aim for functions that do one thing well.",
        threshold=0.43,
    ),
    AnchorPattern(
        name="magic_number",
        description="magic number unexplained numeric literal constant without name or documentation",
        severity="info",
        suggestion="Replace magic numbers with named constants (e.g. MAX_RETRIES = 3) to make intent clear.",
        threshold=0.46,
    ),
    AnchorPattern(
        name="missing_input_validation",
        description="missing input validation user data accepted without checks type coercion sanitization",
        severity="warning",
        suggestion="Validate and sanitize all external input before use. Assume inputs are hostile.",
        threshold=0.42,
    ),
    AnchorPattern(
        name="race_condition",
        description="race condition shared mutable state threading concurrency without locks synchronization",
        severity="error",
        suggestion="Protect shared state with locks, queues, or immutable data structures.",
        threshold=0.43,
    ),
    AnchorPattern(
        name="inefficient_loop",
        description="nested loop O(n squared) quadratic complexity inefficient algorithm performance",
        severity="info",
        suggestion="Consider a more efficient algorithm. Nested loops over large data are often O(n²) — look for hash-map or sort-based alternatives.",
        threshold=0.45,
    ),
]


# ---------------------------------------------------------------------------
# Chunk helpers
# ---------------------------------------------------------------------------

CHUNK_SIZE = 20    # lines per window
CHUNK_STEP = 10    # overlap step (slide by half-window)


def _chunk_lines(lines: list[tuple[int, str]], size: int = CHUNK_SIZE, step: int = CHUNK_STEP) -> list[tuple[int, str]]:
    """
    Slide a window over (line_number, code) pairs.
    Returns list of (start_line, joined_text) chunks.
    """
    chunks: list[tuple[int, str]] = []
    if not lines:
        return chunks
    for start in range(0, len(lines), step):
        window = lines[start : start + size]
        if not window:
            break
        start_line = window[0][0]
        text = "\n".join(code for _, code in window)
        chunks.append((start_line, text))
    return chunks


def _cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    """Cosine similarity between two 1-D vectors."""
    denom = np.linalg.norm(a) * np.linalg.norm(b)
    if denom == 0:
        return 0.0
    return float(np.dot(a, b) / denom)


# ---------------------------------------------------------------------------
# MLReviewer
# ---------------------------------------------------------------------------

class MLReviewer(BaseReviewer):
    """
    Semantic reviewer powered by SentenceTransformer embeddings.

    Attributes
    ----------
    MODEL_NAME  : HuggingFace model id.  Can be overridden via env var
                  ML_MODEL_NAME.  all-MiniLM-L6-v2 is 22 MB, fast on CPU.
    _model      : lazy-loaded SentenceTransformer instance (class-level
                  singleton so the model is shared across requests).
    _anchors    : pre-computed anchor embeddings (computed once alongside
                  the model load).
    """

    MODEL_NAME: ClassVar[str] = "all-MiniLM-L6-v2"
    _model: ClassVar[object | None] = None                   # SentenceTransformer
    _anchor_vecs: ClassVar[list[np.ndarray] | None] = None   # parallel to ANCHORS

    # ------------------------------------------------------------------
    # BaseReviewer interface
    # ------------------------------------------------------------------

    @property
    def name(self) -> str:
        return "ml_reviewer"

    def review(self, files: list[FileDiff]) -> list[FileComment]:
        """Implement BaseReviewer interface — analyse all changed files."""
        comments: list[FileComment] = []
        for file_diff in files:
            comments.extend(self._review_file(file_diff))
        return comments

    def _review_file(self, file_diff: FileDiff) -> list[FileComment]:
        """
        Entry point called by the orchestrator for each changed file.

        Steps
        -----
        1. Skip files with no added lines or non-code extensions.
        2. Ensure the model + anchor vectors are loaded.
        3. Chunk the added lines.
        4. Embed chunks in a single batch call (efficient).
        5. For each chunk × anchor, compute similarity; emit comment if ≥ threshold.
        6. Deduplicate: keep only the highest-similarity match per anchor per file.
        """
        comments: list[FileComment] = []

        # --- guard: skip non-code files ---
        skip_exts = {".md", ".txt", ".json", ".yaml", ".yml", ".toml", ".lock", ".png", ".jpg", ".svg"}
        fpath = getattr(file_diff, "path", getattr(file_diff, "filename", "unknown"))
        ext = "." + fpath.rsplit(".", 1)[-1].lower() if "." in fpath else ""
        if ext in skip_exts:
            return comments

        added = file_diff.added_lines   # list[tuple[int, str]]
        if not added:
            return comments

        # --- load model lazily ---
        try:
            self._ensure_loaded()
        except Exception as exc:   # noqa: BLE001
            logger.warning("MLReviewer: model load failed — skipping. %s", exc)
            return comments

        # --- chunk ---
        chunks = _chunk_lines(added)
        if not chunks:
            return comments

        # --- embed all chunks in one batch ---
        texts = [text for _, text in chunks]
        try:
            chunk_vecs: np.ndarray = self._model.encode(   # type: ignore[union-attr]
                texts,
                batch_size=16,
                show_progress_bar=False,
                convert_to_numpy=True,
                normalize_embeddings=True,
            )
        except Exception as exc:   # noqa: BLE001
            logger.warning("MLReviewer: encode failed — %s", exc)
            return comments

        # --- compare each chunk against each anchor ---
        # Track best match per anchor to avoid duplicate comments
        best_per_anchor: dict[int, tuple[float, int, str]] = {}  # anchor_idx → (sim, line, file)

        for chunk_idx, (start_line, _) in enumerate(chunks):
            chunk_vec = chunk_vecs[chunk_idx]
            for anchor_idx, anchor in enumerate(ANCHORS):
                anchor_vec = self._anchor_vecs[anchor_idx]   # type: ignore[index]
                sim = _cosine_similarity(chunk_vec, anchor_vec)
                if sim >= anchor.threshold:
                    prev = best_per_anchor.get(anchor_idx)
                    if prev is None or sim > prev[0]:
                        best_per_anchor[anchor_idx] = (sim, start_line, fpath)

        # --- emit one comment per triggered anchor ---
        for anchor_idx, (sim, line_no, fp) in best_per_anchor.items():
            anchor = ANCHORS[anchor_idx]
            # Map anchor severity to a valid Literal category
            cat_map = {
                "hardcoded_secret": "security",
                "sql_injection": "security",
                "broad_exception": "style",
                "god_function": "complexity",
                "magic_number": "style",
                "missing_input_validation": "security",
                "race_condition": "complexity",
                "inefficient_loop": "complexity",
            }
            cat = cat_map.get(anchor.name, "security")
            comments.append(
                FileComment(
                    file_path=fp,
                    line_number=line_no,
                    severity=anchor.severity,
                    category=cat,
                    message=(
                        f"[ML] Potential {anchor.name.replace('_', ' ')} detected "
                        f"(semantic similarity {sim:.2f})."
                    ),
                    suggestion=anchor.suggestion,
                )
            )
            logger.debug(
                "MLReviewer: %s → %s @ line %d (sim=%.3f)",
                fp, anchor.name, line_no, sim,
            )

        return comments

    # ------------------------------------------------------------------
    # Lazy model loader (class-level singleton)
    # ------------------------------------------------------------------

    @classmethod
    def _ensure_loaded(cls) -> None:
        """
        Load the SentenceTransformer model and compute anchor embeddings
        exactly once for the lifetime of the process.

        Uses a double-checked pattern: check _model is None before and
        after acquiring — safe for single-process uvicorn.  For
        multi-process (gunicorn), each worker gets its own copy (fine).
        """
        if cls._model is not None:
            return

        logger.info("MLReviewer: loading model '%s' …", cls.MODEL_NAME)

        from sentence_transformers import SentenceTransformer  # local import keeps startup fast

        # Respect ML_MODEL_NAME env override
        import os
        model_name = os.getenv("ML_MODEL_NAME", cls.MODEL_NAME)

        cls._model = SentenceTransformer(model_name)
        logger.info("MLReviewer: model loaded.")

        # Pre-compute anchor embeddings
        anchor_texts = [a.description for a in ANCHORS]
        cls._anchor_vecs = list(
            cls._model.encode(   # type: ignore[union-attr]
                anchor_texts,
                batch_size=len(anchor_texts),
                show_progress_bar=False,
                convert_to_numpy=True,
                normalize_embeddings=True,
            )
        )
        logger.info("MLReviewer: %d anchor embeddings computed.", len(cls._anchor_vecs))
