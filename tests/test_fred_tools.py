"""
Fred Tools Tests
================
Unit tests for the fred_tools action parsing, path validation, and execution.
"""

import os
import sys
import pytest
import tempfile
from unittest.mock import patch, MagicMock, AsyncMock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from products.fred_assistant.services.fred_tools import (
    parse_actions,
    parse_params,
    strip_action_lines,
    validate_path,
    get_tool_definitions,
    TOOLS,
    MAX_ROUNDS,
)


# =============================================================================
# Parsing Tests
# =============================================================================

class TestParseParams:
    def test_string_param(self):
        result = parse_params('title="Hello World"')
        assert result == {"title": "Hello World"}

    def test_integer_param(self):
        result = parse_params("priority=1")
        assert result == {"priority": 1}

    def test_float_param(self):
        result = parse_params("score=3.5")
        assert result == {"score": 3.5}

    def test_boolean_param(self):
        result = parse_params("flag=true")
        assert result == {"flag": True}
        result = parse_params("flag=false")
        assert result == {"flag": False}

    def test_array_param(self):
        result = parse_params('items=["a","b","c"]')
        assert result == {"items": ["a", "b", "c"]}

    def test_multiple_params(self):
        result = parse_params('title="Review PR", board="fredai", priority=1')
        assert result == {"title": "Review PR", "board": "fredai", "priority": 1}

    def test_empty_string(self):
        result = parse_params("")
        assert result == {}

    def test_mixed_types(self):
        result = parse_params('name="test", count=5, active=true')
        assert result == {"name": "test", "count": 5, "active": True}


class TestParseActions:
    def test_single_action(self):
        text = 'I will create that task for you.\nACTION: create_task(title="Review deployment", board="fredai")'
        actions = parse_actions(text)
        assert len(actions) == 1
        assert actions[0]["name"] == "create_task"
        assert actions[0]["params"]["title"] == "Review deployment"
        assert actions[0]["params"]["board"] == "fredai"

    def test_multiple_actions(self):
        text = (
            "Let me do both.\n"
            'ACTION: create_task(title="Task one", board="work")\n'
            'ACTION: remember(category="preferences", key="deploy day", value="Sundays")\n'
        )
        actions = parse_actions(text)
        assert len(actions) == 2
        assert actions[0]["name"] == "create_task"
        assert actions[1]["name"] == "remember"
        assert actions[1]["params"]["value"] == "Sundays"

    def test_no_actions(self):
        text = "Just a regular response with no actions."
        actions = parse_actions(text)
        assert len(actions) == 0

    def test_action_with_no_params(self):
        text = "ACTION: accountability_check()"
        actions = parse_actions(text)
        assert len(actions) == 1
        assert actions[0]["name"] == "accountability_check"
        assert actions[0]["params"] == {}

    def test_action_with_numeric_param(self):
        text = 'ACTION: git_log(project="FredAI", count=5)'
        actions = parse_actions(text)
        assert len(actions) == 1
        assert actions[0]["params"]["count"] == 5

    def test_action_in_middle_of_text(self):
        text = (
            "Sure, let me check that for you.\n"
            'ACTION: git_status(project="FredAI")\n'
            "I'll let you know what I find."
        )
        actions = parse_actions(text)
        assert len(actions) == 1
        assert actions[0]["name"] == "git_status"

    def test_action_with_parens_in_string(self):
        """Verify the regex handles parentheses inside quoted string values."""
        text = 'ACTION: create_task(title="Fix bug (urgent)", board="work")'
        actions = parse_actions(text)
        assert len(actions) == 1
        assert actions[0]["params"]["title"] == "Fix bug (urgent)"
        assert actions[0]["params"]["board"] == "work"

    def test_action_with_multiple_parens_in_strings(self):
        text = 'ACTION: remember(key="deploy (prod)", value="Sundays (morning only)")'
        actions = parse_actions(text)
        assert len(actions) == 1
        assert actions[0]["params"]["key"] == "deploy (prod)"
        assert actions[0]["params"]["value"] == "Sundays (morning only)"


class TestStripActionLines:
    def test_strips_action_lines(self):
        text = (
            "I'll create that task.\n"
            'ACTION: create_task(title="Test", board="work")\n'
            "Done!"
        )
        result = strip_action_lines(text)
        assert "ACTION:" not in result
        assert "I'll create that task." in result
        assert "Done!" in result

    def test_preserves_non_action_lines(self):
        text = "Line one\nLine two\nLine three"
        result = strip_action_lines(text)
        assert result == text

    def test_handles_multiple_action_lines(self):
        text = (
            "Working on it.\n"
            'ACTION: create_task(title="A")\n'
            'ACTION: create_task(title="B")\n'
            "All done."
        )
        result = strip_action_lines(text)
        assert result.count("ACTION:") == 0
        assert "Working on it." in result
        assert "All done." in result


