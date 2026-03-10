"""
El Gringo MCP Server
====================
Exposes El Gringo's multi-agent AI team as native MCP tools.
Claude Code can call these directly — no curl needed.

Setup in ~/.claude/mcp.json or project .mcp.json:
{
  "mcpServers": {
    "el-gringo": {
      "command": "python3",
      "args": ["/Users/fredtaylor/Development/Projects/ElGringo/elgringo/server/mcp_server.py"],
      "env": {
        "ELGRINGO_API_URL": "https://ai.chatterfix.com",
        "ELGRINGO_API_KEY": "your-api-key-here"
      }
    }
  }
}
"""

import json
import logging
import os
import sys
import urllib.parse
import urllib.request
import urllib.error
from typing import Optional

from mcp.server.fastmcp import FastMCP

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stderr)],
)
logger = logging.getLogger("el-gringo-mcp")

mcp = FastMCP("el-gringo")

BASE_URL = os.environ.get("ELGRINGO_API_URL", "https://ai.chatterfix.com")
API_KEY = os.environ.get("ELGRINGO_API_KEY", "")

if not API_KEY:
    logger.warning("ELGRINGO_API_KEY not set — API calls will fail. Set it in your MCP config.")


def _api(method: str, path: str, body: Optional[dict] = None, params: Optional[dict] = None) -> dict:
    """Make an API call to El Gringo. Uses urllib so we have zero extra deps."""
    url = f"{BASE_URL}{path}"
    if params:
        url = f"{url}?{urllib.parse.urlencode(params)}"
    headers = {"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"}
    data = json.dumps(body).encode() if body else None
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    logger.info(f"{method} {path}")
    try:
        with urllib.request.urlopen(req, timeout=300) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        error_body = e.read().decode() if e.fp else str(e)
        logger.error(f"HTTP {e.code} from {path}: {error_body[:200]}")
        return {"error": f"HTTP {e.code}: {error_body}"}
    except urllib.error.URLError as e:
        logger.error(f"Connection failed for {path}: {e.reason}")
        return {"error": f"Connection failed: {e.reason}"}
    except Exception as e:
        logger.error(f"Unexpected error for {path}: {e}")
        return {"error": str(e)}


# ── Response Formatters ──────────────────────────────────────────────

def _fmt_collaborate(result: dict) -> str:
    """Format a /v1/collaborate response."""
    if "error" in result:
        return f"Error: {result['error']}"
    agents = ", ".join(result.get("agents_used", []))
    confidence = result.get("confidence", 0)
    answer = result.get("answer", "")
    return f"[Agents: {agents} | Confidence: {confidence:.0%}]\n\n{answer}"


def _fmt_code_task(result: dict) -> str:
    """Format a /v1/code/task response."""
    if "error" in result:
        return f"Error: {result['error']}"
    status = result.get("status", "unknown")
    summary = result.get("summary", "")
    agents = ", ".join(result.get("agents_used", []))
    iterations = result.get("iterations", 0)
    files_changed = result.get("files_changed", [])
    errors = result.get("errors", [])
    parts = [f"Status: {status}", f"Summary: {summary}", f"Agents: {agents}", f"Iterations: {iterations}"]
    if files_changed:
        parts.append(f"Files changed: {len(files_changed)}")
        for fc in files_changed:
            parts.append(f"  - {fc.get('path', '?')} ({fc.get('action', '?')})")
    if result.get("test_results"):
        tr = result["test_results"]
        parts.append(f"Tests: {'PASS' if tr.get('passed') else 'FAIL'} -- {tr.get('command', '')}")
    if errors:
        parts.append(f"Errors: {'; '.join(errors[:3])}")
    return "\n".join(parts)


def _fmt_review(result: dict) -> str:
    """Format a /v1/code/review response."""
    if "error" in result:
        return f"Error: {result['error']}"
    agents = ", ".join(result.get("agents_used", []))
    files = result.get("files_reviewed", 0)
    return f"[{files} files reviewed by {agents}]\n\n{result.get('findings', 'No findings')}"


# ── Public Tools (elgringo_*) ────────────────────────────────────────

@mcp.tool()
def elgringo_collaborate(prompt: str, context: str = "", mode: str = "parallel") -> str:
    """
    Multi-agent AI collaboration. Sends a task to El Gringo's AI team
    (ChatGPT + Grok + Llama + Claude if configured) and returns their merged answer.

    Args:
        prompt: The task or question for the AI team
        context: Additional context (code snippets, error messages, etc.)
        mode: Collaboration mode:
            - turbo           Fastest (<2s). Picks the single best agent, skips synthesis. Auto-selected for low-complexity high-confidence tasks.
            - parallel        Fast (~12s). All agents answer simultaneously, results merged.
            - sequential      Each agent builds on the previous answer.
            - single          Fast (~2s). Auto-routes to one best-fit agent.
            - debate          Slow (~60s). Agents argue positions, best argument wins.
            - consensus       Slow (60s+). Agents must reach agreement.
            - peer_review     Agents critique and refine a draft answer.
            - brainstorming   Creative ideation — agents generate diverse ideas.
            - expert_panel    Each agent acts as a domain expert, panel discussion.
            - devils_advocate Slow (~30s). One agent steelmans the opposite position.
    """
    return _fmt_collaborate(_api("POST", "/v1/collaborate", {
        "prompt": prompt, "context": context, "mode": mode,
    }))


