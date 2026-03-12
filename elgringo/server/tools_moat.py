"""
Moat & Tier MCP Tools — Features no competitor has + gap closers
================================================================
Tier 1-3 tools, structured output, approval gates, workflows,
production guardian, cross-project intelligence, cache, watchdog.
"""

import json
import uuid

from .mcp_server import mcp, _run_async, _api, _fmt_collaborate, _fmt_code_task, _fmt_review, logger


# ─── TIER 1: High-impact tools ───────────────────────────────────────────────


@mcp.tool()
def ai_team_generate_app(
    description: str,
    name: str = "",
    template: str = "",
    deploy_target: str = "",
) -> str:
    """
    Generate a complete application from a natural language description.
    The full AI team collaborates to scaffold production-ready code.

    Args:
        description: What the app should do (e.g. "task management app with auth")
        name: Project name (auto-generated if empty)
        template: Template — react, next, fastapi, flask, fullstack, mobile, cli, automation
        deploy_target: Deploy target — firebase, vercel, gcp, aws (empty = skip)
    """
    from elgringo.workflows.app_generator import AppGenerator

    gen = AppGenerator()
    kwargs = {}
    if name:
        kwargs["name"] = name
    if template:
        kwargs["template"] = template
    if deploy_target:
        kwargs["deploy_target"] = deploy_target

    try:
        result = _run_async(gen.create_app(description, **kwargs))
    except Exception as e:
        return f"Error generating app: {e}"

    parts = [
        f"## App Generated: {result['project_name']}",
        f"Path: `{result['project_path']}`",
        f"Template: {result['template']}",
        f"Files: {len(result['files_created'])}",
    ]
    for f in result["files_created"]:
        parts.append(f"  - {f}")

    if result.get("next_steps"):
        parts.append("\n### Next Steps")
        for step in result["next_steps"]:
            parts.append(f"  {step}")

    return "\n".join(parts)


@mcp.tool()
def ai_team_semantic_diff(
    project_path: str,
    git_range: str = "HEAD~1..HEAD",
) -> str:
    """
    Analyze git changes semantically — what features were added/removed,
    risk assessment, and compression of large diffs into key insights.

    Args:
        project_path: Absolute path to the git project
        git_range: Git range to analyze (e.g. HEAD~3..HEAD, main..feature-branch)
    """
    import subprocess
    from elgringo.intelligence.semantic_delta import SemanticDeltaExtractor

    try:
        diff_output = subprocess.run(
            ["git", "diff", git_range],
            capture_output=True, text=True, cwd=project_path, timeout=15,
        )
        if diff_output.returncode != 0:
            return f"Git error: {diff_output.stderr.strip()}"
        if not diff_output.stdout.strip():
            return f"No changes found in range `{git_range}`"
    except Exception as e:
        return f"Error running git diff: {e}"

    extractor = SemanticDeltaExtractor(use_mlx=False)
    deltas = extractor.extract_from_git_diff(diff_output.stdout)

    if not deltas:
        return "No semantic changes detected."

    parts = [f"## Semantic Diff: `{git_range}` ({len(deltas)} files)\n"]
    for delta in deltas:
        risk_badge = {"LOW": "low", "MEDIUM": "med", "HIGH": "HIGH", "CRITICAL": "CRIT"}.get(
            delta.risk_level.name, "?"
        )
        parts.append(f"### [{risk_badge}] {delta.file_path}")
        parts.append(f"**Summary:** {delta.summary}")
        parts.append(f"**Risk:** {delta.risk_level.name} | Lines changed: {delta.total_lines_changed} | Compression: {delta.compression_ratio:.0%}")

        if delta.risk_reasons:
            parts.append(f"**Risk factors:** {', '.join(delta.risk_reasons[:3])}")

        for change in delta.changes[:5]:
            parts.append(f"- [{change.change_type.value}] {change.description}")

        parts.append("")

    return "\n".join(parts)