# =============================================================================
# Path Validation Tests
# =============================================================================

class TestPathValidation:
    def test_allowed_development_path(self):
        path = "~/Development/Projects/test.py"
        resolved = validate_path(path)
        assert resolved.startswith(os.path.expanduser("~/Development"))

    def test_allowed_tmp_path(self):
        resolved = validate_path("/tmp/test.txt")
        # macOS resolves /tmp -> /private/tmp
        assert resolved.startswith("/tmp") or resolved.startswith("/private/tmp")

    def test_blocked_ssh_path(self):
        with pytest.raises(ValueError, match="restricted"):
            validate_path("~/.ssh/id_rsa")

    def test_blocked_gnupg_path(self):
        with pytest.raises(ValueError, match="restricted"):
            validate_path("~/.gnupg/keys")

    def test_blocked_aws_path(self):
        with pytest.raises(ValueError, match="restricted"):
            validate_path("~/.aws/credentials")

    def test_blocked_etc_path(self):
        with pytest.raises(ValueError, match="denied|restricted|outside"):
            validate_path("/etc/passwd")

    def test_blocked_system_path(self):
        with pytest.raises(ValueError, match="restricted"):
            validate_path("/System/Library/something")

    def test_outside_allowed_dirs(self):
        with pytest.raises(ValueError, match="outside allowed"):
            validate_path("/opt/something")

    def test_symlink_traversal_blocked(self):
        with pytest.raises(ValueError):
            validate_path("/var/log/system.log")


# =============================================================================
# Tool Registry Tests
# =============================================================================

class TestToolRegistry:
    def test_all_tools_registered(self):
        assert len(TOOLS) == 68

    def test_all_tools_have_required_keys(self):
        for name, tool in TOOLS.items():
            assert "fn" in tool, f"Tool {name} missing 'fn'"
            assert "async" in tool, f"Tool {name} missing 'async'"
            assert "desc" in tool, f"Tool {name} missing 'desc'"
            assert "params" in tool, f"Tool {name} missing 'params'"

    def test_all_fns_are_callable(self):
        for name, tool in TOOLS.items():
            assert callable(tool["fn"]), f"Tool {name} fn not callable"

    def test_tool_definitions_output(self):
        defs = get_tool_definitions()
        assert "Available Actions" in defs
        assert "create_task" in defs
        assert "delete_task" in defs
        assert "search_tasks" in defs
        assert "remember" in defs
        assert "forget" in defs
        assert "update_event" in defs
        assert "delete_event" in defs
        assert "delete_goal" in defs
        assert "generate_review" in defs
        assert "schedule_content" in defs
        assert "git_status" in defs
        assert "read_file" in defs
        assert "accountability_check" in defs
        assert "find_revenue" in defs
        # Repo Intelligence
        assert "analyze_repo" in defs
        assert "create_repo_tasks" in defs
        assert "repo_roadmap" in defs
        assert "repo_health" in defs
        assert "Repo Intelligence" in defs
        # Platform Services
        assert "Platform Services" in defs
        assert "audit_security" in defs
        assert "generate_tests" in defs
        assert "generate_readme" in defs
        assert "platform_status" in defs
        # Workflows
        assert "Workflows" in defs
        assert "full_project_review" in defs
        assert "ship_ready_check" in defs
        assert "bootstrap_project" in defs

    def test_max_rounds_is_5(self):
        assert MAX_ROUNDS == 5

    def test_expected_tool_names(self):
        expected = {
            # Tasks (7)
            "create_task", "update_task", "complete_task", "delete_task",
            "list_tasks", "search_tasks", "create_todo_list",
            # Memory (3)
            "remember", "search_memory", "forget",
            # Calendar (4)
            "create_event", "list_events", "update_event", "delete_event",
            # Goals (6)
            "create_goal", "update_goal", "delete_goal",
            "accountability_check", "find_revenue", "generate_review",
            # Git (5)
            "review_project", "list_projects", "git_status", "git_log", "git_diff",
            # Files (4)
            "read_file", "write_file", "list_files", "search_files",
            # Content (4)
            "generate_content", "schedule_content", "approve_content", "publish_content",
            # Focus Mode (3)
            "start_focus", "end_focus", "focus_stats",
            # Briefing & Shutdown (2)
            "daily_briefing", "daily_shutdown",
            # CRM (6)
            "add_lead", "update_lead", "log_outreach", "schedule_followup",
            "list_leads", "pipeline_summary",
            # CEO Lens (2)
            "ceo_lens", "log_metric",
            # Inbox (2)
            "inbox", "inbox_summary",
            # Playbooks & Autopilot (5)
            "run_playbook", "list_playbooks", "create_playbook",
            "run_autopilot", "list_autopilots",
            # Repo Intelligence (4)
            "analyze_repo", "create_repo_tasks", "repo_roadmap", "repo_health",
            # Platform Services (8)
            "audit_security", "audit_code", "generate_tests", "analyze_tests",
            "generate_readme", "generate_api_docs", "generate_architecture",
            "platform_status",
            # Workflows (3)
            "full_project_review", "ship_ready_check", "bootstrap_project",
        }
        assert set(TOOLS.keys()) == expected
        assert len(expected) == 68

    def test_update_task_mentions_board_in_params(self):
        """Verify update_task documents the board/board_id move capability."""
        desc = TOOLS["update_task"]["params"]
        assert "board" in desc


