"""
Abstract base class for all reviewers (rules-based and ML-based).
"""
from __future__ import annotations
from abc import ABC, abstractmethod
from app.reviewer.models import FileDiff, FileComment


class BaseReviewer(ABC):
    """All reviewers implement this interface."""

    @abstractmethod
    def review(self, files: list[FileDiff]) -> list[FileComment]:
        """
        Analyse a list of changed files and return a list of comments.

        Args:
            files: Parsed FileDiff objects from the PR diff.

        Returns:
            List of FileComment objects to be posted on GitHub.
        """
        ...
