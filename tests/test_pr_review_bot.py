"""
Tests for the El Gringo PR Review Bot product.
"""

import hashlib
import hmac
import json

import pytest
from fastapi.testclient import TestClient

from products import list_products, get_product
from products.pr_review_bot.auth import verify_webhook_signature
from products.pr_review_bot.models import ReviewVerdict
from products.pr_review_bot.reviewer import PRReviewer


# ---------------------------------------------------------------------------
# Product registry
# ---------------------------------------------------------------------------

class TestProductRegistry:
    def test_discovers_all_products(self):
        products = list_products()
        names = {p.name for p in products}
        assert "pr-review-bot" in names
        assert "code-audit" in names
        assert "fred-api" in names
        assert "maintenance-advisor" in names

    def test_pr_review_bot_is_active(self):
        p = get_product("pr-review-bot")
        assert p is not None
        assert p.status == "active"
        assert p.is_active

    def test_code_audit_is_active(self):
        p = get_product("code-audit")
        assert p is not None
        assert p.status == "active"
        assert p.is_active

    def test_fred_api_is_active(self):
        p = get_product("fred-api")
        assert p is not None
        assert p.status == "active"
        assert p.is_active

    def test_maintenance_advisor_is_active(self):
        p = get_product("maintenance-advisor")
        assert p is not None
        assert p.status == "active"
        assert p.is_active

    def test_unknown_product_returns_none(self):
        assert get_product("nonexistent") is None


# ---------------------------------------------------------------------------
# Webhook signature verification
# ---------------------------------------------------------------------------

class TestWebhookSignature:
    SECRET = "test-webhook-secret"

    def _sign(self, payload: bytes) -> str:
        return "sha256=" + hmac.new(
            self.SECRET.encode(), payload, hashlib.sha256
        ).hexdigest()

    def test_valid_signature(self):
        payload = b'{"action":"opened"}'
        sig = self._sign(payload)
        assert verify_webhook_signature(payload, sig, self.SECRET)

    def test_invalid_signature(self):
        payload = b'{"action":"opened"}'
        assert not verify_webhook_signature(payload, "sha256=bad", self.SECRET)

    def test_missing_prefix(self):
        payload = b'{"action":"opened"}'
        raw = hmac.new(self.SECRET.encode(), payload, hashlib.sha256).hexdigest()
        assert not verify_webhook_signature(payload, raw, self.SECRET)


# ---------------------------------------------------------------------------
# Review result parsing
# ---------------------------------------------------------------------------

class TestReviewParsing:
    def test_parses_valid_json(self):
        raw = json.dumps({
            "verdict": "REQUEST_CHANGES",
            "summary": "Found a bug on line 42.",
            "inline_comments": [
                {"path": "app.py", "line": 42, "body": "Possible null dereference"},
            ],
            "confidence": 0.85,
        })
        result = PRReviewer._parse_review(raw, agents_used=["claude", "gpt4"])
        assert result.verdict == ReviewVerdict.REQUEST_CHANGES
        assert "bug" in result.summary
        assert len(result.inline_comments) == 1
        assert result.inline_comments[0].path == "app.py"
        assert result.inline_comments[0].line == 42
        assert result.confidence == 0.85
        assert result.agents_used == ["claude", "gpt4"]

    def test_parses_json_in_code_fence(self):
        raw = '```json\n{"verdict": "APPROVE", "summary": "LGTM", "inline_comments": [], "confidence": 0.95}\n```'
        result = PRReviewer._parse_review(raw)
        assert result.verdict == ReviewVerdict.APPROVE
        assert result.summary == "LGTM"

    def test_fallback_on_invalid_json(self):
        raw = "This is not JSON at all, just a text review."
        result = PRReviewer._parse_review(raw, confidence_fallback=0.3)
        assert result.verdict == ReviewVerdict.COMMENT
        assert "not JSON" in result.summary
        assert result.confidence == 0.3

    def test_unknown_verdict_defaults_to_comment(self):
        raw = json.dumps({"verdict": "MAYBE", "summary": "Unsure", "inline_comments": []})
        result = PRReviewer._parse_review(raw)
        assert result.verdict == ReviewVerdict.COMMENT


# ---------------------------------------------------------------------------
# FastAPI endpoints
# ---------------------------------------------------------------------------

class TestServer:
    @pytest.fixture
    def client(self):
        from products.pr_review_bot.server import app
        return TestClient(app)

    def test_health(self, client):
        resp = client.get("/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"
        assert data["product"] == "pr-review-bot"

    def test_webhook_rejects_bad_signature(self, client, monkeypatch):
        # Set a webhook secret so signature checking is enforced
        monkeypatch.setenv("GITHUB_WEBHOOK_SECRET", "test-secret")
        # Re-init settings
        from products.pr_review_bot import config as cfg
        from products.pr_review_bot import server
        server._settings = cfg.PRReviewBotSettings()

        resp = client.post(
            "/webhook",
            content=b'{"action":"opened"}',
            headers={
                "X-Hub-Signature-256": "sha256=invalid",
                "X-GitHub-Event": "pull_request",
            },
        )
        assert resp.status_code == 401

    def test_webhook_ping(self, client, monkeypatch):
        monkeypatch.delenv("GITHUB_WEBHOOK_SECRET", raising=False)
        from products.pr_review_bot import config as cfg
        from products.pr_review_bot import server
        server._settings = cfg.PRReviewBotSettings()

        resp = client.post(
            "/webhook",
            json={},
            headers={"X-GitHub-Event": "ping"},
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "pong"

    def test_webhook_ignores_non_pr_events(self, client, monkeypatch):
        monkeypatch.delenv("GITHUB_WEBHOOK_SECRET", raising=False)
        from products.pr_review_bot import config as cfg
        from products.pr_review_bot import server
        server._settings = cfg.PRReviewBotSettings()

        resp = client.post(
            "/webhook",
            json={},
            headers={"X-GitHub-Event": "issues"},
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "ignored"
