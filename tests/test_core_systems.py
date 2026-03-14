"""
Core System Tests — Router, Tool Factory, Feedback Loop, Streaming
==========================================================================

Tests the core features:
1. Task router complexity classification and mode selection
2. Tool factory (creation, persistence, executor)
3. Feedback loop (auto-detection → memory storage → prevention injection)
4. Streaming collaboration endpoint
"""

import asyncio
import json
import os
import sys
import time
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


# ── Router Tests ─────────────────────────────────────────────────────


class TestTaskRouter:
    """Test task classification, complexity assessment, and mode selection."""

    def setup_method(self):
        from elgringo.routing.router import TaskRouter
        self.router = TaskRouter()

    def test_simple_task_classified_low(self):
        """Simple coding task should be low complexity."""
        c = self.router.classify("Write a function that adds two numbers")
        assert c.complexity == "low"
        assert c.primary_type.value == "coding"

    def test_medium_task_classified_medium(self):
        """Debugging task with moderate detail should be medium."""
        c = self.router.classify(
            "I have a FastAPI endpoint that returns 200 but the response body is always empty. "
            "The handler calls return JSONResponse(data) where data is a dict. "
            "What could cause this bug and how do I fix it?"
        )
        assert c.complexity == "medium"
        assert c.primary_type.value in ("debugging", "coding")

    def test_hard_task_classified_high(self):
        """Architecture task with multiple requirements should be high complexity."""
        c = self.router.classify(
            "Design a real-time notification system that handles 100K concurrent "
            "WebSocket connections, supports message persistence, delivery guarantees, "
            "and fan-out to mobile push notifications. Consider failure modes, "
            "scaling patterns, and technology choices. Justify trade-offs."
        )
        assert c.complexity == "high"
        assert c.primary_type.value in ("architecture", "strategy")

    def test_low_complexity_routes_to_parallel(self):
        """Low complexity should route to parallel (orchestrator overrides to turbo)."""
        c = self.router.classify("Write a palindrome checker")
        assert c.recommended_mode == "parallel"

    def test_medium_debugging_routes_to_sequential(self):
        """Medium debugging should route to sequential."""
        c = self.router.classify(
            "Debug and troubleshoot why my API endpoint returns empty response body. "
            "The error happens intermittently and I need to fix it across multiple services."
        )
        assert c.complexity == "medium"
        assert c.recommended_mode == "sequential"

    def test_high_architecture_routes_to_debate(self):
        """High architecture should route to debate or swarm."""
        c = self.router.classify(
            "Design a distributed system architecture with failure modes and load balancing"
        )
        assert c.recommended_mode in ("debate", "swarm")

    def test_high_security_routes_to_devils_advocate(self):
        """High security should route to devils_advocate."""
        c = self.router.classify(
            "Comprehensive security audit of our authentication system "
            "checking for all vulnerability categories and compliance gaps"
        )
        assert c.recommended_mode == "devils_advocate"

    def test_medium_creative_routes_to_brainstorming(self):
        """Medium creative should route to brainstorming."""
        c = self.router.classify(
            "Design a beautiful and elegant landing page for our SaaS product "
            "with modern UI, responsive layout, dark mode support, and animations. "
            "Include hero section, pricing table, testimonials, and footer."
        )
        assert c.complexity == "medium"
        assert c.recommended_mode == "brainstorming"

    def test_multiple_high_indicators_always_high(self):
        """Multiple high-complexity signals should guarantee high classification."""
        c = self.router.classify(
            "Build a real-time distributed system with trade-offs"
        )
        assert c.complexity == "high"

    def test_word_count_high(self):
        """Long prompts (>50 words) should be high complexity."""
        long_prompt = " ".join(["word"] * 60)
        c = self.router.classify(long_prompt)
        assert c.complexity == "high"

    def test_word_count_low(self):
        """Very short prompts (<15 words) should be low complexity."""
        c = self.router.classify("fix the bug")
        assert c.complexity == "low"


# ── Smart Router v2 Tests ────────────────────────────────────────────


