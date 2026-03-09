"""
Tests for MCP Server
====================

Unit tests for the El Gringo MCP server (root mcp_server.py).
"""

import pytest
import sys
import os

# Add project root to path
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

# Import tool functions from the consolidated MCP server
try:
    from mcp_server import (
        _fmt_collaborate, _fmt_code_task, _fmt_review,
        ai_team_health, ai_team_build, ai_team_execute,
        ai_team_generate, ai_team_review, ai_team_debug,
        ai_team_architect, ai_team_brainstorm, ai_team_security_audit,
        elgringo_collaborate, elgringo_code_task, elgringo_review,
        elgringo_plan, elgringo_project_info, elgringo_ask,
        elgringo_stream, elgringo_debate,
        memory_search, memory_store_solution, memory_store_mistake,
        memory_stats, ai_team_costs, verify_code, fredfix_scan,
    )
    MCP_AVAILABLE = True
except ImportError:
    MCP_AVAILABLE = False


@pytest.mark.skipif(not MCP_AVAILABLE, reason="MCP server module not available")
class TestToolDefinitions:
    """Test that all expected tools exist as callable functions"""

    def test_core_ai_team_tools_exist(self):
        """Core ai_team_* tools must exist"""
        assert callable(ai_team_health)
        assert callable(ai_team_build)
        assert callable(ai_team_execute)
        assert callable(ai_team_generate)
        assert callable(ai_team_review)

    def test_specialized_tools_exist(self):
        """Specialized tools must exist"""
        assert callable(ai_team_debug)
        assert callable(ai_team_architect)
        assert callable(ai_team_brainstorm)
        assert callable(ai_team_security_audit)

    def test_public_elgringo_tools_exist(self):
        """Public elgringo_* tools must exist"""
        assert callable(elgringo_collaborate)
        assert callable(elgringo_code_task)
        assert callable(elgringo_review)
        assert callable(elgringo_plan)
        assert callable(elgringo_project_info)
        assert callable(elgringo_ask)
        assert callable(elgringo_stream)
        assert callable(elgringo_debate)

    def test_dev_tools_exist(self):
        """Dev-focused local tools must exist"""
        assert callable(memory_search)
        assert callable(memory_store_solution)
        assert callable(memory_store_mistake)
        assert callable(memory_stats)
        assert callable(ai_team_costs)
        assert callable(verify_code)
        assert callable(fredfix_scan)

    def test_response_formatters_exist(self):
        """Response formatters must exist"""
        assert callable(_fmt_collaborate)
        assert callable(_fmt_code_task)
        assert callable(_fmt_review)


@pytest.mark.skipif(not MCP_AVAILABLE, reason="MCP server module not available")
class TestResponseFormatters:
    """Test response formatting functions"""

    def test_fmt_collaborate_success(self):
        result = _fmt_collaborate({
            "agents_used": ["chatgpt", "grok"],
            "confidence": 0.85,
            "answer": "Test answer",
        })
        assert "chatgpt, grok" in result
        assert "85%" in result
        assert "Test answer" in result

    def test_fmt_collaborate_error(self):
        result = _fmt_collaborate({"error": "connection failed"})
        assert "Error: connection failed" in result

    def test_fmt_code_task_success(self):
        result = _fmt_code_task({
            "status": "completed",
            "summary": "Added feature",
            "agents_used": ["chatgpt"],
            "iterations": 2,
            "files_changed": [{"path": "main.py", "action": "edit"}],
        })
        assert "completed" in result
        assert "main.py" in result

    def test_fmt_review_success(self):
        result = _fmt_review({
            "agents_used": ["chatgpt", "grok"],
            "files_reviewed": 5,
            "findings": "No critical issues found",
        })
        assert "5 files reviewed" in result
        assert "No critical issues" in result