@mcp.tool()
def ai_team_code_analysis(
    target: str,
    analysis_type: str = "file",
) -> str:
    """
    AST-based code structure analysis — functions, classes, complexity,
    imports, dependencies, and issues. No AI calls, instant results.

    Args:
        target: Absolute path to a file or project directory
        analysis_type: "file" for single file, "project" for full project
    """
    from elgringo.intelligence.code_analyzer import CodeAnalyzer

    analyzer = CodeAnalyzer()

    if analysis_type == "project":
        try:
            analysis = analyzer.analyze_project(target)
        except Exception as e:
            return f"Error analyzing project: {e}"

        parts = [
            f"## Project Analysis: {analysis.path}",
            f"Files: {len(analysis.files)} | Lines: {analysis.total_lines}",
            f"Functions: {analysis.total_functions} | Classes: {analysis.total_classes}",
            f"Languages: {', '.join(f'{k} ({v})' for k, v in analysis.languages.items())}",
        ]

        if analysis.issues:
            parts.append(f"\n### Issues ({len(analysis.issues)})")
            for issue in analysis.issues[:15]:
                parts.append(f"- [{issue.get('severity', 'info')}] `{issue.get('file', '')}` L{issue.get('line', '?')}: {issue.get('message', '')}")

        complex_files = sorted(analysis.files, key=lambda f: f.complexity_score, reverse=True)[:5]
        if complex_files:
            parts.append("\n### Most Complex Files")
            for f in complex_files:
                parts.append(f"- `{f.path}` — complexity: {f.complexity_score:.1f}, {len(f.functions)} functions, {f.lines} lines")

        return "\n".join(parts)
    else:
        try:
            analysis = analyzer.analyze_file(target)
        except Exception as e:
            return f"Error analyzing file: {e}"

        parts = [
            f"## File Analysis: {analysis.path}",
            f"Language: {analysis.language} | Lines: {analysis.lines} | Complexity: {analysis.complexity_score:.1f}",
        ]

        if analysis.functions:
            parts.append(f"\n### Functions ({len(analysis.functions)})")
            for func in analysis.functions:
                async_tag = "async " if func.is_async else ""
                args_str = ", ".join(func.args[:5])
                parts.append(f"- `{async_tag}{func.name}({args_str})` L{func.start_line}-{func.end_line} complexity:{func.complexity}")

        if analysis.classes:
            parts.append(f"\n### Classes ({len(analysis.classes)})")
            for cls in analysis.classes:
                bases = f" ({', '.join(cls.bases)})" if cls.bases else ""
                parts.append(f"- `{cls.name}{bases}` L{cls.start_line}-{cls.end_line} — {len(cls.methods)} methods")

        if analysis.imports:
            parts.append(f"\n### Imports ({len(analysis.imports)})")
            for imp in analysis.imports[:15]:
                names = ", ".join(imp.names[:4])
                parts.append(f"- `{imp.module}` -> {names}")

        if analysis.todos:
            parts.append(f"\n### TODOs ({len(analysis.todos)})")
            for line, comment in analysis.todos[:10]:
                parts.append(f"- L{line}: {comment[:80]}")

        if analysis.issues:
            parts.append(f"\n### Issues ({len(analysis.issues)})")
            for issue in analysis.issues[:10]:
                parts.append(f"- [{issue.get('severity', 'info')}] L{issue.get('line', '?')}: {issue.get('message', '')}")

        return "\n".join(parts)


@mcp.tool()
def ai_team_teach(
    domain: str,
    topic: str,
    content: str,
    best_practices: str = "",
    anti_patterns: str = "",
) -> str:
    """
    Teach the AI team new knowledge. Adds a lesson to the knowledge base
    so the team applies it in future tasks.

    Args:
        domain: Domain area — frontend, backend, security, architecture, testing, devops
        topic: Specific topic (e.g. "FastAPI CORS setup", "React state management")
        content: Main lesson content
        best_practices: Semicolon-separated best practices (e.g. "Always use httpOnly cookies; Validate on server")
        anti_patterns: Semicolon-separated anti-patterns to avoid
    """
    from elgringo.knowledge import TeachingSystem

    teacher = TeachingSystem()

    bp_list = [s.strip() for s in best_practices.split(";") if s.strip()] if best_practices else []
    ap_list = [s.strip() for s in anti_patterns.split(";") if s.strip()] if anti_patterns else []

    lesson_id = teacher.add_lesson(
        domain=domain,
        topic=topic,
        content=content,
        best_practices=bp_list,
        anti_patterns=ap_list,
        source="mcp_tool",
    )

    parts = [
        f"## Lesson Stored: `{lesson_id}`",
        f"**Domain:** {domain} | **Topic:** {topic}",
    ]
    if bp_list:
        parts.append(f"**Best practices:** {len(bp_list)}")
    if ap_list:
        parts.append(f"**Anti-patterns:** {len(ap_list)}")

    total = len(teacher._lessons)
    parts.append(f"\n_Knowledge base: {total} lessons_")
    return "\n".join(parts)


# ─── TIER 2: Apple Silicon tools ─────────────────────────────────────────────


@mcp.tool()
def ai_team_apple_info() -> str:
    """
    Show Apple Silicon hardware info and local MLX model capabilities.
    Reports chip, memory, GPU cores, and which model sizes can run locally.
    """
    from elgringo.apple.smart_router import get_apple_hardware_info

    hw = get_apple_hardware_info()
    if not hw:
        return "Not running on Apple Silicon (or detection failed)."

    parts = [
        f"## Apple Silicon: {hw.chip} {hw.variant}".strip(),
        f"Memory: {hw.memory_gb} GB",
        f"GPU cores: {hw.gpu_cores} | Neural Engine: {hw.neural_engine_cores} cores",
        f"Can run 7B models: {'Yes' if hw.can_run_7b else 'No'}",
        f"Can run 13B models: {'Yes' if hw.can_run_13b else 'No'}",
        f"Optimal batch size: {hw.optimal_batch_size}",
    ]

    try:
        from pathlib import Path
        cache_dir = Path.home() / ".cache" / "huggingface" / "hub"
        if cache_dir.exists():
            mlx_models = [d.name for d in cache_dir.iterdir() if d.is_dir() and ("mlx" in d.name.lower() or "qwen" in d.name.lower() or "llama" in d.name.lower())]
            if mlx_models:
                parts.append(f"\n### Cached Models ({len(mlx_models)})")
                for m in mlx_models[:10]:
                    parts.append(f"- {m}")
    except Exception:
        pass

    return "\n".join(parts)


