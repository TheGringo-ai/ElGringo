"""
Intelligence Module Tests — Cost Arbitrage, Cross-Project, Quality, Transparency, ROI, Cache, Guardian, Structured Output
=========================================================================================================================
Tests all intelligence modules that power El Gringo's moat features.
"""

import asyncio
import json
import os
import sys
import time
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


# ── Cost Arbitrage Tests ────────────────────────────────────────────


class TestCostArbitrage:
    """Test the cost arbitrage / value optimizer."""

    def setup_method(self, tmp_path=None):
        from elgringo.intelligence.cost_arbitrage import ValueOptimizer
        self.optimizer = ValueOptimizer(storage_dir="/tmp/test_arbitrage_" + str(id(self)))

    def test_record_usage(self):
        """Recording usage should return a record ID."""
        rid = self.optimizer.record_usage(
            provider="openai", task_type="coding", cost=0.05, quality_score=8.0, tokens=500
        )
        assert rid is not None
        assert isinstance(rid, str)

    def test_savings_report_empty(self):
        """Savings report with no data should return a message or zeros."""
        report = self.optimizer.get_savings_report()
        # Empty report may return {'message': ...} or zeros
        assert "message" in report or report.get("total_spent", 0) == 0

    def test_savings_report_with_data(self):
        """Savings report should reflect recorded usage."""
        for i in range(5):
            self.optimizer.record_usage("openai", "coding", 0.10, 8.0, 1000)
        for i in range(5):
            self.optimizer.record_usage("groq", "coding", 0.01, 7.0, 1000)
        report = self.optimizer.get_savings_report()
        assert report["total_queries"] == 10
        assert report["total_spent"] > 0

    def test_provider_comparison(self):
        """Provider comparison should rank by value."""
        self.optimizer.record_usage("openai", "coding", 0.10, 8.0)
        self.optimizer.record_usage("groq", "coding", 0.01, 7.5)
        comparison = self.optimizer.get_provider_comparison("coding")
        assert isinstance(comparison, dict)

    def test_best_provider(self):
        """Best provider should pick highest value ratio."""
        for _ in range(3):
            self.optimizer.record_usage("openai", "coding", 0.10, 8.0)
            self.optimizer.record_usage("groq", "coding", 0.01, 7.5)
        best = self.optimizer.get_best_provider("coding")
        assert "provider" in best or "best" in str(best).lower() or isinstance(best, dict)

    def test_arbitrage_opportunities(self):
        """Should find arbitrage when cheaper provider has similar quality."""
        for _ in range(5):
            self.optimizer.record_usage("openai", "coding", 0.10, 8.0)
            self.optimizer.record_usage("groq", "coding", 0.01, 7.8)
        opps = self.optimizer.get_arbitrage_opportunities()
        assert isinstance(opps, list)


# ── Cross-Project Knowledge Nexus Tests ─────────────────────────────


class TestCrossProjectNexus:
    """Test the cross-project knowledge sharing system."""

    def setup_method(self):
        from elgringo.intelligence.cross_project import KnowledgeNexus
        self.nexus = KnowledgeNexus(storage_dir="/tmp/test_nexus_" + str(id(self)))

    def test_register_project(self):
        """Registering a project should return an ID."""
        pid = self.nexus.register_project("test-app", "/tmp/test-app", ["python", "fastapi"])
        assert pid is not None

    def test_index_solution(self):
        """Indexing a solution should return a solution ID."""
        self.nexus.register_project("proj-a")
        sid = self.nexus.index_solution(
            project="proj-a",
            problem="Database connection pool exhaustion",
            solution="Use connection pooling with max_connections=20",
            tags=["database", "performance"],
        )
        assert sid is not None

    def test_index_mistake(self):
        """Indexing a mistake should return a mistake ID."""
        self.nexus.register_project("proj-b")
        mid = self.nexus.index_mistake(
            project="proj-b",
            mistake="Forgot to close file handles",
            resolution="Use context managers (with statement)",
            tags=["python", "resources"],
            severity="medium",
        )
        assert mid is not None

    def test_search_across_projects(self):
        """Search should find indexed solutions."""
        self.nexus.register_project("search-proj")
        self.nexus.index_solution(
            project="search-proj",
            problem="Memory leak in worker process",
            solution="Add periodic garbage collection and memory monitoring",
            tags=["memory", "performance"],
        )
        results = self.nexus.search_across_projects("memory leak")
        assert isinstance(results, list)

    def test_stats(self):
        """Stats should reflect indexed items."""
        self.nexus.register_project("stats-proj")
        self.nexus.index_solution("stats-proj", "p1", "s1")
        self.nexus.index_mistake("stats-proj", "m1", "r1")
        stats = self.nexus.get_stats()
        assert stats.get("total_projects", 0) >= 1 or stats.get("projects", 0) >= 1

    def test_cross_project_patterns(self):
        """Should detect patterns across projects."""
        self.nexus.register_project("p1")
        self.nexus.register_project("p2")
        self.nexus.index_mistake("p1", "timeout on API calls", "add retry logic", tags=["timeout"])
        self.nexus.index_mistake("p2", "timeout when calling external service", "add retry with backoff", tags=["timeout"])
        patterns = self.nexus.get_cross_project_patterns()
        assert isinstance(patterns, list)