@mcp.tool()
def elgringo_code_task(
    task: str, project_path: str, files_to_read: str = "",
    run_tests: bool = True, auto_commit: bool = False, max_iterations: int = 3,
) -> str:
    """
    Execute a coding task: read files, make edits, run tests, self-correct.

    Args:
        task: What needs to be done (bug fix, feature, refactor)
        project_path: Absolute path to the project on the server
        files_to_read: Comma-separated file paths to read first
        run_tests: Run tests after making changes
        auto_commit: Auto-commit if tests pass
        max_iterations: Max self-correction attempts (1-5)
    """
    files = [f.strip() for f in files_to_read.split(",") if f.strip()] if files_to_read else []
    return _fmt_code_task(_api("POST", "/v1/code/task", {
        "task": task, "project_path": project_path, "files_to_read": files,
        "run_tests": run_tests, "auto_commit": auto_commit, "max_iterations": max_iterations,
    }))


@mcp.tool()
def elgringo_review(project_path: str, focus: str = "bugs", glob_pattern: str = "**/*.py") -> str:
    """
    Multi-agent code review. El Gringo reads the actual files and reviews them.

    Args:
        project_path: Absolute path to the project on the server
        focus: Review focus -- bugs, security, performance, quality
        glob_pattern: File pattern to review (e.g. **/*.py, routers/*.py)
    """
    return _fmt_review(_api("POST", "/v1/code/review", body={
        "project_path": project_path, "focus": focus, "glob_pattern": glob_pattern,
    }))


@mcp.tool()
def elgringo_plan(task: str, project_path: str, files_to_read: str = "") -> str:
    """
    Plan a coding task without executing changes (dry run).

    Args:
        task: What needs to be done
        project_path: Absolute path to the project on the server
        files_to_read: Comma-separated file paths to read for context
    """
    files = [f.strip() for f in files_to_read.split(",") if f.strip()] if files_to_read else []
    result = _api("POST", "/v1/code/plan", {
        "task": task, "project_path": project_path, "files_to_read": files, "run_tests": False,
    })
    if "error" in result:
        return f"Error: {result['error']}"
    agents = ", ".join(result.get("agents_used", []))
    summary = result.get("summary", "")
    plan = result.get("plan", [])
    parts = [f"[Agents: {agents}]", "", summary]
    if plan:
        parts.append("\nPlan:")
        for step in plan[:20]:
            parts.append(f"  {step}")
    return "\n".join(parts)


@mcp.tool()
def elgringo_project_info(project_path: str) -> str:
    """
    Get project structure, languages, and metadata.

    Args:
        project_path: Absolute path to the project on the server
    """
    result = _api("GET", "/v1/code/project-info", params={"project_path": project_path})
    if "error" in result:
        return f"Error: {result['error']}"
    langs = result.get("languages", {})
    lang_str = ", ".join(f"{k}: {v}" for k, v in list(langs.items())[:8])
    structure = result.get("structure", [])
    parts = [
        f"Project: {result.get('project_path', project_path)}",
        f"Files: {result.get('files_count', '?')}",
        f"Languages: {lang_str}",
        f"Tests: {'yes' if result.get('has_tests') else 'no'} | Git: {'yes' if result.get('has_git') else 'no'}",
    ]
    if structure:
        parts.append("\nStructure:")
        for s in structure[:30]:
            parts.append(f"  {s}")
    return "\n".join(parts)


@mcp.tool()
def elgringo_ask(prompt: str, context: str = "") -> str:
    """
    Ask a single AI agent a question. Auto-routes to the best agent.

    Args:
        prompt: Your question
        context: Additional context
    """
    result = _api("POST", "/v1/ask", {"prompt": prompt, "context": context})
    if "error" in result:
        return f"Error: {result['error']}"
    agents = ", ".join(result.get("agents_used", []))
    return f"[Agent: {agents}]\n\n{result.get('answer', '')}"


# ── AI Team Tools (ai_team_*) ───────────────────────────────────────
# These preserve the tool names from the old servers/mcp_server.py
# so existing ~/.claude/mcp.json configs keep working.

