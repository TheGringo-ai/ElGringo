"""
Local MCP Tools — Tools that run locally without the El Gringo API
==================================================================
Memory, code validation, cost tracking, feedback, and context tools.
"""

from .mcp_server import mcp, _run_async, _get_memory, _api, _fmt_collaborate, logger


# ── Memory Tools ───────────────────────────────────────────────────

@mcp.tool()
def memory_search(query: str, search_type: str = "all") -> str:
    """
    Search the AI team's memory for past solutions and mistakes.
    Helps avoid repeating errors and find proven patterns.

    Args:
        query: Search query (e.g. "database connection pooling", "auth bug")
        search_type: What to search — "solutions", "mistakes", or "all"
    """
    memory = _get_memory()
    parts = []

    if search_type in ("solutions", "all"):
        try:
            solutions = _run_async(memory.find_solution_patterns(query, limit=5))
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
        try:
            mistakes = _run_async(memory.find_similar_mistakes({"query": query}, limit=5))
        except Exception:
            mistakes = []
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
    memory = _get_memory()
    steps = [s.strip() for s in solution_steps.replace(";", "\n").split("\n") if s.strip()]
    tag_list = [t.strip() for t in tags.split(",") if t.strip()] if tags else []

    try:
        solution_id = _run_async(memory.capture_solution(
            problem_pattern=problem,
            solution_steps=steps,
            success_rate=1.0,
            tags=tag_list,
        ))
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
    from elgringo.memory.system import MistakeType

    memory = _get_memory()
    type_map = {t.value: t for t in MistakeType}
    mt = type_map.get(mistake_type, MistakeType.CODE_ERROR)

    try:
        mistake_id = _run_async(memory.capture_mistake(
            mistake_type=mt,
            description=description,
            context={"source": "mcp_tool"},
            severity=severity,
            prevention_strategy=prevention,
        ))
        return f"Recorded mistake `{mistake_id}`: [{severity}] {description}"
    except Exception as e:
        return f"Error storing mistake: {e}"


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


# ── Code Validation & Scanning ─────────────────────────────────────

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

    fixer = FredFix()

    try:
        langs = [language] if language else None
        issues = _run_async(fixer.scan_project(project_path, languages=langs))
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


# ── Cost & Performance Tracking ────────────────────────────────────

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
def ai_team_roi(period: str = "all_time") -> str:
    """
    ROI dashboard — shows time saved, money saved, and agent performance rankings.
    Proves El Gringo is making you faster and better.

    Args:
        period: Time period — 'today', 'week', 'month', or 'all_time'
    """
    from elgringo.intelligence.roi_dashboard import get_roi_dashboard

    dashboard = get_roi_dashboard()
    report = dashboard.get_report(period)
    return report.to_readable()


@mcp.tool()
def ai_team_leaderboard() -> str:
    """
    Agent performance leaderboard — which AI agent performs best for each task type.
    Based on real success rates and user feedback.
    """
    from elgringo.intelligence.roi_dashboard import get_roi_dashboard

    dashboard = get_roi_dashboard()
    leaderboard = dashboard.get_agent_leaderboard()

    if not leaderboard:
        return "No tasks recorded yet. Use the AI team to build the leaderboard."

    lines = ["## Agent Leaderboard", ""]
    for entry in leaderboard:
        lines.append(
            f"#{entry['rank']} **{entry['agent']}** — "
            f"{entry['success_rate']} success, best at: {', '.join(entry['best_at'][:2])}"
        )
    return "\n".join(lines)


