"""
Content & Social Media Service — content creation, scheduling, platform management.
"""

import json
import uuid
import logging
from datetime import datetime

from products.fred_assistant.database import get_conn, log_activity

logger = logging.getLogger(__name__)


# ── Content Items ────────────────────────────────────────────────

def list_content(status: str = None, platform: str = None, content_type: str = None) -> list[dict]:
    with get_conn() as conn:
        query = "SELECT * FROM content_items WHERE 1=1"
        params = []
        if status:
            query += " AND status=?"
            params.append(status)
        if platform:
            query += " AND platform=?"
            params.append(platform)
        if content_type:
            query += " AND content_type=?"
            params.append(content_type)
        query += " ORDER BY COALESCE(scheduled_date, created_at) DESC"
        rows = conn.execute(query, params).fetchall()
        results = []
        for r in rows:
            d = dict(r)
            d["tags"] = json.loads(d.get("tags") or "[]")
            d["ai_generated"] = bool(d.get("ai_generated"))
            results.append(d)
        return results


def get_content(content_id: str) -> dict | None:
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM content_items WHERE id=?", (content_id,)).fetchone()
        if row:
            d = dict(row)
            d["tags"] = json.loads(d.get("tags") or "[]")
            d["ai_generated"] = bool(d.get("ai_generated"))
            return d
    return None


def create_content(data: dict) -> dict:
    content_id = uuid.uuid4().hex[:8]
    now = datetime.now().isoformat()
    tags = json.dumps(data.get("tags", []))

    with get_conn() as conn:
        conn.execute(
            """INSERT INTO content_items
               (id, title, body, content_type, platform, status, scheduled_date, scheduled_time,
                tags, ai_generated, created_at, updated_at)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
            (
                content_id, data["title"], data.get("body", ""),
                data.get("content_type", "post"), data.get("platform", "linkedin"),
                data.get("status", "draft"), data.get("scheduled_date"),
                data.get("scheduled_time"), tags,
                1 if data.get("ai_generated") else 0, now, now,
            ),
        )
    log_activity("create_content", "content_item", content_id, {"title": data["title"]})
    return get_content(content_id)


def update_content(content_id: str, data: dict) -> dict | None:
    existing = get_content(content_id)
    if not existing:
        return None

    fields, values = [], []
    for key in ["title", "body", "content_type", "platform", "status",
                "scheduled_date", "scheduled_time"]:
        if key in data and data[key] is not None:
            fields.append(f"{key}=?")
            values.append(data[key])
    if "tags" in data and data["tags"] is not None:
        fields.append("tags=?")
        values.append(json.dumps(data["tags"]))

    if fields:
        fields.append("updated_at=?")
        values.append(datetime.now().isoformat())
        values.append(content_id)
        with get_conn() as conn:
            conn.execute(f"UPDATE content_items SET {','.join(fields)} WHERE id=?", values)

    return get_content(content_id)


def delete_content(content_id: str):
    with get_conn() as conn:
        conn.execute("DELETE FROM content_items WHERE id=?", (content_id,))
    log_activity("delete_content", "content_item", content_id)


def publish_content(content_id: str) -> dict | None:
    """Mark content as published."""
    now = datetime.now().isoformat()
    with get_conn() as conn:
        conn.execute(
            "UPDATE content_items SET status='published', published_at=?, updated_at=? WHERE id=?",
            (now, now, content_id),
        )
    return get_content(content_id)


async def generate_content(topic: str, content_type: str = "post",
                           platform: str = "linkedin", tone: str = "professional",
                           length: str = "medium") -> dict:
    """Use AI to generate content."""
    length_guide = {"short": "50-100 words", "medium": "150-250 words", "long": "400-600 words"}
    word_range = length_guide.get(length, "150-250 words")

    prompt = (
        f"Write a {content_type} for {platform} about: {topic}\n\n"
        f"Tone: {tone}\n"
        f"Length: {word_range}\n\n"
        f"Guidelines:\n"
        f"- Write as Fred Taylor, a tech entrepreneur and AI developer\n"
        f"- Be authentic and insightful\n"
        f"- Include a compelling hook\n"
        f"- End with a call to action or thought-provoking question\n"
        f"- Use appropriate formatting for {platform}\n"
    )

    try:
        from elgringo.orchestrator import AIDevTeam
        team = AIDevTeam(enable_memory=True)
        await team.setup_agents()
        response = await team.ask(prompt)
        body = response.get("response", f"[Draft] {topic}")
    except Exception as e:
        logger.warning(f"AI generation fallback: {e}")
        body = f"[Draft about {topic}]\n\nWrite your {content_type} here..."

    return create_content({
        "title": topic,
        "body": body,
        "content_type": content_type,
        "platform": platform,
        "ai_generated": True,
        "tags": [topic.split()[0].lower()] if topic else [],
    })


def get_content_schedule(days: int = 30) -> list[dict]:
    """Get upcoming scheduled content."""
    from datetime import date, timedelta
    today = date.today().isoformat()
    end = (date.today() + timedelta(days=days)).isoformat()
    with get_conn() as conn:
        rows = conn.execute(
            """SELECT * FROM content_items
               WHERE scheduled_date IS NOT NULL AND scheduled_date >= ? AND scheduled_date <= ?
               ORDER BY scheduled_date, scheduled_time""",
            (today, end),
        ).fetchall()
        results = []
        for r in rows:
            d = dict(r)
            d["tags"] = json.loads(d.get("tags") or "[]")
            d["ai_generated"] = bool(d.get("ai_generated"))
            results.append(d)
        return results


# ── Social Accounts ──────────────────────────────────────────────

def list_accounts() -> list[dict]:
    with get_conn() as conn:
        rows = conn.execute("SELECT * FROM social_accounts ORDER BY platform").fetchall()
        results = []
        for r in rows:
            d = dict(r)
            d["connected"] = bool(d.get("connected"))
            d["metadata"] = json.loads(d.get("metadata") or "{}")
            results.append(d)
        return results


def update_account(account_id: str, data: dict) -> dict | None:
    fields, values = [], []
    for key in ["handle", "display_name"]:
        if key in data and data[key] is not None:
            fields.append(f"{key}=?")
            values.append(data[key])
    if "connected" in data and data["connected"] is not None:
        fields.append("connected=?")
        values.append(1 if data["connected"] else 0)

    if fields:
        values.append(account_id)
        with get_conn() as conn:
            conn.execute(f"UPDATE social_accounts SET {','.join(fields)} WHERE id=?", values)

    with get_conn() as conn:
        row = conn.execute("SELECT * FROM social_accounts WHERE id=?", (account_id,)).fetchone()
        if row:
            d = dict(row)
            d["connected"] = bool(d.get("connected"))
            return d
    return None
