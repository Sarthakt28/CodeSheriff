from __future__ import annotations
from dataclasses import dataclass, field
from typing import Literal


@dataclass
class FileComment:
    """A single review comment on a specific file + line."""
    file_path: str
    line_number: int | None
    severity: Literal["error", "warning", "info"]
    category: Literal["syntax", "style", "security", "complexity", "documentation"]
    message: str
    suggestion: str | None = None


@dataclass
class FileDiff:
    """A single changed file extracted from the unified diff."""
    path: str
    language: str
    added_lines: list[tuple[int, str]] = field(default_factory=list)   # (line_no, code)
    removed_lines: list[tuple[int, str]] = field(default_factory=list)
    is_new_file: bool = False
    is_deleted_file: bool = False
