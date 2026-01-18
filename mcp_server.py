#!/usr/bin/env python3
"""
AITeamPlatform MCP Server
=========================

Model Context Protocol server that exposes AI team capabilities to
Claude Code, VS Code, and other MCP-compatible tools.

This allows seamless collaboration between:
- Claude (you, the user's assistant)
- ChatGPT, Gemini, Grok (the AI team)
- The user
- FredFix (autonomous fixer)

Usage:
    python mcp_server.py

Configure in Claude Code:
    Add to ~/.claude/claude_desktop_config.json or settings
"""

import asyncio
import json
import logging
import os
import sys
from typing import Any, Dict, List, Optional

# MCP Protocol imports
try:
    from mcp.server import Server
    from mcp.server.stdio import stdio_server
    from mcp.types import (
        Tool,
        TextContent,
        CallToolResult,
        ListToolsResult,
    )
    MCP_AVAILABLE = True
except ImportError:
    MCP_AVAILABLE = False
    print("MCP library not installed. Install with: pip install mcp", file=sys.stderr)

# Add parent to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from ai_dev_team import AIDevTeam, FredFix, ParallelCodingEngine
from ai_dev_team.memory import MemorySystem

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.FileHandler('/tmp/ai_team_mcp.log'), logging.StreamHandler(sys.stderr)]
)
logger = logging.getLogger("ai-team-mcp")

# Global instances
team: Optional[AIDevTeam] = None
fixer: Optional[FredFix] = None
engine: Optional[ParallelCodingEngine] = None
memory: Optional[MemorySystem] = None


def get_team() -> AIDevTeam:
    """Get or create AI team instance"""
    global team, fixer, engine, memory
    if team is None:
        logger.info("Initializing AI Team...")
        team = AIDevTeam(project_name="mcp-collaboration")
        memory = MemorySystem()
        fixer = FredFix(team=team, memory=memory)
        engine = ParallelCodingEngine(team)
        logger.info(f"AI Team ready with {len(team.agents)} agents: {list(team.agents.keys())}")
    return team


# Tool definitions
TOOLS = [
    {
        "name": "ai_team_collaborate",
        "description": "Have the AI team (ChatGPT, Gemini, Grok) collaborate on a task. All agents work in parallel and their responses are synthesized. Use this for complex problems that benefit from multiple perspectives.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "prompt": {
                    "type": "string",
                    "description": "The task or question for the AI team"
                },
                "mode": {
                    "type": "string",
                    "enum": ["parallel", "sequential", "consensus"],
                    "description": "Collaboration mode: parallel (all at once), sequential (build on each other), consensus (multiple rounds)",
                    "default": "parallel"
                },
                "context": {
                    "type": "string",
                    "description": "Additional context (code, docs, etc.)",
                    "default": ""
                }
            },
            "required": ["prompt"]
        }
    },
    {
        "name": "ai_team_review",
        "description": "Have the AI team review a project or codebase. Returns analysis from multiple AI perspectives on code quality, security, performance, and architecture.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "project_path": {
                    "type": "string",
                    "description": "Path to the project directory to review"
                },
                "focus_areas": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Specific areas to focus on (e.g., security, performance, architecture)",
                    "default": []
                }
            },
            "required": ["project_path"]
        }
    },
    {
        "name": "ai_team_security_audit",
        "description": "Run a security audit on a project using the AI team. Identifies vulnerabilities, insecure patterns, and provides remediation recommendations.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "project_path": {
                    "type": "string",
                    "description": "Path to the project to audit"
                },
                "severity": {
                    "type": "string",
                    "enum": ["critical", "high", "medium", "low"],
                    "description": "Minimum severity level to report",
                    "default": "medium"
                }
            },
            "required": ["project_path"]
        }
    },
    {
        "name": "ai_team_ask",
        "description": "Ask the AI team a quick question. Gets perspectives from all available agents and synthesizes them.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "question": {
                    "type": "string",
                    "description": "The question to ask"
                },
                "context": {
                    "type": "string",
                    "description": "Optional context for the question",
                    "default": ""
                }
            },
            "required": ["question"]
        }
    },
    {
        "name": "fredfix_scan",
        "description": "Use FredFix to scan a project for issues. Returns a list of detected problems with severity and suggested fixes.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "project_path": {
                    "type": "string",
                    "description": "Path to the project to scan"
                },
                "focus_areas": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Areas to focus on (security, performance, bugs, style)",
                    "default": ["security", "bugs"]
                }
            },
            "required": ["project_path"]
        }
    },
    {
        "name": "fredfix_auto_fix",
        "description": "Use FredFix to automatically scan and generate fixes for a project. Returns detected issues and proposed fixes (safe mode - does not apply changes).",
        "inputSchema": {
            "type": "object",
            "properties": {
                "project_path": {
                    "type": "string",
                    "description": "Path to the project to fix"
                },
                "max_fixes": {
                    "type": "integer",
                    "description": "Maximum number of fixes to generate",
                    "default": 10
                },
                "focus_areas": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Areas to focus on",
                    "default": ["security", "bugs", "performance"]
                }
            },
            "required": ["project_path"]
        }
    },
    {
        "name": "ai_team_status",
        "description": "Get the current status of the AI team including available agents, their roles, and performance stats.",
        "inputSchema": {
            "type": "object",
            "properties": {},
            "required": []
        }
    },
    {
        "name": "ai_team_debug",
        "description": "Have the AI team collaboratively debug an error. Provides root cause analysis and fix recommendations.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "error": {
                    "type": "string",
                    "description": "The error message or description"
                },
                "code": {
                    "type": "string",
                    "description": "Related code (if any)",
                    "default": ""
                },
                "context": {
                    "type": "string",
                    "description": "Additional context about the error",
                    "default": ""
                }
            },
            "required": ["error"]
        }
    },
    {
        "name": "ai_team_architect",
        "description": "Have the AI team design a system architecture. Multiple AI perspectives provide a well-rounded design.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "requirements": {
                    "type": "string",
                    "description": "System requirements description"
                },
                "constraints": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Technical constraints to consider",
                    "default": []
                }
            },
            "required": ["requirements"]
        }
    },
    {
        "name": "memory_search",
        "description": "Search the AI team's memory for past solutions and mistakes. Helps avoid repeating errors and find proven patterns.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Search query for finding relevant past experiences"
                },
                "search_type": {
                    "type": "string",
                    "enum": ["solutions", "mistakes", "all"],
                    "description": "What to search for",
                    "default": "all"
                }
            },
            "required": ["query"]
        }
    }
]


