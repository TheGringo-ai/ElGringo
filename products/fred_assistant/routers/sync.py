"""
Sync Router — local-cloud bidirectional data sync.

Endpoints for both the initiating side (trigger sync) and
the receiving side (accept push/pull requests).
"""

import logging
from fastapi import APIRouter, Request
from pydantic import BaseModel
from typing import Optional

from products.fred_assistant.database import get_conn

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/sync", tags=["sync"])


# ── Schemas ────────────────────────────────────────────────────────

class SyncConfigBody(BaseModel):
    remote_url: str
    token: str


class PushBody(BaseModel):
    table: str
    rows: list
    id_col: str = "id"


class PullBody(BaseModel):
    table: str
    since: str = "2000-01-01"
    id_col: str = "id"


# Allowed tables for sync (security — prevent arbitrary table access)
ALLOWED_TABLES = {
    "tasks", "memories", "chat_messages", "calendar_events",
    "goals", "leads", "content_items", "ai_usage",
}


# ── Client-side endpoints (trigger sync) ─────────────────────────

@router.post("/now")
async def sync_now():
    """Trigger immediate full sync (push + pull)."""
    from products.fred_assistant.services.sync_service import get_sync_service
    svc = get_sync_service()
    if not svc.configured:
        return {"status": "error", "message": "Sync not configured. POST /sync/configure first."}
    result = await svc.full_sync()
    return result


@router.get("/status")
async def sync_status():
    """Current sync status."""
    from products.fred_assistant.services.sync_service import get_sync_service
    svc = get_sync_service()
    return svc.status()


@router.post("/configure")
async def configure_sync(body: SyncConfigBody):
    """Configure remote URL and token for sync."""
    from products.fred_assistant.services.sync_service import get_sync_service
    svc = get_sync_service()
    svc.configure(body.remote_url, body.token)
    return {"status": "ok", "remote_url": body.remote_url}


# ── Server-side endpoints (receive data from peer) ───────────────

@router.post("/push")
async def receive_push(body: PushBody, request: Request):
    """Receive pushed rows from a peer instance. Upsert into local DB."""
    if body.table not in ALLOWED_TABLES:
        return {"status": "error", "message": f"Table '{body.table}' not allowed"}

    if not body.rows:
        return {"status": "ok", "upserted": 0}

    try:
        count = 0
        with get_conn() as conn:
            for row in body.rows:
                cols = list(row.keys())
                placeholders = ", ".join(["?"] * len(cols))
                col_names = ", ".join(cols)
                updates = ", ".join(f"{c}=excluded.{c}" for c in cols if c != body.id_col)

                if updates:
                    conn.execute(
                        f"""INSERT INTO {body.table} ({col_names}) VALUES ({placeholders})
                            ON CONFLICT({body.id_col}) DO UPDATE SET {updates}""",
                        list(row.values()),
                    )
                else:
                    conn.execute(
                        f"INSERT OR IGNORE INTO {body.table} ({col_names}) VALUES ({placeholders})",
                        list(row.values()),
                    )
                count += 1

        return {"status": "ok", "upserted": count}
    except Exception as e:
        logger.warning("Push receive failed for %s: %s", body.table, e)
        return {"status": "error", "message": str(e)}


@router.post("/pull")
async def serve_pull(body: PullBody):
    """Serve changed rows to a peer instance requesting a pull."""
    if body.table not in ALLOWED_TABLES:
        return {"status": "error", "message": f"Table '{body.table}' not allowed"}

    # Determine timestamp column
    ts_col = "updated_at"
    if body.table in ("chat_messages", "ai_usage"):
        ts_col = "created_at"

    try:
        with get_conn() as conn:
            rows = conn.execute(
                f"SELECT * FROM {body.table} WHERE {ts_col} > ? ORDER BY {ts_col} LIMIT 1000",
                (body.since,),
            ).fetchall()
            return {"status": "ok", "rows": [dict(r) for r in rows]}
    except Exception as e:
        logger.warning("Pull serve failed for %s: %s", body.table, e)
        return {"status": "error", "message": str(e)}
