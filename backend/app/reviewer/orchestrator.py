"""
Orchestrator — combines RulesReviewer + MLReviewer results,
deduplicates overlapping comments, and ranks by severity.
"""
from __future__ import annotations
from app.reviewer.base import BaseReviewer
from app.reviewer.models import FileDiff, FileComment
from app.reviewer.rules_reviewer import RulesReviewer
from app.core.config import settings

_SEVERITY_RANK = {"error": 0, "warning": 1, "info": 2}


class ReviewOrchestrator:

    def __init__(self):
        self.reviewers: list[BaseReviewer] = [RulesReviewer()]

        # Lazy-load ML reviewer only if enabled
        if settings.USE_ML_REVIEWER:
            try:
                from app.reviewer.ml_reviewer import MLReviewer
                self.reviewers.append(MLReviewer())
                print("[REVIEWER] ML reviewer loaded.")
            except Exception as e:
                print(f"[REVIEWER WARNING] Could not load ML reviewer: {e}. Using rules only.")

    def run(self, files: list[FileDiff]) -> list[FileComment]:
        """Run all reviewers and return deduplicated, ranked comments."""
        all_comments: list[FileComment] = []
        for reviewer in self.reviewers:
            try:
                all_comments.extend(reviewer.review(files))
            except Exception as e:
                print(f"[REVIEWER ERROR] {type(reviewer).__name__} failed: {e}")

        # Deduplicate: same file + line + category → keep the most severe one
        seen: dict[tuple, FileComment] = {}
        for c in all_comments:
            key = (c.file_path, c.line_number, c.category)
            if key not in seen or _SEVERITY_RANK[c.severity] < _SEVERITY_RANK[seen[key].severity]:
                seen[key] = c

        # Sort: errors first, then warnings, then info
        return sorted(seen.values(), key=lambda c: (_SEVERITY_RANK[c.severity], c.file_path, c.line_number or 0))


# Singleton
orchestrator = ReviewOrchestrator()
