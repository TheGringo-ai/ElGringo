"""Tests for assistant service — chat, context building, action loop, fallbacks."""

import os
import pytest
from unittest.mock import patch, AsyncMock, MagicMock
from datetime import date

os.environ["FRED_DB_PATH"] = ":memory:"

from products.fred_assistant.services import assistant, task_service


# ── save_message / get_history / clear_history ────────────────────

def test_save_and_get_history():
    assistant.save_message("user", "Hello Fred")
    assistant.save_message("assistant", "Hey there!")
    history = assistant.get_history(limit=10)
    assert len(history) == 2
    assert history[0]["role"] == "user"
    assert history[1]["role"] == "assistant"


def test_get_history_respects_limit():
    for i in range(5):
        assistant.save_message("user", f"Message {i}")
    history = assistant.get_history(limit=3)
    assert len(history) == 3


def test_clear_history():
    assistant.save_message("user", "Temp message")
    assistant.clear_history()
    history = assistant.get_history()
    assert len(history) == 0


def test_save_message_with_persona():
    assistant.save_message("user", "Coach question", persona="coach")
    history = assistant.get_history(limit=1)
    assert history[0]["persona"] == "coach"


# ── _build_context ───────────────────────────────────────────────

def test_build_context_includes_date():
    ctx = assistant._build_context()
    today_str = date.today().strftime("%A, %B %d, %Y")
    assert today_str in ctx


def test_build_context_includes_stats():
    ctx = assistant._build_context()
    assert "Active tasks:" in ctx
    assert "In progress:" in ctx
    assert "Streak:" in ctx


def test_build_context_includes_boards():
    task_service.create_board("Test Board")
    ctx = assistant._build_context()
    # Boards section with seeded + new board
    assert "Boards" in ctx


def test_build_context_coach_persona():
    # Coach persona should include goals section attempt
    ctx = assistant._build_context(persona="coach")
    assert "Current Status" in ctx


# ── _build_system_prompt ─────────────────────────────────────────

def test_build_system_prompt_fred():
    prompt = assistant._build_system_prompt("fred")
    assert "Fred" in prompt
    # Should include tool definitions
    assert "ACTION:" in prompt or "action" in prompt.lower()


def test_build_system_prompt_coach():
    prompt = assistant._build_system_prompt("coach")
    assert "Coach" in prompt or "coach" in prompt.lower()


def test_build_system_prompt_unknown_defaults_to_fred():
    prompt = assistant._build_system_prompt("unknown_persona")
    assert "Fred" in prompt


# ── _fallback_response ───────────────────────────────────────────

def test_fallback_tasks():
    task_service.create_task({"title": "Important task", "status": "in_progress"})
    resp = assistant._fallback_response("what should I work on?")
    assert "Important task" in resp


def test_fallback_status():
    resp = assistant._fallback_response("how am I doing?")
    assert "active tasks" in resp


def test_fallback_remember():
    resp = assistant._fallback_response("remember that I like Python")
    assert "memory" in resp.lower() or "remember" in resp.lower()


def test_fallback_generic():
    resp = assistant._fallback_response("tell me a joke")
    assert "offline" in resp.lower() or "unavailable" in resp.lower()


def test_fallback_empty_task_list():
    resp = assistant._fallback_response("what are my tasks?")
    assert "empty" in resp.lower() or "task" in resp.lower()


# ── _format_result_line ──────────────────────────────────────────

def test_format_result_line_success_with_message():
    line = assistant._format_result_line({"action": "create_task", "success": True, "message": "Created task 'Test'"})
    assert "create_task" in line
    assert "OK" in line
    assert "Created task" in line


def test_format_result_line_failure():
    line = assistant._format_result_line({"action": "delete_task", "success": False, "error": "Not found"})
    assert "FAILED" in line
    assert "Not found" in line


def test_format_result_line_no_message():
    line = assistant._format_result_line({"action": "list_tasks", "success": True})
    assert "list_tasks" in line
    assert "OK" in line


# ── chat (mocked LLM) ───────────────────────────────────────────

@pytest.mark.asyncio
async def test_chat_with_mocked_llm():
    with patch.object(assistant, "_llm_response", new_callable=AsyncMock, return_value="Here's your answer!"):
        reply = await assistant.chat("What are my tasks?")
    assert reply == "Here's your answer!"


@pytest.mark.asyncio
async def test_chat_stores_messages():
    assistant.clear_history()
    with patch.object(assistant, "_llm_response", new_callable=AsyncMock, return_value="Reply text"):
        await assistant.chat("Test message")
    history = assistant.get_history()
    roles = [m["role"] for m in history]
    assert "user" in roles
    assert "assistant" in roles


@pytest.mark.asyncio
async def test_chat_fallback_on_llm_failure():
    with patch.object(assistant, "_llm_response", new_callable=AsyncMock, return_value=""):
        reply = await assistant.chat("what are my tasks?")
    # Fallback response should mention tasks or offline
    assert reply != ""


@pytest.mark.asyncio
async def test_chat_with_persona():
    with patch.object(assistant, "_llm_response", new_callable=AsyncMock, return_value="Coach says hi"):
        reply = await assistant.chat("How am I doing?", persona="coach")
    assert reply == "Coach says hi"


# ── get_chat_messages ────────────────────────────────────────────

def test_get_chat_messages_structure():
    assistant.save_message("user", "Hello")
    messages = assistant.get_chat_messages()
    # Should have system prompt(s) + context + history
    assert messages[0]["role"] == "system"
    # At least system + context + 1 history message
    assert len(messages) >= 3


def test_get_chat_messages_custom_prompt():
    messages = assistant.get_chat_messages(system_prompt="Custom system prompt")
    assert messages[0]["content"] == "Custom system prompt"


# ── get_today_briefing ───────────────────────────────────────────

def test_get_today_briefing_none():
    assert assistant.get_today_briefing() is None