@mcp.tool()
def ai_team_health() -> str:
    """Check El Gringo API health and list available agents with their capabilities."""
    health = _api("GET", "/v1/health")
    if "error" in health:
        return f"Error: {health['error']}"
    agents_result = _api("GET", "/v1/agents")
    if isinstance(agents_result, list):
        agent_lines = [f"  - {a['name']} ({a['role']}): {', '.join(a.get('capabilities', []))}" for a in agents_result]
        agent_str = "\n".join(agent_lines)
    else:
        agent_str = "  (unavailable)"
    return f"Status: {health.get('status', 'unknown')} | v{health.get('version', '?')}\nAgents:\n{agent_str}"


@mcp.tool()
def ai_team_build(prompt: str, context: str = "") -> str:
    """
    Full AI team parallel build. All agents work on the task simultaneously
    and results are merged into a unified response.

    Args:
        prompt: The build task or feature request
        context: Code, specs, or requirements for context
    """
    return _fmt_collaborate(_api("POST", "/v1/collaborate", {
        "prompt": prompt, "context": context, "mode": "parallel",
    }))


@mcp.tool()
def ai_team_execute(prompt: str, context: str = "", agents: str = "", mode: str = "parallel") -> str:
    """
    Execute a task with the AI team, optionally specifying which agents to use.

    Args:
        prompt: The task to execute
        context: Additional context
        agents: Comma-separated agent names (empty = all agents).
                Available: chatgpt-coder, gemini-creative, grok-reasoner, grok-coder,
                llama-llama-3-3-70b-groq, claude-analyst (requires ANTHROPIC_API_KEY on server)
        mode: Collaboration mode:
            - turbo           Fastest (<2s). Picks the single best agent, skips synthesis. Auto-selected for low-complexity high-confidence tasks.
            - parallel        Fast (~12s). All agents answer simultaneously, results merged.
            - sequential      Each agent builds on the previous answer.
            - single          Fast (~2s). Auto-routes to one best-fit agent.
            - debate          Agents argue positions, best argument wins.
            - consensus       Slow (60s+). Agents must reach agreement.
            - peer_review     One agent drafts, others critique and refine.
            - brainstorming   Creative ideation — agents generate diverse ideas.
            - expert_panel    Each agent acts as a domain expert, panel discussion.
            - devils_advocate One agent steelmans the opposite position.
    """
    body: dict = {"prompt": prompt, "context": context, "mode": mode}
    if agents:
        body["agents"] = [a.strip() for a in agents.split(",") if a.strip()]
    return _fmt_collaborate(_api("POST", "/v1/collaborate", body))


@mcp.tool()
def ai_team_generate(
    task: str, project_path: str, files_to_read: str = "",
    run_tests: bool = True, auto_commit: bool = False,
) -> str:
    """
    Generate a feature or implement a task using the AI coding agent.
    Reads code, makes edits, tests, and self-corrects.

    Args:
        task: Feature or task description
        project_path: Absolute path to the project on the server
        files_to_read: Comma-separated file paths to read first
        run_tests: Run tests after changes
        auto_commit: Auto-commit if tests pass
    """
    files = [f.strip() for f in files_to_read.split(",") if f.strip()] if files_to_read else []
    return _fmt_code_task(_api("POST", "/v1/code/task", {
        "task": task, "project_path": project_path, "files_to_read": files,
        "run_tests": run_tests, "auto_commit": auto_commit, "max_iterations": 3,
    }))


@mcp.tool()
def ai_team_review(project_path: str, focus: str = "bugs", glob_pattern: str = "**/*.py") -> str:
    """
    Multi-agent code review by the AI team.

    Args:
        project_path: Absolute path to the project on the server
        focus: Review focus -- bugs, security, performance, quality
        glob_pattern: File pattern to review
    """
    return _fmt_review(_api("POST", "/v1/code/review", body={
        "project_path": project_path, "focus": focus, "glob_pattern": glob_pattern,
    }))


@mcp.tool()
def ai_team_debug(prompt: str, error_message: str = "", stacktrace: str = "", code: str = "") -> str:
    """
    Debug an issue with the full AI team. Provide error details and
    the team will analyze root cause and suggest fixes.

    Args:
        prompt: Description of the bug or issue
        error_message: The error message received
        stacktrace: Full stack trace if available
        code: Relevant code snippet
    """
    context_parts = []
    if error_message:
        context_parts.append(f"ERROR: {error_message}")
    if stacktrace:
        context_parts.append(f"STACKTRACE:\n{stacktrace}")
    if code:
        context_parts.append(f"CODE:\n{code}")
    context = "\n\n".join(context_parts)
    return _fmt_collaborate(_api("POST", "/v1/collaborate", {
        "prompt": f"Debug this issue: {prompt}",
        "context": context,
        "mode": "peer_review",  # one agent diagnoses, others verify
    }))


