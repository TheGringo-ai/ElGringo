"""
Business Coach Service — goals, weekly reviews, accountability.
"""

import json
import uuid
import logging
from datetime import date, datetime, timedelta

from products.fred_assistant.database import get_conn, log_activity
from products.fred_assistant.services import task_service

logger = logging.getLogger(__name__)


# ── Goals ────────────────────────────────────────────────────────

def list_goals(status: str = None, category: str = None) -> list[dict]:
    with get_conn() as conn:
        query = "SELECT * FROM goals WHERE 1=1"
        params = []
        if status:
            query += " AND status=?"
            params.append(status)
        if category:
            query += " AND category=?"
            params.append(category)
        query += " ORDER BY CASE status WHEN 'active' THEN 0 WHEN 'paused' THEN 1 ELSE 2 END, created_at DESC"
        rows = conn.execute(query, params).fetchall()
        results = []
        for r in rows:
            d = dict(r)
            d["milestones"] = json.loads(d.get("milestones") or "[]")
            results.append(d)
        return results


def get_goal(goal_id: str) -> dict | None:
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM goals WHERE id=?", (goal_id,)).fetchone()
        if row:
            d = dict(row)
            d["milestones"] = json.loads(d.get("milestones") or "[]")
            return d
    return None


def create_goal(data: dict) -> dict:
    goal_id = uuid.uuid4().hex[:8]
    now = datetime.now().isoformat()
    milestones = json.dumps(data.get("milestones", []))

    with get_conn() as conn:
        conn.execute(
            """INSERT INTO goals
               (id, title, description, category, target_date, status, progress, milestones, notes, created_at, updated_at)
               VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
            (
                goal_id, data["title"], data.get("description", ""),
                data.get("category", "business"), data.get("target_date"),
                "active", 0, milestones, "", now, now,
            ),
        )
    log_activity("create_goal", "goal", goal_id, {"title": data["title"]})
    return get_goal(goal_id)


def update_goal(goal_id: str, data: dict) -> dict | None:
    existing = get_goal(goal_id)
    if not existing:
        return None

    fields, values = [], []
    for key in ["title", "description", "category", "target_date", "status", "progress", "notes"]:
        if key in data and data[key] is not None:
            fields.append(f"{key}=?")
            values.append(data[key])
    if "milestones" in data and data["milestones"] is not None:
        fields.append("milestones=?")
        values.append(json.dumps(data["milestones"]))

    if fields:
        fields.append("updated_at=?")
        values.append(datetime.now().isoformat())
        values.append(goal_id)
        with get_conn() as conn:
            conn.execute(f"UPDATE goals SET {','.join(fields)} WHERE id=?", values)

    return get_goal(goal_id)


def delete_goal(goal_id: str):
    with get_conn() as conn:
        conn.execute("DELETE FROM goals WHERE id=?", (goal_id,))
    log_activity("delete_goal", "goal", goal_id)


# ── Weekly Reviews ───────────────────────────────────────────────

def list_reviews(limit: int = 10) -> list[dict]:
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM weekly_reviews ORDER BY week_start DESC LIMIT ?", (limit,)
        ).fetchall()
        results = []
        for r in rows:
            d = dict(r)
            for key in ["wins", "challenges", "lessons", "next_week_priorities"]:
                d[key] = json.loads(d.get(key) or "[]")
            results.append(d)
        return results


def get_current_review() -> dict | None:
    """Get review for the current week."""
    today = date.today()
    week_start = (today - timedelta(days=today.weekday())).isoformat()
    with get_conn() as conn:
        row = conn.execute(
            "SELECT * FROM weekly_reviews WHERE week_start=?", (week_start,)
        ).fetchone()
        if row:
            d = dict(row)
            for key in ["wins", "challenges", "lessons", "next_week_priorities"]:
                d[key] = json.loads(d.get(key) or "[]")
            return d
    return None


def save_review(data: dict) -> dict:
    """Create or update the current week's review."""
    today = date.today()
    week_start = data.get("week_start") or (today - timedelta(days=today.weekday())).isoformat()
    review_id = uuid.uuid4().hex[:8]
    now = datetime.now().isoformat()

    with get_conn() as conn:
        conn.execute(
            """INSERT OR REPLACE INTO weekly_reviews
               (id, week_start, wins, challenges, lessons, next_week_priorities, ai_insights, created_at)
               VALUES (?,?,?,?,?,?,?,?)""",
            (
                review_id, week_start,
                json.dumps(data.get("wins", [])),
                json.dumps(data.get("challenges", [])),
                json.dumps(data.get("lessons", [])),
                json.dumps(data.get("next_week_priorities", [])),
                data.get("ai_insights", ""), now,
            ),
        )

    log_activity("save_review", "weekly_review", review_id)
    return get_current_review() or {"id": review_id, "week_start": week_start}


async def generate_weekly_review() -> dict:
    """Use AI to generate a weekly review based on activity."""
    stats = task_service.get_dashboard_stats()
    task_service.get_today_tasks()
    goals = list_goals(status="active")

    context = (
        f"This week's stats: {stats['completed_today']} completed today, "
        f"{stats['total_tasks']} total active, {stats['overdue']} overdue.\n"
        f"Active goals: {', '.join(g['title'] for g in goals[:5])}\n"
    )

    prompt = (
        "You are a business coach reviewing Fred Taylor's week.\n\n"
        f"{context}\n"
        "Generate a concise weekly review with:\n"
        "1. wins (3-5 bullet points of accomplishments)\n"
        "2. challenges (2-3 things that were difficult)\n"
        "3. lessons (2-3 key takeaways)\n"
        "4. next_week_priorities (3-5 things to focus on)\n"
        "5. ai_insights (a paragraph of strategic advice)\n\n"
        "Return as JSON with these exact keys. Each list should contain strings."
    )

    try:
        from elgringo.orchestrator import AIDevTeam
        team = AIDevTeam(enable_memory=True)
        await team.setup_agents()
        response = await team.ask(prompt)
        text = response.get("response", "{}")
        # Try to parse JSON from the response
        import re
        json_match = re.search(r'\{.*\}', text, re.DOTALL)
        if json_match:
            review_data = json.loads(json_match.group())
        else:
            review_data = {}
    except Exception as e:
        logger.warning(f"AI review fallback: {e}")
        review_data = {
            "wins": ["Kept building!", "Made progress on tasks"],
            "challenges": ["Need to review priorities"],
            "lessons": ["Consistency is key"],
            "next_week_priorities": ["Review goals", "Clear overdue items"],
            "ai_insights": "Focus on your highest-impact tasks. Don't let the overdue list grow.",
        }

    return save_review(review_data)


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
"""