@mcp.tool()
def ai_team_mlx_generate(prompt: str, model: str = "coder") -> str:
    """
    Zero-cost local code generation using MLX on Apple Silicon.
    No API calls, no cost, runs entirely on your Mac.
    Models stay loaded in memory for instant responses.

    Args:
        prompt: The coding task or question
        model: "coder" (Qwen 7B — best for code) or "general" (Qwen 3B — fastest)
    """
    # Delegate to mlx_ask in tools_local (uses shared multi-model cache)
    from .tools_local import mlx_ask
    return mlx_ask(prompt, model=model)


# ─── TIER 3: Nice-to-have tools ──────────────────────────────────────────────


@mcp.tool()
def ai_team_parallel_review(
    project_path: str,
    focus_areas: str = "",
) -> str:
    """
    Parallel multi-agent code review — each agent reviews with their specialty
    (security, performance, code quality, architecture) simultaneously.

    Args:
        project_path: Absolute path to the project
        focus_areas: Comma-separated focus areas (empty = all). Options:
                     security, performance, code_quality, architecture, testing
    """
    from elgringo.workflows.parallel_coding import ParallelCodingEngine

    engine = ParallelCodingEngine()
    areas = [a.strip() for a in focus_areas.split(",") if a.strip()] if focus_areas else None

    try:
        result = _run_async(engine.review_project(project_path, focus_areas=areas))
    except Exception as e:
        return f"Error running parallel review: {e}"

    parts = [
        f"## Parallel Review: {result.project_path}",
        f"**Status:** {'Success' if result.success else 'Failed'} | Time: {result.total_time:.1f}s",
        f"\n### Summary\n{result.summary}",
    ]

    if result.proposed_fixes:
        parts.append(f"\n### Proposed Fixes ({len(result.proposed_fixes)})")
        for fix in result.proposed_fixes[:10]:
            parts.append(f"- `{fix.file_path}` ({fix.agent_name}, {fix.confidence:.0%}): {fix.description}")

    if result.errors:
        parts.append(f"\n### Errors")
        for err in result.errors:
            parts.append(f"- {err}")

    return "\n".join(parts)


@mcp.tool()
def ai_team_performance_report() -> str:
    """
    Agent performance report — response times, success rates, and rankings
    per task type. Based on real tracked outcomes across sessions.
    """
    from elgringo.routing.performance_tracker import PerformanceTracker

    tracker = PerformanceTracker()

    if not tracker._models:
        return "No performance data collected yet. Use the AI team tools to generate data."

    parts = ["## Agent Performance Report\n"]

    ranked = sorted(tracker._models.values(), key=lambda m: m.total_tasks, reverse=True)

    for model in ranked:
        success_rate = model.successful_tasks / max(model.total_tasks, 1)
        avg_time = model.total_response_time / max(model.total_tasks, 1)

        parts.append(f"### {model.model_name}")
        parts.append(f"Tasks: {model.total_tasks} | Success: {success_rate:.0%} | Avg time: {avg_time:.1f}s")

        if model.task_type_stats:
            for task_type, stats in model.task_type_stats.items():
                tt_success = stats.get("success", 0) / max(stats.get("total", 1), 1)
                parts.append(f"  - {task_type}: {tt_success:.0%} ({int(stats.get('total', 0))} tasks)")

        if model.recent_outcomes:
            recent = model.recent_outcomes[-10:]
            recent_rate = sum(recent) / len(recent)
            trend = "improving" if recent_rate > success_rate else "declining" if recent_rate < success_rate - 0.05 else "stable"
            parts.append(f"  Trend: **{trend}** (last 10: {recent_rate:.0%})")

        parts.append("")

    parts.append(f"_Total outcomes tracked: {len(tracker._outcomes)}_")
    return "\n".join(parts)


# ─── GAP CLOSERS: Features that match CrewAI/AutoGen/LangGraph ───────────────