@mcp.tool()
def ai_team_architect(prompt: str, context: str = "", constraints: str = "") -> str:
    """
    Get architecture recommendations from the AI team. Useful for
    system design, API design, database schema, and tech stack decisions.

    Args:
        prompt: Architecture question or design challenge
        context: Current system context, requirements, or constraints
        constraints: Specific constraints (budget, timeline, tech stack)
    """
    full_context = context
    if constraints:
        full_context = f"{context}\n\nCONSTRAINTS: {constraints}" if context else f"CONSTRAINTS: {constraints}"
    return _fmt_collaborate(_api("POST", "/v1/collaborate", {
        "prompt": f"Architecture review: {prompt}",
        "context": full_context,
        "mode": "expert_panel",  # each agent plays a domain expert role
    }))


@mcp.tool()
def ai_team_brainstorm(topic: str, context: str = "", num_ideas: int = 5) -> str:
    """
    Brainstorm ideas with the full AI team. Each agent contributes
    unique perspectives for creative problem solving.

    Args:
        topic: The topic or problem to brainstorm about
        context: Background info or constraints
        num_ideas: Target number of ideas to generate
    """
    return _fmt_collaborate(_api("POST", "/v1/collaborate", {
        "prompt": f"Brainstorm {num_ideas} ideas for: {topic}",
        "context": context,
        "mode": "brainstorming",  # dedicated creative ideation mode
    }))


@mcp.tool()
def ai_team_security_audit(project_path: str, glob_pattern: str = "**/*.py") -> str:
    """
    Run a security-focused code audit with the AI team. Checks for
    vulnerabilities, injection risks, auth issues, and data exposure.

    Args:
        project_path: Absolute path to the project on the server
        glob_pattern: File pattern to audit
    """
    return _fmt_review(_api("POST", "/v1/code/review", body={
        "project_path": project_path, "focus": "security", "glob_pattern": glob_pattern,
    }))


@mcp.tool()
def elgringo_stream(prompt: str, agent: str = "") -> str:
    """
    Stream a response token-by-token from a single agent. Fastest option (~2s)
    for quick questions. Returns the full assembled response.

    Args:
        prompt: The question or task
        agent: Specific agent name (empty = auto-route). Options:
               chatgpt-coder, gemini-creative, grok-reasoner, grok-coder,
               llama-llama-3-3-70b-groq,
               claude-analyst (available if ANTHROPIC_API_KEY set on server)
    """
    url = f"{BASE_URL}/v1/stream"
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json",
        "Accept": "text/event-stream",
    }
    body: dict = {"prompt": prompt}
    if agent:
        body["agent"] = agent
    data = json.dumps(body).encode()
    req = urllib.request.Request(url, data=data, headers=headers, method="POST")
    logger.info(f"POST /v1/stream (agent={agent or 'auto'})")
    try:
        tokens = []
        used_agent = ""
        with urllib.request.urlopen(req, timeout=60) as resp:
            for raw_line in resp:
                line = raw_line.decode().strip()
                if not line.startswith("data:"):
                    continue
                try:
                    event = json.loads(line[5:].strip())
                except json.JSONDecodeError:
                    continue
                if event.get("type") == "token":
                    tokens.append(event.get("content", ""))
                elif event.get("type") == "start":
                    used_agent = event.get("agent", "")
                elif event.get("type") == "done":
                    break
        answer = "".join(tokens)
        prefix = f"[Agent: {used_agent}]\n\n" if used_agent else ""
        return f"{prefix}{answer}"
    except urllib.error.HTTPError as e:
        error_body = e.read().decode() if e.fp else str(e)
        return f"Error: HTTP {e.code}: {error_body}"
    except Exception as e:
        return f"Error: {e}"


@mcp.tool()
def elgringo_feedback(node_id: str, success: bool, feedback: str = "") -> str:
    """Record whether a previous El Gringo suggestion worked or not. This improves future results by adjusting confidence scores. Use after applying a suggestion from diagnose, refactor, or other tools."""
    data = _api("POST", "/v1/feedback", {
        "node_id": node_id,
        "success": success,
        "feedback": feedback,
    })
    if isinstance(data, str) and data.startswith("ERROR"):
        return data
    if "error" in data:
        return f"Error: {data['error']}"
    return (
        f"Feedback recorded for {node_id}\n"
        f"Success: {'Yes' if success else 'No'}\n"
        f"New confidence: {data.get('new_confidence', 'N/A')}"
    )


