"""
Rules-based code reviewer using Pygments for syntax analysis.

Rules implemented:
  1. Syntax errors        — Pygments Token.Error tokens
  2. Long lines           — lines > 120 chars
  3. TODO / FIXME         — leftover debug comments
  4. Hardcoded secrets    — regex patterns (passwords, API keys, tokens)
  5. Large functions      — Python defs with > 50 added lines
  6. Missing docstrings   — Python `def` without a docstring on the next line
  7. Print statements     — `print(` left in production code (Python)
  8. Commented-out code   — large blocks of commented lines
"""
from __future__ import annotations
import re
from pygments.lexers import get_lexer_by_name, guess_lexer
from pygments.token import Token
from pygments.util import ClassNotFound

from app.reviewer.base import BaseReviewer
from app.reviewer.models import FileDiff, FileComment

# ── Secret patterns ───────────────────────────────────────────────────────────
_SECRET_PATTERNS = [
    (re.compile(r'(?i)(password|passwd|pwd)\s*=\s*["\'][^"\']{4,}["\']'), "Hardcoded password detected"),
    (re.compile(r'(?i)(api_key|apikey|api_secret)\s*=\s*["\'][^"\']{8,}["\']'), "Hardcoded API key detected"),
    (re.compile(r'(?i)(secret|token|auth_token)\s*=\s*["\'][^"\']{8,}["\']'), "Hardcoded secret/token detected"),
    (re.compile(r'(?i)aws_access_key_id\s*=\s*["\'][A-Z0-9]{20}["\']'), "Hardcoded AWS access key detected"),
    (re.compile(r'(?i)aws_secret_access_key\s*=\s*["\'][^"\']{40}["\']'), "Hardcoded AWS secret key detected"),
    (re.compile(r'-----BEGIN (RSA|EC|OPENSSH) PRIVATE KEY-----'), "Private key embedded in source code"),
]

_TODO_PATTERN = re.compile(r'(?i)#\s*(TODO|FIXME|HACK|XXX|BUG)\b')
_PRINT_PATTERN = re.compile(r'\bprint\s*\(')
_COMMENTED_CODE = re.compile(r'^\s*#.*[({=;]')     # comment lines that look like code


