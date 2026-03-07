"""
Fred — Your AI Personal Assistant.
Uses Gemini 2.5 Flash for fast, capable chat with action execution.
Supports ACTION: execution loop for real task/memory/git/file operations.
"""

import logging
import json
import os
from datetime import date, datetime

from products.fred_assistant.database import get_conn
from products.fred_assistant.services.llm_shared import get_gemini as _get_gemini, llm_response as _llm_response

logger = logging.getLogger(__name__)

# Lazy imports to avoid circular dependency chains at startup
_fred_tools_cache = None


def _get_fred_tools():
    global _fred_tools_cache
    if _fred_tools_cache is None:
        from products.fred_assistant.services import fred_tools
        _fred_tools_cache = fred_tools
    return _fred_tools_cache


def _lazy_service(name):
    import importlib
    return importlib.import_module(f"products.fred_assistant.services.{name}")


# Re-export fred_tools functions as lazy accessors
def parse_actions(text): return _get_fred_tools().parse_actions(text)
def strip_action_lines(text): return _get_fred_tools().strip_action_lines(text)
async def execute_actions(actions): return await _get_fred_tools().execute_actions(actions)
def get_tool_definitions(): return _get_fred_tools().get_tool_definitions()
MAX_ROUNDS = 5  # Same as fred_tools.MAX_ROUNDS

FRED_SYSTEM_PROMPT = """You are Fred, a highly capable AI personal assistant for Fred Taylor.
You are the central brain of the El Gringo platform — you command an entire AI dev team through your actions.
You are direct, efficient, and proactive. You know Fred's tasks, schedule, preferences, and history.

Your personality:
- Concise and action-oriented (no fluff)
- Proactive — suggest what to work on, flag overdue items, remind about priorities
- Personal — you remember preferences and patterns
- Honest — push back when something doesn't make sense

You command these platform services:
- Code Audit Service — security audits, code quality reviews
- Test Generator — AI-generated unit tests, coverage analysis
- Doc Generator — READMEs, API docs, architecture diagrams
- PR Review Bot — automated pull request reviews
- Repo Intelligence — project health analysis, task generation

You can help with:
- Task management (create, prioritize, move tasks)
- Daily planning and time blocking
- Project strategy and architecture decisions
- Code audits, test generation, and documentation
- Full project reviews (chains audit + tests + docs + analysis)
- Content creation and review
- Remembering anything Fred tells you
- Code reviews, debugging, and technical guidance
- Calendar and scheduling
- Content generation for social media
- Business strategy and goal tracking
- CRM / lead pipeline management

When Fred asks you to do something, USE YOUR ACTIONS to actually do it.
Don't just describe what you would do — take the action.
For platform services (audit, tests, docs), use the platform tools to dispatch work to specialist services.
You are the orchestrator — you decide what gets done and command the team to do it.

When Fred asks you to remember something, acknowledge it clearly.
When he asks about his tasks or schedule, reference actual data.
Always be specific and actionable.
"""

COACH_SYSTEM_PROMPT = """You are Fred's AI Business Coach — a direct, no-BS strategic advisor.

Your role:
- Hold Fred accountable to his goals
- Challenge assumptions and push for clarity
- Provide actionable business strategy advice
- Help prioritize what actually matters
- Give honest feedback, even when it's uncomfortable

Your style:
- Direct and concise (no motivational fluff)
- Data-driven (reference actual progress, metrics)
- Strategic (think long-term, not just tactics)
- Empathetic but firm (push back when needed)

You know Fred's goals, tasks, and weekly progress. Reference them in your advice.
Always end with a specific action item or question to keep momentum.

When asked to do something (check accountability, create goals, find revenue),
USE YOUR ACTIONS to actually do it.
"""

PERSONA_PROMPTS = {
    "fred": FRED_SYSTEM_PROMPT,
    "coach": COACH_SYSTEM_PROMPT,
}


def _build_system_prompt(persona: str = "fred") -> str:
    """Build full system prompt with tool definitions."""
    base = PERSONA_PROMPTS.get(persona, FRED_SYSTEM_PROMPT)
    tools = get_tool_definitions()
    return f"{base}\n\n{tools}"


