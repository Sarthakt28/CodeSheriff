"""
conftest.py — Shared pytest fixtures for all CodeSheriff backend tests.

This file is loaded automatically by pytest before any test module.
Order of operations:
  1. os.environ patching (MUST happen before any app import)
  2. Fixture definitions (available to all test files)

Fixtures provided:
  - env_vars      : sets required env vars; session-scoped (once per run)
  - mock_db       : MagicMock database session; function-scoped (fresh per test)
  - mock_review   : a fake PRReview ORM object with realistic fields
  - sample_diff   : a realistic unified diff string for PR review tests
"""

from __future__ import annotations
import os
import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest

# ── Add backend/ to sys.path so `app` package is importable ──────────────────
sys.path.insert(0, str(Path(__file__).parent.parent))

# ── Set required env vars BEFORE any app import ──────────────────────────────
# These override whatever is in .env so tests are hermetic (no real credentials).
_TEST_ENV = {
    "GITHUB_CLIENT_ID":      "test_client_id",
    "GITHUB_CLIENT_SECRET":  "test_client_secret",
    "GITHUB_WEBHOOK_SECRET": "test_webhook_secret_32chars_long",
    "JWT_SECRET_KEY":        "test_jwt_secret_key_for_pytest",
    "DATABASE_URL":          "sqlite:///./test_codesheriff.db",
    "REDIS_URL":             "redis://localhost:6379/0",
    "USE_ML_REVIEWER":       "false",
    "ALLOWED_ORIGINS":       "http://localhost:5173",
}

for key, val in _TEST_ENV.items():
    os.environ.setdefault(key, val)


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture(scope="session")
def env_vars():
    """Expose the test env dict to any test that needs to inspect it."""
    return _TEST_ENV


@pytest.fixture
def mock_db():
    """
    A MagicMock that quacks like a SQLAlchemy Session.

    Supports:
      db.query(...).filter(...).first()   → returns None by default
      db.add(obj)
      db.commit()
      db.refresh(obj)
      db.close()
    """
    db = MagicMock()
    db.query.return_value.filter.return_value.first.return_value = None
    db.query.return_value.get.return_value = None
    return db


@pytest.fixture
def mock_review():
    """
    A realistic fake PRReview object with all fields the review task accesses.
    """
    review = MagicMock()
    review.id = 1
    review.pr_number = 42
    review.pr_title = "Add login feature"
    review.pr_author = "octocat"
    review.commit_sha = "abc123def456abc123def456abc123def456abc1"
    review.status = "pending"
    review.total_issues = 0
    review.summary = ""

    # Nested repo + user
    review.repository = MagicMock()
    review.repository.id = 10
    review.repository.full_name = "octocat/hello-world"
    review.repository.github_repo_id = 999

    review.repository.user = MagicMock()
    review.repository.user.id = 1
    review.repository.user.github_username = "octocat"
    review.repository.user.access_token = "ghs_test_access_token_placeholder"

    return review


@pytest.fixture
def sample_diff() -> str:
    """
    A realistic unified diff for a small Python change.
    Contains: a hardcoded password (secrets rule) + a TODO (style rule).
    Used by review pipeline tests to assert comments are generated.
    """
    return """\
diff --git a/app/auth.py b/app/auth.py
--- a/app/auth.py
+++ b/app/auth.py
@@ -1,5 +1,8 @@
 import os
+
+# TODO: move to env
+DB_PASSWORD = 'hunter2'
+
 def get_connection():
-    pass
+    return connect(DB_PASSWORD)
"""


@pytest.fixture
def mock_db_with_review(mock_db, mock_review):
    """
    A mock DB that returns mock_review when queried.
    Use when you need the review task to find a review in the DB.
    """
    mock_db.query.return_value.filter.return_value.first.return_value = mock_review
    mock_db.query.return_value.get.return_value = mock_review
    return mock_db