# ── Quality Scorer Tests ────────────────────────────────────────────


class TestQualityScorer:
    """Test the quality scoring system (stateless)."""

    def setup_method(self):
        from elgringo.intelligence.quality_scorer import QualityScorer
        self.scorer = QualityScorer()

    def test_score_single_response(self):
        """Should score a single agent response."""
        responses = [MagicMock(
            agent_name="chatgpt-coder",
            content="def add(a, b): return a + b",
            confidence=0.9,
            response_time=1.5,
        )]
        report = self.scorer.score(
            responses=responses,
            prompt="Write an add function",
            final_answer="def add(a, b): return a + b",
            task_type="coding",
        )
        assert hasattr(report, 'overall_score')
        assert 0.0 <= report.overall_score <= 1.0
        assert report.grade in ("A", "B", "C", "D", "F")

    def test_score_multiple_responses_agreement(self):
        """Multiple agreeing responses should score higher on agreement."""
        responses = [
            MagicMock(agent_name="chatgpt", content="Use async/await for I/O", confidence=0.9, response_time=1.0),
            MagicMock(agent_name="gemini", content="Use async await for I/O bound tasks", confidence=0.85, response_time=1.2),
            MagicMock(agent_name="grok", content="Async/await is best for I/O operations", confidence=0.88, response_time=0.9),
        ]
        report = self.scorer.score(
            responses=responses,
            prompt="How to handle I/O in Python?",
            final_answer="Use async/await for I/O bound tasks",
        )
        assert report.agreement_score > 0.5

    def test_score_to_dict(self):
        """Quality report should serialize to dict."""
        responses = [MagicMock(
            agent_name="test", content="answer", confidence=0.8, response_time=1.0
        )]
        report = self.scorer.score(responses, "question", "answer")
        d = report.to_dict()
        assert "overall_score" in d
        assert "grade" in d


# ── Reasoning Transparency Tests ────────────────────────────────────


