"""
Tests for MCP Server
====================

Unit tests for the AI Team Platform MCP server.
"""

import asyncio
import json
import pytest
import sys
import os

# Add both project root and servers directory to path
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)
sys.path.insert(0, os.path.join(PROJECT_ROOT, "servers"))

# Import TOOLS from servers/mcp_server.py
try:
    from servers.mcp_server import TOOLS
    MCP_AVAILABLE = True
except ImportError:
    try:
        from mcp_server import TOOLS
        MCP_AVAILABLE = True
    except ImportError:
        TOOLS = []
        MCP_AVAILABLE = False


@pytest.mark.skipif(not MCP_AVAILABLE, reason="MCP server module not available")
class TestToolDefinitions:
    """Test that tool definitions are correct"""

    def test_all_tools_have_required_fields(self):
        """All tools must have name, description, and inputSchema"""
        for tool in TOOLS:
            assert "name" in tool, f"Tool missing name"
            assert "description" in tool, f"Tool {tool.get('name')} missing description"
            assert "inputSchema" in tool, f"Tool {tool.get('name')} missing inputSchema"

    def test_tool_schemas_are_valid(self):
        """Tool schemas must be valid JSON Schema"""
        for tool in TOOLS:
            schema = tool["inputSchema"]
            assert "type" in schema, f"Tool {tool['name']} schema missing type"
            assert schema["type"] == "object", f"Tool {tool['name']} schema type must be object"
            assert "properties" in schema, f"Tool {tool['name']} schema missing properties"

    def test_required_tools_exist(self):
        """Core tools must be present"""
        tool_names = [t["name"] for t in TOOLS]

        required_tools = [
            "ai_team_collaborate",
            "ai_team_review",
            "ai_team_ask",
            "ai_team_debug",
            "ai_team_status",
            "fredfix_scan",
            "memory_search",
        ]

        for required in required_tools:
            assert required in tool_names, f"Required tool {required} not found"

    def test_new_tools_exist(self):
        """New tools added in v2 must be present"""
        tool_names = [t["name"] for t in TOOLS]

        new_tools = [
            "ai_team_teach",
            "ai_team_insights",
            "ai_team_prompts",
            "memory_store_mistake",
            "memory_store_solution",
            "ai_team_brainstorm",
        ]

        for new_tool in new_tools:
            assert new_tool in tool_names, f"New tool {new_tool} not found"


class TestMemorySystem:
    """Test memory system functionality"""

    @pytest.fixture
    def memory(self, tmp_path):
        """Create a test memory system"""
        from ai_dev_team.memory import MemorySystem
        return MemorySystem(storage_dir=str(tmp_path / "memory"))

    @pytest.mark.asyncio
    async def test_capture_mistake(self, memory):
        """Test capturing a mistake"""
        from ai_dev_team.memory.system import MistakeType

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
        from ai_dev_team.memory.system import MistakeType

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
        from ai_dev_team.collaboration import WeightedConsensus

        wc = WeightedConsensus()

        # Claude should be high on analysis
        assert wc.get_expertise_weight("claude-analyst", "analysis") >= 0.9

        # ChatGPT should be high on coding
        assert wc.get_expertise_weight("chatgpt-coder", "coding") >= 0.9

        # Gemini should be high on creative
        assert wc.get_expertise_weight("gemini-creative", "creative") >= 0.9

        # Grok coder should be high on optimization
        assert wc.get_expertise_weight("grok-coder", "optimization") >= 0.9

    def test_unknown_agent_gets_default_weight(self):
        """Unknown agents should get default weights"""
        from ai_dev_team.collaboration import WeightedConsensus

        wc = WeightedConsensus()
        weight = wc.get_expertise_weight("unknown-agent-xyz", "coding")

        assert 0.4 <= weight <= 0.6  # Should be around 0.5 default


class TestFredFix:
    """Test FredFix functionality"""

    def test_issue_parsing_json(self):
        """Test JSON issue parsing"""
        from ai_dev_team.fredfix import FredFix

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
        from ai_dev_team.fredfix import FredFix

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
        from ai_dev_team.fredfix import FredFix
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
        from ai_dev_team.fredfix import LANGUAGE_CONFIG

        assert "python" in LANGUAGE_CONFIG
        assert "javascript" in LANGUAGE_CONFIG
        assert "typescript" in LANGUAGE_CONFIG
        assert "go" in LANGUAGE_CONFIG
        assert "rust" in LANGUAGE_CONFIG
        assert "java" in LANGUAGE_CONFIG


class TestCollaborationEngine:
    """Test collaboration engine"""

    def test_collaboration_modes_exist(self):
        """Test that all collaboration modes are defined"""
        from ai_dev_team.collaboration import CollaborationMode

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
        from ai_dev_team.memory.system import tokenize

        tokens = tokenize("Hello World! This is a test.")

        assert "hello" in tokens
        assert "world" in tokens
        assert "test" in tokens
        # Short words should be excluded
        assert "is" not in tokens
        assert "a" not in tokens

    def test_tfidf_scoring(self):
        """Test TF-IDF scoring"""
        from ai_dev_team.memory.system import tokenize, compute_tf_idf_score

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
