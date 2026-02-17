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
    from mcp.server import Server, InitializationOptions
    from mcp.server.stdio import stdio_server
    from mcp.types import (
        Tool,
        TextContent,
        CallToolResult,
        ListToolsResult,
        ServerCapabilities,
        ToolsCapability,
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
    },
    {
        "name": "ai_team_teach",
        "description": "Teach the AI team new knowledge, patterns, or domain expertise. This knowledge will be used in future interactions.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "topic": {
                    "type": "string",
                    "description": "The topic or subject being taught"
                },
                "content": {
                    "type": "string",
                    "description": "The knowledge content to teach"
                },
                "domain": {
                    "type": "string",
                    "enum": ["frontend", "backend", "devops", "security", "architecture", "testing", "general"],
                    "description": "The domain this knowledge belongs to",
                    "default": "general"
                },
                "examples": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Optional examples demonstrating the knowledge",
                    "default": []
                }
            },
            "required": ["topic", "content"]
        }
    },
    {
        "name": "ai_team_insights",
        "description": "Get insights and lessons learned from the AI team's past interactions. Returns patterns, lessons, and recommendations.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "insight_type": {
                    "type": "string",
                    "enum": ["lesson", "pattern", "mistake", "solution", "all"],
                    "description": "Type of insights to retrieve",
                    "default": "all"
                },
                "domain": {
                    "type": "string",
                    "description": "Filter insights by domain (e.g., frontend, backend, security)",
                    "default": ""
                },
                "limit": {
                    "type": "integer",
                    "description": "Maximum number of insights to return",
                    "default": 10
                }
            },
            "required": []
        }
    },
    {
        "name": "ai_team_prompts",
        "description": "Get effective prompts that have worked well in the past. Useful for improving how you interact with the AI team.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "task_type": {
                    "type": "string",
                    "enum": ["coding", "debugging", "review", "architecture", "documentation", "all"],
                    "description": "Filter prompts by task type",
                    "default": "all"
                },
                "domain": {
                    "type": "string",
                    "description": "Filter prompts by domain",
                    "default": ""
                }
            },
            "required": []
        }
    },
    {
        "name": "memory_store_mistake",
        "description": "Store a mistake pattern in memory to prevent it from happening again. The AI team will learn from this.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "description": {
                    "type": "string",
                    "description": "Description of the mistake"
                },
                "mistake_type": {
                    "type": "string",
                    "enum": ["code_error", "architecture_flaw", "performance_issue", "security_vulnerability", "deployment_failure", "logic_error", "integration_issue"],
                    "description": "Type of mistake"
                },
                "severity": {
                    "type": "string",
                    "enum": ["critical", "high", "medium", "low"],
                    "description": "Severity of the mistake",
                    "default": "medium"
                },
                "resolution": {
                    "type": "string",
                    "description": "How the mistake was resolved",
                    "default": ""
                },
                "prevention_strategy": {
                    "type": "string",
                    "description": "How to prevent this mistake in the future",
                    "default": ""
                },
                "project": {
                    "type": "string",
                    "description": "Project where the mistake occurred",
                    "default": "default"
                }
            },
            "required": ["description", "mistake_type"]
        }
    },
    {
        "name": "memory_store_solution",
        "description": "Store a successful solution pattern in memory. The AI team will use this for similar problems in the future.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "problem_pattern": {
                    "type": "string",
                    "description": "Description of the problem this solution addresses"
                },
                "solution_steps": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Steps to implement the solution"
                },
                "best_practices": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Best practices learned from this solution",
                    "default": []
                },
                "project": {
                    "type": "string",
                    "description": "Project where this solution was applied",
                    "default": "default"
                }
            },
            "required": ["problem_pattern", "solution_steps"]
        }
    },
    {
        "name": "ai_team_brainstorm",
        "description": "Have the AI team brainstorm creative ideas and solutions. Each agent brings unique perspectives for innovation.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "topic": {
                    "type": "string",
                    "description": "The topic or problem to brainstorm about"
                },
                "constraints": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Any constraints to consider",
                    "default": []
                },
                "num_ideas": {
                    "type": "integer",
                    "description": "Target number of ideas to generate",
                    "default": 5
                }
            },
            "required": ["topic"]
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
                fixer = FredFix(team=team, memory=memory)
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
                fixer = FredFix(team=team, memory=memory, safe_mode=True)
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

            results = {"query": query, "solutions": [], "mistakes": [], "stats": memory.get_statistics()}

            try:
                if search_type in ["solutions", "all"]:
                    solutions = await memory.find_solution_patterns(query)
                    results["solutions"] = [
                        {
                            "pattern": getattr(s, 'problem_pattern', str(s)),
                            "steps": getattr(s, 'solution_steps', []),
                            "success_rate": getattr(s, 'success_rate', 0.0),
                            "projects": getattr(s, 'projects_used', [])
                        }
                        for s in solutions
                    ]

                if search_type in ["mistakes", "all"]:
                    mistakes = await memory.find_similar_mistakes({"query": query})
                    results["mistakes"] = [
                        {
                            "type": getattr(m, 'mistake_type', 'unknown'),
                            "description": getattr(m, 'description', str(m)),
                            "prevention": getattr(m, 'prevention_strategy', ''),
                            "severity": getattr(m, 'severity', 'medium'),
                            "resolution": getattr(m, 'resolution', '')
                        }
                        for m in mistakes
                    ]
            except Exception as e:
                logger.warning(f"Memory search partial failure: {e}")
                results["warning"] = str(e)

            return json.dumps(results, indent=2)

        elif name == "ai_team_teach":
            team = get_team()
            topic = arguments["topic"]
            content = arguments["content"]
            domain = arguments.get("domain", "general")
            examples = arguments.get("examples", [])

            # Use the teaching system
            if hasattr(team, '_teaching_system'):
                team._teaching_system.teach(
                    topic=topic,
                    content=content,
                    domain=domain,
                    examples=examples
                )
                return json.dumps({
                    "success": True,
                    "message": f"Taught the AI team about '{topic}' in domain '{domain}'",
                    "knowledge_stats": team._teaching_system.get_statistics()
                }, indent=2)
            else:
                return json.dumps({
                    "success": False,
                    "error": "Teaching system not available"
                }, indent=2)

        elif name == "ai_team_insights":
            team = get_team()
            insight_type = arguments.get("insight_type", "all")
            domain = arguments.get("domain", "")
            limit = arguments.get("limit", 10)

            insights = team.get_learned_insights(
                insight_type=insight_type if insight_type != "all" else None,
                domain=domain if domain else None
            )[:limit]

            return json.dumps({
                "insights": insights,
                "total_found": len(insights),
                "knowledge_stats": team._teaching_system.get_statistics() if hasattr(team, '_teaching_system') else {}
            }, indent=2)

        elif name == "ai_team_prompts":
            team = get_team()
            task_type = arguments.get("task_type", "all")
            domain = arguments.get("domain", "")

            prompts = team.get_effective_prompts(
                task_type=task_type if task_type != "all" else None,
                domain=domain if domain else None
            )

            return json.dumps({
                "effective_prompts": prompts,
                "count": len(prompts),
                "tip": "Use these patterns to improve your prompts"
            }, indent=2)

        elif name == "memory_store_mistake":
            if memory is None:
                memory = MemorySystem()

            from ai_dev_team.memory.system import MistakeType

            mistake_type_map = {
                "code_error": MistakeType.CODE_ERROR,
                "architecture_flaw": MistakeType.ARCHITECTURE_FLAW,
                "performance_issue": MistakeType.PERFORMANCE_ISSUE,
                "security_vulnerability": MistakeType.SECURITY_VULNERABILITY,
                "deployment_failure": MistakeType.DEPLOYMENT_FAILURE,
                "logic_error": MistakeType.LOGIC_ERROR,
                "integration_issue": MistakeType.INTEGRATION_ISSUE,
            }

            mistake_type = mistake_type_map.get(arguments["mistake_type"], MistakeType.CODE_ERROR)

            mistake_id = await memory.capture_mistake(
                mistake_type=mistake_type,
                description=arguments["description"],
                context={"source": "mcp_tool", "project": arguments.get("project", "default")},
                resolution=arguments.get("resolution", ""),
                prevention_strategy=arguments.get("prevention_strategy", ""),
                severity=arguments.get("severity", "medium"),
                project=arguments.get("project", "default")
            )

            return json.dumps({
                "success": True,
                "mistake_id": mistake_id,
                "message": f"Stored mistake pattern: {arguments['description'][:50]}...",
                "stats": memory.get_statistics()
            }, indent=2)

        elif name == "memory_store_solution":
            if memory is None:
                memory = MemorySystem()

            solution_id = await memory.capture_solution(
                problem_pattern=arguments["problem_pattern"],
                solution_steps=arguments["solution_steps"],
                project=arguments.get("project", "default"),
                best_practices=arguments.get("best_practices", [])
            )

            return json.dumps({
                "success": True,
                "solution_id": solution_id,
                "message": f"Stored solution pattern: {arguments['problem_pattern'][:50]}...",
                "stats": memory.get_statistics()
            }, indent=2)

        elif name == "ai_team_brainstorm":
            team = get_team()
            topic = arguments["topic"]
            constraints = arguments.get("constraints", [])
            num_ideas = arguments.get("num_ideas", 5)

            constraints_text = "\n".join(f"- {c}" for c in constraints) if constraints else "None"

            prompt = f"""BRAINSTORMING SESSION

Topic: {topic}

Constraints:
{constraints_text}

Generate {num_ideas} creative, innovative ideas. For each idea provide:
1. A catchy name/title
2. Brief description (2-3 sentences)
3. Key benefits
4. Potential challenges

Think outside the box and explore unconventional approaches."""

            result = await team.collaborate(
                prompt=prompt,
                mode="parallel"  # All agents contribute simultaneously
            )

            return json.dumps({
                "success": result.success,
                "ideas": result.final_answer,
                "agents_contributed": result.participating_agents,
                "confidence": result.confidence_score,
                "time": result.total_time
            }, indent=2)

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

    init_options = InitializationOptions(
        server_name="ai-team-platform",
        server_version="1.0.0",
        capabilities=ServerCapabilities(tools=ToolsCapability()),
    )

    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, init_options)