def _build_realtime_context(persona: str = "fred") -> list[str]:
    """Build real-time context sections shared by both context builders."""
    parts = []

    parts.append(f"Today is {date.today().strftime('%A, %B %d, %Y')}.\n")

    stats = _lazy_service("task_service").get_dashboard_stats()
    parts.append(f"## Current Status")
    parts.append(f"- Active tasks: {stats['total_tasks']}")
    parts.append(f"- In progress: {stats['in_progress']}")
    parts.append(f"- Due today: {stats['due_today']}")
    parts.append(f"- Overdue: {stats['overdue']}")
    parts.append(f"- Completed today: {stats['completed_today']}")
    parts.append(f"- Streak: {stats['streak_days']} days\n")

    boards = _lazy_service("task_service").list_boards()
    if boards:
        parts.append("## Boards")
        for b in boards:
            parts.append(f"- **{b['id']}**: {b['name']} ({b.get('task_count', 0)} active tasks)")
        parts.append("")

    today_tasks = _lazy_service("task_service").get_today_tasks()
    if today_tasks:
        parts.append("## Today's Tasks")
        for t in today_tasks[:15]:
            status_icon = {"todo": "⬜", "in_progress": "🔵", "review": "🟡", "done": "✅"}.get(
                t["status"], "⬜"
            )
            overdue = ""
            if t.get("due_date") and t["due_date"] < date.today().isoformat() and t["status"] != "done":
                overdue = " ⚠️ OVERDUE"
            parts.append(f"- {status_icon} [{t['board_id']}] {t['title']} (P{t['priority']}){overdue}")
        parts.append("")

    if persona == "coach":
        try:
            from products.fred_assistant.services import coach_service
            goals = coach_service.list_goals(status="active")
            if goals:
                parts.append("## Active Goals")
                for g in goals[:10]:
                    parts.append(f"- {g['title']} ({g['category']}, {g['progress']}% complete)")
                parts.append("")

            review = coach_service.get_current_review()
            if review and review.get("week_start"):
                parts.append("## This Week's Review")
                if review.get("wins"):
                    parts.append(f"- Wins: {', '.join(review['wins'][:3])}")
                if review.get("challenges"):
                    parts.append(f"- Challenges: {', '.join(review['challenges'][:3])}")
                parts.append("")
        except Exception:
            pass

    try:
        from products.fred_assistant.services import inbox_service
        inbox_count = inbox_service.get_inbox_count()
        if inbox_count.get("total", 0) > 0:
            parts.append(f"## Inbox: {inbox_count['total']} items needing attention")
            for t, c in inbox_count.get("by_type", {}).items():
                parts.append(f"- {t}: {c}")
            parts.append("")
    except Exception:
        pass

    try:
        from products.fred_assistant.services import focus_service
        active = focus_service.get_active_session()
        if active:
            parts.append(f"## Active Focus Session")
            parts.append(f"- Task: {active.get('task_title', 'None')}")
            parts.append(f"- Started: {active['started_at'][:16]}")
            parts.append(f"- Planned: {active['planned_minutes']} min")
            parts.append("")
    except Exception:
        pass

    try:
        from products.fred_assistant.services import crm_service
        pipeline = crm_service.get_pipeline_summary()
        if pipeline.get("total_leads", 0) > 0:
            parts.append(f"## Pipeline: {pipeline['total_leads']} leads (${pipeline['total_pipeline_value']:,.0f} total)")
            for stage, data in pipeline.get("stages", {}).items():
                if data["count"] > 0:
                    parts.append(f"- {stage}: {data['count']} (${data['total_value']:,.0f})")
            parts.append("")
    except Exception:
        pass

    try:
        from products.fred_assistant.services import platform_services
        cached = platform_services.get_cached_status()
        if cached:
            online = sum(1 for s in cached.values() if s.get("healthy"))
            total = len(cached)
            parts.append(f"## Platform: {online}/{total} services online")
            for name, s in cached.items():
                st = "online" if s.get("healthy") else "offline"
                parts.append(f"- {s.get('label', name)}: {st}")
            parts.append("")
    except Exception:
        pass

    try:
        from products.fred_assistant.services import platform_services as ps
        recent = ps.get_recent_results(service="pr_review", limit=3)
        if recent:
            parts.append("## Recent PR Reviews")
            for r in recent:
                try:
                    data = json.loads(r.get("result", "{}"))
                except (ValueError, TypeError):
                    data = {}
                verdict = data.get("verdict", r.get("action", ""))
                pr_num = data.get("pr_number", "")
                parts.append(f"- {r.get('project_name', '?')} PR #{pr_num}: {verdict}")
            parts.append("")
    except Exception:
        pass

    return parts