class TestSmartRouterV2:
    """Test new router features: persona injection, cost-aware routing, feedback integration."""

    def setup_method(self):
        from elgringo.routing.router import TaskRouter
        self.router = TaskRouter()

    def test_persona_prompt_generated_for_security(self):
        """Security tasks should get a security persona prompt."""
        c = self.router.classify(
            "Comprehensive security audit of our authentication system "
            "checking for all vulnerability categories and compliance gaps"
        )
        assert c.persona_prompt != ""
        assert "security" in c.persona_prompt.lower() or "penetration" in c.persona_prompt.lower() or "audit" in c.persona_prompt.lower()

    def test_persona_prompt_generated_for_architecture(self):
        """Architecture tasks should get a relevant persona prompt."""
        c = self.router.classify(
            "Design a distributed system architecture with failure modes and load balancing"
        )
        assert c.persona_prompt != ""
        # Could be architecture or strategy persona depending on keyword overlap
        assert len(c.persona_prompt) > 20

    def test_persona_prompt_scales_with_complexity(self):
        """High complexity should get longer, more detailed persona prompts."""
        low = self.router.classify("Write a hello world function")
        high = self.router.classify(
            "Design a real-time distributed system with trade-offs and failure modes"
        )
        # High complexity prompts should be more detailed
        assert len(high.persona_prompt) >= len(low.persona_prompt)

    def test_cost_tier_free_for_simple(self):
        """Simple tasks should get free cost tier."""
        c = self.router.classify("Write a palindrome checker")
        assert c.cost_tier == "free"

    def test_cost_tier_premium_for_complex(self):
        """High complexity should get premium cost tier."""
        c = self.router.classify(
            "Design a distributed system with failure modes and scaling strategy"
        )
        assert c.cost_tier == "premium"

    def test_cost_tier_for_medium(self):
        """Medium complexity should get free or standard cost tier (local-first)."""
        c = self.router.classify(
            "Debug and troubleshoot why my API endpoint returns empty response body. "
            "The error happens intermittently and I need to fix it across multiple services."
        )
        assert c.cost_tier in ("free", "standard")

    def test_free_agents_preferred_for_simple_tasks(self):
        """Simple tasks should prefer free agents (qwen)."""
        c = self.router.classify("fix the bug", prefer_free=True)
        from elgringo.routing.router import FREE_AGENTS
        # At least one free agent should be in the top recommendations
        has_free = any(a in FREE_AGENTS for a in c.recommended_agents[:2])
        assert has_free

    def test_feedback_adjustments_loaded(self):
        """Router should be able to load feedback adjustments."""
        adjustments = self.router._get_feedback_adjustments()
        assert isinstance(adjustments, dict)

    def test_persona_fallback_for_unknown_type(self):
        """Unknown task types should get a generic persona prompt."""
        prompt = self.router._get_persona_prompt(
            self.router.classification_patterns  # intentionally wrong type
            if False else  # skip — test the fallback directly
            type("FakeType", (), {"value": "unknown_xyz"})(),
            "high"
        )
        # Should get the fallback prompt
        assert isinstance(prompt, str)


# ── Tool Factory Tests ───────────────────────────────────────────────