@mcp.tool()
def ai_team_rate(task_id: str, rating: str, comment: str = "") -> str:
    """
    Rate a previous AI response to improve future results.
    Positive ratings boost similar patterns, negative ratings decay bad solutions.

    Args:
        task_id: The task_id from a previous collaboration result
        rating: 'good', 'bad', or a number from -1.0 to 1.0
        comment: Optional feedback comment
    """
    from elgringo.intelligence.feedback_loop import get_feedback_loop

    # Parse rating
    rating_map = {"good": 0.8, "great": 1.0, "bad": -0.8, "terrible": -1.0, "ok": 0.3}
    try:
        numeric_rating = rating_map.get(rating.lower(), float(rating))
    except (ValueError, AttributeError):
        return f"Invalid rating '{rating}'. Use 'good', 'bad', or a number from -1.0 to 1.0."

    floop = get_feedback_loop()

    result = _run_async(floop.process_feedback(
        task_id=task_id, rating=numeric_rating,
        agents=[], task_type="general",
        comment=comment or None,
    ))

    lines = [
        f"## Feedback Recorded",
        f"Task: {task_id}",
        f"Rating: {numeric_rating:+.1f}",
    ]
    for action in result.actions_taken:
        lines.append(f"- {action}")

    summary = floop.get_roi_summary()
    lines.append(f"\nSystem trending: **{summary['trending']}** ({summary['total_feedback_events']} total feedback events)")
    return "\n".join(lines)


# ── Context & Reflection Tools ─────────────────────────────────────

@mcp.tool()
def claude_context(task: str, project: str = "", task_type: str = "auto") -> str:
    """
    CALL THIS FIRST before working on any significant task.
    Pulls all relevant context from El Gringo's memory to make you smarter:
    - Past solutions that match this task
    - Mistakes to avoid
    - Project conventions and best practices
    - Relevant lessons from the teaching system
    - Agent performance insights

    This is what makes you better than vanilla Claude — you have institutional memory.

    Args:
        task: What you're about to work on (e.g. "fix auth bug", "add rate limiting", "review PR")
        project: Project name if relevant (e.g. "managers-dashboard", "elgringo")
        task_type: Task type — "coding", "debugging", "architecture", "security", or "auto" to detect
    """
    from elgringo.memory import MemorySystem
    from elgringo.knowledge import TeachingSystem

    memory = _get_memory()
    teacher = TeachingSystem()

    parts = ["# El Gringo Context for This Task", ""]

    # Auto-detect task type
    if task_type == "auto":
        task_lower = task.lower()
        if any(w in task_lower for w in ["bug", "fix", "error", "crash", "debug", "broken"]):
            task_type = "debugging"
        elif any(w in task_lower for w in ["review", "audit", "check", "scan"]):
            task_type = "code_review"
        elif any(w in task_lower for w in ["secure", "auth", "vulnerab", "inject", "xss"]):
            task_type = "security"
        elif any(w in task_lower for w in ["design", "architect", "plan", "structure"]):
            task_type = "architecture"
        elif any(w in task_lower for w in ["test", "spec", "coverage"]):
            task_type = "testing"
        else:
            task_type = "coding"

    parts.append(f"**Task type detected:** {task_type}")
    if project:
        parts.append(f"**Project:** {project}")
    parts.append("")

    # 1. Search for relevant solutions
    try:
        query = f"{task} {project}".strip()
        solutions = _run_async(memory.find_solution_patterns(query, limit=5))

        curated = [s for s in solutions if s.best_practices]
        auto = [s for s in solutions if not s.best_practices]

        if curated:
            parts.append("## MANDATORY Rules (from past experience)")
            for s in curated[:3]:
                parts.append(f"\n### {s.problem_pattern}")
                for bp in s.best_practices:
                    parts.append(f"  - **{bp}**")
                if s.solution_steps:
                    parts.append("  Steps that worked:")
                    for step in s.solution_steps[:3]:
                        if len(step) < 200:
                            parts.append(f"    {step}")

        if auto:
            parts.append("\n## Related Solutions")
            for s in auto[:3]:
                steps_preview = "; ".join(step[:80] for step in s.solution_steps[:2])
                parts.append(f"- **{s.problem_pattern}** ({s.success_rate:.0%} success)")
                if steps_preview:
                    parts.append(f"  {steps_preview}")
    except Exception as e:
        logger.debug(f"Solution search failed: {e}")

    # 2. Search for relevant mistakes to AVOID
    try:
        mistakes = _run_async(
            memory.find_similar_mistakes({"query": task, "task_type": task_type}, limit=5)
        )

        if mistakes:
            parts.append("\n## MISTAKES TO AVOID")
            for m in mistakes[:3]:
                parts.append(f"- [{m.severity}] **{m.description}**")
                if m.prevention_strategy:
                    parts.append(f"  Prevention: {m.prevention_strategy}")
    except Exception as e:
        logger.debug(f"Mistake search failed: {e}")

    # 3. Pull relevant teaching lessons
    relevant_domains = {
        "coding": ["backend", "frontend"],
        "debugging": ["backend", "testing"],
        "architecture": ["architecture", "backend"],
        "security": ["security", "backend"],
        "testing": ["testing", "backend"],
        "code_review": ["backend", "security"],
    }.get(task_type, ["backend"])

    matching_lessons = [
        l for l in teacher._lessons
        if l.domain in relevant_domains
        and l.best_practices
        and l.source in ("manual", "system")
    ]
    if matching_lessons:
        parts.append(f"\n## Relevant Lessons ({len(matching_lessons)} found)")
        for l in matching_lessons[:5]:
            parts.append(f"\n**{l.topic}** [{l.domain}]")
            for bp in l.best_practices[:3]:
                parts.append(f"  - {bp}")
            if l.anti_patterns:
                parts.append("  Avoid:")
                for ap in l.anti_patterns[:2]:
                    parts.append(f"    - {ap}")

    # 4. Agent performance insights for this task type
    try:
        from elgringo.intelligence.feedback_loop import get_feedback_loop
        floop = get_feedback_loop()
        profiles = floop.get_all_profiles()
        if profiles:
            parts.append(f"\n## Agent Performance for {task_type}")
            for name, profile in profiles.items():
                if profile:
                    score = profile.get("task_type_scores", {}).get(task_type, None)
                    if score is not None:
                        parts.append(
                            f"- {name}: satisfaction {profile['satisfaction_rate']:.0%}, "
                            f"{task_type} score: {score:.2f}"
                        )
    except Exception:
        pass

    # 5. Memory stats
    stats = memory.get_statistics()
    parts.append(
        f"\n---\n_El Gringo memory: {stats.get('total_solutions', 0)} solutions, "
        f"{stats.get('total_mistakes', 0)} mistakes, "
        f"{stats.get('total_interactions', 0)} interactions_"
    )

    return "\n".join(parts)