@mcp.tool()
def elgringo_diagnose(
    error_message: str, stacktrace: str = "", project_path: str = "",
    language: str = "", files_context: str = "",
) -> str:
    """
    AI debugger: multi-agent root cause analysis for errors and bugs.
    Sends the error to the full AI team for diagnosis.

    Args:
        error_message: The error message to diagnose
        stacktrace: Full stack trace if available
        project_path: Absolute path to the project (for reading files)
        language: Programming language (auto-detect if empty)
        files_context: Comma-separated file paths to read for context
    """
    files = [f.strip() for f in files_context.split(",") if f.strip()] if files_context else []
    result = _api("POST", "/v1/diagnose", {
        "error_message": error_message,
        "stacktrace": stacktrace,
        "project_path": project_path,
        "language": language,
        "files_context": files,
    })
    if "error" in result:
        return f"Error: {result['error']}"
    agents = ", ".join(result.get("agents_used", []))
    confidence = result.get("confidence", 0)
    parts = [
        f"[Agents: {agents} | Confidence: {confidence:.0%} | {result.get('total_time', 0):.1f}s]",
        "",
        f"## Root Cause",
        result.get("root_cause", "Unknown"),
        "",
        f"## Explanation",
        result.get("explanation", ""),
    ]
    if result.get("suggested_fix"):
        parts.extend(["", "## Suggested Fix", result["suggested_fix"]])
    if result.get("related_files"):
        parts.extend(["", f"Related files: {', '.join(result['related_files'])}"])
    return "\n".join(parts)


@mcp.tool()
def elgringo_changelog(
    project_path: str, git_range: str = "HEAD~10..HEAD",
    audience: str = "developer", format: str = "markdown",
) -> str:
    """
    Generate changelog from git history for developers or stakeholders.
    Analyzes commits and categorizes changes automatically.

    Args:
        project_path: Absolute path to the project (must be a git repo)
        git_range: Git commit range (e.g. HEAD~10..HEAD, v1.0..HEAD)
        audience: Target audience — developer (technical), stakeholder (business), user (simple)
        format: Output format — markdown or json
    """
    result = _api("POST", "/v1/changelog", {
        "project_path": project_path,
        "git_range": git_range,
        "audience": audience,
        "format": format,
    })
    if "error" in result:
        return f"Error: {result['error']}"
    commits = result.get("commits_analyzed", 0)
    parts = [
        f"[{commits} commits analyzed | {result.get('total_time', 0):.1f}s]",
        "",
        result.get("changelog", ""),
    ]
    categories = result.get("categories", {})
    non_empty = {k: v for k, v in categories.items() if v}
    if non_empty:
        parts.extend(["", "---", f"Categories: {', '.join(f'{k} ({len(v)})' for k, v in non_empty.items())}"])
    return "\n".join(parts)


@mcp.tool()
def elgringo_refactor(
    project_path: str, focus: str = "all",
    glob_pattern: str = "**/*.py", target_files: str = "",
) -> str:
    """
    Multi-agent refactor analysis: finds complexity, duplication, tech debt.
    Returns prioritized recommendations with effort estimates.

    Args:
        project_path: Absolute path to the project
        focus: Analysis focus — complexity, duplication, performance, security, all
        glob_pattern: File pattern to analyze (e.g. **/*.py, src/**/*.ts)
        target_files: Comma-separated specific files to analyze (overrides glob)
    """
    files = [f.strip() for f in target_files.split(",") if f.strip()] if target_files else []
    result = _api("POST", "/v1/refactor", {
        "project_path": project_path,
        "focus": focus,
        "glob_pattern": glob_pattern,
        "target_files": files,
    })
    if "error" in result:
        return f"Error: {result['error']}"
    agents = ", ".join(result.get("agents_used", []))
    score = result.get("tech_debt_score", 0)
    parts = [
        f"[Agents: {agents} | Tech Debt Score: {score:.0f}/100 | {result.get('total_time', 0):.1f}s]",
        "",
        f"## Summary",
        result.get("summary", ""),
    ]
    recs = result.get("recommendations", [])
    if recs:
        parts.extend(["", f"## Recommendations ({len(recs)})"])
        for i, rec in enumerate(recs, 1):
            priority = rec.get("priority", "medium")
            effort = rec.get("effort", "?")
            parts.append(f"{i}. [{priority.upper()}] `{rec.get('file', '?')}` — {rec.get('issue', '?')}")
            if rec.get("suggestion"):
                parts.append(f"   Fix: {rec['suggestion']} (effort: {effort})")
    return "\n".join(parts)


