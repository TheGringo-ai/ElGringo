"""
API-based MCP Tools — Tools that call the El Gringo REST API
=============================================================
All tools in this module require a running El Gringo API server.
"""

import json
import urllib.request

from .mcp_server import mcp, _api, _fmt_collaborate, _fmt_code_task, _fmt_review, logger, BASE_URL, API_KEY


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
            - turbo           Fastest (<2s). Picks the single best agent, skips synthesis.
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
    Debug an issue with the full AI team.

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
        "prompt": f"Debug this issue: {prompt}", "context": context, "mode": "peer_review",
    }))


@mcp.tool()
def ai_team_architect(prompt: str, context: str = "", constraints: str = "") -> str:
    """
    Get architecture recommendations from the AI team.

    Args:
        prompt: Architecture question or design challenge
        context: Current system context, requirements, or constraints
        constraints: Specific constraints (budget, timeline, tech stack)
    """
    full_context = context
    if constraints:
        full_context = f"{context}\n\nCONSTRAINTS: {constraints}" if context else f"CONSTRAINTS: {constraints}"
    return _fmt_collaborate(_api("POST", "/v1/collaborate", {
        "prompt": f"Architecture review: {prompt}", "context": full_context, "mode": "expert_panel",
    }))


@mcp.tool()
def ai_team_brainstorm(topic: str, context: str = "", num_ideas: int = 5) -> str:
    """
    Brainstorm ideas with the full AI team.

    Args:
        topic: The topic or problem to brainstorm about
        context: Background info or constraints
        num_ideas: Target number of ideas to generate
    """
    return _fmt_collaborate(_api("POST", "/v1/collaborate", {
        "prompt": f"Brainstorm {num_ideas} ideas for: {topic}", "context": context, "mode": "brainstorming",
    }))


@mcp.tool()
def ai_team_security_audit(project_path: str, glob_pattern: str = "**/*.py") -> str:
    """
    Run a security-focused code audit with the AI team.

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
    Stream a response token-by-token from a single agent.

    Args:
        prompt: The question or task
        agent: Specific agent name (empty = auto-route)
    """
    from .mcp_server import BASE_URL, API_KEY

    url = f"{BASE_URL}/v1/stream"
    headers = {"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json", "Accept": "text/event-stream"}
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
    """Record whether a previous El Gringo suggestion worked or not."""
    data = _api("POST", "/v1/feedback", {"node_id": node_id, "success": success, "feedback": feedback})
    if isinstance(data, str) and data.startswith("ERROR"):
        return data
    if "error" in data:
        return f"Error: {data['error']}"
    return f"Feedback recorded for {node_id}\nSuccess: {'Yes' if success else 'No'}\nNew confidence: {data.get('new_confidence', 'N/A')}"