def _build_context(persona: str = "fred") -> str:
    """Build full context from tasks + memories for the AI."""
    parts = _build_realtime_context(persona)

    memory_ctx = _lazy_service("memory_service").get_context_for_chat()
    if memory_ctx:
        parts.append(memory_ctx)

    return "\n".join(parts)


def _build_context_with_rag(user_message: str, persona: str = "fred") -> str:
    """Build context using RAG for semantic retrieval of memories/tasks/results.

    Real-time sections (stats, boards, today's tasks, inbox, focus, CRM, platform)
    are shared via _build_realtime_context(). Only memories, backlog tasks, and
    service results use semantic retrieval.

    Falls back to _build_context() if RAG is unavailable.
    """
    parts = _build_realtime_context(persona)

    # ── RAG sections (semantic retrieval replaces dump-everything) ──

    rag_used = False
    try:
        from products.fred_assistant.services.rag_service import get_rag
        rag = get_rag()
        if rag.is_ready:
            results = rag.query_for_context(user_message)

            # Relevant memories
            if results["memories"]:
                rag_used = True
                parts.append("## What I know about you (relevant):")
                for item in results["memories"]:
                    parts.append(f"- {item['document']}")
                parts.append("")

            # Relevant backlog tasks
            if results["tasks"]:
                rag_used = True
                parts.append("## Related tasks:")
                for item in results["tasks"]:
                    meta = item.get("metadata", {})
                    status = meta.get("status", "")
                    board = meta.get("board_id", "")
                    parts.append(f"- [{board}] {item['document']} ({status})")
                parts.append("")

            # Relevant service results
            if results["service_results"]:
                rag_used = True
                parts.append("## Related platform results:")
                for item in results["service_results"]:
                    parts.append(f"- {item['document']}")
                parts.append("")

            # Relevant project knowledge
            if results.get("projects"):
                rag_used = True
                parts.append("## Relevant project context:")
                for item in results["projects"]:
                    meta = item.get("metadata", {})
                    project = meta.get("project", "")
                    chunk = meta.get("chunk", "")
                    parts.append(f"- [{project}/{chunk}] {item['document']}")
                parts.append("")
    except Exception:
        pass

    # Fallback: if RAG didn't provide memories, use old dump
    if not rag_used:
        memory_ctx = _lazy_service("memory_service").get_context_for_chat()
        if memory_ctx:
            parts.append(memory_ctx)

    return "\n".join(parts)


def get_chat_messages(system_prompt: str = None, persona: str = "fred", limit: int = 20) -> list[dict]:
    """Get recent chat history formatted for LLM."""
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT role, content FROM chat_messages ORDER BY id DESC LIMIT ?", (limit,)
        ).fetchall()

    prompt = system_prompt or _build_system_prompt(persona)
    messages = [{"role": "system", "content": prompt}]
    # Add context as a system message
    ctx = _build_context(persona)
    if ctx:
        messages.append({"role": "system", "content": ctx})
    # Add history in chronological order
    for r in reversed(rows):
        messages.append({"role": r["role"], "content": r["content"]})
    return messages


def save_message(role: str, content: str, persona: str = "fred"):
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO chat_messages (role, content, persona) VALUES (?,?,?)",
            (role, content, persona),
        )
        msg_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
    # Index in RAG (fire-and-forget)
    try:
        from products.fred_assistant.services.rag_service import get_rag
        get_rag().index_chat_message(str(msg_id), role, content, persona)
    except Exception:
        pass