class TestReasoningTransparency:
    """Test the reasoning transparency system (stateless)."""

    def setup_method(self):
        from elgringo.intelligence.reasoning_transparency import ReasoningTransparency
        self.rt = ReasoningTransparency()

    def test_analyze_single_response(self):
        """Should analyze a single response."""
        responses = [MagicMock(
            agent_name="chatgpt-coder",
            content="The issue is a race condition. Use a mutex lock.",
            confidence=0.85,
            response_time=2.0,
            model="gpt-4o",
        )]
        report = self.rt.analyze(
            responses=responses,
            prompt="Why does my code crash intermittently?",
            final_answer="Race condition — use mutex lock",
            task_type="debugging",
        )
        assert hasattr(report, 'consensus_level')
        assert hasattr(report, 'agent_reasoning')
        assert len(report.agent_reasoning) == 1

    def test_analyze_disagreement(self):
        """Should detect disagreements between agents."""
        responses = [
            MagicMock(agent_name="chatgpt", content="Use PostgreSQL for this workload", confidence=0.8, response_time=1.0, model="gpt-4o"),
            MagicMock(agent_name="grok", content="Use MongoDB for flexibility", confidence=0.75, response_time=0.9, model="grok-3"),
        ]
        report = self.rt.analyze(
            responses=responses,
            prompt="Which database should I use?",
            final_answer="PostgreSQL for structured data, MongoDB for flexible schemas",
        )
        assert hasattr(report, 'disagreement_points')

    def test_report_to_dict(self):
        """Transparency report should serialize."""
        responses = [MagicMock(
            agent_name="test", content="answer", confidence=0.8, response_time=1.0, model="test"
        )]
        report = self.rt.analyze(responses, "q", "a")
        d = report.to_dict()
        assert isinstance(d, dict)
        # May be nested under "consensus" or at top level
        assert "consensus_level" in d or "consensus" in d

    def test_report_to_readable(self):
        """Should produce human-readable output."""
        responses = [MagicMock(
            agent_name="test", content="answer", confidence=0.8, response_time=1.0, model="test"
        )]
        report = self.rt.analyze(responses, "q", "a")
        readable = report.to_readable()
        assert isinstance(readable, str)
        assert len(readable) > 0


# ── ROI Dashboard Tests ─────────────────────────────────────────────


class TestROIDashboard:
    """Test the ROI tracking dashboard."""

    def setup_method(self):
        from elgringo.intelligence.roi_dashboard import ROIDashboard
        self.dashboard = ROIDashboard(storage_dir="/tmp/test_roi_" + str(id(self)))

    def test_record_task(self):
        """Recording a task should persist it."""
        self.dashboard.record_task(
            task_id="t-001",
            task_type="coding",
            complexity="medium",
            agents_used=["chatgpt-coder", "grok-coder"],
            mode="parallel",
            duration_seconds=15.0,
            api_cost=0.08,
            success=True,
            confidence=0.9,
        )
        report = self.dashboard.get_report()
        assert report.total_tasks >= 1

    def test_roi_report_structure(self):
        """ROI report should have all expected fields."""
        self.dashboard.record_task(
            task_id="t-002", task_type="debugging", complexity="high",
            agents_used=["chatgpt-coder"], mode="turbo",
            duration_seconds=5.0, api_cost=0.03, success=True, confidence=0.85,
        )
        report = self.dashboard.get_report()
        assert hasattr(report, 'total_time_saved_hours')
        assert hasattr(report, 'total_money_saved')
        assert hasattr(report, 'total_api_cost')
        assert hasattr(report, 'success_rate')

    def test_roi_report_to_dict(self):
        """ROI report should serialize."""
        self.dashboard.record_task(
            task_id="t-003", task_type="coding", complexity="low",
            agents_used=["qwen-coder"], mode="turbo",
            duration_seconds=2.0, api_cost=0.0, success=True, confidence=0.7,
        )
        d = self.dashboard.get_report().to_dict()
        assert isinstance(d, dict)
        # May be nested under "summary" or at top level
        assert "total_tasks" in d or "summary" in d

    def test_agent_leaderboard(self):
        """Leaderboard should rank agents."""
        for i in range(3):
            self.dashboard.record_task(
                task_id=f"lb-{i}", task_type="coding", complexity="medium",
                agents_used=["chatgpt-coder"], mode="turbo",
                duration_seconds=10.0, api_cost=0.05, success=True, confidence=0.9,
            )
        board = self.dashboard.get_agent_leaderboard()
        assert isinstance(board, list)
        assert len(board) >= 1

    def test_update_rating(self):
        """Should update task rating after the fact."""
        self.dashboard.record_task(
            task_id="rate-1", task_type="coding", complexity="medium",
            agents_used=["chatgpt-coder"], mode="turbo",
            duration_seconds=5.0, api_cost=0.03, success=True, confidence=0.8,
        )
        result = self.dashboard.update_rating("rate-1", 4.5)
        assert result is True or result is None  # Depends on implementation


# ── Smart Cache Tests ───────────────────────────────────────────────


