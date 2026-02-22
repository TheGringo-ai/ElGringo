"""
Fred — Your AI Personal Assistant.
Wraps the FredAI orchestrator with personal context awareness.
"""

import logging
import json
from datetime import date, datetime

from products.fred_assistant.database import get_conn
from products.fred_assistant.services import memory_service, task_service

logger = logging.getLogger(__name__)

FRED_SYSTEM_PROMPT = """You are Fred, a highly capable AI personal assistant for Fred Taylor.
You are direct, efficient, and proactive. You know Fred's tasks, schedule, preferences, and history.
You help him stay on track with work and life.

Your personality:
- Concise and action-oriented (no fluff)
- Proactive — suggest what to work on, flag overdue items, remind about priorities
- Personal — you remember preferences and patterns
- Honest — push back when something doesn't make sense

You can help with:
- Task management (create, prioritize, move tasks)
- Daily planning and time blocking
- Project strategy and architecture decisions
- Content creation and review
- Remembering anything Fred tells you
- Code reviews, debugging, and technical guidance

When Fred asks you to remember something, acknowledge it clearly.
When he asks about his tasks or schedule, reference actual data.
Always be specific and actionable.
"""


def _build_context() -> str:
    """Build full context from tasks + memories for the AI."""
    parts = []

    # Today's date
    parts.append(f"Today is {date.today().strftime('%A, %B %d, %Y')}.\n")

    # Dashboard stats
    stats = task_service.get_dashboard_stats()
    parts.append(f"## Current Status")
    parts.append(f"- Active tasks: {stats['total_tasks']}")
    parts.append(f"- In progress: {stats['in_progress']}")
    parts.append(f"- Due today: {stats['due_today']}")
    parts.append(f"- Overdue: {stats['overdue']}")
    parts.append(f"- Completed today: {stats['completed_today']}")
    parts.append(f"- Streak: {stats['streak_days']} days\n")

    # Today's tasks
    today_tasks = task_service.get_today_tasks()
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

    # Memories
    memory_ctx = memory_service.get_context_for_chat()
    if memory_ctx:
        parts.append(memory_ctx)

    return "\n".join(parts)


def get_chat_messages(system_prompt: str = None, limit: int = 20) -> list[dict]:
    """Get recent chat history formatted for LLM."""
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT role, content FROM chat_messages ORDER BY id DESC LIMIT ?", (limit,)
        ).fetchall()

    messages = [{"role": "system", "content": system_prompt or FRED_SYSTEM_PROMPT}]
    # Add context as a system message
    ctx = _build_context()
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


async def chat(message: str, persona: str = "fred") -> str:
    """Send a message to Fred and get a response using the AI orchestrator."""
    save_message("user", message, persona)

    # Try to use the FredAI orchestrator
    try:
        from ai_dev_team.orchestrator import AIDevTeam

        team = AIDevTeam(enable_memory=True)
        await team.setup_agents()

        messages = get_chat_messages()
        # Build a prompt with context
        prompt = f"{messages[0]['content']}\n\n"
        for m in messages[1:]:
            if m["role"] == "system":
                prompt += f"\n{m['content']}\n"

        prompt += f"\nUser: {message}\nFred:"

        response = await team.ask(prompt)
        reply = response.get("response", "I'm having trouble processing that right now.")

    except Exception as e:
        logger.warning(f"Orchestrator unavailable, using fallback: {e}")
        reply = _fallback_response(message)

    save_message("assistant", reply, persona)
    return reply


async def stream_chat(message: str, persona: str = "fred"):
    """Stream a response token by token."""
    save_message("user", message, persona)

    try:
        from ai_dev_team.orchestrator import AIDevTeam

        team = AIDevTeam(enable_memory=True)
        await team.setup_agents()

        context = _build_context()
        full_prompt = f"{FRED_SYSTEM_PROMPT}\n\n{context}\n\nUser: {message}\nFred:"

        response = await team.ask(full_prompt)
        reply = response.get("response", "I'm having trouble right now.")
        save_message("assistant", reply, persona)

        # Yield as chunks (orchestrator doesn't support true streaming yet)
        words = reply.split(" ")
        for i, word in enumerate(words):
            yield word + (" " if i < len(words) - 1 else "")

    except Exception as e:
        logger.warning(f"Orchestrator error: {e}")
        reply = _fallback_response(message)
        save_message("assistant", reply, persona)
        yield reply


def _fallback_response(message: str) -> str:
    """Basic response when the AI orchestrator is unavailable."""
    msg = message.lower()
    stats = task_service.get_dashboard_stats()

    if any(w in msg for w in ["task", "todo", "what should", "work on"]):
        today = task_service.get_today_tasks()
        if today:
            lines = ["Here's what's on your plate today:"]
            for t in today[:5]:
                lines.append(f"- {t['title']} (P{t['priority']}, {t['status']})")
            return "\n".join(lines)
        return "Your task list is empty. Want to add something?"

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
    stats = task_service.get_dashboard_stats()
    today_tasks = task_service.get_today_tasks()

    # Try AI-generated briefing
    try:
        from ai_dev_team.orchestrator import AIDevTeam

        team = AIDevTeam(enable_memory=True)
        await team.setup_agents()

        context = _build_context()
        prompt = (
            f"{FRED_SYSTEM_PROMPT}\n\n{context}\n\n"
            "Generate a concise daily briefing for Fred. Include:\n"
            "1. Top priorities for today\n"
            "2. Any overdue items that need attention\n"
            "3. A motivating note\n"
            "Keep it under 200 words. Be direct and actionable."
        )
        response = await team.ask(prompt)
        content = response.get("response", "")
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


def get_today_briefing() -> dict | None:
    today = date.today().isoformat()
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM briefings WHERE date=?", (today,)).fetchone()
        if row:
            d = dict(row)
            d["tasks_snapshot"] = json.loads(d.get("tasks_snapshot") or "{}")
            return d
    return None