def get_history(limit: int = 50) -> list[dict]:
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT role, content, persona, created_at FROM chat_messages ORDER BY id DESC LIMIT ?",
            (limit,),
        ).fetchall()
        return [dict(r) for r in reversed(rows)]


def clear_history():
    with get_conn() as conn:
        conn.execute("DELETE FROM chat_messages")


def _format_result_line(r: dict) -> str:
    """Format a single action result into a string Gemini can understand."""
    status = "OK" if r.get("success") else "FAILED"
    msg = r.get("message", r.get("error", ""))
    if msg:
        return f"- {r['action']}: {status} — {msg}"
    # No message — serialize key fields (skip internal keys)
    skip = {"action", "success", "fn", "async"}
    data = {k: v for k, v in r.items() if k not in skip and v}
    if data:
        summary = json.dumps(data, default=str)[:1000]
        return f"- {r['action']}: {status} — {summary}"
    return f"- {r['action']}: {status}"


async def _run_action_loop(prompt: str, system_prompt: str, persona: str = "fred") -> tuple[str, list[dict]]:
    """Run the AI with action execution loop. Returns (final_reply, all_action_results)."""
    all_results = []
    reply = ""
    original_prompt = prompt

    for round_num in range(MAX_ROUNDS):
        reply = await _llm_response(prompt, system_prompt)
        if not reply:
            # LLM unavailable — use fallback
            if all_results:
                return _format_action_results(all_results), all_results
            return _fallback_response(original_prompt), all_results

        # Check for actions
        actions = parse_actions(reply)
        if not actions:
            return strip_action_lines(reply), all_results

        # Execute actions
        results = await execute_actions(actions)
        all_results.extend(results)

        # Build follow-up prompt — compact format to avoid token bloat
        results_text = "\n".join(
            _format_result_line(r)
            for r in results
        )
        if round_num == 0:
            prompt = (
                f"{prompt}\n\nAssistant: {reply}\n\n"
                f"[Action results]\n{results_text}\n\n"
                f"Now respond to the user naturally based on the action results above. "
                f"Do NOT include ACTION: lines — all actions are complete."
            )
        else:
            all_results_text = "\n".join(
                _format_result_line(r)
                for r in all_results
            )
            prompt = (
                f"{original_prompt}\n\n"
                f"[All action results from {len(all_results)} actions]\n{all_results_text}\n\n"
                f"Now respond to the user naturally based on ALL action results above. "
                f"Do NOT include ACTION: lines — all actions are complete."
            )

    return strip_action_lines(reply), all_results


def _format_action_results(results: list[dict]) -> str:
    """Format action results into a readable response."""
    lines = ["Here's what I did:"]
    for r in results:
        lines.append(_format_result_line(r))
    return "\n".join(lines)


async def chat(message: str, persona: str = "fred") -> str:
    """Send a message to Fred and get a response with action execution."""
    save_message("user", message, persona)

    system_prompt = _build_system_prompt(persona)
    context = _build_context_with_rag(message, persona)
    user_prompt = f"{context}\n\nUser: {message}\nFred:"

    reply, action_results = await _run_action_loop(user_prompt, system_prompt, persona)

    save_message("assistant", reply, persona)
    return reply


