"""
test_diff_parser.py — Unit tests for the unified diff parser.

We feed raw diff strings and assert that:
  - Added lines are extracted with correct real line numbers
  - Deleted lines are ignored (not in added_lines)
  - Context lines are ignored
  - Multiple hunks are handled correctly
  - Binary/empty diffs return empty results
"""

import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.reviewer.diff_parser import parse_diff
from app.reviewer.models import FileDiff


# ---------------------------------------------------------------------------
# Fixtures — raw diff strings
# ---------------------------------------------------------------------------

SIMPLE_DIFF = """\
diff --git a/foo.py b/foo.py
--- a/foo.py
+++ b/foo.py
@@ -1,3 +1,5 @@
 def hello():
+    password = 'hunter2'
+    print(password)
     return 1
-    pass
"""

MULTI_HUNK_DIFF = """\
diff --git a/bar.py b/bar.py
--- a/bar.py
+++ b/bar.py
@@ -1,4 +1,5 @@
 class Foo:
+    # TODO: implement
     pass


@@ -10,3 +11,4 @@
 def baz():
+    x = 1
     return x
"""

EMPTY_DIFF = ""

BINARY_DIFF = """\
diff --git a/image.png b/image.png
Binary files a/image.png and b/image.png differ
"""

RENAME_DIFF = """\
diff --git a/old.py b/new.py
similarity index 85%
rename from old.py
rename to new.py
--- a/old.py
+++ b/new.py
@@ -1,2 +1,3 @@
 x = 1
+y = 2
 z = 3
"""


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestParseDiff:
    def test_simple_diff_extracts_added_lines(self):
        files = parse_diff(SIMPLE_DIFF)
        assert len(files) == 1
        f: FileDiff = files[0]
        # FileDiff.path holds the filename
        assert "foo.py" in f.path
        assert len(f.added_lines) == 2

    def test_added_line_content_correct(self):
        files = parse_diff(SIMPLE_DIFF)
        lines_dict = dict(files[0].added_lines)
        assert any("password" in code for code in lines_dict.values())

    def test_deleted_lines_not_in_added(self):
        files = parse_diff(SIMPLE_DIFF)
        # "pass" was on a deleted line; it must NOT appear in added_lines
        added_codes = [code for _, code in files[0].added_lines]
        assert not any(code.strip() == "pass" for code in added_codes)

    def test_multi_hunk_both_hunks_captured(self):
        files = parse_diff(MULTI_HUNK_DIFF)
        assert len(files) == 1
        f = files[0]
        # Two hunks → two added lines
        assert len(f.added_lines) == 2

    def test_empty_diff_returns_empty_list(self):
        files = parse_diff(EMPTY_DIFF)
        assert files == []

    def test_binary_diff_no_added_lines(self):
        files = parse_diff(BINARY_DIFF)
        for f in files:
            assert f.added_lines == []

    def test_rename_diff_uses_new_filename(self):
        files = parse_diff(RENAME_DIFF)
        # Parser reads "+++ b/new.py" so path should be "new.py"
        paths = [f.path for f in files]
        assert any("new.py" in p for p in paths)

    def test_line_numbers_are_positive(self):
        files = parse_diff(SIMPLE_DIFF + MULTI_HUNK_DIFF)
        for f in files:
            for ln, _ in f.added_lines:
                assert ln > 0, f"Line number must be positive, got {ln}"

    def test_language_detected_for_python(self):
        files = parse_diff(SIMPLE_DIFF)
        assert files[0].language == "python"

    def test_removed_lines_captured(self):
        files = parse_diff(SIMPLE_DIFF)
        # "    pass" was removed
        assert len(files[0].removed_lines) >= 1

    def test_multiple_files_in_diff(self):
        combined = SIMPLE_DIFF + "\n" + MULTI_HUNK_DIFF
        files = parse_diff(combined)
        assert len(files) == 2
        paths = {f.path for f in files}
        assert any("foo.py" in p for p in paths)
        assert any("bar.py" in p for p in paths)
