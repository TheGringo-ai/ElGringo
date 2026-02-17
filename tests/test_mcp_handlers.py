"""
MCP Server Handler Tests
========================

Tests for MCP server tool definitions and schemas.
Consolidated and optimized test suite.
"""

import os
import pytest
import sys

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


# Expected tools that should exist
EXPECTED_TOOLS = [
    "ai_team_collaborate",
    "ai_team_review",
    "ai_team_security_audit",
    "ai_team_ask",
    "ai_team_debug",
    "ai_team_architect",
    "ai_team_status",
    "fredfix_scan",
    "fredfix_auto_fix",
    "memory_search",
    "ai_team_teach",
    "ai_team_insights",
    "ai_team_prompts",
    "memory_store_mistake",
    "memory_store_solution",
    "ai_team_brainstorm",
]


@pytest.mark.skipif(not MCP_AVAILABLE, reason="MCP server module not available")
class TestMCPToolDefinitions:
    """Test MCP tool definitions - consolidated tests"""

    def test_tools_import(self):
        """Tools should be importable and non-empty"""
        assert isinstance(TOOLS, list)
        assert len(TOOLS) > 0

    def test_tool_count(self):
        """Should have expected number of tools (at least 15)"""
        assert len(TOOLS) >= 15

    def test_tool_names_unique(self):
        """All tool names must be unique"""
        names = [t["name"] for t in TOOLS]
        assert len(names) == len(set(names)), f"Duplicate tool names found: {[n for n in names if names.count(n) > 1]}"

    @pytest.mark.parametrize("tool_name", EXPECTED_TOOLS)
    def test_expected_tool_exists(self, tool_name):
        """Each expected tool should exist"""
        tool = next((t for t in TOOLS if t["name"] == tool_name), None)
        assert tool is not None, f"Tool '{tool_name}' not found in TOOLS"

    def test_all_tools_have_required_fields(self):
        """Every tool must have name, description, and inputSchema"""
        for tool in TOOLS:
            assert "name" in tool, f"Tool missing 'name': {tool}"
            assert isinstance(tool["name"], str), f"Tool name not string: {tool}"
            assert len(tool["name"]) > 0, f"Tool name empty: {tool}"

            assert "description" in tool, f"Tool '{tool['name']}' missing description"
            assert isinstance(tool["description"], str), f"Tool '{tool['name']}' description not string"
            assert len(tool["description"]) > 10, f"Tool '{tool['name']}' description too short"

            assert "inputSchema" in tool, f"Tool '{tool['name']}' missing inputSchema"
            schema = tool["inputSchema"]
            assert schema.get("type") == "object", f"Tool '{tool['name']}' schema type not 'object'"
            assert "properties" in schema, f"Tool '{tool['name']}' schema missing properties"


@pytest.mark.skipif(not MCP_AVAILABLE, reason="MCP server module not available")
class TestToolSchemas:
    """Test specific tool schema requirements"""

    def test_collaborate_mode_parameter(self):
        """ai_team_collaborate should have mode with enum values"""
        tool = next((t for t in TOOLS if t["name"] == "ai_team_collaborate"), None)
        if tool:
            mode_prop = tool["inputSchema"]["properties"].get("mode", {})
            if "enum" in mode_prop:
                assert "parallel" in mode_prop["enum"]
                assert "consensus" in mode_prop["enum"]

    def test_memory_search_parameters(self):
        """memory_search should have query as required"""
        tool = next((t for t in TOOLS if t["name"] == "memory_search"), None)
        if tool:
            assert "query" in tool["inputSchema"]["properties"]
            required = tool["inputSchema"].get("required", [])
            assert "query" in required

    def test_memory_search_type_enum(self):
        """memory_search search_type should have valid enum"""
        tool = next((t for t in TOOLS if t["name"] == "memory_search"), None)
        if tool:
            search_type = tool["inputSchema"]["properties"].get("search_type", {})
            if "enum" in search_type:
                assert "solutions" in search_type["enum"]
                assert "mistakes" in search_type["enum"]
                assert "all" in search_type["enum"]

    def test_teach_required_parameters(self):
        """ai_team_teach should require topic and content"""
        tool = next((t for t in TOOLS if t["name"] == "ai_team_teach"), None)
        if tool:
            required = tool["inputSchema"].get("required", [])
            assert "topic" in required
            assert "content" in required

    def test_store_mistake_parameters(self):
        """memory_store_mistake should have proper parameters"""
        tool = next((t for t in TOOLS if t["name"] == "memory_store_mistake"), None)
        if tool:
            required = tool["inputSchema"].get("required", [])
            assert "description" in required
            assert "mistake_type" in required

            mistake_type = tool["inputSchema"]["properties"].get("mistake_type", {})
            if "enum" in mistake_type:
                assert "code_error" in mistake_type["enum"]
                assert "security_vulnerability" in mistake_type["enum"]

    def test_store_solution_parameters(self):
        """memory_store_solution should have proper parameters"""
        tool = next((t for t in TOOLS if t["name"] == "memory_store_solution"), None)
        if tool:
            required = tool["inputSchema"].get("required", [])
            assert "problem_pattern" in required
            assert "solution_steps" in required

    def test_fredfix_scan_parameters(self):
        """fredfix_scan should have project_path"""
        tool = next((t for t in TOOLS if t["name"] == "fredfix_scan"), None)
        if tool:
            assert "project_path" in tool["inputSchema"]["properties"]

    def test_security_audit_parameters(self):
        """ai_team_security_audit should have project_path"""
        tool = next((t for t in TOOLS if t["name"] == "ai_team_security_audit"), None)
        if tool:
            assert "project_path" in tool["inputSchema"]["properties"]

    def test_ask_parameters(self):
        """ai_team_ask should have question parameter"""
        tool = next((t for t in TOOLS if t["name"] == "ai_team_ask"), None)
        if tool:
            assert "question" in tool["inputSchema"]["properties"]

    def test_brainstorm_parameters(self):
        """ai_team_brainstorm should require topic"""
        tool = next((t for t in TOOLS if t["name"] == "ai_team_brainstorm"), None)
        if tool:
            required = tool["inputSchema"].get("required", [])
            assert "topic" in required


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
