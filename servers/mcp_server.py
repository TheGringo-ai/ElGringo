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
from ai_dev_team.project_context import ProjectContextManager, ProjectProfile

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
project_ctx = ProjectContextManager()


def get_team() -> AIDevTeam:
    """Get or create AI team instance"""
    global team, fixer, engine, memory
    if team is None:
        logger.info("Initializing AI Team...")
        team = AIDevTeam(project_name="mcp-collaboration")
        has_firestore = bool(os.getenv("GOOGLE_APPLICATION_CREDENTIALS"))
        memory = MemorySystem(use_firestore=has_firestore)
        if has_firestore:
            logger.info("Firestore memory enabled (persistent cross-session)")

        # Share the MCP memory with the orchestrator so collaborate()
        # auto-injects stored solution patterns into prompts
        team._memory_system = memory
        if team._prevention:
            team._prevention.memory = memory
        logger.info("Shared memory wired into orchestrator for auto-injection")

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
                },
                "project": {
                    "type": "string",
                    "description": "Project name for memory lookup (e.g. 'managers-dashboard'). Pulls relevant patterns and conventions from past solutions.",
                    "default": ""
                },
                "session_id": {
                    "type": "string",
                    "description": "Session ID for multi-turn conversations. Agents remember previous exchanges in the same session. Use any string (e.g. 'auth-refactor', 'debug-session-1').",
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
    },
    {
        "name": "load_project_context",
        "description": "Load a project's key files and conventions into El Gringo's memory. Auto-detects tech stack, reads important files (requirements.txt, main entry, first router, config). The team will use this context in future collaborate calls.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "project_name": {
                    "type": "string",
                    "description": "Name for this project (e.g. 'managers-dashboard')"
                },
                "project_path": {
                    "type": "string",
                    "description": "Absolute path to the project directory"
                },
                "key_patterns": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Project-specific coding conventions and rules the team must follow",
                    "default": []
                },
                "files": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Specific files to load (relative to project_path). Auto-detects if empty.",
                    "default": []
                },
                "max_lines": {
                    "type": "integer",
                    "description": "Max lines to read per file",
                    "default": 50
                }
            },
            "required": ["project_name", "project_path"]
        }
    },
    {
        "name": "verify_code",
        "description": "Verify generated code by running the project's build/import check. Returns pass/fail with error details. Use after generating code to catch issues before committing.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "project_path": {
                    "type": "string",
                    "description": "Path to the project directory"
                },
                "check_type": {
                    "type": "string",
                    "enum": ["python_import", "npm_build", "python_syntax", "all"],
                    "description": "Type of verification to run",
                    "default": "all"
                },
                "files": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Specific files to check (relative paths). If empty, runs project-wide checks.",
                    "default": []
                }
            },
            "required": ["project_path"]
        }
    },
    {
        "name": "memory_curate",
        "description": "Curate the AI team's memory: consolidate duplicate solutions, extract key patterns from verbose entries, and prune noise. Makes memory more effective for future pattern injection.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "project": {
                    "type": "string",
                    "description": "Curate solutions for a specific project, or 'all'",
                    "default": "all"
                },
                "dry_run": {
                    "type": "boolean",
                    "description": "If true, show what would change without modifying memory",
                    "default": True
                }
            }
        }
    },
    {
        "name": "ai_team_benchmark",
        "description": "Run benchmarks comparing all agents on standardized prompts. Scores each agent's output quality and builds a routing table of which agent is best at which task type.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "task_type": {
                    "type": "string",
                    "enum": ["coding", "debugging", "architecture", "security", "all"],
                    "description": "Which task type to benchmark, or 'all' for comprehensive"
                },
                "agents": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Specific agent names to benchmark (default: all available)"
                }
            },
            "required": ["task_type"]
        }
    },
    {
        "name": "ai_team_routing_table",
        "description": "Show the current agent routing table — which agent is best for which task type, based on benchmarks and performance data.",
        "inputSchema": {
            "type": "object",
            "properties": {},
            "required": []
        }
    },
    {
        "name": "ai_team_costs",
        "description": "Get detailed cost report: today's spend, weekly/monthly breakdown, per-model costs, and budget status.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "period": {
                    "type": "string",
                    "enum": ["today", "week", "month", "all"],
                    "description": "Time period for the cost report",
                    "default": "all"
                }
            }
        }
    },
    {
        "name": "ai_team_rate",
        "description": "Rate a collaborate output as positive or negative. This feedback improves future pattern injection — good patterns get boosted, bad ones get demoted.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "task_id": {
                    "type": "string",
                    "description": "The task_id from the collaborate result (shown in metadata)"
                },
                "rating": {
                    "type": "string",
                    "enum": ["positive", "negative"],
                    "description": "Was the output helpful?"
                },
                "note": {
                    "type": "string",
                    "description": "Optional note about what was good/bad",
                    "default": ""
                }
            },
            "required": ["task_id", "rating"]
        }
    },
    {
        "name": "ai_team_quality_report",
        "description": "Get a quality report on stored memory patterns — distribution of scores, top patterns, and user-rated solutions.",
        "inputSchema": {
            "type": "object",
            "properties": {},
            "required": []
        }
    },
    {
        "name": "ai_team_sessions",
        "description": "List active conversation sessions or get details of a specific session. Sessions enable multi-turn conversations where agents remember context.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "session_id": {
                    "type": "string",
                    "description": "Get details for a specific session. If omitted, lists all sessions.",
                    "default": ""
                },
                "action": {
                    "type": "string",
                    "enum": ["list", "get", "delete"],
                    "description": "Action to perform",
                    "default": "list"
                }
            }
        }
    },
    {
        "name": "ai_team_review_pr",
        "description": "Review a GitHub PR with the full AI team. Pulls the diff, runs multi-agent review from security/performance/architecture angles. Returns structured review.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "pr": {
                    "type": "string",
                    "description": "PR number or URL (e.g. '123' or 'owner/repo#123')"
                },
                "repo": {
                    "type": "string",
                    "description": "Repository in owner/repo format. Optional if PR URL includes it.",
                    "default": ""
                },
                "focus": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Areas to focus on: security, performance, architecture, bugs, style",
                    "default": ["security", "bugs", "performance"]
                }
            },
            "required": ["pr"]
        }
    },
    {
        "name": "ai_team_create_persona",
        "description": "Create a custom AI agent persona with specialized knowledge and behavior. The persona persists and can be used in future collaborate calls.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "name": {
                    "type": "string",
                    "description": "Unique name for the persona (e.g. 'django-expert', 'security-auditor')"
                },
                "role": {
                    "type": "string",
                    "description": "Role description (e.g. 'Senior Django Developer')"
                },
                "system_prompt": {
                    "type": "string",
                    "description": "Custom system prompt defining the persona's expertise, style, and rules"
                },
                "model": {
                    "type": "string",
                    "enum": ["chatgpt", "gemini", "grok", "grok-fast", "ollama"],
                    "description": "Which AI model backs this persona",
                    "default": "chatgpt"
                },
                "capabilities": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of capabilities (e.g. ['django', 'postgresql', 'rest-api'])",
                    "default": []
                }
            },
            "required": ["name", "role", "system_prompt"]
        }
    }
]


