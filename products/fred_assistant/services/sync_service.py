"""
SyncService — bidirectional REST-based sync between local SQLite and cloud.

Push local changes to remote, pull remote changes to local.
Conflict resolution: last-write-wins based on updated_at / created_at.
"""

import json
import logging
import os
from datetime import datetime

import httpx

logger = logging.getLogger(__name__)

_sync_service = None

SYNCABLE_TABLES = [
    # (table, timestamp_col, id_col)
    ("tasks", "updated_at", "id"),
    ("memories", "updated_at", "id"),
    ("chat_messages", "created_at", "id"),
    ("calendar_events", "updated_at", "id"),
    ("goals", "updated_at", "id"),
    ("leads", "updated_at", "id"),
    ("content_items", "updated_at", "id"),
    ("ai_usage", "created_at", "id"),
]


class SyncService:
    """REST-based push/pull sync between local and remote Fred Assistant."""

    def __init__(self):
        self._remote_url = os.getenv("FRED_SYNC_URL", "")
        self._token = os.getenv("FRED_SYNC_TOKEN", "")
        self._last_sync = None
        self._last_error = None
        self._load_config()

    def _load_config(self):
        """Load sync config from memories table."""
        try:
            from products.fred_assistant.database import get_conn
            with get_conn() as conn:
                row = conn.execute(
                    "SELECT value FROM memories WHERE category='system' AND key='sync_config'"
                ).fetchone()
                if row:
                    cfg = json.loads(row["value"])
                    self._remote_url = cfg.get("remote_url", self._remote_url)
                    self._token = cfg.get("token", self._token)
        except Exception:
            pass

    def configure(self, remote_url: str, token: str):
        """Save sync config to DB + env."""
        import uuid
        self._remote_url = remote_url
        self._token = token
        try:
            from products.fred_assistant.database import get_conn
            cfg = json.dumps({"remote_url": remote_url, "token": token})
            with get_conn() as conn:
                conn.execute(
                    """INSERT INTO memories (id, category, key, value, importance)
                       VALUES (?, 'system', 'sync_config', ?, 10)
                       ON CONFLICT(category, key) DO UPDATE SET value=excluded.value, updated_at=datetime('now')""",
                    (str(uuid.uuid4()), cfg),
                )
        except Exception as e:
            logger.warning("Failed to save sync config: %s", e)

    @property
    def configured(self) -> bool:
        return bool(self._remote_url and self._token)

    def status(self) -> dict:
        """Current sync status for the UI."""
        pending = self._count_pending() if self.configured else 0
        return {
            "configured": self.configured,
            "remote_url": self._remote_url or None,
            "last_sync": self._last_sync,
            "last_error": self._last_error,
            "pending": pending,
            "status": "ok" if self.configured and not self._last_error else ("error" if self._last_error else "unconfigured"),
        }

    def _count_pending(self) -> int:
        """Count rows changed since last sync."""
        try:
            from products.fred_assistant.database import get_conn
            with get_conn() as conn:
                total = 0
                for table, ts_col, _ in SYNCABLE_TABLES:
                    row = conn.execute(
                        f"SELECT last_push FROM sync_meta WHERE table_name = ?",
                        (table,),
                    ).fetchone()
                    since = row["last_push"] if row else "2000-01-01"
                    cnt = conn.execute(
                        f"SELECT COUNT(*) as c FROM {table} WHERE {ts_col} > ?",
                        (since,),
                    ).fetchone()
                    total += cnt["c"] if cnt else 0
                return total
        except Exception:
            return 0

    async def push(self) -> dict:
        """Push local changes to remote."""
        if not self.configured:
            return {"status": "error", "message": "Sync not configured"}

        results = {}
        try:
            from products.fred_assistant.database import get_conn
            async with httpx.AsyncClient(timeout=30) as client:
                for table, ts_col, id_col in SYNCABLE_TABLES:
                    with get_conn() as conn:
                        # Get last push time
                        meta = conn.execute(
                            "SELECT last_push FROM sync_meta WHERE table_name = ?",
                            (table,),
                        ).fetchone()
                        since = meta["last_push"] if meta else "2000-01-01"

                        # Get changed rows
                        rows = conn.execute(
                            f"SELECT * FROM {table} WHERE {ts_col} > ? ORDER BY {ts_col} LIMIT 1000",
                            (since,),
                        ).fetchall()

                        if not rows:
                            results[table] = 0
                            continue

                        data = [dict(r) for r in rows]

                    # Push to remote
                    resp = await client.post(
                        f"{self._remote_url}/sync/push",
                        json={"table": table, "rows": data, "id_col": id_col},
                        headers={"Authorization": f"Bearer {self._token}"},
                    )

                    if resp.status_code == 200:
                        now = datetime.utcnow().isoformat()
                        with get_conn() as conn:
                            conn.execute(
                                """INSERT INTO sync_meta (table_name, last_push)
                                   VALUES (?, ?) ON CONFLICT(table_name)
                                   DO UPDATE SET last_push = excluded.last_push""",
                                (table, now),
                            )
                            conn.execute(
                                "INSERT INTO sync_log (direction, table_name, rows_synced, status) VALUES ('push', ?, ?, 'ok')",
                                (table, len(data)),
                            )
                        results[table] = len(data)
                    else:
                        results[table] = f"error: {resp.status_code}"

            self._last_sync = datetime.utcnow().isoformat()
            self._last_error = None
            return {"status": "ok", "pushed": results}

        except Exception as e:
            self._last_error = str(e)
            logger.warning("Sync push failed: %s", e)
            return {"status": "error", "message": str(e)}

    async def pull(self) -> dict:
        """Pull remote changes to local."""
        if not self.configured:
            return {"status": "error", "message": "Sync not configured"}

        results = {}
        try:
            from products.fred_assistant.database import get_conn
            async with httpx.AsyncClient(timeout=30) as client:
                for table, ts_col, id_col in SYNCABLE_TABLES:
                    with get_conn() as conn:
                        meta = conn.execute(
                            "SELECT last_pull FROM sync_meta WHERE table_name = ?",
                            (table,),
                        ).fetchone()
                        since = meta["last_pull"] if meta else "2000-01-01"

                    resp = await client.post(
                        f"{self._remote_url}/sync/pull",
                        json={"table": table, "since": since, "id_col": id_col},
                        headers={"Authorization": f"Bearer {self._token}"},
                    )

                    if resp.status_code != 200:
                        results[table] = f"error: {resp.status_code}"
                        continue

                    remote_rows = resp.json().get("rows", [])
                    if not remote_rows:
                        results[table] = 0
                        continue

                    # Upsert into local DB
                    with get_conn() as conn:
                        for row in remote_rows:
                            cols = list(row.keys())
                            placeholders = ", ".join(["?"] * len(cols))
                            col_names = ", ".join(cols)
                            updates = ", ".join(f"{c}=excluded.{c}" for c in cols if c != id_col)
                            conn.execute(
                                f"""INSERT INTO {table} ({col_names}) VALUES ({placeholders})
                                    ON CONFLICT({id_col}) DO UPDATE SET {updates}""",
                                list(row.values()),
                            )

                        now = datetime.utcnow().isoformat()
                        conn.execute(
                            """INSERT INTO sync_meta (table_name, last_pull)
                               VALUES (?, ?) ON CONFLICT(table_name)
                               DO UPDATE SET last_pull = excluded.last_pull""",
                            (table, now),
                        )
                        conn.execute(
                            "INSERT INTO sync_log (direction, table_name, rows_synced, status) VALUES ('pull', ?, ?, 'ok')",
                            (table, len(remote_rows)),
                        )
                    results[table] = len(remote_rows)

            self._last_sync = datetime.utcnow().isoformat()
            self._last_error = None
            return {"status": "ok", "pulled": results}

        except Exception as e:
            self._last_error = str(e)
            logger.warning("Sync pull failed: %s", e)
            return {"status": "error", "message": str(e)}

    async def full_sync(self) -> dict:
        """Push then pull — full bidirectional sync."""
        push_result = await self.push()
        pull_result = await self.pull()
        return {"push": push_result, "pull": pull_result}


def get_sync_service() -> SyncService:
    """Singleton SyncService."""
    global _sync_service
    if _sync_service is None:
        _sync_service = SyncService()
    return _sync_service