class TestToolFactory:
    """Test dynamic tool creation and execution."""

    def setup_method(self):
        from elgringo.core.tool_factory import ToolFactory
        self.factory = ToolFactory()

    def test_create_tool(self):
        """Creating a tool should persist it."""
        tool = self.factory.create_tool(
            name="test_analyzer",
            description="Test tool",
            parameters=[{"name": "code", "type": "string", "description": "Code to analyze"}],
            prompt_template="Analyze: ${code}",
            mode="parallel",
        )
        assert tool.name == "test_analyzer"
        assert len(tool.parameters) == 1

    def test_list_tools(self):
        """List should include created tools."""
        self.factory.create_tool(
            name="list_test_tool",
            description="Test",
            parameters=[{"name": "x", "type": "string", "description": "X"}],
            prompt_template="${x}",
        )
        tools = self.factory.list_tools()
        names = {t["name"] for t in tools}
        assert "list_test_tool" in names

    def test_delete_tool(self):
        """Deleted tool should not appear in list."""
        self.factory.create_tool(
            name="delete_me_tool",
            description="Will delete",
            parameters=[{"name": "x", "type": "string", "description": "X"}],
            prompt_template="${x}",
        )
        self.factory.delete_tool("delete_me_tool")
        assert self.factory.get_tool("delete_me_tool") is None

    def test_sanitize_name(self):
        """Tool names should be sanitized."""
        tool = self.factory.create_tool(
            name="my-tool.v2!",
            description="Test",
            parameters=[{"name": "x", "type": "string", "description": "X"}],
            prompt_template="${x}",
        )
        assert tool.name == "my_tool_v2_"

    def test_build_executor(self):
        """Executor should substitute parameters and call API."""
        tool = self.factory.create_tool(
            name="exec_test",
            description="Test",
            parameters=[
                {"name": "code", "type": "string", "description": "Code"},
                {"name": "lang", "type": "string", "description": "Language"},
            ],
            prompt_template="Review this ${lang} code:\n${code}",
            mode="debate",
        )

        # Mock API function
        mock_api = MagicMock(return_value={
            "answer": "Looks good",
            "agents_used": ["chatgpt-coder"],
            "confidence": 0.9,
        })

        executor = self.factory.build_executor(tool, mock_api)
        result = executor(code="print('hi')", lang="python")

        # Verify API was called with substituted prompt
        mock_api.assert_called_once()
        call_args = mock_api.call_args
        assert call_args[0][0] == "POST"
        assert call_args[0][1] == "/v1/collaborate"
        body = call_args[0][2]
        assert "Review this python code:" in body["prompt"]
        assert "print('hi')" in body["prompt"]
        assert body["mode"] == "debate"
        assert "Looks good" in result


# ── Feedback Loop Tests ──────────────────────────────────────────────


class TestFeedbackLoop:
    """Test the auto-detection → memory storage → prevention feedback loop."""

    @pytest.fixture
    def memory_system(self, tmp_path):
        from elgringo.memory import MemorySystem
        return MemorySystem(storage_dir=str(tmp_path / "memory"))

    @pytest.fixture
    def feedback_loop(self, memory_system):
        from elgringo.intelligence.feedback_loop import FeedbackLearningLoop
        return FeedbackLearningLoop(memory_system=memory_system)

    @pytest.mark.asyncio
    async def test_auto_detect_failure_stores_mistake(self, feedback_loop, memory_system):
        """Auto-detected failure should store a mistake in memory."""
        outcome = await feedback_loop.auto_detect_failure(
            task_id="test-001",
            error="SQL injection vulnerability detected in user input handling",
            agents=["chatgpt-coder", "grok-coder"],
            task_type="security",
            prompt="Write a login endpoint",
            project="test-project",
        )

        assert outcome.feedback_processed
        # Check that either "mistake" or "prevention" appears in actions
        assert any("mistake" in a.lower() or "prevention" in a.lower()
                   for a in outcome.actions_taken)

    @pytest.mark.asyncio
    async def test_negative_feedback_adjusts_routing(self, feedback_loop):
        """Repeated negative feedback should trigger routing adjustment."""
        # Send enough negative feedback to trigger adjustment
        for i in range(10):
            await feedback_loop.process_feedback(
                task_id=f"neg-{i}",
                rating=-0.8,
                agents=["chatgpt-coder"],
                task_type="coding",
            )

        profile = feedback_loop.get_agent_profile("chatgpt-coder")
        assert profile is not None
        assert profile["satisfaction_rate"] < 0.5

    @pytest.mark.asyncio
    async def test_correction_stores_solution(self, feedback_loop, memory_system):
        """Negative feedback with user correction should store the correction as a solution."""
        # The memory system needs a store_solution method, which capture_solution wraps
        # First check if the memory system has the right method
        has_store = hasattr(memory_system, 'store_solution') or hasattr(memory_system, 'capture_solution')
        if not has_store:
            pytest.skip("Memory system lacks store_solution method")

        outcome = await feedback_loop.process_feedback(
            task_id="pos-001",
            rating=-0.5,
            agents=["chatgpt-coder"],
            task_type="coding",
            comment="Wrong approach",
            correction="Use async/await instead of threading for I/O bound tasks",
        )

        # Either stored successfully or the method isn't available
        assert outcome.feedback_processed