@mcp.tool()
def claude_reflect(task: str, outcome: str, what_worked: str = "", what_failed: str = "", project: str = "") -> str:
    """
    CALL THIS AFTER completing a significant task to capture what you learned.
    This is how El Gringo builds institutional memory from your work.

    Args:
        task: What you just did
        outcome: "success" or "failure"
        what_worked: What approach/pattern worked well (stored as solution)
        what_failed: What went wrong or should be avoided (stored as mistake)
        project: Project name if relevant
    """
    memory = _get_memory()
    results = []

    if what_worked and outcome == "success":
        try:
            steps = [s.strip() for s in what_worked.split(";") if s.strip()]
            sid = _run_async(memory.capture_solution(
                problem_pattern=task,
                solution_steps=steps,
                project=project or "default",
                tags=["claude_reflection"],
            ))
            results.append(f"Solution stored (ID: {sid})")
        except Exception as e:
            results.append(f"Failed to store solution: {e}")

    if what_failed:
        try:
            from elgringo.memory.system import MistakeType
            mid = _run_async(memory.capture_mistake(
                description=what_failed,
                mistake_type=MistakeType.CODE_ERROR,
                context={"source": "claude_reflect", "task": task},
                severity="medium",
                prevention_strategy=f"When doing '{task}', avoid: {what_failed}",
                project=project or "default",
                tags=["claude_reflection"],
            ))
            results.append(f"Mistake recorded (ID: {mid})")
        except Exception as e:
            results.append(f"Failed to store mistake: {e}")

    if not results:
        return "Nothing to store. Provide what_worked (for success) or what_failed."

    stats = memory.get_statistics()
    results.append(
        f"\nMemory updated: {stats.get('total_solutions', 0)} solutions, "
        f"{stats.get('total_mistakes', 0)} mistakes"
    )
    return "\n".join(results)


