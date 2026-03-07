"""Persistent memory service — Fred never forgets."""

import uuid
from datetime import datetime

from products.fred_assistant.database import get_conn, log_activity


def list_memories(category: str = None):
    with get_conn() as conn:
        if category:
            rows = conn.execute(
                "SELECT * FROM memories WHERE category=? ORDER BY importance DESC, updated_at DESC",
                (category,),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM memories ORDER BY importance DESC, updated_at DESC"
            ).fetchall()
        return [dict(r) for r in rows]


def get_memory(memory_id: str):
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM memories WHERE id=?", (memory_id,)).fetchone()
        return dict(row) if row else None


def remember(category: str, key: str, value: str, context: str = "", importance: int = 5):
    """Store or update a memory. Upserts on (category, key)."""
    now = datetime.utcnow().isoformat()
    mem_id = uuid.uuid4().hex[:8]
    with get_conn() as conn:
        existing = conn.execute(
            "SELECT id FROM memories WHERE category=? AND key=?", (category, key)
        ).fetchone()
        if existing:
            conn.execute(
                "UPDATE memories SET value=?, context=?, importance=?, updated_at=? WHERE id=?",
                (value, context, importance, now, existing["id"]),
            )
            mem_id = existing["id"]
        else:
            conn.execute(
                """INSERT INTO memories (id, category, key, value, context, importance, created_at, updated_at)
                   VALUES (?,?,?,?,?,?,?,?)""",
                (mem_id, category, key, value, context, importance, now, now),
            )
    log_activity("memory_stored", "memory", mem_id, {"category": category, "key": key})
    mem = get_memory(mem_id)
    # Index in RAG (fire-and-forget)
    try:
        from products.fred_assistant.services.rag_service import get_rag
        get_rag().index_memory(mem)
    except Exception:
        pass
    return mem


def forget(memory_id: str):
    with get_conn() as conn:
        conn.execute("DELETE FROM memories WHERE id=?", (memory_id,))
    log_activity("memory_deleted", "memory", memory_id)
    # Remove from RAG (fire-and-forget)
    try:
        from products.fred_assistant.services.rag_service import get_rag
        get_rag().delete_memory(memory_id)
    except Exception:
        pass


def search_memories(query: str, limit: int = 10):
    """Simple keyword search across memories."""
    with get_conn() as conn:
        rows = conn.execute(
            """SELECT * FROM memories
               WHERE value LIKE ? OR key LIKE ? OR context LIKE ?
               ORDER BY importance DESC LIMIT ?""",
            (f"%{query}%", f"%{query}%", f"%{query}%", limit),
        ).fetchall()
        return [dict(r) for r in rows]


def get_context_for_chat() -> str:
    """Build a context string of important memories for the AI."""
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT category, key, value FROM memories ORDER BY importance DESC LIMIT 50"
        ).fetchall()
    if not rows:
        return ""
    lines = ["## What I know about you:"]
    current_cat = None
    for r in rows:
        if r["category"] != current_cat:
            current_cat = r["category"]
            lines.append(f"\n### {current_cat.title()}")
        lines.append(f"- **{r['key']}**: {r['value']}")
    return "\n".join(lines)


def get_categories():
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT DISTINCT category FROM memories ORDER BY category"
        ).fetchall()
        return [r["category"] for r in rows]