# =============================================================================
# Executor Tests — Tasks
# =============================================================================

class TestTaskExecutors:
    @patch("products.fred_assistant.services.fred_tools.task_service")
    def test_create_task(self, mock_ts):
        mock_ts.create_task.return_value = {"id": "abc123", "title": "Test task", "board_id": "work"}
        from products.fred_assistant.services.fred_tools import _exec_create_task
        result = _exec_create_task({"title": "Test task", "board": "work"})
        assert result["success"] is True
        assert "Test task" in result["message"]
        mock_ts.create_task.assert_called_once()

    @patch("products.fred_assistant.services.fred_tools.task_service")
    def test_complete_task(self, mock_ts):
        mock_ts.update_task.return_value = {"id": "abc", "title": "Done task", "status": "done"}
        from products.fred_assistant.services.fred_tools import _exec_complete_task
        result = _exec_complete_task({"task_id": "abc"})
        assert result["success"] is True
        mock_ts.update_task.assert_called_with("abc", {"status": "done"})

    @patch("products.fred_assistant.services.fred_tools.task_service")
    def test_complete_task_missing_id(self, mock_ts):
        from products.fred_assistant.services.fred_tools import _exec_complete_task
        result = _exec_complete_task({})
        assert result["success"] is False
        assert "required" in result["error"]

    @patch("products.fred_assistant.services.fred_tools.task_service")
    def test_delete_task(self, mock_ts):
        mock_ts.get_task.return_value = {"id": "abc", "title": "Old task"}
        from products.fred_assistant.services.fred_tools import _exec_delete_task
        result = _exec_delete_task({"task_id": "abc"})
        assert result["success"] is True
        assert "Old task" in result["message"]
        mock_ts.delete_task.assert_called_with("abc")

    @patch("products.fred_assistant.services.fred_tools.task_service")
    def test_delete_task_not_found(self, mock_ts):
        mock_ts.get_task.return_value = None
        from products.fred_assistant.services.fred_tools import _exec_delete_task
        result = _exec_delete_task({"task_id": "nope"})
        assert result["success"] is False

    @patch("products.fred_assistant.services.fred_tools.task_service")
    def test_list_tasks(self, mock_ts):
        mock_ts.list_tasks.return_value = [
            {"id": "1", "title": "Task A", "priority": 1, "status": "todo", "due_date": None, "board_id": "work"},
            {"id": "2", "title": "Task B", "priority": 2, "status": "in_progress", "due_date": "2026-02-22", "board_id": "fredai"},
        ]
        from products.fred_assistant.services.fred_tools import _exec_list_tasks
        result = _exec_list_tasks({"board": "work"})
        assert result["success"] is True
        assert result["count"] == 2

    @patch("products.fred_assistant.services.fred_tools.task_service")
    def test_create_todo_list(self, mock_ts):
        mock_ts.create_task.side_effect = lambda d: {"id": "x", "title": d["title"]}
        from products.fred_assistant.services.fred_tools import _exec_create_todo_list
        result = _exec_create_todo_list({
            "title": "Launch checklist",
            "items": ["Design landing page", "Set up Stripe", "Write docs"],
            "board": "work",
        })
        assert result["success"] is True
        assert result["count"] == 3
        assert mock_ts.create_task.call_count == 3

    @patch("products.fred_assistant.services.fred_tools.task_service")
    def test_update_task_with_board_move(self, mock_ts):
        mock_ts.update_task.return_value = {"id": "abc", "title": "Moved task", "board_id": "personal"}
        from products.fred_assistant.services.fred_tools import _exec_update_task
        result = _exec_update_task({"task_id": "abc", "board": "personal"})
        assert result["success"] is True
        mock_ts.update_task.assert_called_with("abc", {"board_id": "personal"})

    @patch("products.fred_assistant.services.fred_tools.get_conn")
    def test_search_tasks(self, mock_conn):
        mock_ctx = MagicMock()
        mock_conn.return_value.__enter__ = MagicMock(return_value=mock_ctx)
        mock_conn.return_value.__exit__ = MagicMock(return_value=False)
        mock_ctx.execute.return_value.fetchall.return_value = [
            {"id": "t1", "title": "Stripe integration", "priority": 2, "status": "todo", "board_id": "work", "due_date": None},
        ]
        from products.fred_assistant.services.fred_tools import _exec_search_tasks
        result = _exec_search_tasks({"query": "Stripe"})
        assert result["success"] is True
        assert result["count"] == 1
        assert "Stripe" in result["tasks"][0]