@mcp.tool()
def ai_team_structured(
    prompt: str,
    schema: str = "task_plan",
    custom_schema: str = "",
    mode: str = "parallel",
) -> str:
    """
    Get AI team response forced into a validated JSON schema.
    Like CrewAI's structured output — guarantees parseable, typed responses.

    Args:
        prompt: The task or question
        schema: Built-in schema name — task_plan, code_review, bug_report, architecture
        custom_schema: Custom JSON schema (overrides schema param). Pass as JSON string.
        mode: Collaboration mode — parallel, consensus, single, turbo
    """
    from elgringo.intelligence.structured_output import get_structured_enforcer

    enforcer = get_structured_enforcer()

    if custom_schema:
        try:
            schema_obj = json.loads(custom_schema)
        except json.JSONDecodeError:
            return f"Invalid custom_schema JSON: {custom_schema[:200]}"
    else:
        schema_obj = enforcer.get_schema(schema)
        if not schema_obj:
            available = ", ".join(enforcer.list_schemas())
            return f"Unknown schema '{schema}'. Available: {available}"

    full_prompt = prompt + enforcer.build_prompt_suffix(schema_obj)

    result = _api("POST", "/v1/collaborate", {
        "prompt": full_prompt,
        "mode": mode,
        "budget": "standard",
    })

    raw = result.get("final_answer", "") if isinstance(result, dict) else str(result)

    enforcement = enforcer.enforce(raw, schema_obj)

    if enforcement.success:
        formatted = json.dumps(enforcement.data, indent=2)
        retries_note = f" (auto-repaired)" if enforcement.retries > 0 else ""
        return f"## Structured Output{retries_note}\n\n```json\n{formatted}\n```"
    else:
        errors = "\n".join(f"- {e}" for e in enforcement.errors)
        return f"## Schema Validation Failed\n\n{errors}\n\n### Raw Response\n{raw[:2000]}"


@mcp.tool()
def ai_team_approval_create(
    description: str,
    gate_type: str = "custom",
    workflow_id: str = "",
    context: str = "",
    timeout_minutes: int = 60,
) -> str:
    """
    Create a human-in-the-loop approval gate. The workflow pauses until
    you approve, reject, or modify. Like CrewAI/LangGraph's human checkpoints.

    Args:
        description: What needs approval (e.g. "Deploy 15 changes to production?")
        gate_type: Type — deploy, code_change, security, data_delete, cost, workflow_step, custom
        workflow_id: Optional workflow ID to associate with
        context: JSON string with additional context (e.g. '{"risk": "high", "changes": 15}')
        timeout_minutes: Minutes before gate expires (default 60)
    """
    from elgringo.intelligence.approval_gates import get_gate_manager

    mgr = get_gate_manager()

    ctx = {}
    if context:
        try:
            ctx = json.loads(context)
        except json.JSONDecodeError:
            ctx = {"raw": context}

    gate_id = mgr.create_gate(
        workflow_id=workflow_id or f"manual-{uuid.uuid4().hex[:6]}",
        description=description,
        gate_type=gate_type,
        context=ctx,
        timeout_seconds=timeout_minutes * 60,
    )

    gate = mgr.get_gate(gate_id)
    status = gate.status.value if gate else "unknown"

    if status == "skipped":
        return f"## Gate Auto-Approved\nID: `{gate_id}` — matched an auto-rule"

    return (
        f"## Approval Gate Created\n"
        f"**ID:** `{gate_id}`\n"
        f"**Status:** PENDING\n"
        f"**Description:** {description}\n"
        f"**Type:** {gate_type}\n"
        f"**Expires in:** {timeout_minutes} minutes\n\n"
        f"Use `ai_team_approval_decide` to approve or reject."
    )


@mcp.tool()
def ai_team_approval_decide(
    gate_id: str,
    decision: str,
    comment: str = "",
) -> str:
    """
    Approve, reject, or modify a pending approval gate.

    Args:
        gate_id: The gate ID to decide on
        decision: "approve", "reject", or "modify"
        comment: Reason or modifications (required for reject/modify)
    """
    from elgringo.intelligence.approval_gates import get_gate_manager

    mgr = get_gate_manager()
    gate = mgr.get_gate(gate_id)

    if not gate:
        return f"Gate `{gate_id}` not found."
    if gate.is_resolved:
        return f"Gate `{gate_id}` already resolved: **{gate.status.value}** ({gate.comment})"

    if decision == "approve":
        mgr.approve(gate_id, comment)
        return f"## Gate APPROVED\n`{gate_id}`: {gate.description}\n{comment}"
    elif decision == "reject":
        mgr.reject(gate_id, comment or "Rejected")
        return f"## Gate REJECTED\n`{gate_id}`: {gate.description}\nReason: {comment or 'No reason given'}"
    elif decision == "modify":
        mods = {}
        if comment:
            try:
                mods = json.loads(comment)
            except json.JSONDecodeError:
                mods = {"instructions": comment}
        mgr.modify_and_approve(gate_id, mods, comment)
        return f"## Gate MODIFIED + APPROVED\n`{gate_id}`: {gate.description}"
    else:
        return f"Invalid decision '{decision}'. Use: approve, reject, modify"


@mcp.tool()
def ai_team_approval_list() -> str:
    """
    List all pending approval gates waiting for human decision.
    """
    from elgringo.intelligence.approval_gates import get_gate_manager

    mgr = get_gate_manager()
    pending = mgr.get_pending_gates()

    if not pending:
        return "No pending approval gates."

    parts = [f"## Pending Approval Gates ({len(pending)})\n"]
    for gate in pending:
        parts.append(
            f"- **`{gate.gate_id}`** [{gate.gate_type.value}] {gate.description}\n"
            f"  Created: {gate.created_at[:19]} | Workflow: {gate.workflow_id}"
        )
        if gate.context:
            ctx_str = ", ".join(f"{k}={v}" for k, v in list(gate.context.items())[:3])
            parts.append(f"  Context: {ctx_str}")

    return "\n".join(parts)