@mcp.tool()
def elgringo_test_generate(
    project_path: str, target_file: str,
    coverage_focus: str = "edge_cases", test_framework: str = "",
) -> str:
    """
    AI test writer: generates comprehensive tests for any source file.
    Auto-detects test framework and writes tests with proper conventions.

    Args:
        project_path: Absolute path to the project
        target_file: Relative path to the file to generate tests for
        coverage_focus: Test focus — happy_path, edge_cases, comprehensive
        test_framework: Test framework (auto-detect if empty): pytest, jest, go test
    """
    result = _api("POST", "/v1/test-generate", {
        "project_path": project_path,
        "target_file": target_file,
        "coverage_focus": coverage_focus,
        "test_framework": test_framework,
    })
    if "error" in result:
        return f"Error: {result['error']}"
    agents = ", ".join(result.get("agents_used", []))
    count = result.get("tests_count", 0)
    test_path = result.get("test_file_path", "")
    parts = [
        f"[Agents: {agents} | {count} tests | {result.get('total_time', 0):.1f}s]",
        f"Suggested test file: `{test_path}`",
        "",
    ]
    if result.get("test_code"):
        parts.append(result["test_code"])
    areas = result.get("coverage_areas", [])
    if areas:
        parts.extend(["", "## Coverage Areas"])
        for area in areas:
            parts.append(f"- {area}")
    return "\n".join(parts)


@mcp.tool()
def elgringo_deploy_check(
    project_path: str, git_range: str = "HEAD~5..HEAD",
    environment: str = "production",
) -> str:
    """
    Pre-deploy risk assessment with go/no-go recommendation.
    Analyzes git changes, config diffs, and potential risks.

    Args:
        project_path: Absolute path to the project
        git_range: Git range to analyze (e.g. HEAD~5..HEAD)
        environment: Target environment — production, staging, dev
    """
    result = _api("POST", "/v1/deploy-check", {
        "project_path": project_path,
        "git_range": git_range,
        "environment": environment,
    })
    if "error" in result:
        return f"Error: {result['error']}"
    agents = ", ".join(result.get("agents_used", []))
    risk = result.get("risk_score", 0)
    level = result.get("risk_level", "unknown")
    verdict = result.get("go_no_go", "?")
    emoji_map = {"GO": "GO", "NO-GO": "!! NO-GO !!"}
    parts = [
        f"[Agents: {agents} | {result.get('total_time', 0):.1f}s]",
        "",
        f"## Verdict: {emoji_map.get(verdict, verdict)}",
        f"Risk Score: {risk:.1f}/10 ({level})",
        f"Environment: {environment}",
    ]
    findings = result.get("findings", [])
    if findings:
        parts.extend(["", f"## Findings ({len(findings)})"])
        for f in findings:
            sev = f.get("severity", "?")
            parts.append(f"- [{sev.upper()}] {f.get('category', '?')}: {f.get('description', '?')}")
            if f.get("recommendation"):
                parts.append(f"  Recommendation: {f['recommendation']}")
    else:
        parts.append("\nNo specific findings.")
    return "\n".join(parts)


@mcp.tool()
def elgringo_onboard(
    project_path: str, focus: str = "overview", depth: str = "medium",
) -> str:
    """
    Project explainer: architecture, key files, patterns, gotchas for onboarding.
    Helps new developers understand a codebase quickly.

    Args:
        project_path: Absolute path to the project
        focus: What to focus on — overview, architecture, api, frontend, backend
        depth: Detail level — quick (highlights only), medium (enough to contribute), deep (thorough)
    """
    result = _api("POST", "/v1/onboard", {
        "project_path": project_path,
        "focus": focus,
        "depth": depth,
    })
    if "error" in result:
        return f"Error: {result['error']}"
    agents = ", ".join(result.get("agents_used", []))
    parts = [
        f"[Agents: {agents} | Focus: {focus} | Depth: {depth} | {result.get('total_time', 0):.1f}s]",
        "",
        f"## Summary",
        result.get("summary", ""),
    ]
    if result.get("architecture"):
        parts.extend(["", "## Architecture", result["architecture"]])
    key_files = result.get("key_files", [])
    if key_files:
        parts.extend(["", "## Key Files"])
        for kf in key_files:
            imp = kf.get("importance", "medium")
            parts.append(f"- `{kf.get('path', '?')}` [{imp}] — {kf.get('purpose', '?')}")
    patterns = result.get("patterns", [])
    if patterns:
        parts.extend(["", "## Patterns"])
        for p in patterns:
            parts.append(f"- {p}")
    gotchas = result.get("gotchas", [])
    if gotchas:
        parts.extend(["", "## Gotchas"])
        for g in gotchas:
            parts.append(f"- {g}")
    if result.get("getting_started"):
        parts.extend(["", "## Getting Started", result["getting_started"]])
    return "\n".join(parts)


@mcp.tool()
def elgringo_debate(prompt: str, context: str = "", mode: str = "debate") -> str:
    """
    Put a topic, decision, or design to adversarial scrutiny. Agents argue
    opposing positions to surface weaknesses and trade-offs.

    ⚠️  These modes are slow (30–90s) — use for important decisions only.

    Args:
        prompt: The proposition, decision, or design to challenge
        context: Background info, constraints, or existing solution
        mode: Adversarial mode:
            - debate          (~60s) Agents argue positions; strongest argument wins.
            - devils_advocate (~30s) One agent steelmans the opposite position.
            - peer_review     (~20s) One agent proposes, others critique and refine.
    """
    return _fmt_collaborate(_api("POST", "/v1/collaborate", {
        "prompt": prompt, "context": context, "mode": mode,
    }))