def format_intelligence_report(intel: Dict[str, Any], result) -> str:
    """Format the intelligence visibility report — makes the invisible visible."""
    if not intel:
        return ""

    lines = []
    lines.append("=" * 50)
    lines.append("INTELLIGENCE REPORT")
    lines.append("=" * 50)

    # --- Routing ---
    routing = intel.get("routing", {})
    if routing:
        task_type = routing.get("task_type", "unknown")
        complexity = routing.get("complexity", "unknown")
        mode = routing.get("mode", "unknown")
        lines.append("")
        lines.append(f"ROUTING: {task_type} task ({complexity} complexity)")
        lines.append(f"  Mode: {mode}")
        if routing.get("scores"):
            score_strs = [
                f"{s['agent']} ({s['score']:.2f})" for s in routing["scores"][:5]
            ]
            lines.append(f"  Agent scores: {' > '.join(score_strs)}")
        elif routing.get("selected_agents"):
            lines.append(f"  Selected: {', '.join(routing['selected_agents'])}")
        method = routing.get("selection_method", "")
        if method:
            lines.append(f"  Method: {method}")

    # --- Memory ---
    mem = intel.get("memory", {})
    if mem.get("patterns_injected"):
        lines.append("")
        lines.append(f"MEMORY: {mem['patterns_injected']} patterns injected ({mem.get('curated_count', 0)} curated)")
        for p in mem.get("patterns", []):
            curated_tag = " [curated]" if p.get("has_best_practices") else ""
            lines.append(
                f'  - "{p["name"]}" (quality: {p["quality"]}, used {p["times_used"]}x){curated_tag}'
            )
    if mem.get("prevention_applied"):
        lines.append("")
        lines.append("  !! MISTAKE PREVENTION ACTIVE !!")
        lines.append(f"  Blocked a known failure pattern from being repeated.")
        summary = mem.get("prevention_summary", "")
        if summary:
            lines.append(f"  Context: {summary[:150]}")

    # --- Agent Perspectives ---
    agents = intel.get("agents", [])
    if agents:
        lines.append("")
        lines.append(f"AGENT PERSPECTIVES ({len(agents)} agents):")
        for a in agents:
            status = "OK" if a.get("success") else "FAILED"
            cost_entry = next(
                (c for c in intel.get("cost", {}).get("breakdown", []) if c["agent"] == a["name"]),
                None,
            )
            cost_str = f", ${cost_entry['cost']:.4f}" if cost_entry and cost_entry["cost"] > 0 else ""
            tokens = a.get("tokens", {})
            tok_str = ""
            if tokens.get("input") or tokens.get("output"):
                tok_str = f", {tokens.get('input', 0)}+{tokens.get('output', 0)} tok"
            lines.append(
                f"  {a['name']} ({a.get('model', '?')}) — "
                f"confidence: {a['confidence']}, {a['response_time']}s{tok_str}{cost_str}"
            )
            summary = a.get("summary", "")
            if summary and len(summary) > 10:
                # Show first ~150 chars of their take
                lines.append(f'    "{summary[:150]}..."')

    # --- Consensus ---
    consensus = intel.get("consensus", {})
    if consensus.get("level"):
        lines.append("")
        level = consensus["level"].upper()
        desc = consensus.get("description", "")
        lines.append(f"CONSENSUS: {level}")
        if desc:
            lines.append(f"  {desc}")
        if consensus.get("divergent_agents"):
            lines.append(f"  Divergent: {', '.join(consensus['divergent_agents'])}")

    # --- Learning ---
    learning = intel.get("learning", {})
    if learning:
        lines.append("")
        extracted = learning.get("patterns_extracted", 0)
        tags = learning.get("tags", [])
        total = learning.get("total_patterns", 0)
        if extracted:
            lines.append(f"LEARNED: {extracted} new pattern(s) extracted")
            if tags:
                lines.append(f"  Tags: {', '.join(tags)}")
        elif learning.get("stored"):
            lines.append("LEARNED: Pattern stored in memory")
        if total:
            lines.append(f"  Memory now has {total} solution patterns")

    # --- Cost ---
    cost = intel.get("cost", {})
    if cost.get("total", 0) > 0:
        lines.append("")
        lines.append(f"COST: ${cost['total']:.4f} total")
        if cost.get("breakdown"):
            parts = [f"{c['agent']}: ${c['cost']:.4f}" for c in cost["breakdown"] if c["cost"] > 0]
            if parts:
                lines.append(f"  {' | '.join(parts)}")

    # --- Session ---
    session = intel.get("session", {})
    if session:
        lines.append("")
        lines.append(f"SESSION: {session.get('id', '?')} ({session.get('turns', 0)} turns)")
        if session.get("has_summary"):
            lines.append("  Older turns summarized for context efficiency")

    lines.append("")
    lines.append("=" * 50)

    return "\n".join(lines)