@mcp.tool()
def ai_team_workflow(
    yaml_def: str,
    variables: str = "",
    context: str = "",
) -> str:
    """
    Execute a declarative YAML workflow — like CrewAI tasks or LangGraph pipelines.
    Define multi-step AI workflows with dependencies, modes, and schemas.

    Args:
        yaml_def: YAML workflow definition (inline). Example:
            name: review-pipeline
            steps:
              - name: analyze
                prompt: "Analyze code for bugs"
                mode: parallel
              - name: fix
                prompt: "Fix the top 3 bugs found"
                mode: consensus
                depends_on: [analyze]
        variables: JSON string of variables to substitute ${var} in prompts
        context: Additional context to pass to all steps
    """
    from elgringo.workflows.yaml_runner import YAMLWorkflowRunner

    vars_dict = {}
    if variables:
        try:
            vars_dict = json.loads(variables)
        except json.JSONDecodeError:
            return f"Invalid variables JSON: {variables[:200]}"

    async def collaborate_via_api(prompt, mode="parallel", context="", **kwargs):
        body = {"prompt": prompt, "mode": mode, "budget": "standard"}
        if context:
            body["context"] = context
        result = _api("POST", "/v1/collaborate", body)
        class _R:
            def __init__(self, d):
                self.final_answer = d.get("final_answer", str(d)) if isinstance(d, dict) else str(d)
        return _R(result)

    runner = YAMLWorkflowRunner(collaborate_fn=collaborate_via_api)

    try:
        definition = runner.parse_yaml(yaml_def)
    except Exception as e:
        return f"YAML parse error: {e}"

    try:
        result = _run_async(runner.run(definition, context=context))
    except Exception as e:
        return f"Workflow execution error: {e}"

    parts = [
        f"## Workflow: {result.workflow_name}",
        f"**Status:** {'SUCCESS' if result.success else 'FAILED'} | "
        f"Steps: {result.steps_completed}/{result.steps_total} | "
        f"Time: {result.total_time:.1f}s",
    ]

    for step in result.step_results:
        icon = "OK" if step["status"] == "completed" else "FAIL" if step["status"] == "failed" else "SKIP"
        parts.append(f"\n### [{icon}] {step['name']} ({step['duration']}s)")
        if step["output_preview"]:
            parts.append(step["output_preview"])
        if step["error"]:
            parts.append(f"**Error:** {step['error']}")

    if result.errors:
        parts.append("\n### Errors")
        for err in result.errors:
            parts.append(f"- {err}")

    return "\n".join(parts)


@mcp.tool()
def ai_team_schemas() -> str:
    """
    List all built-in structured output schemas available for ai_team_structured.
    """
    from elgringo.intelligence.structured_output import get_structured_enforcer

    enforcer = get_structured_enforcer()
    schemas = enforcer.list_schemas()

    parts = ["## Built-in Structured Output Schemas\n"]
    for name in schemas:
        schema = enforcer.get_schema(name)
        props = list(schema.get("properties", {}).keys())
        required = schema.get("required", [])
        parts.append(f"### `{name}`")
        parts.append(f"Fields: {', '.join(props)}")
        parts.append(f"Required: {', '.join(required)}")
        parts.append("")

    return "\n".join(parts)


# ── Moat Feature #1: Live Production Agent ─────────────────────────

@mcp.tool()
def ai_team_guardian(error_text: str) -> str:
    """
    Auto-diagnose a production error using El Gringo's Production Guardian.
    Pattern-matches against 9 known error categories (connection, auth, OOM, SSL, etc.)
    and suggests fixes with confidence scores. No API call needed — runs locally.

    Args:
        error_text: The error message or stack trace to diagnose
    """
    from elgringo.intelligence.production_guardian import get_guardian

    guardian = get_guardian()
    result = guardian.diagnose(error_text)

    parts = [
        f"## Diagnosis",
        f"**Category:** {result.category}",
        f"**Confidence:** {result.confidence:.0%}",
        f"**Likely Cause:** {result.likely_cause}",
        "",
        "### Suggested Fixes",
    ]
    for i, fix in enumerate(result.suggested_fixes, 1):
        parts.append(f"{i}. {fix}")

    return "\n".join(parts)


# ── Moat Feature #2: Cross-Project Intelligence ───────────────────

@mcp.tool()
def ai_team_knowledge_store(
    item_type: str = "solution",
    content: str = "",
    context: str = "",
    tags: str = "",
    source_project: str = "",
) -> str:
    """
    Store knowledge (solution, mistake, pattern, lesson) in El Gringo's
    cross-project intelligence nexus for future reuse across ALL projects.
    No API call needed — runs locally.

    Args:
        item_type: Type of knowledge: solution, mistake, pattern, or lesson
        content: The knowledge content to store
        context: Additional context about when/why this was learned
        tags: Comma-separated tags (e.g. "python,fastapi,cors")
        source_project: Which project this came from
    """
    from elgringo.intelligence.knowledge_packs import get_exporter
    from elgringo.intelligence.cross_project import get_nexus

    tag_list = [t.strip() for t in tags.split(",") if t.strip()] if tags else []

    exporter = get_exporter()
    item_id = exporter.add_knowledge(
        item_type=item_type, content=content, context=context,
        tags=tag_list, source_project=source_project,
    )

    nexus = get_nexus()
    if item_type == "solution":
        nexus.index_solution(source_project or "unknown", context or content, content, tag_list)
    elif item_type == "mistake":
        nexus.index_mistake(source_project or "unknown", content, context, tag_list)

    return f"Stored {item_type} (ID: {item_id}) with tags: {tag_list or 'none'}"