# ── Local Dev Tools (no API needed) ────────────────────────────────

def _get_memory():
    """Lazy-load memory system."""
    from elgringo.memory import MemorySystem
    if not hasattr(_get_memory, "_instance"):
        _get_memory._instance = MemorySystem()
    return _get_memory._instance


@mcp.tool()
def memory_search(query: str, search_type: str = "all") -> str:
    """
    Search the AI team's memory for past solutions and mistakes.
    Helps avoid repeating errors and find proven patterns.

    Args:
        query: Search query (e.g. "database connection pooling", "auth bug")
        search_type: What to search — "solutions", "mistakes", or "all"
    """
    import asyncio
    memory = _get_memory()
    parts = []

    if search_type in ("solutions", "all"):
        solutions = asyncio.get_event_loop().run_until_complete(
            memory.find_solution_patterns(query, limit=5)
        ) if asyncio.get_event_loop().is_running() else []
        # Fallback for non-async context
        if not solutions:
            try:
                loop = asyncio.new_event_loop()
                solutions = loop.run_until_complete(memory.find_solution_patterns(query, limit=5))
                loop.close()
            except Exception:
                solutions = []
        if solutions:
            parts.append(f"## Solutions ({len(solutions)} found)")
            for s in solutions:
                steps = "; ".join(s.solution_steps[:3])
                parts.append(f"- **{s.problem_pattern}** (success: {s.success_rate:.0%})\n  Steps: {steps}")
        else:
            parts.append("No matching solutions found.")

    if search_type in ("mistakes", "all"):
        mistakes = []
        try:
            loop = asyncio.new_event_loop()
            mistakes = loop.run_until_complete(memory.find_similar_mistakes({"query": query}, limit=5))
            loop.close()
        except Exception:
            pass
        if mistakes:
            parts.append(f"\n## Mistakes ({len(mistakes)} found)")
            for m in mistakes:
                parts.append(f"- [{m.severity}] **{m.description}**\n  Prevention: {m.prevention_strategy}")
        elif search_type == "mistakes":
            parts.append("No matching mistakes found.")

    stats = memory.get_statistics()
    parts.append(f"\n_Memory: {stats.get('total_solutions', 0)} solutions, {stats.get('total_mistakes', 0)} mistakes_")
    return "\n".join(parts)


@mcp.tool()
def memory_store_solution(problem: str, solution_steps: str, tags: str = "") -> str:
    """
    Store a solution pattern so the AI team remembers it for next time.

    Args:
        problem: The problem pattern (e.g. "FastAPI CORS not working")
        solution_steps: Steps that fixed it, separated by newlines or semicolons
        tags: Comma-separated tags (e.g. "fastapi, cors, python")
    """
    import asyncio
    memory = _get_memory()
    steps = [s.strip() for s in solution_steps.replace(";", "\n").split("\n") if s.strip()]
    tag_list = [t.strip() for t in tags.split(",") if t.strip()] if tags else []

    try:
        loop = asyncio.new_event_loop()
        solution_id = loop.run_until_complete(memory.capture_solution(
            problem_pattern=problem,
            solution_steps=steps,
            success_rate=1.0,
            tags=tag_list,
        ))
        loop.close()
        return f"Stored solution `{solution_id}` for: {problem}\nSteps: {len(steps)} | Tags: {', '.join(tag_list) or 'none'}"
    except Exception as e:
        return f"Error storing solution: {e}"


@mcp.tool()
def memory_store_mistake(description: str, mistake_type: str = "code_error",
                         severity: str = "medium", prevention: str = "") -> str:
    """
    Record a mistake so the AI team never repeats it.

    Args:
        description: What went wrong (e.g. "Used shell=True with user input")
        mistake_type: Type — code_error, security_vulnerability, performance_issue,
                      architecture_flaw, deployment_failure, logic_error, integration_issue
        severity: low, medium, high, critical
        prevention: How to prevent this in the future
    """
    import asyncio
    from elgringo.memory.system import MistakeType

    memory = _get_memory()
    type_map = {t.value: t for t in MistakeType}
    mt = type_map.get(mistake_type, MistakeType.CODE_ERROR)

    try:
        loop = asyncio.new_event_loop()
        mistake_id = loop.run_until_complete(memory.capture_mistake(
            mistake_type=mt,
            description=description,
            context={"source": "mcp_tool"},
            severity=severity,
            prevention_strategy=prevention,
        ))
        loop.close()
        return f"Recorded mistake `{mistake_id}`: [{severity}] {description}"
    except Exception as e:
        return f"Error storing mistake: {e}"