@pytest.mark.skipif(not MCP_AVAILABLE, reason="MCP server module not available")
class TestVerifyCode:
    """Test verify_code tool"""

    def test_valid_python(self):
        result = verify_code("x = 1\ny = 2\nprint(x + y)\n", language="python")
        assert "python" in result.lower()

    def test_security_warning_eval(self):
        result = verify_code("result = eval(user_input)", language="python")
        assert "eval" in result.lower() or "security" in result.lower()

    def test_auto_detect_language(self):
        result = verify_code("import os\ndef foo():\n    pass\n")
        assert "python" in result.lower()

    def test_empty_code(self):
        result = verify_code("")
        assert "valid" in result.lower() or "no issues" in result.lower()


@pytest.mark.skipif(not MCP_AVAILABLE, reason="MCP server module not available")
class TestMemoryStats:
    """Test memory_stats tool"""

    def test_returns_stats(self):
        result = memory_stats()
        assert "Memory System" in result
        assert "solutions" in result.lower()
        assert "mistakes" in result.lower()


@pytest.mark.skipif(not MCP_AVAILABLE, reason="MCP server module not available")
class TestAiTeamCosts:
    """Test ai_team_costs tool"""

    def test_returns_cost_report(self):
        result = ai_team_costs()
        assert "Costs" in result
        assert "Budget" in result


class TestMemorySystem:
    """Test memory system functionality"""

    @pytest.fixture
    def memory(self, tmp_path):
        """Create a test memory system"""
        from elgringo.memory import MemorySystem
        return MemorySystem(storage_dir=str(tmp_path / "memory"))

    @pytest.mark.asyncio
    async def test_capture_mistake(self, memory):
        """Test capturing a mistake"""
        from elgringo.memory.system import MistakeType

        mistake_id = await memory.capture_mistake(
            mistake_type=MistakeType.CODE_ERROR,
            description="Test mistake",
            context={"test": True},
            severity="medium",
        )

        assert mistake_id is not None
        assert len(memory._mistakes_cache) == 1
        assert memory._mistakes_cache[0].description == "Test mistake"

    @pytest.mark.asyncio
    async def test_capture_solution(self, memory):
        """Test capturing a solution"""
        solution_id = await memory.capture_solution(
            problem_pattern="Test problem",
            solution_steps=["Step 1", "Step 2"],
            success_rate=0.9,
        )

        assert solution_id is not None
        assert len(memory._solutions_cache) == 1
        assert memory._solutions_cache[0].problem_pattern == "Test problem"

    @pytest.mark.asyncio
    async def test_find_similar_mistakes(self, memory):
        """Test finding similar mistakes"""
        from elgringo.memory.system import MistakeType

        # Add some mistakes
        await memory.capture_mistake(
            mistake_type=MistakeType.SECURITY_VULNERABILITY,
            description="SQL injection in login form",
            context={"module": "auth"},
            severity="critical",
        )
        await memory.capture_mistake(
            mistake_type=MistakeType.PERFORMANCE_ISSUE,
            description="Slow database query",
            context={"module": "database"},
            severity="medium",
        )

        # Search for similar
        results = await memory.find_similar_mistakes({"query": "SQL injection authentication"})

        assert len(results) > 0
        # The SQL injection mistake should be found
        assert any("SQL injection" in m.description for m in results)

    @pytest.mark.asyncio
    async def test_find_solution_patterns(self, memory):
        """Test finding solution patterns"""
        await memory.capture_solution(
            problem_pattern="Database connection pooling",
            solution_steps=["Use connection pool", "Set max connections"],
            success_rate=0.95,
        )

        results = await memory.find_solution_patterns("database connection performance")

        assert len(results) > 0
        assert any("connection" in s.problem_pattern.lower() for s in results)

    def test_statistics(self, memory):
        """Test statistics generation"""
        stats = memory.get_statistics()

        assert "total_interactions" in stats
        assert "total_mistakes" in stats
        assert "total_solutions" in stats
        assert "success_rate" in stats