# ── Moat Feature #4: Project Registration ─────────────────────────

@mcp.tool()
def elgringo_project_register(project_name: str = "", project_path: str = "") -> str:
    """
    Register a project in El Gringo's cross-project intelligence nexus.
    Shows what knowledge from OTHER projects might help this one.
    No API call needed — runs locally.

    Args:
        project_name: Name of the project to register
        project_path: Path to the project directory
    """
    from elgringo.intelligence.cross_project import get_nexus

    nexus = get_nexus()

    proj_id = nexus.register_project(project_name, project_path)

    stats = nexus.get_stats()
    patterns = nexus.get_cross_project_patterns()

    parts = [
        f"## Project Registered: {project_name}",
        f"**ID:** {proj_id}",
        "",
        f"### Cross-Project Knowledge Available",
        f"- **{stats['total_solutions']}** solutions indexed across **{stats['total_projects']}** projects",
        f"- **{stats['total_mistakes']}** mistakes documented for prevention",
        f"- **{len(patterns)}** cross-project patterns detected",
    ]

    if patterns:
        parts.append("\n### Patterns That Span Multiple Projects")
        for p in patterns[:5]:
            parts.append(f"- **{p.pattern}** — seen in {', '.join(p.projects_affected)} ({p.occurrences} times)")

    return "\n".join(parts)


# ── Smart Response Cache ──────────────────────────────────────────

@mcp.tool()
def ai_team_cache_stats() -> str:
    """
    Show El Gringo's smart response cache statistics.
    See hit rate, cost savings, fuzzy vs exact matches, and top cached prompts.
    """
    from elgringo.intelligence.smart_cache import get_smart_cache

    cache = get_smart_cache()
    stats = cache.get_stats()
    top_hits = cache.get_top_hits(5)

    parts = [
        "## Smart Cache Stats",
        f"**Entries:** {stats['total_entries']} / {stats['max_entries']}",
        f"**Hit Rate:** {stats['hit_rate']} ({stats['hits']} hits, {stats['misses']} misses)",
        f"**Exact Hits:** {stats['exact_hits']} | **Fuzzy Hits:** {stats['fuzzy_hits']}",
        f"**Cost Saved:** {stats['cost_saved']}",
        f"**Tokens Saved:** {stats['tokens_saved']:,}",
        f"**Similarity Threshold:** {stats['similarity_threshold']}",
    ]

    if top_hits:
        parts.append("\n### Top Cached Prompts")
        for hit in top_hits:
            parts.append(f"- **{hit['hit_count']}x** {hit['prompt']} ({hit['agent']}, saved ${hit['total_saved']:.4f})")

    return "\n".join(parts)


# ── Agent Quality Watchdog ────────────────────────────────────────

@mcp.tool()
def ai_team_quality_watchdog() -> str:
    """
    Show the health status of all AI agents in El Gringo's team.
    Includes quality scores, response times, trends, and any demoted agents.
    """
    from elgringo.intelligence.quality_watchdog import get_watchdog

    watchdog = get_watchdog()
    report = watchdog.get_health_report()

    parts = [
        "## Agent Health Report",
        f"**Demoted:** {report['demoted_count']} | **Active Alerts:** {report['active_alerts']}",
        "",
    ]

    for name, data in sorted(report["agents"].items()):
        icon = {"active": "OK", "warning": "WARN", "demoted": "DOWN", "probation": "PROB"}.get(data["status"], "?")
        parts.append(
            f"| {icon} | **{name}** | quality: {data['avg_quality']} | "
            f"speed: {data['avg_response_time']}s | "
            f"success: {data['success_rate']} | trend: {data['quality_trend']} |"
        )
        if data.get("demoted_reason"):
            parts.append(f"  *Reason: {data['demoted_reason']}*")

    alerts = watchdog.get_alerts(limit=5)
    if alerts:
        parts.append("\n### Recent Alerts")
        for a in alerts:
            parts.append(f"- [{a['severity']}] {a['message']}")

    return "\n".join(parts)


# ── Cost Arbitrage ─────────────────────────────────────────────────

