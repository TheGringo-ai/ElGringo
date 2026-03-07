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
      "args": ["/Users/fredtaylor/Development/Projects/ElGringo/mcp_server.py"],
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
            - parallel        Fast (~12s). All agents answer simultaneously, results merged.
            - sequential      Each agent builds on the previous answer.
            - single          Fastest (~2s). Auto-routes to one best-fit agent.
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
            - parallel        Fast (~12s). All agents answer simultaneously, results merged.
            - sequential      Each agent builds on the previous answer.
            - single          Fastest (~2s). Auto-routes to one best-fit agent.
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


if __name__ == "__main__":
    mcp.run()