# ── MLX Local Inference Tools ─────────────────────────────────────

def _get_mlx():
    """Lazy-load MLX inference engine (cached)."""
    if not hasattr(_get_mlx, "_instance"):
        from elgringo.apple.mlx_inference import get_mlx_inference
        _get_mlx._instance = get_mlx_inference()
    return _get_mlx._instance


@mcp.tool()
def mlx_ask(prompt: str, model: str = "auto", system_prompt: str = "", max_tokens: int = 2048) -> str:
    """
    Ask a local MLX model running on Apple Silicon. Zero cost, instant, private.
    Uses Qwen 2.5 Coder 7B for code tasks, Qwen 2.5 3B for general tasks.
    Both models stay loaded in unified memory (~6GB total).

    Use this for:
    - Quick code generation, completions, and explanations
    - Drafting code before refining with cloud models
    - Private/sensitive queries that shouldn't leave the machine
    - Fast iteration when you need many small answers

    Args:
        prompt: Your question or coding task
        model: "coder" (Qwen 7B), "general" (Qwen 3B), or "auto" (picks based on prompt)
        system_prompt: Optional system prompt for context
        max_tokens: Max response length (default 2048)
    """
    mlx = _get_mlx()
    if not mlx.is_available:
        return "MLX not available on this system (requires Apple Silicon + mlx package)"

    # Resolve model
    model_map = {
        "coder": "mlx-community/Qwen2.5-Coder-7B-Instruct-4bit",
        "general": "mlx-community/Qwen2.5-3B-Instruct-4bit",
    }

    if model == "auto":
        code_keywords = ["code", "function", "class", "bug", "error", "fix", "refactor",
                         "python", "javascript", "typescript", "rust", "go", "sql",
                         "implement", "write", "debug", "test", "api", "endpoint"]
        is_code = any(kw in prompt.lower() for kw in code_keywords)
        model_name = model_map["coder"] if is_code else model_map["general"]
    else:
        model_name = model_map.get(model, model_map["coder"])

    # Load model if needed and generate
    try:
        _run_async(mlx.load_model(model_name))
        response = _run_async(mlx.generate(
            prompt=prompt,
            model_name=model_name,
            system_prompt=system_prompt or None,
            max_tokens=max_tokens,
        ))

        short_name = "Qwen Coder 7B" if "Coder" in model_name else "Qwen 3B"
        return (
            f"[MLX {short_name} | {response.tokens_per_second:.0f} tok/s | "
            f"{response.inference_time:.1f}s | {response.memory_used_mb:.0f}MB | $0.00]\n\n"
            f"{response.content}"
        )
    except Exception as e:
        logger.error(f"MLX generation failed: {e}")
        return f"MLX error: {e}"


@mcp.tool()
def mlx_status() -> str:
    """
    Check MLX local inference status — available models, memory usage, loaded state.
    """
    mlx = _get_mlx()
    if not mlx.is_available:
        return "MLX not available (requires Apple Silicon + mlx package)"

    mem = mlx.get_memory_info()
    loaded = mlx.loaded_models

    from elgringo.apple.mlx_inference import AVAILABLE_MODELS

    parts = [
        "## MLX Local Inference Status",
        f"Available: yes",
        f"Active memory: {mem.get('active_mb', 0):.0f} MB",
        f"Peak memory: {mem.get('peak_mb', 0):.0f} MB",
        f"Models loaded: {len(loaded)}",
    ]

    if loaded:
        parts.append("\n### Loaded Models")
        for m in loaded:
            info = AVAILABLE_MODELS.get(m, {})
            parts.append(f"- {m} ({info.get('size', '?')}, {info.get('quantization', '?')})")

    parts.append("\n### Available Models")
    for name, info in AVAILABLE_MODELS.items():
        status = "LOADED" if name in loaded else "ready"
        parts.append(f"- [{status}] {info.get('alias', name)}: {name} ({info['size']})")

    return "\n".join(parts)