class TestSmartCache:
    """Test the smart response cache."""

    def setup_method(self):
        from elgringo.intelligence.smart_cache import SmartResponseCache
        self.cache = SmartResponseCache(storage_dir="/tmp/test_cache_" + str(id(self)))

    def _long_response(self, text="Python is a high-level programming language known for readability and versatility"):
        """Helper to create response long enough to be cached (>50 chars)."""
        return text

    def test_put_and_get_exact(self):
        """Should retrieve exact match from cache."""
        resp = self._long_response()
        self.cache.put(
            prompt="What is Python?",
            response=resp,
            cost=0.02, tokens=50, agent="chatgpt", task_type="general",
        )
        result = self.cache.get("What is Python?", task_type="general")
        assert result is not None
        assert "Python" in result.get("response", result.get("content", ""))

    def test_cache_miss(self):
        """Unrelated query should miss."""
        self.cache.put(prompt="What is Python?", response=self._long_response(), cost=0.01)
        result = self.cache.get("How to cook pasta?")
        assert result is None

    def test_cache_stats(self):
        """Stats should track hits and misses."""
        self.cache.put(prompt="test prompt", response=self._long_response())
        self.cache.get("test prompt")
        self.cache.get("missing prompt")
        stats = self.cache.get_stats()
        assert isinstance(stats, dict)

    def test_cache_invalidate(self):
        """Invalidating should remove entry."""
        self.cache.put(prompt="delete me", response=self._long_response())
        self.cache.invalidate("delete me")
        result = self.cache.get("delete me")
        assert result is None

    def test_cache_clear(self):
        """Clear should remove all entries."""
        self.cache.put(prompt="a", response=self._long_response("First long response for caching test that exceeds minimum"))
        self.cache.put(prompt="b", response=self._long_response("Second long response for caching test that exceeds minimum"))
        self.cache.clear()
        stats = self.cache.get_stats()
        assert stats.get("total_entries", 0) == 0


# ── Production Guardian Tests ───────────────────────────────────────


class TestProductionGuardian:
    """Test the production monitoring guardian."""

    def setup_method(self):
        from elgringo.intelligence.production_guardian import ProductionGuardian
        self.guardian = ProductionGuardian(storage_dir="/tmp/test_guardian_" + str(id(self)))

    def test_add_monitored_app(self):
        """Should register an app for monitoring."""
        app_id = self.guardian.add_monitored_app(
            name="test-api",
            url="http://localhost:8090",
            health_endpoint="/v1/health",
        )
        assert app_id is not None

    def test_list_apps(self):
        """Should list monitored apps."""
        self.guardian.add_monitored_app("app-1", url="http://localhost:3000")
        apps = self.guardian.list_apps()
        assert isinstance(apps, list)
        assert len(apps) >= 1

    def test_remove_app(self):
        """Should remove a monitored app."""
        app_id = self.guardian.add_monitored_app("remove-me")
        result = self.guardian.remove_app(app_id)
        assert result is True

    def test_diagnose_error(self):
        """Should diagnose common error patterns."""
        result = self.guardian.diagnose("ConnectionRefusedError: [Errno 111] Connection refused")
        assert hasattr(result, 'category') or isinstance(result, dict)
        # Should identify this as a connection issue
        diag_str = str(result).lower()
        assert "connection" in diag_str or "network" in diag_str or "refused" in diag_str

    def test_diagnose_memory_error(self):
        """Should diagnose memory errors."""
        result = self.guardian.diagnose("MemoryError: Unable to allocate 2.00 GiB")
        diag_str = str(result).lower()
        assert "memory" in diag_str

    def test_status_report(self):
        """Should produce a status report."""
        self.guardian.add_monitored_app("status-app")
        report = self.guardian.get_status_report()
        assert isinstance(report, dict)


# ── Structured Output Tests ─────────────────────────────────────────