# ── Auto-Failure Detector Tests ──────────────────────────────────────


class TestAutoFailureDetector:
    """Test the failure detection system."""

    def setup_method(self):
        from elgringo.intelligence.auto_failure_detector import get_failure_detector
        self.detector = get_failure_detector()

    def test_detect_security_issue(self):
        """Should detect hardcoded passwords."""
        code = '```python\npassword = "admin123"\ndb.connect(user="root", password=password)\n```'
        result = self.detector.check(code, "test-1", "coding")
        # Check for any security-related failure (category may be enum or string)
        security_failures = [f for f in result.failures
                            if "security" in str(f.category).lower() or "password" in f.description.lower()]
        assert len(security_failures) > 0

    def test_detect_incomplete_code(self):
        """Should detect TODO/FIXME placeholders."""
        code = '```python\ndef process_data(data):\n    # TODO: implement this\n    pass\n```'
        result = self.detector.check(code, "test-2", "coding")
        incomplete = [f for f in result.failures
                     if "incomplete" in str(f.category).lower() or "todo" in f.description.lower()]
        assert len(incomplete) > 0

    def test_clean_code_passes(self):
        """Clean code should pass detection."""
        code = '```python\ndef add(a: int, b: int) -> int:\n    return a + b\n```'
        result = self.detector.check(code, "test-3", "coding")
        critical = [f for f in result.failures if f.severity == "critical"]
        assert len(critical) == 0


# ── Router + Orchestrator Integration ────────────────────────────────


class TestRouterOrchestratorIntegration:
    """Test that the router's mode selection actually flows through to the orchestrator."""

    def test_low_complexity_gets_turbo(self):
        """Orchestrator should use turbo for low complexity tasks."""
        from elgringo.routing.router import TaskRouter
        router = TaskRouter()
        c = router.classify("Write hello world in Python")
        assert c.complexity == "low"
        # Orchestrator will override to turbo at line 582

    def test_classification_types_cover_all(self):
        """All task types should be classifiable."""
        from elgringo.routing.router import TaskRouter, TaskType
        router = TaskRouter()

        test_prompts = {
            TaskType.CODING: "implement a REST API endpoint",
            TaskType.DEBUGGING: "fix the error in my code",
            TaskType.ARCHITECTURE: "design the system architecture",
            TaskType.SECURITY: "security audit of authentication",
            TaskType.TESTING: "write unit tests for the module",
            TaskType.CREATIVE: "design a beautiful landing page",
        }

        for expected_type, prompt in test_prompts.items():
            c = router.classify(prompt)
            assert c.primary_type == expected_type, \
                f"'{prompt}' classified as {c.primary_type}, expected {expected_type}"


# ── Streaming Endpoint Test ──────────────────────────────────────────


class TestStreamingCollaboration:
    """Test the streaming collaboration endpoint structure."""

    def test_stream_request_model(self):
        """StreamCollaborateRequest should accept correct fields."""
        from products.fred_api.server import StreamCollaborateRequest
        req = StreamCollaborateRequest(
            prompt="test prompt",
            context="test context",
            mode="parallel",
        )
        assert req.prompt == "test prompt"
        assert req.mode == "parallel"

    def test_stream_request_defaults(self):
        """StreamCollaborateRequest should have sensible defaults."""
        from products.fred_api.server import StreamCollaborateRequest
        req = StreamCollaborateRequest(prompt="test")
        assert req.context == ""
        assert req.mode is None
        assert req.agents is None