async def handle_tool_call(name: str, arguments: Dict[str, Any]) -> str:
    """Handle a tool call and return the result"""
    global engine, fixer, memory
    logger.info(f"Tool call: {name} with args: {json.dumps(arguments)[:200]}")

    try:
        if name == "ai_team_collaborate":
            team = get_team()
            result = await team.collaborate(
                prompt=arguments["prompt"],
                mode=arguments.get("mode", "parallel"),
                context=arguments.get("context", "")
            )
            return json.dumps({
                "success": result.success,
                "response": result.final_answer,
                "agents": result.participating_agents,
                "confidence": result.confidence_score,
                "time": result.total_time
            }, indent=2)

        elif name == "ai_team_review":
            team = get_team()
            if engine is None:
                engine = ParallelCodingEngine(team)
            result = await engine.review_project(
                arguments["project_path"],
                focus_areas=arguments.get("focus_areas")
            )
            return json.dumps({
                "success": result.success,
                "summary": result.summary,
                "findings": result.agent_results,
                "proposed_fixes": len(result.proposed_fixes),
                "time": result.total_time
            }, indent=2)

        elif name == "ai_team_security_audit":
            team = get_team()
            if engine is None:
                engine = ParallelCodingEngine(team)
            result = await engine.security_audit(
                arguments["project_path"],
                severity_threshold=arguments.get("severity", "medium")
            )
            return json.dumps({
                "success": result.success,
                "summary": result.summary,
                "findings": result.agent_results,
                "time": result.total_time
            }, indent=2)

        elif name == "ai_team_ask":
            team = get_team()
            result = await team.collaborate(
                prompt=arguments["question"],
                context=arguments.get("context", ""),
                mode="parallel"
            )
            return json.dumps({
                "answer": result.final_answer,
                "agents": result.participating_agents,
                "confidence": result.confidence_score
            }, indent=2)

        elif name == "fredfix_scan":
            team = get_team()
            if fixer is None:
                fixer = FredFix(team=team)
            issues = await fixer.scan_project(
                arguments["project_path"],
                focus_areas=arguments.get("focus_areas", ["security", "bugs"])
            )
            return json.dumps({
                "issues_found": len(issues),
                "issues": [
                    {
                        "file": i.file_path,
                        "type": i.issue_type,
                        "severity": i.severity,
                        "description": i.description,
                        "suggested_fix": i.suggested_fix
                    }
                    for i in issues
                ]
            }, indent=2)

        elif name == "fredfix_auto_fix":
            team = get_team()
            if fixer is None:
                fixer = FredFix(team=team, safe_mode=True)
            result = await fixer.auto_fix(
                arguments["project_path"],
                max_fixes=arguments.get("max_fixes", 10),
                focus_areas=arguments.get("focus_areas", ["security", "bugs", "performance"])
            )
            return json.dumps({
                "success": result.success,
                "summary": result.summary,
                "issues_found": len(result.issues_found),
                "fixes_generated": len(result.fixes_applied),
                "fixes_skipped": len(result.fixes_skipped),
                "fixes": result.fixes_applied,
                "confidence": result.confidence,
                "time": result.total_time
            }, indent=2)

        elif name == "ai_team_status":
            team = get_team()
            status = team.get_team_status()
            if fixer:
                status["fredfix"] = fixer.get_stats()
            return json.dumps(status, indent=2)

        elif name == "ai_team_debug":
            team = get_team()
            result = await team.debug(
                error=arguments["error"],
                code=arguments.get("code", ""),
                context=arguments.get("context", "")
            )
            return json.dumps({
                "success": result.success,
                "analysis": result.final_answer,
                "agents": result.participating_agents,
                "confidence": result.confidence_score
            }, indent=2)

        elif name == "ai_team_architect":
            team = get_team()
            result = await team.architect(
                requirements=arguments["requirements"],
                constraints=arguments.get("constraints")
            )
            return json.dumps({
                "success": result.success,
                "architecture": result.final_answer,
                "agents": result.participating_agents,
                "confidence": result.confidence_score
            }, indent=2)

        elif name == "memory_search":
            if memory is None:
                memory = MemorySystem()

            query = arguments["query"]
            search_type = arguments.get("search_type", "all")

            results = {"query": query, "solutions": [], "mistakes": []}

            if search_type in ["solutions", "all"]:
                solutions = await memory.find_solution_patterns(query)
                results["solutions"] = [
                    {
                        "pattern": s.problem_pattern,
                        "steps": s.solution_steps,
                        "success_rate": s.success_rate
                    }
                    for s in solutions
                ]

            if search_type in ["mistakes", "all"]:
                mistakes = await memory.find_similar_mistakes({"query": query})
                results["mistakes"] = [
                    {
                        "type": m.mistake_type,
                        "description": m.description,
                        "prevention": m.prevention_strategy
                    }
                    for m in mistakes
                ]

            return json.dumps(results, indent=2)

        else:
            return json.dumps({"error": f"Unknown tool: {name}"})

    except Exception as e:
        logger.error(f"Tool error: {e}", exc_info=True)
        return json.dumps({"error": str(e)})