# =============================================================================
# Executor Tests — Memory
# =============================================================================

class TestMemoryExecutors:
    @patch("products.fred_assistant.services.fred_tools.memory_service")
    def test_remember(self, mock_ms):
        mock_ms.remember.return_value = {"id": "m1", "category": "pref", "key": "deploy", "value": "Sundays"}
        from products.fred_assistant.services.fred_tools import _exec_remember
        result = _exec_remember({"category": "pref", "key": "deploy", "value": "Sundays"})
        assert result["success"] is True
        assert "deploy" in result["message"]

    @patch("products.fred_assistant.services.fred_tools.memory_service")
    def test_remember_missing_key(self, mock_ms):
        from products.fred_assistant.services.fred_tools import _exec_remember
        result = _exec_remember({"category": "pref"})
        assert result["success"] is False

    @patch("products.fred_assistant.services.fred_tools.memory_service")
    def test_search_memory(self, mock_ms):
        mock_ms.search_memories.return_value = [
            {"category": "pref", "key": "deploy", "value": "Sundays"}
        ]
        from products.fred_assistant.services.fred_tools import _exec_search_memory
        result = _exec_search_memory({"query": "deploy"})
        assert result["success"] is True
        assert result["count"] == 1

    @patch("products.fred_assistant.services.fred_tools.memory_service")
    def test_forget_by_id(self, mock_ms):
        mock_ms.get_memory.return_value = {"id": "m1", "key": "old fact", "value": "stale"}
        from products.fred_assistant.services.fred_tools import _exec_forget
        result = _exec_forget({"memory_id": "m1"})
        assert result["success"] is True
        assert "old fact" in result["message"]
        mock_ms.forget.assert_called_with("m1")

    @patch("products.fred_assistant.services.fred_tools.memory_service")
    def test_forget_by_key(self, mock_ms):
        mock_ms.search_memories.return_value = [{"id": "m2", "category": "pref", "key": "deploy", "value": "old"}]
        mock_ms.get_memory.return_value = {"id": "m2", "key": "deploy", "value": "old"}
        from products.fred_assistant.services.fred_tools import _exec_forget
        result = _exec_forget({"key": "deploy"})
        assert result["success"] is True
        mock_ms.forget.assert_called_with("m2")

    @patch("products.fred_assistant.services.fred_tools.memory_service")
    def test_forget_not_found(self, mock_ms):
        mock_ms.get_memory.return_value = None
        from products.fred_assistant.services.fred_tools import _exec_forget
        result = _exec_forget({"memory_id": "nope"})
        assert result["success"] is False


# =============================================================================
# Executor Tests — Calendar
# =============================================================================