@mcp.tool()
def elgringo_diagnose(
    error_message: str, stacktrace: str = "", project_path: str = "",
    language: str = "", files_context: str = "",
) -> str:
    """
    AI debugger: multi-agent root cause analysis for errors and bugs.

    Args:
        error_message: The error message to diagnose
        stacktrace: Full stack trace if available
        project_path: Absolute path to the project (for reading files)
        language: Programming language (auto-detect if empty)
        files_context: Comma-separated file paths to read for context
    """
    files = [f.strip() for f in files_context.split(",") if f.strip()] if files_context else []
    result = _api("POST", "/v1/diagnose", {
        "error_message": error_message, "stacktrace": stacktrace,
        "project_path": project_path, "language": language, "files_context": files,
    })
    if "error" in result:
        return f"Error: {result['error']}"
    agents = ", ".join(result.get("agents_used", []))
    confidence = result.get("confidence", 0)
    parts = [
        f"[Agents: {agents} | Confidence: {confidence:.0%} | {result.get('total_time', 0):.1f}s]",
        "", f"## Root Cause", result.get("root_cause", "Unknown"),
        "", f"## Explanation", result.get("explanation", ""),
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
    Generate changelog from git history.

    Args:
        project_path: Absolute path to the project (must be a git repo)
        git_range: Git commit range (e.g. HEAD~10..HEAD, v1.0..HEAD)
        audience: Target audience — developer, stakeholder, user
        format: Output format — markdown or json
    """
    result = _api("POST", "/v1/changelog", {
        "project_path": project_path, "git_range": git_range, "audience": audience, "format": format,
    })
    if "error" in result:
        return f"Error: {result['error']}"
    commits = result.get("commits_analyzed", 0)
    parts = [f"[{commits} commits analyzed | {result.get('total_time', 0):.1f}s]", "", result.get("changelog", "")]
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

    Args:
        project_path: Absolute path to the project
        focus: Analysis focus — complexity, duplication, performance, security, all
        glob_pattern: File pattern to analyze
        target_files: Comma-separated specific files to analyze (overrides glob)
    """
    files = [f.strip() for f in target_files.split(",") if f.strip()] if target_files else []
    result = _api("POST", "/v1/refactor", {
        "project_path": project_path, "focus": focus, "glob_pattern": glob_pattern, "target_files": files,
    })
    if "error" in result:
        return f"Error: {result['error']}"
    agents = ", ".join(result.get("agents_used", []))
    score = result.get("tech_debt_score", 0)
    parts = [
        f"[Agents: {agents} | Tech Debt Score: {score:.0f}/100 | {result.get('total_time', 0):.1f}s]",
        "", f"## Summary", result.get("summary", ""),
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

    Args:
        project_path: Absolute path to the project
        target_file: Relative path to the file to generate tests for
        coverage_focus: Test focus — happy_path, edge_cases, comprehensive
        test_framework: Test framework (auto-detect if empty)
    """
    result = _api("POST", "/v1/test-generate", {
        "project_path": project_path, "target_file": target_file,
        "coverage_focus": coverage_focus, "test_framework": test_framework,
    })
    if "error" in result:
        return f"Error: {result['error']}"
    agents = ", ".join(result.get("agents_used", []))
    count = result.get("tests_count", 0)
    test_path = result.get("test_file_path", "")
    parts = [f"[Agents: {agents} | {count} tests | {result.get('total_time', 0):.1f}s]", f"Suggested test file: `{test_path}`", ""]
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
    project_path: str, git_range: str = "HEAD~5..HEAD", environment: str = "production",
) -> str:
    """
    Pre-deploy risk assessment with go/no-go recommendation.

    Args:
        project_path: Absolute path to the project
        git_range: Git range to analyze
        environment: Target environment — production, staging, dev
    """
    result = _api("POST", "/v1/deploy-check", {
        "project_path": project_path, "git_range": git_range, "environment": environment,
    })
    if "error" in result:
        return f"Error: {result['error']}"
    agents = ", ".join(result.get("agents_used", []))
    risk = result.get("risk_score", 0)
    level = result.get("risk_level", "unknown")
    verdict = result.get("go_no_go", "?")
    parts = [
        f"[Agents: {agents} | {result.get('total_time', 0):.1f}s]", "",
        f"## Verdict: {verdict}", f"Risk Score: {risk:.1f}/10 ({level})", f"Environment: {environment}",
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

    Args:
        project_path: Absolute path to the project
        focus: What to focus on — overview, architecture, api, frontend, backend
        depth: Detail level — quick, medium, deep
    """
    result = _api("POST", "/v1/onboard", {
        "project_path": project_path, "focus": focus, "depth": depth,
    })
    if "error" in result:
        return f"Error: {result['error']}"
    agents = ", ".join(result.get("agents_used", []))
    parts = [
        f"[Agents: {agents} | Focus: {focus} | Depth: {depth} | {result.get('total_time', 0):.1f}s]",
        "", f"## Summary", result.get("summary", ""),
    ]
    if result.get("architecture"):
        parts.extend(["", "## Architecture", result["architecture"]])
    key_files = result.get("key_files", [])
    if key_files:
        parts.extend(["", "## Key Files"])
        for kf in key_files:
            parts.append(f"- `{kf.get('path', '?')}` [{kf.get('importance', 'medium')}] — {kf.get('purpose', '?')}")
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
    Put a topic to adversarial scrutiny. Agents argue opposing positions.

    Args:
        prompt: The proposition, decision, or design to challenge
        context: Background info, constraints, or existing solution
        mode: Adversarial mode — debate, devils_advocate, peer_review
    """
    return _fmt_collaborate(_api("POST", "/v1/collaborate", {
        "prompt": prompt, "context": context, "mode": mode,
    }))


@mcp.tool()
def claude_second_opinion(question: str, my_answer: str, concern: str = "") -> str:
    """
    Get a second opinion from the full AI team on your proposed answer.

    Args:
        question: The original user question
        my_answer: Your proposed answer that you want validated
        concern: What specifically you're unsure about
    """
    prompt = f"""A developer asked: {question}

One AI proposed this answer:
{my_answer[:2000]}

{"Specific concern: " + concern if concern else ""}

Review this answer critically. Is it correct? Complete? Are there better approaches?"""

    result = _api("POST", "/v1/collaborate", {"prompt": prompt, "mode": "peer_review", "budget": "standard"})
    return _fmt_collaborate(result)