async def run_mcp_server():
    """Run the MCP server"""
    if not MCP_AVAILABLE:
        print("Error: MCP library not available", file=sys.stderr)
        print("Install with: pip install mcp", file=sys.stderr)
        sys.exit(1)

    server = Server("ai-team-platform")

    @server.list_tools()
    async def list_tools() -> ListToolsResult:
        """List available tools"""
        return ListToolsResult(tools=[
            Tool(
                name=t["name"],
                description=t["description"],
                inputSchema=t["inputSchema"]
            )
            for t in TOOLS
        ])

    @server.call_tool()
    async def call_tool(name: str, arguments: Dict[str, Any]) -> CallToolResult:
        """Handle tool calls"""
        result = await handle_tool_call(name, arguments)
        return CallToolResult(content=[TextContent(type="text", text=result)])

    logger.info("Starting AI Team MCP Server...")
    logger.info(f"Available tools: {[t['name'] for t in TOOLS]}")

    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream)


def main():
    """Main entry point"""
    print("""
╔═══════════════════════════════════════════════════════════════════╗
║           AITeamPlatform MCP Server                               ║
╠═══════════════════════════════════════════════════════════════════╣
║  Connecting Claude Code with the AI Team                          ║
║                                                                   ║
║  Available Tools:                                                 ║
║    • ai_team_collaborate  - Multi-agent collaboration             ║
║    • ai_team_review       - Code review                           ║
║    • ai_team_security_audit - Security analysis                   ║
║    • ai_team_ask          - Quick questions                       ║
║    • ai_team_debug        - Collaborative debugging               ║
║    • ai_team_architect    - Architecture design                   ║
║    • fredfix_scan         - Scan for issues                       ║
║    • fredfix_auto_fix     - Generate fixes                        ║
║    • memory_search        - Search past solutions                 ║
║    • ai_team_status       - Team status                           ║
╚═══════════════════════════════════════════════════════════════════╝
    """, file=sys.stderr)

    try:
        asyncio.run(run_mcp_server())
    except KeyboardInterrupt:
        logger.info("Server stopped")


if __name__ == "__main__":
    main()