async def stream_chat(message: str, persona: str = "fred"):
    """Stream a response with action execution support."""
    save_message("user", message, persona)

    system_prompt = _build_system_prompt(persona)
    context = _build_context_with_rag(message, persona)
    user_prompt = f"{context}\n\nUser: {message}\nFred:"

    all_results = []
    reply = ""
    original_prompt = user_prompt

    for round_num in range(MAX_ROUNDS):
        reply = await _llm_response(user_prompt, system_prompt)
        if not reply:
            # LLM unavailable — use fallback
            fallback = _fallback_response(message)
            save_message("assistant", fallback, persona)
            yield {"type": "token", "data": fallback}
            return

        # Check for actions
        actions = parse_actions(reply)
        if not actions:
            # No actions — stream the clean reply
            clean = strip_action_lines(reply)
            save_message("assistant", clean, persona)
            yield {"type": "token", "data": clean}
            return

        # Has actions — signal thinking, execute, loop
        action_names = ", ".join(a["name"] for a in actions)
        yield {"type": "thinking", "data": action_names}

        results = await execute_actions(actions)
        all_results.extend(results)

        yield {"type": "thinking_done", "data": f"{len(results)} actions completed"}

        # Build follow-up prompt
        results_text = "\n".join(
            _format_result_line(r)
            for r in results
        )
        if round_num == 0:
            user_prompt = (
                f"{user_prompt}\n\nAssistant: {reply}\n\n"
                f"[Action results]\n{results_text}\n\n"
                f"Now respond to the user naturally based on the action results above. "
                f"Do NOT include ACTION: lines — all actions are complete."
            )
        else:
            all_results_text = "\n".join(
                _format_result_line(r)
                for r in all_results
            )
            user_prompt = (
                f"{original_prompt}\n\n"
                f"[All action results from {len(all_results)} actions]\n{all_results_text}\n\n"
                f"Now respond to the user naturally based on ALL action results above. "
                f"Do NOT include ACTION: lines — all actions are complete."
            )

    # Max rounds — stream what we have
    clean = strip_action_lines(reply)
    save_message("assistant", clean, persona)
    yield {"type": "token", "data": clean}


def _fallback_response(message: str) -> str:
    """Basic response when the AI orchestrator is unavailable."""
    msg = message.lower()
    stats = _lazy_service("task_service").get_dashboard_stats()

    if any(w in msg for w in ["task", "todo", "what should", "work on"]):
        today = _lazy_service("task_service").get_today_tasks()
        if today:
            lines = ["Here's what's on your plate today:"]
            for t in today[:5]:
                lines.append(f"- {t['title']} (P{t['priority']}, {t['status']})")
            return "\n".join(lines)
        return "Your task list is empty. Want to add something?"

    if any(w in msg for w in ["platform", "service", "running", "online", "health check"]):
        try:
            from products.fred_assistant.services import platform_services
            status = platform_services.check_all_services()
            online = sum(1 for s in status.values() if s.get("healthy"))
            total = len(status)
            lines = [f"Platform Status: {online}/{total} services online\n"]
            for name, s in status.items():
                icon = "🟢" if s.get("healthy") else "🔴"
                lines.append(f"{icon} {s.get('label', name)} (port {s.get('port', '?')})")
            return "\n".join(lines)
        except Exception:
            return "Unable to check platform status right now."

    if any(w in msg for w in ["status", "how am i", "progress", "stats"]):
        return (
            f"Here's where you stand:\n"
            f"- {stats['total_tasks']} active tasks\n"
            f"- {stats['in_progress']} in progress\n"
            f"- {stats['completed_today']} completed today\n"
            f"- {stats['overdue']} overdue\n"
            f"- {stats['streak_days']} day streak"
        )

    if "remember" in msg:
        return "I'd love to remember that, but I need the AI orchestrator running to parse it. Save it as a memory manually for now."

    return (
        "I'm running in offline mode (AI orchestrator not available). "
        "I can still show your tasks and stats. Try asking about your tasks or status."
    )


async def generate_briefing() -> dict:
    """Generate today's daily briefing."""
    import uuid

    today = date.today().isoformat()
    stats = _lazy_service("task_service").get_dashboard_stats()
    today_tasks = _lazy_service("task_service").get_today_tasks()

    # Try AI-generated briefing
    try:
        context = _build_context()
        prompt = (
            f"{context}\n\n"
            "Generate a concise daily briefing for Fred. Include:\n"
            "1. Top priorities for today\n"
            "2. Any overdue items that need attention\n"
            "3. A motivating note\n"
            "Keep it under 200 words. Be direct and actionable."
        )
        content = await _llm_response(prompt, FRED_SYSTEM_PROMPT)
    except Exception:
        # Fallback briefing
        lines = [f"# Daily Briefing — {date.today().strftime('%A, %B %d')}\n"]
        lines.append(f"**{stats['total_tasks']}** active tasks, **{stats['overdue']}** overdue, "
                      f"**{stats['due_today']}** due today.\n")
        if today_tasks:
            lines.append("## Top Priorities")
            for t in today_tasks[:5]:
                lines.append(f"- {t['title']} (P{t['priority']})")
        else:
            lines.append("No tasks scheduled for today. Time to plan!")
        if stats["streak_days"] > 0:
            lines.append(f"\n🔥 You're on a {stats['streak_days']}-day streak. Keep it up!")
        content = "\n".join(lines)

    briefing_id = uuid.uuid4().hex[:8]
    with get_conn() as conn:
        conn.execute(
            "INSERT OR REPLACE INTO briefings (id, date, content, tasks_snapshot) VALUES (?,?,?,?)",
            (briefing_id, today, content, json.dumps(stats)),
        )
    return {"id": briefing_id, "date": today, "content": content, "tasks_snapshot": stats}