class TestWeightedConsensus:
    """Test weighted consensus system"""

    def test_expertise_weights(self):
        """Test that expertise weights are returned correctly"""
        from elgringo.collaboration import WeightedConsensus

        wc = WeightedConsensus()

        # Claude should be high on analysis
        assert wc.get_expertise_weight("claude-analyst", "analysis") >= 0.8

        # ChatGPT should be high on coding
        assert wc.get_expertise_weight("chatgpt-coder", "coding") >= 0.9

        # Gemini should be high on creative
        assert wc.get_expertise_weight("gemini-creative", "creative") >= 0.9

        # Grok coder should be high on optimization
        assert wc.get_expertise_weight("grok-coder", "optimization") >= 0.9

    def test_unknown_agent_gets_default_weight(self):
        """Unknown agents should get default weights"""
        from elgringo.collaboration import WeightedConsensus

        wc = WeightedConsensus()
        weight = wc.get_expertise_weight("unknown-agent-xyz", "coding")

        assert 0.4 <= weight <= 0.6  # Should be around 0.5 default


class TestFredFix:
    """Test FredFix functionality"""

    def test_issue_parsing_json(self):
        """Test JSON issue parsing"""
        from elgringo.workflows.fredfix import FredFix

        fixer = FredFix()

        response = '''
        [
            {
                "file_path": "app/main.py",
                "severity": "high",
                "issue_type": "security",
                "description": "SQL injection vulnerability",
                "suggested_fix": "Use parameterized queries"
            }
        ]
        '''

        issues = fixer._parse_issues(response, "/project")

        assert len(issues) == 1
        assert issues[0].file_path == "app/main.py"
        assert issues[0].severity == "high"
        assert issues[0].issue_type == "security"

    def test_issue_parsing_text(self):
        """Test text issue parsing"""
        from elgringo.workflows.fredfix import FredFix

        fixer = FredFix()

        response = '''
        file_path: src/utils.py
        severity: medium
        issue_type: performance
        description: Inefficient loop detected
        suggested_fix: Use list comprehension
        '''

        issues = fixer._parse_issues(response, "/project")

        assert len(issues) == 1
        assert issues[0].file_path == "src/utils.py"
        assert issues[0].issue_type == "performance"

    def test_language_detection(self):
        """Test language detection from file path"""
        from elgringo.workflows.fredfix import FredFix
        from pathlib import Path

        fixer = FredFix()

        assert fixer._detect_language(Path("test.py")) == "python"
        assert fixer._detect_language(Path("test.js")) == "javascript"
        assert fixer._detect_language(Path("test.ts")) == "typescript"
        assert fixer._detect_language(Path("test.go")) == "go"
        assert fixer._detect_language(Path("test.rs")) == "rust"
        assert fixer._detect_language(Path("test.java")) == "java"

    def test_supported_languages(self):
        """Test that multiple languages are supported"""
        from elgringo.workflows.fredfix import LANGUAGE_CONFIG

        assert "python" in LANGUAGE_CONFIG
        assert "javascript" in LANGUAGE_CONFIG
        assert "typescript" in LANGUAGE_CONFIG
        assert "go" in LANGUAGE_CONFIG
        assert "rust" in LANGUAGE_CONFIG
        assert "java" in LANGUAGE_CONFIG


@pytest.mark.skipif(not MCP_AVAILABLE, reason="MCP server module not available")
class TestFmtCollaborateEdgeCases:
    """Edge cases for _fmt_collaborate"""

    def test_empty_agents_list(self):
        result = _fmt_collaborate({"agents_used": [], "confidence": 0.5, "answer": "ok"})
        assert "ok" in result

    def test_zero_confidence(self):
        result = _fmt_collaborate({"agents_used": ["a"], "confidence": 0.0, "answer": "x"})
        assert "0%" in result

    def test_full_confidence(self):
        result = _fmt_collaborate({"agents_used": ["a"], "confidence": 1.0, "answer": "x"})
        assert "100%" in result

    def test_missing_agents_key(self):
        result = _fmt_collaborate({"confidence": 0.5, "answer": "x"})
        assert isinstance(result, str)

    def test_missing_confidence_key(self):
        result = _fmt_collaborate({"agents_used": ["a"], "answer": "x"})
        assert isinstance(result, str)

    def test_missing_answer_key(self):
        result = _fmt_collaborate({"agents_used": ["a"], "confidence": 0.5})
        assert isinstance(result, str)

    def test_empty_dict(self):
        result = _fmt_collaborate({})
        assert isinstance(result, str)

    def test_single_agent(self):
        result = _fmt_collaborate({"agents_used": ["chatgpt"], "confidence": 0.9, "answer": "hi"})
        assert "chatgpt" in result