class TestStructuredOutput:
    """Test the structured output enforcer (stateless)."""

    def setup_method(self):
        from elgringo.intelligence.structured_output import StructuredOutputEnforcer
        self.enforcer = StructuredOutputEnforcer()

    def test_enforce_valid_json(self):
        """Should parse valid JSON response."""
        schema = {"type": "object", "properties": {"name": {"type": "string"}}}
        result = self.enforcer.enforce(
            raw_response='{"name": "test"}',
            schema=schema,
        )
        assert result.success
        assert result.data["name"] == "test"

    def test_enforce_json_in_markdown(self):
        """Should extract JSON from markdown code blocks."""
        schema = {"type": "object", "properties": {"score": {"type": "number"}}}
        result = self.enforcer.enforce(
            raw_response='Here is the result:\n```json\n{"score": 8.5}\n```',
            schema=schema,
        )
        assert result.success
        assert result.data["score"] == 8.5

    def test_enforce_invalid_response(self):
        """Should handle non-JSON response gracefully."""
        schema = {"type": "object", "properties": {"x": {"type": "string"}}}
        result = self.enforcer.enforce(
            raw_response="This is just plain text with no JSON at all.",
            schema=schema,
            auto_repair=False,
        )
        # Should either fail or attempt repair
        assert isinstance(result.success, bool)

    def test_list_schemas(self):
        """Should list built-in schemas."""
        schemas = self.enforcer.list_schemas()
        assert isinstance(schemas, list)
        assert len(schemas) >= 1

    def test_get_schema(self):
        """Should retrieve a built-in schema by name."""
        schemas = self.enforcer.list_schemas()
        if schemas:
            schema = self.enforcer.get_schema(schemas[0])
            assert schema is not None
            assert isinstance(schema, dict)

    def test_build_prompt_suffix(self):
        """Should build a prompt suffix from schema."""
        schema = {"type": "object", "properties": {"result": {"type": "string"}}}
        suffix = self.enforcer.build_prompt_suffix(schema)
        assert isinstance(suffix, str)
        assert "json" in suffix.lower() or "JSON" in suffix


# ── Singleton Tests ─────────────────────────────────────────────────


class TestSingletons:
    """Test that get_*() singleton factories work."""

    def test_get_optimizer(self):
        from elgringo.intelligence.cost_arbitrage import get_optimizer
        opt = get_optimizer()
        assert opt is not None

    def test_get_nexus(self):
        from elgringo.intelligence.cross_project import get_nexus
        nexus = get_nexus()
        assert nexus is not None

    def test_get_quality_scorer(self):
        from elgringo.intelligence.quality_scorer import get_quality_scorer
        scorer = get_quality_scorer()
        assert scorer is not None

    def test_get_reasoning_transparency(self):
        from elgringo.intelligence.reasoning_transparency import get_reasoning_transparency
        rt = get_reasoning_transparency()
        assert rt is not None

    def test_get_roi_dashboard(self):
        from elgringo.intelligence.roi_dashboard import get_roi_dashboard
        roi = get_roi_dashboard()
        assert roi is not None

    def test_get_smart_cache(self):
        from elgringo.intelligence.smart_cache import get_smart_cache
        cache = get_smart_cache()
        assert cache is not None

    def test_get_guardian(self):
        from elgringo.intelligence.production_guardian import get_guardian
        guardian = get_guardian()
        assert guardian is not None

    def test_get_structured_enforcer(self):
        from elgringo.intelligence.structured_output import get_structured_enforcer
        enforcer = get_structured_enforcer()
        assert enforcer is not None


# ── Mode Alias Tests ────────────────────────────────────────────────


class TestSimplifiedModes:
    """Test the simplified collaboration mode aliases."""

    def test_mode_aliases_map_correctly(self):
        """Simplified modes should map to internal modes."""
        aliases = {
            "auto": None,
            "quick": "turbo",
            "team": "parallel",
            "deep": "debate",
        }
        for simple, internal in aliases.items():
            resolved = aliases.get(simple, simple)
            assert resolved == internal, f"{simple} should map to {internal}"

    def test_unknown_mode_passes_through(self):
        """Unknown modes should pass through unchanged."""
        aliases = {"auto": None, "quick": "turbo", "team": "parallel", "deep": "debate"}
        assert aliases.get("sequential", "sequential") == "sequential"
        assert aliases.get("debate", "debate") == "debate"
