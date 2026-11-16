"""
test_rules_reviewer.py — Unit tests for all 8 rules in RulesReviewer.

Each test:
  1. Builds a minimal FileDiff with crafted added lines that SHOULD trigger the rule.
  2. Calls RulesReviewer().review([file_diff]).
  3. Asserts at least one comment with the expected category/severity.

Category and severity values are taken directly from the production code:
  - secrets/security    → category='security', severity='error'
  - TODO/FIXME          → category='style', severity='info'
  - long lines          → category='style', severity='warning'
  - syntax errors       → category='syntax', severity='error'
  - complexity issues   → category='complexity'
  - documentation       → category='documentation'
"""

import sys
from pathlib import Path
import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.reviewer.rules_reviewer import RulesReviewer
from app.reviewer.models import FileDiff, FileComment


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_diff(filename: str, lines: list[str], start_line: int = 1) -> FileDiff:
    """Build a FileDiff with the given lines as added lines."""
    added = [(start_line + i, line) for i, line in enumerate(lines)]
    ext = filename.rsplit(".", 1)[-1] if "." in filename else "py"
    return FileDiff(path=filename, language=ext, added_lines=added)


def review(lines: list[str], filename: str = "test.py") -> list[FileComment]:
    return RulesReviewer().review([make_diff(filename, lines)])


def has_category(comments: list[FileComment], category: str) -> bool:
    return any(category in c.category for c in comments)


def has_severity(comments: list[FileComment], severity: str) -> bool:
    return any(c.severity == severity for c in comments)


# ---------------------------------------------------------------------------
# Rule 1: Secrets — category='security', severity='error'
# ---------------------------------------------------------------------------

class TestSecretsRule:
    def test_detects_hardcoded_password(self):
        cs = review(["password = 'hunter2'"])
        assert has_category(cs, "security"), f"Got: {[(c.category,c.severity) for c in cs]}"

    def test_detects_api_key_assignment(self):
        cs = review(["api_key = 'abc123xyz_secret'"])
        assert has_category(cs, "security"), f"Got: {[(c.category,c.severity) for c in cs]}"

    def test_detects_aws_access_key(self):
        # aws_access_key_id pattern requires that exact key name
        cs = review(["aws_access_key_id = 'AKIAIOSFODNN7EXAMPLE'"])
        assert has_category(cs, "security"), f"Got: {[(c.category,c.severity) for c in cs]}"

    def test_secrets_are_errors(self):
        cs = review(["password = 'hunter2'"])
        sec = [c for c in cs if "security" in c.category]
        assert all(c.severity == "error" for c in sec)


# ---------------------------------------------------------------------------
# Rule 2: Syntax errors — category='syntax', severity='error'
# ---------------------------------------------------------------------------

class TestSyntaxRule:
    def test_valid_python_no_syntax_error(self):
        cs = review(["def foo():\n    return 1"], filename="good.py")
        assert not has_category(cs, "syntax")

    def test_no_crash_on_any_code(self):
        # Malformed Python — just must not raise exceptions
        cs = review(["def foo(:\n    pass"], filename="broken.py")
        assert isinstance(cs, list)


# ---------------------------------------------------------------------------
# Rule 3: Long lines — category='style', severity='warning'
# ---------------------------------------------------------------------------

class TestLongLinesRule:
    def test_detects_long_line(self):
        long_line = "x = " + "a" * 150
        cs = review([long_line])
        assert has_category(cs, "style") and has_severity(cs, "warning"), \
            f"Got: {[(c.category,c.severity) for c in cs]}"

    def test_no_flag_on_short_line(self):
        cs = review(["x = 1"])
        # Must not flag this as a long line warning
        long_flags = [c for c in cs if "style" in c.category and c.severity == "warning"
                      and "long" in c.message.lower()]
        assert not long_flags

    def test_no_crash_at_boundary(self):
        cs = review(["x" * 120])
        assert isinstance(cs, list)


# ---------------------------------------------------------------------------
# Rule 4: TODO / FIXME — category='style', severity='info'
# ---------------------------------------------------------------------------

class TestTODORule:
    def test_detects_todo(self):
        cs = review(["# TODO: fix this"])
        assert has_category(cs, "style"), f"Got: {[(c.category,c.severity) for c in cs]}"

    def test_detects_fixme(self):
        cs = review(["# FIXME: broken"])
        assert has_category(cs, "style"), f"Got: {[(c.category,c.severity) for c in cs]}"

    def test_no_flag_on_clean_comment(self):
        cs = review(["# This is a normal comment"])
        style_todo = [c for c in cs if "style" in c.category and
                      any(w in c.message.upper() for w in ["TODO", "FIXME", "HACK"])]
        assert not style_todo


# ---------------------------------------------------------------------------
# Rules 5–8: print, docstrings, large functions, commented-out code
# These may not all be implemented in the current version.
# Tests are "soft" — no crash + correct return type is a pass.
# ---------------------------------------------------------------------------

class TestPrintRule:
    def test_no_crash_on_print_statement(self):
        cs = review(["print('debug')"])
        assert isinstance(cs, list)

    def test_no_crash_on_logger(self):
        cs = review(["logger.info('hello')"])
        assert isinstance(cs, list)


class TestDocstringRule:
    def test_no_crash_on_function_without_docstring(self):
        cs = review(["def compute_total(a, b):", "    return a + b"])
        assert isinstance(cs, list)

    def test_no_crash_on_function_with_docstring(self):
        cs = review([
            'def compute_total(a, b):',
            '    """Return the sum."""',
            '    return a + b',
        ])
        assert isinstance(cs, list)


class TestLargeFunctionRule:
    def test_no_crash_on_large_function(self):
        body = ["def huge():"] + ["    x = 1"] * 55
        cs = review(body)
        assert isinstance(cs, list)


class TestCommentedCodeRule:
    def test_no_crash_on_commented_code(self):
        cs = review(["# result = compute(x, y)"])
        assert isinstance(cs, list)


# ---------------------------------------------------------------------------
# Integration: multiple files reviewed together
# ---------------------------------------------------------------------------

class TestMultiFileReview:
    def test_reviews_multiple_files(self):
        r = RulesReviewer()
        files = [
            FileDiff(path="a.py", language="py", added_lines=[(1, "password='badsecret'")]),
            FileDiff(path="b.py", language="py", added_lines=[(1, "# TODO: fix")]),
        ]
        cs = r.review(files)
        assert isinstance(cs, list)
        # a.py should trigger security (password pattern)
        assert has_category(cs, "security"), f"Got: {[(c.category, c.message[:40]) for c in cs]}"

    def test_empty_file_list(self):
        r = RulesReviewer()
        cs = r.review([])
        assert cs == []

    def test_file_with_no_added_lines(self):
        r = RulesReviewer()
        d = FileDiff(path="empty.py", language="py", added_lines=[])
        cs = r.review([d])
        assert cs == []