@mcp.tool()
def ai_team_arbitrage() -> str:
    """
    Cost savings report — total spent vs baseline, per-provider breakdown,
    and which providers deliver best value. Shows how much El Gringo's
    smart routing is saving you.
    """
    from elgringo.intelligence.cost_arbitrage import get_optimizer

    opt = get_optimizer()
    report = opt.get_savings_report()

    parts = [
        "## Cost Arbitrage Report",
        f"**Total Spent:** ${report.get('total_spent', 0):.4f}",
        f"**Baseline (single provider):** ${report.get('baseline_cost', 0):.4f}",
        f"**Savings:** ${report.get('total_saved', 0):.4f} ({report.get('savings_pct', 0):.0f}%)",
        f"**Tasks Routed:** {report.get('total_tasks', 0)}",
    ]

    providers = report.get("provider_breakdown", {})
    if providers:
        parts.append("\n### Per Provider")
        for name, data in sorted(providers.items(), key=lambda x: x[1].get("cost", 0), reverse=True):
            parts.append(
                f"- **{name}**: ${data.get('cost', 0):.4f} | "
                f"{data.get('tasks', 0)} tasks | "
                f"avg quality: {data.get('avg_quality', 0):.2f}"
            )

    return "\n".join(parts)


@mcp.tool()
def ai_team_provider_compare(task_type: str = "coding") -> str:
    """
    Compare AI providers by value ratio for a specific task type.
    Shows which provider gives best quality-per-dollar for coding, analysis, etc.

    Args:
        task_type: Task type to compare — coding, debugging, analysis, writing, architecture
    """
    from elgringo.intelligence.cost_arbitrage import get_optimizer

    opt = get_optimizer()
    comparison = opt.get_provider_comparison(task_type)

    parts = [f"## Provider Comparison: {task_type}\n"]

    rankings = comparison.get("rankings", [])
    if not rankings:
        return f"No data yet for task type '{task_type}'. Use the AI team to build data."

    for i, entry in enumerate(rankings, 1):
        parts.append(
            f"{i}. **{entry.get('provider', '?')}** — "
            f"value: {entry.get('value_ratio', 0):.2f} | "
            f"quality: {entry.get('avg_quality', 0):.2f} | "
            f"cost: ${entry.get('avg_cost', 0):.4f}/task"
        )

    best = comparison.get("recommended", "")
    if best:
        parts.append(f"\n**Recommended:** {best}")

    return "\n".join(parts)


# ── Auto Failure Detection ─────────────────────────────────────────

@mcp.tool()
def ai_team_scan_response(
    content: str,
    task_type: str = "general",
    language: str = "",
) -> str:
    """
    Scan AI-generated output for syntax errors, security issues, hallucinations,
    incomplete code, and placeholder patterns. Catches problems that verify_code misses
    (response-level quality, not just syntax).

    Args:
        content: The AI response or code to scan
        task_type: What the task was — coding, debugging, analysis, general
        language: Programming language hint (auto-detected if empty)
    """
    from elgringo.intelligence.auto_failure_detector import get_failure_detector

    detector = get_failure_detector()
    result = detector.check(content, task_type=task_type, language=language or None)

    parts = [
        f"## Response Scan: {'PASSED' if result.passed else 'FAILED'}",
        f"Code blocks checked: {result.code_blocks_checked}",
        f"Failures found: {len(result.failures)}",
    ]

    if result.failures:
        critical = [f for f in result.failures if f.severity == "critical"]
        warnings = [f for f in result.failures if f.severity == "warning"]

        if critical:
            parts.append(f"\n### Critical ({len(critical)})")
            for f in critical[:5]:
                parts.append(f"- {f.description}")
                if f.fix_suggestion:
                    parts.append(f"  Fix: {f.fix_suggestion}")

        if warnings:
            parts.append(f"\n### Warnings ({len(warnings)})")
            for f in warnings[:5]:
                parts.append(f"- {f.description}")
    else:
        parts.append("\nNo issues detected.")

    return "\n".join(parts)


# ── Reasoning Transparency ────────────────────────────────────────

@mcp.tool()
def ai_team_transparency(
    prompt: str,
    answer: str,
    agent_responses_json: str = "",
) -> str:
    """
    Show how a multi-agent answer was built — consensus level, disagreements,
    contribution weights, and reasoning steps. Explains WHY the team gave
    this answer instead of alternatives.

    Args:
        prompt: The original prompt
        answer: The final synthesized answer
        agent_responses_json: JSON array of agent responses (each with agent_name, content, confidence).
                              If empty, returns a basic analysis of the answer.
    """
    from elgringo.intelligence.reasoning_transparency import get_reasoning_transparency
    from elgringo.agents.base import AgentResponse, ModelType

    rt = get_reasoning_transparency()

    responses = []
    if agent_responses_json:
        try:
            raw = json.loads(agent_responses_json)
            for r in raw:
                responses.append(AgentResponse(
                    agent_name=r.get("agent_name", "unknown"),
                    model_type=ModelType.LOCAL,
                    content=r.get("content", ""),
                    confidence=r.get("confidence", 0.5),
                    response_time=r.get("response_time", 0.0),
                ))
        except (json.JSONDecodeError, KeyError):
            return "Invalid agent_responses_json. Expected JSON array with agent_name, content, confidence."

    if not responses:
        return f"No agent responses to analyze. Provide agent_responses_json for transparency report."

    report = rt.analyze(responses, prompt, answer)
    d = report.to_dict()

    parts = [
        "## Reasoning Transparency Report",
        f"**Consensus:** {d['consensus']['level']:.0%} — {d['consensus']['description']}",
        f"**Primary Contributor:** {d.get('primary_contributor', 'N/A')}",
    ]

    if d.get("contribution_breakdown"):
        parts.append("\n### Contribution Weights")
        for agent, weight in sorted(d["contribution_breakdown"].items(), key=lambda x: x[1], reverse=True):
            parts.append(f"- {agent}: {weight:.0%}")

    if d["consensus"].get("agreements"):
        parts.append(f"\n### Agreement Points ({len(d['consensus']['agreements'])})")
        for a in d["consensus"]["agreements"][:5]:
            parts.append(f"- {a}")

    if d["consensus"].get("disagreements"):
        parts.append(f"\n### Disagreements ({len(d['consensus']['disagreements'])})")
        for dis in d["consensus"]["disagreements"][:3]:
            parts.append(f"- **{dis['topic']}** — Resolution: {dis['resolution']} ({dis['method']})")

    return "\n".join(parts)


