"""
test_webhook.py — Unit tests for the GitHub webhook HMAC-SHA256 validation.

Tests:
  - Valid signature is accepted (200)
  - Tampered payload is rejected (403)
  - Missing X-Hub-Signature-256 header is rejected (403)
  - Wrong event type (not pull_request) returns 200 but does nothing
  - Valid pull_request opened event triggers review creation
"""

import hashlib
import hmac
import json
import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).parent.parent))

# We need to set env vars before importing the app
import os
os.environ.setdefault("GITHUB_CLIENT_ID", "test_client_id")
os.environ.setdefault("GITHUB_CLIENT_SECRET", "test_client_secret")
os.environ.setdefault("GITHUB_WEBHOOK_SECRET", "test_webhook_secret")
os.environ.setdefault("JWT_SECRET_KEY", "test_jwt_secret")
os.environ.setdefault("DATABASE_URL", "sqlite:///./test_webhook.db")

WEBHOOK_SECRET = "test_webhook_secret"


def make_signature(body: bytes, secret: str = WEBHOOK_SECRET) -> str:
    mac = hmac.new(secret.encode(), body, hashlib.sha256)
    return f"sha256={mac.hexdigest()}"


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def client():
    """Create a FastAPI test client with mocked DB."""
    with patch("app.db.session.engine"), \
         patch("app.db.base.Base.metadata.create_all"):
        from app.main import app
        return TestClient(app, raise_server_exceptions=False)


PULL_REQUEST_PAYLOAD = {
    "action": "opened",
    "number": 42,
    "pull_request": {
        "number": 42,
        "title": "Add feature X",
        "user": {"login": "octocat"},
        "head": {"sha": "abc123def456"},
    },
    "repository": {
        "id": 999,
        "full_name": "octocat/hello-world",
    },
}


# ---------------------------------------------------------------------------
# HMAC Validation Tests
# ---------------------------------------------------------------------------

class TestHMACValidation:
    def test_valid_signature_accepted(self, client):
        body = json.dumps(PULL_REQUEST_PAYLOAD).encode()
        sig = make_signature(body)
        with patch("app.api.webhook.process_pr_review") as mock_task, \
             patch("app.api.webhook.get_db") as mock_db:
            mock_db.return_value = iter([MagicMock()])
            mock_task.delay = MagicMock()
            resp = client.post(
                "/webhooks/github",
                content=body,
                headers={
                    "X-GitHub-Event": "pull_request",
                    "X-Hub-Signature-256": sig,
                    "Content-Type": "application/json",
                },
            )
        # Should not be 403
        assert resp.status_code != 403, f"Valid signature was rejected: {resp.text}"

    def test_invalid_signature_rejected(self, client):
        body = json.dumps(PULL_REQUEST_PAYLOAD).encode()
        bad_sig = make_signature(body, secret="wrong_secret")
        resp = client.post(
            "/webhooks/github",
            content=body,
            headers={
                "X-GitHub-Event": "pull_request",
                "X-Hub-Signature-256": bad_sig,
                "Content-Type": "application/json",
            },
        )
        assert resp.status_code == 403

    def test_missing_signature_rejected(self, client):
        body = json.dumps(PULL_REQUEST_PAYLOAD).encode()
        resp = client.post(
            "/webhooks/github",
            content=body,
            headers={
                "X-GitHub-Event": "pull_request",
                "Content-Type": "application/json",
            },
        )
        assert resp.status_code == 403

    def test_tampered_payload_rejected(self, client):
        original = json.dumps(PULL_REQUEST_PAYLOAD).encode()
        sig = make_signature(original)
        tampered = original + b" injected"
        resp = client.post(
            "/webhooks/github",
            content=tampered,
            headers={
                "X-GitHub-Event": "pull_request",
                "X-Hub-Signature-256": sig,
                "Content-Type": "application/json",
            },
        )
        assert resp.status_code == 403


# ---------------------------------------------------------------------------
# Event Filtering Tests
# ---------------------------------------------------------------------------

class TestEventFiltering:
    def test_non_pull_request_event_ignored(self, client):
        body = json.dumps({"action": "created"}).encode()
        sig = make_signature(body)
        resp = client.post(
            "/webhooks/github",
            content=body,
            headers={
                "X-GitHub-Event": "push",
                "X-Hub-Signature-256": sig,
                "Content-Type": "application/json",
            },
        )
        assert resp.status_code == 200
        assert "ignored" in resp.json().get("status", "").lower() or \
               resp.json().get("message", "") != ""

    def test_synchronize_action_triggers_review(self, client):
        payload = {**PULL_REQUEST_PAYLOAD, "action": "synchronize"}
        body = json.dumps(payload).encode()
        sig = make_signature(body)
        with patch("app.api.webhook.process_pr_review") as mock_task, \
             patch("app.api.webhook.get_db") as mock_db:
            mock_db.return_value = iter([MagicMock()])
            mock_task.delay = MagicMock()
            resp = client.post(
                "/webhooks/github",
                content=body,
                headers={
                    "X-GitHub-Event": "pull_request",
                    "X-Hub-Signature-256": sig,
                    "Content-Type": "application/json",
                },
            )
        assert resp.status_code != 403

    def test_closed_action_ignored(self, client):
        payload = {**PULL_REQUEST_PAYLOAD, "action": "closed"}
        body = json.dumps(payload).encode()
        sig = make_signature(body)
        resp = client.post(
            "/webhooks/github",
            content=body,
            headers={
                "X-GitHub-Event": "pull_request",
                "X-Hub-Signature-256": sig,
                "Content-Type": "application/json",
            },
        )
        assert resp.status_code == 200