class TestCalendarExecutors:
    @patch("products.fred_assistant.services.fred_tools.calendar_service")
    def test_create_event(self, mock_cs):
        mock_cs.create_event.return_value = {"id": "e1", "title": "Meeting", "start_date": "2026-02-23"}
        from products.fred_assistant.services.fred_tools import _exec_create_event
        result = _exec_create_event({"title": "Meeting", "start_date": "2026-02-23"})
        assert result["success"] is True

    @patch("products.fred_assistant.services.fred_tools.calendar_service")
    def test_update_event(self, mock_cs):
        mock_cs.update_event.return_value = {"id": "e1", "title": "Updated meeting"}
        from products.fred_assistant.services.fred_tools import _exec_update_event
        result = _exec_update_event({"event_id": "e1", "title": "Updated meeting"})
        assert result["success"] is True
        mock_cs.update_event.assert_called_once()

    @patch("products.fred_assistant.services.fred_tools.calendar_service")
    def test_update_event_not_found(self, mock_cs):
        mock_cs.update_event.return_value = None
        from products.fred_assistant.services.fred_tools import _exec_update_event
        result = _exec_update_event({"event_id": "nope", "title": "X"})
        assert result["success"] is False

    @patch("products.fred_assistant.services.fred_tools.calendar_service")
    def test_delete_event(self, mock_cs):
        mock_cs.get_event.return_value = {"id": "e1", "title": "Old event"}
        from products.fred_assistant.services.fred_tools import _exec_delete_event
        result = _exec_delete_event({"event_id": "e1"})
        assert result["success"] is True
        assert "Old event" in result["message"]
        mock_cs.delete_event.assert_called_with("e1")

    @patch("products.fred_assistant.services.fred_tools.calendar_service")
    def test_delete_event_not_found(self, mock_cs):
        mock_cs.get_event.return_value = None
        from products.fred_assistant.services.fred_tools import _exec_delete_event
        result = _exec_delete_event({"event_id": "nope"})
        assert result["success"] is False


# =============================================================================
# Executor Tests — Goals
# =============================================================================

class TestGoalExecutors:
    @patch("products.fred_assistant.services.fred_tools.coach_service")
    def test_create_goal(self, mock_cs):
        mock_cs.create_goal.return_value = {"id": "g1", "title": "Launch MVP"}
        from products.fred_assistant.services.fred_tools import _exec_create_goal
        result = _exec_create_goal({"title": "Launch MVP", "category": "business"})
        assert result["success"] is True

    @patch("products.fred_assistant.services.fred_tools.coach_service")
    def test_delete_goal(self, mock_cs):
        mock_cs.get_goal.return_value = {"id": "g1", "title": "Old goal"}
        from products.fred_assistant.services.fred_tools import _exec_delete_goal
        result = _exec_delete_goal({"goal_id": "g1"})
        assert result["success"] is True
        assert "Old goal" in result["message"]
        mock_cs.delete_goal.assert_called_with("g1")

    @patch("products.fred_assistant.services.fred_tools.coach_service")
    def test_delete_goal_not_found(self, mock_cs):
        mock_cs.get_goal.return_value = None
        from products.fred_assistant.services.fred_tools import _exec_delete_goal
        result = _exec_delete_goal({"goal_id": "nope"})
        assert result["success"] is False

    @patch("products.fred_assistant.services.fred_tools.coach_service")
    def test_delete_goal_missing_id(self, mock_cs):
        from products.fred_assistant.services.fred_tools import _exec_delete_goal
        result = _exec_delete_goal({})
        assert result["success"] is False


# =============================================================================
# Executor Tests — Content
# =============================================================================

class TestContentExecutors:
    @patch("products.fred_assistant.services.fred_tools.content_service")
    def test_schedule_content(self, mock_cs):
        mock_cs.update_content.return_value = {"id": "c1", "title": "AI Post", "scheduled_date": "2026-03-01"}
        from products.fred_assistant.services.fred_tools import _exec_schedule_content
        result = _exec_schedule_content({"content_id": "c1", "scheduled_date": "2026-03-01"})
        assert result["success"] is True
        assert "2026-03-01" in result["message"]

    @patch("products.fred_assistant.services.fred_tools.content_service")
    def test_schedule_content_not_found(self, mock_cs):
        mock_cs.update_content.return_value = None
        from products.fred_assistant.services.fred_tools import _exec_schedule_content
        result = _exec_schedule_content({"content_id": "nope", "scheduled_date": "2026-03-01"})
        assert result["success"] is False

    def test_schedule_content_missing_date(self):
        from products.fred_assistant.services.fred_tools import _exec_schedule_content
        result = _exec_schedule_content({"content_id": "c1"})
        assert result["success"] is False
        assert "required" in result["error"]


# =============================================================================
# Executor Tests — Files
# =============================================================================