async def handle_tool_call(name: str, arguments: Dict[str, Any]) -> str:
    """Handle a tool call and return the result"""
    global engine, fixer, memory
    logger.info(f"Tool call: {name} with args: {json.dumps(arguments)[:200]}")

    try:
        if name == "ai_team_collaborate":
            team = get_team()
            # If project specified, set it for memory lookup + context injection
            project = arguments.get("project", "")
            context = arguments.get("context", "")
            if project:
                team.project_name = project
                # Auto-inject project context from stored profile
                profile = project_ctx.get_profile(project)
                if profile:
                    project_block = profile.generate_context_block()
                    system_hint = profile.generate_system_prompt()
                    if project_block:
                        context = f"{project_block}\n\n{context}" if context else project_block
                    if system_hint:
                        context = f"{system_hint}\n\n{context}" if context else system_hint
            session_id = arguments.get("session_id", "") or None
            result = await team.collaborate(
                prompt=arguments["prompt"],
                mode=arguments.get("mode", "parallel"),
                context=context,
                session_id=session_id,
            )

            # Build visible intelligence report
            intel = getattr(result, 'intelligence', {})
            intel_report = format_intelligence_report(intel, result)

            return json.dumps({
                "success": result.success,
                "task_id": result.task_id,
                "response": result.final_answer,
                "intelligence_report": intel_report,
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
                memory = MemorySystem(use_firestore=bool(os.getenv("GOOGLE_APPLICATION_CREDENTIALS")))

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
                memory = MemorySystem(use_firestore=bool(os.getenv("GOOGLE_APPLICATION_CREDENTIALS")))

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
                memory = MemorySystem(use_firestore=bool(os.getenv("GOOGLE_APPLICATION_CREDENTIALS")))

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

        elif name == "load_project_context":
            project_name = arguments["project_name"]
            project_path = arguments["project_path"]
            key_patterns = arguments.get("key_patterns", [])
            files = arguments.get("files", [])
            max_lines = arguments.get("max_lines", 50)

            profile = project_ctx.load_project_files(
                profile_name=project_name,
                project_path=project_path,
                file_patterns=files if files else None,
                max_lines_per_file=max_lines,
            )
            if key_patterns:
                profile.key_patterns = key_patterns
                project_ctx.save_profile(profile)

            return json.dumps({
                "success": True,
                "project": project_name,
                "tech_stack": profile.tech_stack,
                "files_loaded": list(profile.key_files.keys()),
                "patterns_count": len(profile.key_patterns),
                "message": f"Loaded {len(profile.key_files)} files for '{project_name}'. Use project='{project_name}' in collaborate calls.",
            }, indent=2)

        elif name == "verify_code":
            import subprocess
            import tempfile
            project_path = arguments["project_path"]
            check_type = arguments.get("check_type", "all")
            files = arguments.get("files", [])
            results = []

            if check_type in ("python_import", "python_syntax", "all"):
                # Check Python imports
                py_dir = project_path
                for sub in ["backend", "app", "src"]:
                    candidate = os.path.join(project_path, sub)
                    if os.path.isdir(candidate):
                        py_dir = candidate
                        break

                if files:
                    for f in files:
                        if f.endswith(".py"):
                            try:
                                r = subprocess.run(
                                    [sys.executable, "-c", f"import ast; ast.parse(open('{os.path.join(project_path, f)}').read())"],
                                    capture_output=True, text=True, timeout=10
                                )
                                if r.returncode == 0:
                                    results.append({"file": f, "check": "syntax", "status": "pass"})
                                else:
                                    results.append({"file": f, "check": "syntax", "status": "fail", "error": r.stderr[:500]})
                            except Exception as e:
                                results.append({"file": f, "check": "syntax", "status": "error", "error": str(e)})
                else:
                    # Run a general import check on all Python files in the main dir
                    try:
                        r = subprocess.run(
                            [sys.executable, "-m", "py_compile", "--help"],
                            capture_output=True, text=True, timeout=5
                        )
                        # Check syntax of all .py files
                        for py_file in sorted(Path(py_dir).rglob("*.py"))[:20]:
                            try:
                                r = subprocess.run(
                                    [sys.executable, "-m", "py_compile", str(py_file)],
                                    capture_output=True, text=True, timeout=10
                                )
                                if r.returncode != 0:
                                    results.append({"file": str(py_file.relative_to(project_path)), "check": "compile", "status": "fail", "error": r.stderr[:300]})
                            except Exception:
                                pass
                        if not any(r["status"] == "fail" for r in results):
                            results.append({"check": "python_compile", "status": "pass", "files_checked": min(20, len(list(Path(py_dir).rglob("*.py"))))})
                    except Exception as e:
                        results.append({"check": "python", "status": "error", "error": str(e)})

            if check_type in ("npm_build", "all"):
                # Check frontend build
                frontend_dir = None
                for sub in ["frontend", "client", "web", ""]:
                    candidate = os.path.join(project_path, sub) if sub else project_path
                    if os.path.exists(os.path.join(candidate, "package.json")):
                        frontend_dir = candidate
                        break

                if frontend_dir:
                    try:
                        r = subprocess.run(
                            ["npm", "run", "build"],
                            capture_output=True, text=True, timeout=120,
                            cwd=frontend_dir
                        )
                        if r.returncode == 0:
                            results.append({"check": "npm_build", "status": "pass"})
                        else:
                            error_lines = r.stderr.splitlines()[-10:] if r.stderr else r.stdout.splitlines()[-10:]
                            results.append({"check": "npm_build", "status": "fail", "error": "\n".join(error_lines)})
                    except subprocess.TimeoutExpired:
                        results.append({"check": "npm_build", "status": "timeout"})
                    except Exception as e:
                        results.append({"check": "npm_build", "status": "error", "error": str(e)})

            all_pass = all(r.get("status") == "pass" for r in results)
            return json.dumps({
                "success": all_pass,
                "results": results,
                "summary": "All checks passed" if all_pass else "Some checks failed",
            }, indent=2)

        elif name == "memory_curate":
            if memory is None:
                memory = MemorySystem(use_firestore=bool(os.getenv("GOOGLE_APPLICATION_CREDENTIALS")))

            project_filter = arguments.get("project", "all")
            dry_run = arguments.get("dry_run", True)

            stats_before = memory.get_statistics()
            solutions = memory._solutions_cache
            curated_count = 0
            pruned_count = 0
            consolidated = []

            # Find solutions with overly long steps (auto-captured full responses)
            verbose_solutions = []
            clean_solutions = []
            for s in solutions:
                has_long_steps = any(len(step) > 500 for step in s.solution_steps)
                if project_filter != "all" and project_filter not in s.projects_used:
                    clean_solutions.append(s)
                    continue
                if has_long_steps and not s.best_practices:
                    verbose_solutions.append(s)
                else:
                    clean_solutions.append(s)

            # Find near-duplicate solutions (same problem_pattern prefix)
            seen_patterns = {}
            duplicates = []
            for s in clean_solutions:
                key = s.problem_pattern[:80].lower().strip()
                if key in seen_patterns:
                    duplicates.append(s)
                else:
                    seen_patterns[key] = s

            if not dry_run:
                # Actually prune verbose solutions and duplicates
                from ai_dev_team.memory.system import tokenize
                kept = [s for s in solutions if s not in verbose_solutions and s not in duplicates]
                memory._solutions_cache = kept
                # Rebuild TF-IDF index
                memory._solution_tokens = [
                    tokenize(f"{s.problem_pattern} {' '.join(s.solution_steps)}")
                    for s in kept
                ]
                pruned_count = len(verbose_solutions) + len(duplicates)

            return json.dumps({
                "success": True,
                "dry_run": dry_run,
                "total_solutions": len(solutions),
                "verbose_entries": len(verbose_solutions),
                "duplicate_entries": len(duplicates),
                "would_prune": len(verbose_solutions) + len(duplicates),
                "would_keep": len(solutions) - len(verbose_solutions) - len(duplicates),
                "message": f"{'Would prune' if dry_run else 'Pruned'} {len(verbose_solutions)} verbose + {len(duplicates)} duplicate entries. "
                           f"Run with dry_run=false to apply.",
            }, indent=2)

        elif name == "ai_team_benchmark":
            team = get_team()
            from ai_dev_team.routing.benchmark import BenchmarkRunner
            runner = BenchmarkRunner(team)
            task_type = arguments.get("task_type", "coding")
            agent_names = arguments.get("agents")
            suite = await runner.run_benchmark(task_type, agent_names=agent_names)
            return json.dumps({
                "success": True,
                "suite_id": suite.suite_id,
                "task_type": suite.task_type,
                "total_results": len(suite.results),
                "agent_rankings": suite.agent_rankings,
                "best_agent": max(suite.agent_rankings, key=suite.agent_rankings.get) if suite.agent_rankings else None,
                "details": [
                    {
                        "agent": r.agent_name,
                        "prompt": r.prompt_id,
                        "composite": r.composite_score,
                        "keyword": r.keyword_score,
                        "structure": r.structure_score,
                        "eval": r.eval_score,
                        "time": round(r.response_time, 2),
                        "cost": r.cost,
                    }
                    for r in suite.results
                ],
            }, indent=2)

        elif name == "ai_team_routing_table":
            from ai_dev_team.routing.benchmark import BenchmarkRunner
            team = get_team()
            runner = BenchmarkRunner(team)
            table = runner.get_routing_table()
            if not table:
                return json.dumps({
                    "message": "No benchmark data yet. Run ai_team_benchmark first to build the routing table.",
                    "routing_table": {}
                }, indent=2)
            return json.dumps({
                "routing_table": table,
                "summary": {
                    task_type: data.get("best_agent", "unknown")
                    for task_type, data in table.items()
                },
            }, indent=2)

        elif name == "ai_team_costs":
            from ai_dev_team.routing.cost_tracker import get_cost_tracker
            tracker = get_cost_tracker()
            period = arguments.get("period", "all")
            if period == "today":
                return json.dumps(tracker.get_daily_report(), indent=2)
            elif period == "week":
                return json.dumps(tracker.get_weekly_report(), indent=2)
            elif period == "month":
                return json.dumps(tracker.get_monthly_report(), indent=2)
            else:
                return json.dumps(tracker.get_statistics(), indent=2)

        elif name == "ai_team_rate":
            if memory is None:
                memory = MemorySystem(use_firestore=bool(os.getenv("GOOGLE_APPLICATION_CREDENTIALS")))
            task_id = arguments["task_id"]
            rating = arguments["rating"]
            note = arguments.get("note", "")
            result = memory.rate_interaction(task_id, rating, note)
            # Also run decay and auto-prune opportunistically
            decayed = memory.decay_old_patterns(days_threshold=30)
            pruned = memory.auto_prune(min_quality=0.15, min_age_days=14)
            result["maintenance"] = {"decayed": decayed, "pruned": pruned}
            return json.dumps(result, indent=2)

        elif name == "ai_team_quality_report":
            if memory is None:
                memory = MemorySystem(use_firestore=bool(os.getenv("GOOGLE_APPLICATION_CREDENTIALS")))
            report = memory.get_quality_report()
            return json.dumps(report, indent=2)

        elif name == "ai_team_sessions":
            from ai_dev_team.sessions import get_session_manager
            sm = get_session_manager()
            action = arguments.get("action", "list")
            sid = arguments.get("session_id", "")

            if action == "delete" and sid:
                sm.delete(sid)
                return json.dumps({"success": True, "message": f"Deleted session {sid}"})
            elif action == "get" and sid:
                session = sm.get_or_create(sid)
                return json.dumps({
                    "session_id": session.session_id,
                    "project": session.project,
                    "turns": session.turn_count,
                    "created": session.created,
                    "updated": session.updated,
                    "summary": session.summary,
                    "recent_turns": [
                        {"role": t.role, "content": t.content[:200], "agents": t.agents}
                        for t in session.turns[-10:]
                    ],
                }, indent=2)
            else:
                sessions = sm.list_sessions()
                return json.dumps({"sessions": sessions, "total": len(sessions)}, indent=2)

        elif name == "ai_team_review_pr":
            team = get_team()
            pr = arguments["pr"]
            repo = arguments.get("repo", "")
            focus = arguments.get("focus", ["security", "bugs", "performance"])

            # Pull PR diff via gh CLI
            import subprocess
            gh_args = ["gh", "pr", "diff", str(pr)]
            if repo:
                gh_args.extend(["-R", repo])
            try:
                diff_result = subprocess.run(
                    gh_args, capture_output=True, text=True, timeout=30
                )
                if diff_result.returncode != 0:
                    return json.dumps({"error": f"gh pr diff failed: {diff_result.stderr[:500]}"})
                diff_text = diff_result.stdout
            except FileNotFoundError:
                return json.dumps({"error": "gh CLI not installed. Install: https://cli.github.com"})
            except subprocess.TimeoutExpired:
                return json.dumps({"error": "gh pr diff timed out"})

            # Also get PR info
            info_args = ["gh", "pr", "view", str(pr), "--json", "title,body,author,files"]
            if repo:
                info_args.extend(["-R", repo])
            try:
                info_result = subprocess.run(
                    info_args, capture_output=True, text=True, timeout=15
                )
                pr_info = json.loads(info_result.stdout) if info_result.returncode == 0 else {}
            except Exception:
                pr_info = {}

            # Cap diff size
            if len(diff_text) > 15000:
                diff_text = diff_text[:15000] + "\n... (diff truncated)"

            focus_str = ", ".join(focus)
            pr_title = pr_info.get("title", f"PR #{pr}")

            review_prompt = f"""REVIEW THIS PULL REQUEST

Title: {pr_title}
Author: {pr_info.get('author', {}).get('login', 'unknown')}
Files changed: {len(pr_info.get('files', []))}

Focus areas: {focus_str}

For each issue found, provide:
- Severity (critical/high/medium/low)
- File and line context
- What's wrong
- How to fix it

Also provide an overall assessment: APPROVE, REQUEST_CHANGES, or COMMENT.

DIFF:
```diff
{diff_text}
```"""

            result = await team.collaborate(
                prompt=review_prompt,
                mode="parallel",
            )

            return json.dumps({
                "success": result.success,
                "pr": pr_title,
                "review": result.final_answer,
                "agents": result.participating_agents,
                "confidence": result.confidence_score,
                "intelligence_report": format_intelligence_report(
                    getattr(result, 'intelligence', {}), result
                ),
            }, indent=2)

        elif name == "ai_team_create_persona":
            from ai_dev_team.personas import get_persona_manager
            pm = get_persona_manager()
            team = get_team()

            persona = pm.create_persona(
                name=arguments["name"],
                role=arguments["role"],
                system_prompt=arguments["system_prompt"],
                model_backend=arguments.get("model", "chatgpt"),
                capabilities=arguments.get("capabilities", []),
            )

            # Register as a real agent
            agent = pm.create_agent(persona)
            if agent:
                team.register_agent(agent)

            return json.dumps({
                "success": True,
                "persona": persona.name,
                "role": persona.role,
                "model": persona.model_backend,
                "message": f"Created persona '{persona.name}' and registered as agent. Use in collaborate calls.",
                "total_personas": len(pm.list_personas()),
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