async def generate_shutdown() -> dict:
    """Generate end-of-day shutdown review."""
    import uuid

    today = date.today().isoformat()
    stats = _lazy_service("task_service").get_dashboard_stats()
    today_tasks = _lazy_service("task_service").get_today_tasks()

    completed = [t for t in today_tasks if t.get("status") == "done"]
    incomplete = [t for t in today_tasks if t.get("status") != "done"]

    try:
        context = _build_context()
        prompt = (
            f"{context}\n\n"
            "Generate an end-of-day shutdown review for Fred. Include:\n"
            "1. What got done today (celebrate wins)\n"
            "2. What didn't get done (be honest, no shame)\n"
            "3. Top 3 priorities for tomorrow\n"
            "4. Any blockers or concerns to address\n"
            "Keep it under 200 words. Be direct and supportive."
        )
        content = await _llm_response(prompt, FRED_SYSTEM_PROMPT)
    except Exception:
        lines = [f"# Daily Shutdown — {date.today().strftime('%A, %B %d')}\n"]
        lines.append(f"**{len(completed)}** tasks completed, **{len(incomplete)}** remaining.\n")
        if completed:
            lines.append("## Wins")
            for t in completed[:5]:
                lines.append(f"- {t['title']}")
        if incomplete:
            lines.append("\n## Still Open")
            for t in incomplete[:5]:
                lines.append(f"- {t['title']} (P{t['priority']})")
        lines.append("\n## Tomorrow's Top 3")
        for t in sorted(incomplete, key=lambda x: x.get("priority", 3))[:3]:
            lines.append(f"1. {t['title']}")
        content = "\n".join(lines)

    briefing_id = uuid.uuid4().hex[:8]
    with get_conn() as conn:
        conn.execute(
            "INSERT OR REPLACE INTO briefings (id, date, content, tasks_snapshot, briefing_type) VALUES (?,?,?,?,?)",
            (briefing_id, today + "_shutdown", content, json.dumps(stats), "shutdown"),
        )
    return {"id": briefing_id, "date": today, "content": content, "type": "shutdown", "tasks_snapshot": stats}


def get_tomorrow_tasks() -> list[dict]:
    """Get tasks locked in as tomorrow's priorities."""
    tomorrow = date.today().isoformat()
    with get_conn() as conn:
        row = conn.execute(
            "SELECT tasks_snapshot FROM briefings WHERE date=? AND briefing_type='shutdown' ORDER BY created_at DESC LIMIT 1",
            (tomorrow + "_shutdown",),
        ).fetchone()
    if row:
        try:
            return json.loads(row["tasks_snapshot"]).get("tomorrow_priorities", [])
        except (json.JSONDecodeError, TypeError):
            pass
    # Fallback: top 3 active tasks by priority
    tasks = _lazy_service("task_service").get_today_tasks()
    active = [t for t in tasks if t.get("status") != "done"]
    return sorted(active, key=lambda x: x.get("priority", 3))[:3]


def get_today_briefing() -> dict | None:
    today = date.today().isoformat()
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM briefings WHERE date=?", (today,)).fetchone()
        if row:
            d = dict(row)
            d["tasks_snapshot"] = json.loads(d.get("tasks_snapshot") or "{}")
            return d
    return None
