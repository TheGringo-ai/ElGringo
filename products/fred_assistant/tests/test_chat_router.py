"""Tests for chat router — HTTP endpoint integration tests."""

import os
import pytest
from unittest.mock import patch, AsyncMock

os.environ["FRED_DB_PATH"] = ":memory:"

from fastapi.testclient import TestClient

import products.fred_assistant.database as db
from products.fred_assistant.server import app
from products.fred_assistant.services import assistant

client = TestClient(app)


# ── GET /chat/history ────────────────────────────────────────────

def test_get_history_empty():
    resp = client.get("/chat/history")
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


def test_get_history_with_messages():
    assistant.save_message("user", "Hello")
    assistant.save_message("assistant", "Hi there!")
    resp = client.get("/chat/history")
    assert resp.status_code == 200
    messages = resp.json()
    assert len(messages) >= 2
    roles = [m["role"] for m in messages]
    assert "user" in roles
    assert "assistant" in roles


# ── POST /chat ───────────────────────────────────────────────────

def test_chat_returns_response():
    with patch.object(assistant, "chat", new_callable=AsyncMock, return_value="Mocked reply"):
        resp = client.post("/chat", json={"message": "What are my tasks?"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["role"] == "assistant"
    assert data["content"] == "Mocked reply"


def test_chat_with_persona():
    with patch.object(assistant, "chat", new_callable=AsyncMock, return_value="Coach reply") as mock_chat:
        resp = client.post("/chat", json={"message": "How am I doing?", "persona": "coach"})
    assert resp.status_code == 200
    mock_chat.assert_called_once_with("How am I doing?", "coach")


def test_chat_missing_message():
    resp = client.post("/chat", json={})
    assert resp.status_code == 422


def test_chat_empty_message():
    # Empty string is still a valid string per Pydantic, but let's test the behavior
    with patch.object(assistant, "chat", new_callable=AsyncMock, return_value=""):
        resp = client.post("/chat", json={"message": ""})
    assert resp.status_code == 200


# ── DELETE /chat/history ─────────────────────────────────────────

def test_clear_history():
    assistant.save_message("user", "Test message")
    resp = client.delete("/chat/history")
    assert resp.status_code == 204
    # Verify cleared
    history = client.get("/chat/history").json()
    assert len(history) == 0


# ── POST /chat/stream ───────────────────────────────────────────

def test_stream_chat_returns_sse():
    async def mock_stream(message, persona):
        yield {"type": "token", "data": "Hello from stream"}

    with patch.object(assistant, "stream_chat", side_effect=mock_stream):
        resp = client.post("/chat/stream", json={"message": "Stream test"})
    assert resp.status_code == 200
    assert "text/event-stream" in resp.headers["content-type"]
    # SSE data should contain our token
    assert "Hello from stream" in resp.text


def test_stream_chat_missing_message():
    resp = client.post("/chat/stream", json={})
    assert resp.status_code == 422