# ── Agent Insights (deep profiles from feedback loop) ─────────────

@mcp.tool()
def ai_team_agent_insights() -> str:
    """
    Deep agent profiles built from accumulated feedback — satisfaction rates,
    per-task-type scores, expertise adjustments, and performance trends.
    Reads data recorded by ai_team_rate().
    """
    from elgringo.intelligence.feedback_loop import get_feedback_loop

    floop = get_feedback_loop()
    profiles = floop.get_all_profiles()
    summary = floop.get_roi_summary()

    if not profiles:
        return "No agent insights yet. Use `ai_team_rate` to record feedback."

    parts = [
        "## Agent Insights",
        f"**Trending:** {summary.get('trending', 'neutral')}",
        f"**Total Feedback Events:** {summary.get('total_feedback_events', 0)}",
        f"**Avg Satisfaction:** {summary.get('avg_satisfaction', 0):.0%}",
        "",
    ]

    for name, profile in sorted(profiles.items()):
        if not profile:
            continue
        parts.append(f"### {name}")
        parts.append(f"Satisfaction: {profile.get('satisfaction_rate', 0):.0%} | Events: {profile.get('total_events', 0)}")

        scores = profile.get("task_type_scores", {})
        if scores:
            score_str = ", ".join(f"{k}: {v:.2f}" for k, v in sorted(scores.items(), key=lambda x: x[1], reverse=True)[:5])
            parts.append(f"Task scores: {score_str}")

        adjustments = profile.get("expertise_adjustments", {})
        if adjustments:
            adj_str = ", ".join(f"{k}: {v:+.2f}" for k, v in sorted(adjustments.items(), key=lambda x: abs(x[1]), reverse=True)[:3])
            parts.append(f"Expertise adjustments: {adj_str}")

        parts.append("")

    return "\n".join(parts)


# ── Cross-Project Intelligence (Nexus) ────────────────────────────

@mcp.tool()
def ai_team_nexus_search(query: str, limit: int = 10) -> str:
    """
    Search solutions and mistakes across ALL registered projects.
    Finds patterns from other projects that might help your current task.

    Args:
        query: Search query (e.g. "database migration", "auth token refresh")
        limit: Max results to return (default 10)
    """
    from elgringo.intelligence.cross_project import get_nexus

    nexus = get_nexus()
    results = nexus.search_across_projects(query, limit=limit)

    if not results:
        stats = nexus.get_stats()
        return (
            f"No matches for '{query}'.\n"
            f"Nexus has {stats['total_solutions']} solutions and "
            f"{stats['total_mistakes']} mistakes across {stats['total_projects']} projects."
        )

    parts = [f"## Nexus Search: '{query}' ({len(results)} results)\n"]
    for r in results:
        parts.append(
            f"- [{r.get('type', '?')}] **{r.get('summary', r.get('content', '')[:80])}**\n"
            f"  Project: {r.get('project', 'unknown')} | "
            f"Tags: {', '.join(r.get('tags', [])[:5])}"
        )

    return "\n".join(parts)


@mcp.tool()
def ai_team_nexus_patterns() -> str:
    """
    Show patterns spanning multiple projects — recurring solutions, common
    mistakes, and cross-project insights from the Knowledge Nexus.
    """
    from elgringo.intelligence.cross_project import get_nexus

    nexus = get_nexus()
    patterns = nexus.get_cross_project_patterns()
    stats = nexus.get_stats()

    parts = [
        "## Cross-Project Patterns",
        f"**Projects:** {stats['total_projects']} | "
        f"**Solutions:** {stats['total_solutions']} | "
        f"**Mistakes:** {stats['total_mistakes']}",
    ]

    if not patterns:
        parts.append("\nNo cross-project patterns detected yet. Register more projects and store knowledge.")
        return "\n".join(parts)

    parts.append("")
    for p in patterns[:10]:
        parts.append(
            f"- **{p.pattern}** — {p.occurrences} occurrences across "
            f"{', '.join(p.projects_affected[:3])}"
        )
        if p.solution:
            parts.append(f"  Solution: {p.solution}")

    return "\n".join(parts)
