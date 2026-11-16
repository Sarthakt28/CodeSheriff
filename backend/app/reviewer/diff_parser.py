"""
Unified diff parser — converts a raw diff string into a list of FileDiff objects.
Each FileDiff contains only the ADDED lines (the ones we review) with their real line numbers.
"""
from __future__ import annotations
import re
from app.reviewer.models import FileDiff

# Map common file extensions to language names (for Pygments)
_EXT_TO_LANG = {
    ".py": "python", ".js": "javascript", ".ts": "typescript",
    ".jsx": "jsx", ".tsx": "tsx", ".java": "java", ".go": "go",
    ".rb": "ruby", ".rs": "rust", ".cpp": "cpp", ".c": "c",
    ".cs": "csharp", ".php": "php", ".swift": "swift", ".kt": "kotlin",
    ".sh": "bash", ".yaml": "yaml", ".yml": "yaml", ".json": "json",
    ".html": "html", ".css": "css", ".scss": "scss", ".sql": "sql",
    ".md": "markdown", ".toml": "toml",
}


def _detect_language(path: str) -> str:
    for ext, lang in _EXT_TO_LANG.items():
        if path.endswith(ext):
            return lang
    return "text"


def parse_diff(diff_text: str) -> list[FileDiff]:
    """Parse a unified diff string and return a list of FileDiff objects."""
    files: list[FileDiff] = []
    current_file: FileDiff | None = None
    new_line_no = 0

    for line in diff_text.splitlines():
        # New file header
        if line.startswith("diff --git"):
            if current_file:
                files.append(current_file)
            current_file = None
            continue

        if line.startswith("+++ b/"):
            path = line[6:]
            current_file = FileDiff(path=path, language=_detect_language(path))
            continue

        if line.startswith("+++ /dev/null"):
            # Deleted file — skip
            current_file = None
            continue

        if line.startswith("--- /dev/null") and current_file:
            current_file.is_new_file = True
            continue

        if current_file is None:
            continue

        # Hunk header: @@ -old_start,old_len +new_start,new_len @@
        hunk_match = re.match(r"^@@ -\d+(?:,\d+)? \+(\d+)(?:,\d+)? @@", line)
        if hunk_match:
            new_line_no = int(hunk_match.group(1))
            continue

        if line.startswith("+") and not line.startswith("+++"):
            # Added line
            current_file.added_lines.append((new_line_no, line[1:]))
            new_line_no += 1
        elif line.startswith("-") and not line.startswith("---"):
            # Removed line — track for context but don't increment new line counter
            current_file.removed_lines.append((new_line_no, line[1:]))
        else:
            # Context line
            new_line_no += 1

    if current_file:
        files.append(current_file)

    return files