def main():
    """Main entry point"""
    print("""
╔═══════════════════════════════════════════════════════════════════════════╗
║                    AITeamPlatform MCP Server v2.0                         ║
╠═══════════════════════════════════════════════════════════════════════════╣
║  Connecting Claude Code with the AI Team (ChatGPT, Gemini, Grok, Ollama)  ║
║                                                                           ║
║  🤖 COLLABORATION TOOLS:                                                  ║
║    • ai_team_collaborate    - Multi-agent parallel/sequential/consensus   ║
║    • ai_team_review         - Code review from multiple AI perspectives   ║
║    • ai_team_security_audit - Security vulnerability detection            ║
║    • ai_team_ask            - Quick question answering                    ║
║    • ai_team_debug          - Collaborative debugging with root cause     ║
║    • ai_team_architect      - System architecture design                  ║
║    • ai_team_brainstorm     - Creative ideation and innovation            ║
║                                                                           ║
║  🔧 FREDFIX (Autonomous Fixer):                                           ║
║    • fredfix_scan           - Scan project for issues                     ║
║    • fredfix_auto_fix       - Generate and preview fixes                  ║
║                                                                           ║
║  🧠 MEMORY & LEARNING:                                                    ║
║    • memory_search          - Search past solutions and mistakes          ║
║    • memory_store_mistake   - Record mistake patterns to avoid            ║
║    • memory_store_solution  - Store successful solution patterns          ║
║    • ai_team_teach          - Teach the AI team new knowledge             ║
║    • ai_team_insights       - Get learned insights and lessons            ║
║    • ai_team_prompts        - Get effective prompt patterns               ║
║                                                                           ║
║  📊 STATUS:                                                               ║
║    • ai_team_status         - Team status and performance metrics         ║
╚═══════════════════════════════════════════════════════════════════════════╝
    """, file=sys.stderr)

    try:
        asyncio.run(run_mcp_server())
    except KeyboardInterrupt:
        logger.info("Server stopped")


if __name__ == "__main__":
    main()