class TestFileExecutors:
    def test_read_file_blocked_path(self):
        from products.fred_assistant.services.fred_tools import _exec_read_file
        result = _exec_read_file({"path": "~/.ssh/id_rsa"})
        assert result["success"] is False
        assert "denied" in result["error"].lower() or "restricted" in result["error"].lower()

    def test_read_file_missing_path(self):
        from products.fred_assistant.services.fred_tools import _exec_read_file
        result = _exec_read_file({})
        assert result["success"] is False

    def test_write_file_blocked_path(self):
        from products.fred_assistant.services.fred_tools import _exec_write_file
        result = _exec_write_file({"path": "/etc/hosts", "content": "evil"})
        assert result["success"] is False

    def test_list_files_blocked_path(self):
        from products.fred_assistant.services.fred_tools import _exec_list_files
        result = _exec_list_files({"path": "/etc"})
        assert result["success"] is False

    def test_read_real_tmp_file(self):
        from products.fred_assistant.services.fred_tools import _exec_read_file
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", dir="/tmp", delete=False) as f:
            f.write("hello world")
            tmp_path = f.name
        try:
            result = _exec_read_file({"path": tmp_path})
            assert result["success"] is True
            assert "hello world" in result["content"]
        finally:
            os.unlink(tmp_path)

    def test_write_real_tmp_file(self):
        from products.fred_assistant.services.fred_tools import _exec_write_file
        tmp_path = f"/tmp/fred_tools_test_{os.getpid()}.txt"
        try:
            result = _exec_write_file({"path": tmp_path, "content": "test content"})
            assert result["success"] is True
            with open(tmp_path) as f:
                assert f.read() == "test content"
        finally:
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)


# =============================================================================
# Executor Tests — Projects
# =============================================================================

class TestProjectExecutors:
    @patch("products.fred_assistant.services.fred_tools.projects_service")
    def test_list_projects(self, mock_ps):
        mock_ps.list_projects.return_value = [
            {"name": "FredAI", "tech_stack": ["Python", "React"], "git_status": "dirty"},
            {"name": "Other", "tech_stack": ["Go"], "git_status": "clean"},
        ]
        from products.fred_assistant.services.fred_tools import _exec_list_projects
        result = _exec_list_projects({})
        assert result["success"] is True
        assert result["count"] == 2

    @patch("products.fred_assistant.services.fred_tools.projects_service")
    def test_find_revenue(self, mock_ps):
        mock_ps.list_projects.return_value = [
            {
                "name": "ai-dashboard",
                "tech_stack": ["Python", "React", "Docker"],
                "git_status": "dirty",
                "remote_url": "https://github.com/test/ai-dashboard",
            },
            {
                "name": "notes",
                "tech_stack": [],
                "git_status": "clean",
                "remote_url": None,
            },
        ]
        from products.fred_assistant.services.fred_tools import _exec_find_revenue
        result = _exec_find_revenue({})
        assert result["success"] is True
        assert result["total_scanned"] == 2
        if result["projects"]:
            assert result["projects"][0]["name"] == "ai-dashboard"
            assert result["projects"][0]["score"] >= 30


# =============================================================================
# Accountability check — SQL filter test
# =============================================================================

class TestAccountabilityCheck:
    @patch("products.fred_assistant.services.fred_tools.get_conn")
    @patch("products.fred_assistant.services.fred_tools.task_service")
    @patch("products.fred_assistant.services.fred_tools.coach_service")
    def test_accountability_uses_sql_filter(self, mock_coach, mock_ts, mock_conn):
        mock_coach.list_goals.return_value = [
            {"title": "Goal A", "progress": 50, "category": "business"},
        ]
        mock_ts.get_dashboard_stats.return_value = {
            "total_tasks": 5, "completed_today": 1, "overdue": 2,
            "in_progress": 1, "due_today": 0, "boards": 3,
            "memories": 2, "streak_days": 3,
        }
        # Mock the SQL connection for overdue query
        mock_ctx = MagicMock()
        mock_conn.return_value.__enter__ = MagicMock(return_value=mock_ctx)
        mock_conn.return_value.__exit__ = MagicMock(return_value=False)
        mock_ctx.execute.return_value.fetchall.return_value = [
            {"id": "t1", "title": "Overdue thing", "due_date": "2026-02-01", "board_id": "work"},
        ]

        from products.fred_assistant.services.fred_tools import _exec_accountability_check
        result = _exec_accountability_check({})
        assert result["success"] is True
        assert result["report"]["overdue_count"] == 1
        assert result["report"]["active_goals"] == 1
        # Verify SQL was called (not full table scan)
        mock_ctx.execute.assert_called_once()
        call_args = mock_ctx.execute.call_args
        assert "due_date < ?" in call_args[0][0]
        assert "status != 'done'" in call_args[0][0]