@mcp.tool()
def ai_team_costs() -> str:
    """
    Show AI team cost report — daily, weekly, and per-model spending breakdown.
    Helps track API usage and stay within budget.
    """
    from elgringo.routing.cost_tracker import get_cost_tracker

    ct = get_cost_tracker()
    stats = ct.get_statistics()
    ct.get_daily_report()
    budget = ct.get_budget_status()

    parts = [
        "## AI Team Costs",
        f"Total requests: {stats.get('total_requests', 0)}",
        f"Total cost: ${stats.get('total_cost', 0):.4f}",
        "",
        "### Budget",
        f"Daily: ${budget.get('daily_spent', 0):.4f} / ${budget.get('daily_limit', 10):.2f}",
        f"Monthly: ${budget.get('monthly_spent', 0):.4f} / ${budget.get('monthly_limit', 100):.2f}",
    ]

    model_costs = ct.get_model_costs()
    if model_costs:
        parts.append("\n### Per Model")
        for model, data in sorted(model_costs.items(), key=lambda x: x[1].get("total_cost", 0), reverse=True):
            parts.append(f"- {model}: ${data.get('total_cost', 0):.4f} ({data.get('total_requests', 0)} calls)")

    return "\n".join(parts)


@mcp.tool()
def verify_code(code: str, language: str = "") -> str:
    """
    Validate a code snippet for syntax errors, security issues, and lint warnings.
    Returns structured feedback with fix suggestions.

    Args:
        code: The code to validate
        language: Programming language (auto-detected if empty). Options: python, javascript, typescript
    """
    from elgringo.validation.code_validator import CodeValidator

    validator = CodeValidator()
    result = validator.validate(code, language=language or None)

    parts = [f"Language: {result.language}", f"Valid: {'yes' if result.valid else 'NO'}"]

    if result.errors:
        parts.append(f"\n### Errors ({len(result.errors)})")
        for err in result.errors[:10]:
            parts.append(f"- {err}")

    if result.warnings:
        parts.append(f"\n### Warnings ({len(result.warnings)})")
        for warn in result.warnings[:10]:
            parts.append(f"- {warn}")

    if result.suggestions:
        parts.append("\n### Suggestions")
        for sug in result.suggestions[:5]:
            parts.append(f"- {sug}")

    if not result.errors and not result.warnings:
        parts.append("\nNo issues found.")

    return "\n".join(parts)


@mcp.tool()
def fredfix_scan(project_path: str, language: str = "", severity: str = "medium") -> str:
    """
    Scan a project directory for security vulnerabilities, bugs, and code issues.
    Uses pattern matching and the AI team's knowledge of common mistakes.

    Args:
        project_path: Absolute path to the project or file to scan
        language: Filter by language (empty = auto-detect). Options: python, javascript, typescript, go, rust, java
        severity: Minimum severity to report — low, medium, high, critical
    """
    from elgringo.workflows.fredfix import FredFix
    import asyncio

    fixer = FredFix()

    try:
        loop = asyncio.new_event_loop()
        langs = [language] if language else None
        issues = loop.run_until_complete(fixer.scan_project(project_path, languages=langs))
        loop.close()
    except Exception as e:
        return f"Error scanning: {e}"

    severity_order = {"critical": 4, "high": 3, "medium": 2, "low": 1}
    min_sev = severity_order.get(severity, 2)
    filtered = [i for i in issues if severity_order.get(i.severity, 0) >= min_sev]

    if not filtered:
        return f"No issues found at severity >= {severity} in {project_path}"

    parts = [f"## FredFix Scan: {len(filtered)} issues found\n"]
    for issue in filtered[:20]:
        parts.append(f"- [{issue.severity.upper()}] `{issue.file_path}` — {issue.description}")
        if issue.suggested_fix:
            parts.append(f"  Fix: {issue.suggested_fix}")

    if len(filtered) > 20:
        parts.append(f"\n... and {len(filtered) - 20} more issues")

    return "\n".join(parts)


@mcp.tool()
def memory_stats() -> str:
    """
    Get memory system statistics — total interactions, solutions, mistakes,
    and success rates. Quick health check for the learning system.
    """
    memory = _get_memory()
    stats = memory.get_statistics()

    parts = [
        "## Memory System Stats",
        f"Total interactions: {stats.get('total_interactions', 0)}",
        f"Total solutions: {stats.get('total_solutions', 0)}",
        f"Total mistakes: {stats.get('total_mistakes', 0)}",
        f"Success rate: {stats.get('success_rate', 0):.0%}",
    ]

    if stats.get("top_tags"):
        parts.append(f"\nTop tags: {', '.join(stats['top_tags'][:10])}")

    return "\n".join(parts)


if __name__ == "__main__":
    mcp.run()