class RulesReviewer(BaseReviewer):

    MAX_LINE_LENGTH = 120
    MAX_FUNCTION_LINES = 50
    MIN_COMMENTED_CODE_BLOCK = 5    # consecutive commented-code lines to flag

    def review(self, files: list[FileDiff]) -> list[FileComment]:
        comments: list[FileComment] = []

        for file in files:
            if not file.added_lines:
                continue

            comments.extend(self._check_long_lines(file))
            comments.extend(self._check_todos(file))
            comments.extend(self._check_secrets(file))
            comments.extend(self._check_syntax_errors(file))

            if file.language == "python":
                comments.extend(self._check_print_statements(file))
                comments.extend(self._check_missing_docstrings(file))
                comments.extend(self._check_large_functions(file))

            comments.extend(self._check_commented_out_code(file))

        return comments

    # ── Individual rules ──────────────────────────────────────────────────────

    def _check_long_lines(self, file: FileDiff) -> list[FileComment]:
        result = []
        for line_no, code in file.added_lines:
            if len(code) > self.MAX_LINE_LENGTH:
                result.append(FileComment(
                    file_path=file.path,
                    line_number=line_no,
                    severity="warning",
                    category="style",
                    message=f"Line is {len(code)} characters long (max {self.MAX_LINE_LENGTH}).",
                    suggestion="Break this line into multiple lines for readability.",
                ))
        return result

    def _check_todos(self, file: FileDiff) -> list[FileComment]:
        result = []
        for line_no, code in file.added_lines:
            m = _TODO_PATTERN.search(code)
            if m:
                result.append(FileComment(
                    file_path=file.path,
                    line_number=line_no,
                    severity="info",
                    category="style",
                    message=f"Found `{m.group(0).strip()}` comment — resolve before merging.",
                    suggestion="Create a tracked issue for this instead of leaving it in source code.",
                ))
        return result

    def _check_secrets(self, file: FileDiff) -> list[FileComment]:
        result = []
        for line_no, code in file.added_lines:
            for pattern, label in _SECRET_PATTERNS:
                if pattern.search(code):
                    result.append(FileComment(
                        file_path=file.path,
                        line_number=line_no,
                        severity="error",
                        category="security",
                        message=f"🚨 {label}. Never commit secrets to source control.",
                        suggestion="Use environment variables or a secrets manager (e.g. AWS Secrets Manager, HashiCorp Vault).",
                    ))
                    break   # one secret error per line is enough
        return result

    def _check_syntax_errors(self, file: FileDiff) -> list[FileComment]:
        """Use Pygments to tokenize and flag Token.Error tokens."""
        result = []
        try:
            lexer = get_lexer_by_name(file.language)
        except ClassNotFound:
            return result

        for line_no, code in file.added_lines:
            tokens = list(lexer.get_tokens(code))
            has_error = any(ttype is Token.Error for ttype, _ in tokens)
            if has_error:
                result.append(FileComment(
                    file_path=file.path,
                    line_number=line_no,
                    severity="error",
                    category="syntax",
                    message="Potential syntax error detected by lexer analysis.",
                    suggestion="Review this line carefully — it may contain invalid syntax.",
                ))
        return result

    def _check_print_statements(self, file: FileDiff) -> list[FileComment]:
        result = []
        for line_no, code in file.added_lines:
            stripped = code.strip()
            if _PRINT_PATTERN.search(stripped) and not stripped.startswith("#"):
                result.append(FileComment(
                    file_path=file.path,
                    line_number=line_no,
                    severity="warning",
                    category="style",
                    message="`print()` statement found in production code.",
                    suggestion="Use a proper logging framework (`import logging`) instead of print statements.",
                ))
        return result

    def _check_missing_docstrings(self, file: FileDiff) -> list[FileComment]:
        """Flag Python `def` lines not followed by a docstring."""
        result = []
        lines = [(ln, code) for ln, code in file.added_lines]

        for i, (line_no, code) in enumerate(lines):
            stripped = code.strip()
            if re.match(r'^def\s+\w+', stripped) or re.match(r'^async\s+def\s+\w+', stripped):
                # Check if the NEXT added line starts a docstring
                next_code = lines[i + 1][1].strip() if i + 1 < len(lines) else ""
                if not (next_code.startswith('"""') or next_code.startswith("'''")):
                    result.append(FileComment(
                        file_path=file.path,
                        line_number=line_no,
                        severity="info",
                        category="documentation",
                        message=f"Function `{_extract_func_name(stripped)}` is missing a docstring.",
                        suggestion='Add a docstring: `"""Brief description of what this function does."""`',
                    ))
        return result

    def _check_large_functions(self, file: FileDiff) -> list[FileComment]:
        """Flag Python functions where > MAX_FUNCTION_LINES lines were added."""
        result = []
        func_start: int | None = None
        func_name: str = ""
        func_line_count = 0

        for line_no, code in file.added_lines:
            stripped = code.strip()
            m = re.match(r'^(?:async\s+)?def\s+(\w+)', stripped)
            if m:
                # Check previous function
                if func_start and func_line_count > self.MAX_FUNCTION_LINES:
                    result.append(FileComment(
                        file_path=file.path,
                        line_number=func_start,
                        severity="warning",
                        category="complexity",
                        message=f"Function `{func_name}` has {func_line_count} added lines — consider breaking it up.",
                        suggestion="Extract logical sections into smaller, well-named helper functions.",
                    ))
                func_start = line_no
                func_name = m.group(1)
                func_line_count = 1
            elif func_start:
                func_line_count += 1

        # Check last function
        if func_start and func_line_count > self.MAX_FUNCTION_LINES:
            result.append(FileComment(
                file_path=file.path,
                line_number=func_start,
                severity="warning",
                category="complexity",
                message=f"Function `{func_name}` has {func_line_count} added lines — consider breaking it up.",
                suggestion="Extract logical sections into smaller, well-named helper functions.",
            ))

        return result

    def _check_commented_out_code(self, file: FileDiff) -> list[FileComment]:
        """Flag long blocks of commented-out code."""
        result = []
        streak: list[tuple[int, str]] = []

        def _flush():
            if len(streak) >= self.MIN_COMMENTED_CODE_BLOCK:
                start_line = streak[0][0]
                result.append(FileComment(
                    file_path=file.path,
                    line_number=start_line,
                    severity="info",
                    category="style",
                    message=f"{len(streak)} consecutive lines of commented-out code detected.",
                    suggestion="Remove dead code instead of commenting it out — use version control (git) to recover it if needed.",
                ))

        for line_no, code in file.added_lines:
            if _COMMENTED_CODE.match(code):
                streak.append((line_no, code))
            else:
                _flush()
                streak = []
        _flush()

        return result


def _extract_func_name(def_line: str) -> str:
    m = re.search(r'def\s+(\w+)', def_line)
    return m.group(1) if m else "unknown"