@pytest.mark.skipif(not MCP_AVAILABLE, reason="MCP server module not available")
class TestFmtCodeTaskEdgeCases:
    """Edge cases for _fmt_code_task"""

    def test_error_response(self):
        result = _fmt_code_task({"error": "something broke"})
        assert "Error" in result or "error" in result.lower()

    def test_empty_files_changed(self):
        result = _fmt_code_task({"status": "done", "summary": "s", "agents_used": [], "iterations": 1, "files_changed": []})
        assert isinstance(result, str)

    def test_multiple_files(self):
        result = _fmt_code_task({
            "status": "done", "summary": "s", "agents_used": ["a"],
            "iterations": 1, "files_changed": [
                {"path": "a.py", "action": "edit"},
                {"path": "b.py", "action": "create"},
            ]
        })
        assert "a.py" in result
        assert "b.py" in result

    def test_missing_optional_keys(self):
        result = _fmt_code_task({"status": "done"})
        assert isinstance(result, str)


@pytest.mark.skipif(not MCP_AVAILABLE, reason="MCP server module not available")
class TestFmtReviewEdgeCases:
    """Edge cases for _fmt_review"""

    def test_error_response(self):
        result = _fmt_review({"error": "fail"})
        assert "Error" in result or "error" in result.lower()

    def test_zero_files(self):
        result = _fmt_review({"agents_used": ["a"], "files_reviewed": 0, "findings": "none"})
        assert "0" in result

    def test_missing_all_keys(self):
        result = _fmt_review({})
        assert isinstance(result, str)

    def test_empty_agents(self):
        result = _fmt_review({"agents_used": [], "files_reviewed": 3, "findings": "ok"})
        assert isinstance(result, str)


class TestCollaborationEngine:
    """Test collaboration engine"""

    def test_collaboration_modes_exist(self):
        """Test that all collaboration modes are defined"""
        from elgringo.collaboration import CollaborationMode

        modes = [
            "PARALLEL",
            "SEQUENTIAL",
            "CONSENSUS",
            "DEVILS_ADVOCATE",
            "PEER_REVIEW",
            "BRAINSTORMING",
            "DEBATE",
            "EXPERT_PANEL",
        ]

        for mode in modes:
            assert hasattr(CollaborationMode, mode), f"Mode {mode} not found"


class TestTokenization:
    """Test TF-IDF tokenization"""

    def test_tokenize(self):
        """Test basic tokenization"""
        from elgringo.memory.system import tokenize

        tokens = tokenize("Hello World! This is a test.")

        assert "hello" in tokens
        assert "world" in tokens
        assert "test" in tokens
        # Short words should be excluded
        assert "is" not in tokens
        assert "a" not in tokens

    def test_tfidf_scoring(self):
        """Test TF-IDF scoring"""
        from elgringo.memory.system import tokenize, compute_tf_idf_score

        query = tokenize("database connection error")
        doc1 = tokenize("database connection pooling error handling")
        doc2 = tokenize("user interface styling")
        all_docs = [doc1, doc2]

        score1 = compute_tf_idf_score(query, doc1, all_docs)
        score2 = compute_tf_idf_score(query, doc2, all_docs)

        # doc1 should score higher (more relevant)
        assert score1 > score2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
