"""
SQLite database for Fred Assistant.
All data stays local on your Mac — fast, private, zero setup.
"""

import sqlite3
import json
import os
from contextlib import contextmanager

DB_PATH = os.path.expanduser("~/.fred-assistant/fred.db")


def get_db_path():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    return DB_PATH


@contextmanager
def get_conn():
    conn = sqlite3.connect(get_db_path())
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db():
    """Create all tables if they don't exist."""
    with get_conn() as conn:
        conn.executescript("""
        -- Boards (kanban boards for different life areas)
        CREATE TABLE IF NOT EXISTS boards (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            icon TEXT DEFAULT '📋',
            color TEXT DEFAULT 'blue',
            position INTEGER DEFAULT 0,
            columns TEXT DEFAULT '["todo","in_progress","done"]',
            created_at TEXT DEFAULT (datetime('now')),
            archived INTEGER DEFAULT 0
        );

        -- Tasks (universal todos — work, personal, chores, anything)
        CREATE TABLE IF NOT EXISTS tasks (
            id TEXT PRIMARY KEY,
            board_id TEXT NOT NULL,
            title TEXT NOT NULL,
            description TEXT DEFAULT '',
            status TEXT DEFAULT 'todo',
            priority INTEGER DEFAULT 3,
            category TEXT DEFAULT 'general',
            due_date TEXT,
            due_time TEXT,
            recurring TEXT,
            tags TEXT DEFAULT '[]',
            notes TEXT DEFAULT '',
            position INTEGER DEFAULT 0,
            created_at TEXT DEFAULT (datetime('now')),
            updated_at TEXT DEFAULT (datetime('now')),
            completed_at TEXT,
            FOREIGN KEY (board_id) REFERENCES boards(id)
        );

        -- Memory (persistent facts Fred remembers about you)
        CREATE TABLE IF NOT EXISTS memories (
            id TEXT PRIMARY KEY,
            category TEXT NOT NULL,
            key TEXT NOT NULL,
            value TEXT NOT NULL,
            context TEXT DEFAULT '',
            importance INTEGER DEFAULT 5,
            created_at TEXT DEFAULT (datetime('now')),
            updated_at TEXT DEFAULT (datetime('now')),
            expires_at TEXT,
            UNIQUE(category, key)
        );

        -- Chat history (conversations with Fred)
        CREATE TABLE IF NOT EXISTS chat_messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            role TEXT NOT NULL,
            content TEXT NOT NULL,
            persona TEXT DEFAULT 'fred',
            metadata TEXT DEFAULT '{}',
            created_at TEXT DEFAULT (datetime('now'))
        );

        -- Daily briefings
        CREATE TABLE IF NOT EXISTS briefings (
            id TEXT PRIMARY KEY,
            date TEXT NOT NULL UNIQUE,
            content TEXT NOT NULL,
            tasks_snapshot TEXT DEFAULT '{}',
            created_at TEXT DEFAULT (datetime('now'))
        );

        -- Activity log (what you did, for patterns)
        CREATE TABLE IF NOT EXISTS activity_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            action TEXT NOT NULL,
            entity_type TEXT,
            entity_id TEXT,
            details TEXT DEFAULT '{}',
            created_at TEXT DEFAULT (datetime('now'))
        );

        -- Calendar events (time blocking, deadlines, appointments)
        CREATE TABLE IF NOT EXISTS calendar_events (
            id TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            description TEXT DEFAULT '',
            event_type TEXT DEFAULT 'event',
            start_date TEXT NOT NULL,
            start_time TEXT,
            end_date TEXT,
            end_time TEXT,
            all_day INTEGER DEFAULT 0,
            recurring TEXT,
            color TEXT DEFAULT 'blue',
            location TEXT DEFAULT '',
            linked_task_id TEXT,
            created_at TEXT DEFAULT (datetime('now')),
            updated_at TEXT DEFAULT (datetime('now'))
        );

        -- Content items (posts, articles, newsletters)
        CREATE TABLE IF NOT EXISTS content_items (
            id TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            body TEXT DEFAULT '',
            content_type TEXT DEFAULT 'post',
            platform TEXT DEFAULT 'linkedin',
            status TEXT DEFAULT 'draft',
            scheduled_date TEXT,
            scheduled_time TEXT,
            published_at TEXT,
            tags TEXT DEFAULT '[]',
            ai_generated INTEGER DEFAULT 0,
            created_at TEXT DEFAULT (datetime('now')),
            updated_at TEXT DEFAULT (datetime('now'))
        );

        -- Social media accounts (connected platforms)
        CREATE TABLE IF NOT EXISTS social_accounts (
            id TEXT PRIMARY KEY,
            platform TEXT NOT NULL,
            handle TEXT NOT NULL,
            display_name TEXT DEFAULT '',
            connected INTEGER DEFAULT 1,
            metadata TEXT DEFAULT '{}',
            created_at TEXT DEFAULT (datetime('now'))
        );

        -- Goals (business coach tracking)
        CREATE TABLE IF NOT EXISTS goals (
            id TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            description TEXT DEFAULT '',
            category TEXT DEFAULT 'business',
            target_date TEXT,
            status TEXT DEFAULT 'active',
            progress INTEGER DEFAULT 0,
            milestones TEXT DEFAULT '[]',
            notes TEXT DEFAULT '',
            created_at TEXT DEFAULT (datetime('now')),
            updated_at TEXT DEFAULT (datetime('now'))
        );

        -- Weekly reviews (business coach)
        CREATE TABLE IF NOT EXISTS weekly_reviews (
            id TEXT PRIMARY KEY,
            week_start TEXT NOT NULL,
            wins TEXT DEFAULT '[]',
            challenges TEXT DEFAULT '[]',
            lessons TEXT DEFAULT '[]',
            next_week_priorities TEXT DEFAULT '[]',
            ai_insights TEXT DEFAULT '',
            created_at TEXT DEFAULT (datetime('now'))
        );

        -- Seed default boards if empty
        INSERT OR IGNORE INTO boards (id, name, icon, color, position, columns)
        VALUES
            ('work', 'Work', '💻', 'blue', 0, '["backlog","in_progress","review","done"]'),
            ('personal', 'Personal', '🏠', 'emerald', 1, '["todo","in_progress","done"]'),
            ('elgringo', 'El Gringo Dev', '🤖', 'purple', 2, '["backlog","in_progress","review","done"]'),
            ('health', 'Health & Fitness', '💪', 'red', 3, '["todo","in_progress","done"]'),
            ('ideas', 'Ideas & Research', '💡', 'amber', 4, '["capture","exploring","validated","parked"]');

        -- Focus sessions (focus mode / pomodoro timer)
        CREATE TABLE IF NOT EXISTS focus_sessions (
            id TEXT PRIMARY KEY,
            task_id TEXT,
            task_title TEXT DEFAULT '',
            started_at TEXT NOT NULL,
            ended_at TEXT,
            planned_minutes INTEGER DEFAULT 25,
            notes TEXT DEFAULT '',
            completed INTEGER DEFAULT 0,
            created_at TEXT DEFAULT (datetime('now')),
            FOREIGN KEY (task_id) REFERENCES tasks(id)
        );

        -- Leads (revenue CRM)
        CREATE TABLE IF NOT EXISTS leads (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            company TEXT DEFAULT '',
            email TEXT DEFAULT '',
            phone TEXT DEFAULT '',
            source TEXT DEFAULT '',
            pipeline_stage TEXT DEFAULT 'cold',
            deal_value REAL DEFAULT 0,
            notes TEXT DEFAULT '',
            next_followup TEXT,
            tags TEXT DEFAULT '[]',
            created_at TEXT DEFAULT (datetime('now')),
            updated_at TEXT DEFAULT (datetime('now'))
        );

        -- Outreach log (CRM activity)
        CREATE TABLE IF NOT EXISTS outreach_log (
            id TEXT PRIMARY KEY,
            lead_id TEXT NOT NULL,
            outreach_type TEXT DEFAULT 'email',
            content TEXT DEFAULT '',
            result TEXT DEFAULT '',
            created_at TEXT DEFAULT (datetime('now')),
            FOREIGN KEY (lead_id) REFERENCES leads(id)
        );

        -- Metrics snapshots (CEO lens)
        CREATE TABLE IF NOT EXISTS metrics_snapshots (
            id TEXT PRIMARY KEY,
            date TEXT NOT NULL,
            mrr REAL DEFAULT 0,
            leads_contacted INTEGER DEFAULT 0,
            calls_booked INTEGER DEFAULT 0,
            trials_started INTEGER DEFAULT 0,
            deals_closed INTEGER DEFAULT 0,
            sprint_completion_pct REAL DEFAULT 0,
            content_published INTEGER DEFAULT 0,
            revenue REAL DEFAULT 0,
            custom_metrics TEXT DEFAULT '{}',
            created_at TEXT DEFAULT (datetime('now')),
            UNIQUE(date)
        );

        -- Playbooks (agent playbooks / autopilot)
        CREATE TABLE IF NOT EXISTS playbooks (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL UNIQUE,
            description TEXT DEFAULT '',
            category TEXT DEFAULT 'general',
            steps TEXT DEFAULT '[]',
            created_at TEXT DEFAULT (datetime('now')),
            updated_at TEXT DEFAULT (datetime('now'))
        );

        -- Playbook runs (execution log)
        CREATE TABLE IF NOT EXISTS playbook_runs (
            id TEXT PRIMARY KEY,
            playbook_id TEXT NOT NULL,
            status TEXT DEFAULT 'running',
            step_results TEXT DEFAULT '[]',
            started_at TEXT DEFAULT (datetime('now')),
            completed_at TEXT,
            FOREIGN KEY (playbook_id) REFERENCES playbooks(id)
        );

        -- Repo analyses (repo intelligence engine)
        CREATE TABLE IF NOT EXISTS repo_analyses (
            id TEXT PRIMARY KEY,
            project_name TEXT NOT NULL,
            project_path TEXT NOT NULL,
            depth TEXT DEFAULT 'quick',
            health_score INTEGER DEFAULT 0,
            tech_stack TEXT DEFAULT '[]',
            findings TEXT DEFAULT '{}',
            tasks_generated TEXT DEFAULT '[]',
            summary TEXT DEFAULT '',
            created_at TEXT DEFAULT (datetime('now'))
        );
        CREATE INDEX IF NOT EXISTS idx_repo_analyses_project ON repo_analyses(project_name);

        -- Platform service results (cross-service integration)
        CREATE TABLE IF NOT EXISTS service_results (
            id TEXT PRIMARY KEY,
            service TEXT NOT NULL,
            action TEXT NOT NULL,
            project_name TEXT,
            input_summary TEXT,
            result TEXT DEFAULT '',
            agents_used TEXT DEFAULT '[]',
            total_time REAL DEFAULT 0,
            created_at TEXT DEFAULT (datetime('now'))
        );
        CREATE INDEX IF NOT EXISTS idx_service_results_project ON service_results(project_name);
        CREATE INDEX IF NOT EXISTS idx_service_results_service ON service_results(service);

        -- AI usage tracking (every LLM call)
        CREATE TABLE IF NOT EXISTS ai_usage (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            model TEXT NOT NULL,
            provider TEXT NOT NULL,
            input_tokens INTEGER DEFAULT 0,
            output_tokens INTEGER DEFAULT 0,
            cost_usd REAL DEFAULT 0,
            latency_ms REAL DEFAULT 0,
            feature TEXT DEFAULT 'chat',
            error TEXT,
            created_at TEXT DEFAULT (datetime('now'))
        );
        CREATE INDEX IF NOT EXISTS idx_ai_usage_created ON ai_usage(created_at);
        CREATE INDEX IF NOT EXISTS idx_ai_usage_model ON ai_usage(model);

        -- Sync metadata (local-cloud sync)
        CREATE TABLE IF NOT EXISTS sync_meta (
            table_name TEXT PRIMARY KEY,
            last_push TEXT,
            last_pull TEXT,
            pending_changes INTEGER DEFAULT 0
        );

        CREATE TABLE IF NOT EXISTS sync_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            direction TEXT NOT NULL,
            table_name TEXT NOT NULL,
            rows_synced INTEGER DEFAULT 0,
            status TEXT DEFAULT 'ok',
            error TEXT,
            created_at TEXT DEFAULT (datetime('now'))
        );

        -- Seed default social accounts
        INSERT OR IGNORE INTO social_accounts (id, platform, handle, display_name, connected)
        VALUES
            ('linkedin', 'linkedin', '', 'LinkedIn', 0),
            ('twitter', 'twitter', '', 'X / Twitter', 0),
            ('github', 'github', 'TheGringo-ai', 'GitHub', 1),
            ('youtube', 'youtube', '', 'YouTube', 0);

        -- App Factory: app registry
        CREATE TABLE IF NOT EXISTS apps (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL UNIQUE,
            display_name TEXT NOT NULL,
            description TEXT DEFAULT '',
            app_type TEXT DEFAULT 'fullstack',
            tech_stack TEXT DEFAULT '{}',
            spec TEXT DEFAULT '{}',
            status TEXT DEFAULT 'draft',
            repo_url TEXT DEFAULT '',
            deploy_url TEXT DEFAULT '',
            port INTEGER DEFAULT 0,
            project_dir TEXT DEFAULT '',
            error_message TEXT DEFAULT '',
            created_at TEXT DEFAULT (datetime('now')),
            updated_at TEXT DEFAULT (datetime('now'))
        );

        -- App Factory: build pipeline steps
        CREATE TABLE IF NOT EXISTS app_builds (
            id TEXT PRIMARY KEY,
            app_id TEXT NOT NULL,
            version INTEGER DEFAULT 1,
            step TEXT NOT NULL,
            status TEXT DEFAULT 'pending',
            log TEXT DEFAULT '',
            started_at TEXT,
            completed_at TEXT,
            FOREIGN KEY (app_id) REFERENCES apps(id)
        );
        CREATE INDEX IF NOT EXISTS idx_app_builds_app ON app_builds(app_id);

        -- App Factory: customer tracking per app
        CREATE TABLE IF NOT EXISTS app_customers (
            id TEXT PRIMARY KEY,
            app_id TEXT NOT NULL,
            name TEXT NOT NULL,
            email TEXT DEFAULT '',
            plan TEXT DEFAULT 'free',
            stripe_customer_id TEXT DEFAULT '',
            stripe_subscription_id TEXT DEFAULT '',
            mrr REAL DEFAULT 0,
            status TEXT DEFAULT 'trial',
            created_at TEXT DEFAULT (datetime('now')),
            updated_at TEXT DEFAULT (datetime('now')),
            FOREIGN KEY (app_id) REFERENCES apps(id)
        );
        CREATE INDEX IF NOT EXISTS idx_app_customers_app ON app_customers(app_id);

        -- Project Notes: AI-generated and manual notes per project
        CREATE TABLE IF NOT EXISTS project_notes (
            id TEXT PRIMARY KEY,
            project_name TEXT NOT NULL,
            title TEXT NOT NULL,
            content TEXT NOT NULL DEFAULT '',
            note_type TEXT DEFAULT 'ai_generated',
            tags TEXT DEFAULT '[]',
            pinned INTEGER DEFAULT 0,
            metadata TEXT DEFAULT '{}',
            created_at TEXT DEFAULT (datetime('now')),
            updated_at TEXT DEFAULT (datetime('now'))
        );
        CREATE INDEX IF NOT EXISTS idx_project_notes_project ON project_notes(project_name);
        """)

        # Idempotent ALTER TABLE migrations
        _migrate_columns(conn)


def _migrate_columns(conn):
    """Add columns to existing tables (idempotent — ignores if already exists)."""
    migrations = [
        ("briefings", "briefing_type", "TEXT DEFAULT 'morning'"),
        ("content_items", "approval_status", "TEXT DEFAULT 'pending'"),
        ("content_items", "published_url", "TEXT DEFAULT ''"),
    ]
    for table, column, col_def in migrations:
        try:
            conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {col_def}")
        except Exception:
            pass  # Column already exists


# ── AI Usage tracking ─────────────────────────────────────────────


def _get_model_costs():
    """Import MODEL_COSTS lazily to avoid circular imports."""
    try:
        from ai_dev_team.routing.cost_optimizer import MODEL_COSTS
        return MODEL_COSTS
    except ImportError:
        return {}


def _provider_from_model(model: str) -> str:
    """Infer provider name from model string."""
    m = model.lower()
    if "gemini" in m:
        return "gemini"
    if "gpt" in m:
        return "openai"
    if "claude" in m:
        return "anthropic"
    if "grok" in m:
        return "grok"
    if "llama" in m and ("groq" in m or "together" in m or "versatile" in m or "instant" in m):
        return "llama_cloud"
    if "mlx" in m:
        return "mlx"
    # Ollama models are typically short names like "llama3.2:3b"
    if ":" in m or "ollama" in m:
        return "ollama"
    return "unknown"


def record_ai_usage(
    model: str,
    provider: str = None,
    input_tokens: int = 0,
    output_tokens: int = 0,
    latency_ms: float = 0,
    feature: str = "chat",
    error: str = None,
):
    """Record a single LLM call. Computes cost from MODEL_COSTS."""
    if not provider:
        provider = _provider_from_model(model)

    costs = _get_model_costs()
    rate = costs.get(model, (0.0, 0.0))
    cost_usd = (input_tokens / 1_000_000) * rate[0] + (output_tokens / 1_000_000) * rate[1]

    with get_conn() as conn:
        conn.execute(
            """INSERT INTO ai_usage
               (model, provider, input_tokens, output_tokens, cost_usd, latency_ms, feature, error)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (model, provider, input_tokens, output_tokens, cost_usd, latency_ms, feature, error),
        )


def get_usage_today() -> dict:
    """Today's aggregated usage."""
    with get_conn() as conn:
        row = conn.execute(
            """SELECT COUNT(*) as requests, COALESCE(SUM(input_tokens),0) as input_tokens,
                      COALESCE(SUM(output_tokens),0) as output_tokens,
                      COALESCE(SUM(cost_usd),0) as cost,
                      COALESCE(AVG(latency_ms),0) as avg_latency,
                      COALESCE(SUM(CASE WHEN error IS NOT NULL THEN 1 ELSE 0 END),0) as errors
               FROM ai_usage WHERE date(created_at) = date('now')"""
        ).fetchone()
        return dict(row) if row else {}


def get_usage_summary(days: int = 30) -> list:
    """Daily aggregates for charting."""
    with get_conn() as conn:
        rows = conn.execute(
            """SELECT date(created_at) as date, COUNT(*) as requests,
                      SUM(input_tokens) as input_tokens, SUM(output_tokens) as output_tokens,
                      SUM(cost_usd) as cost, AVG(latency_ms) as avg_latency
               FROM ai_usage
               WHERE created_at >= datetime('now', ?)
               GROUP BY date(created_at) ORDER BY date(created_at)""",
            (f"-{days} days",),
        ).fetchall()
        return [dict(r) for r in rows]


def get_usage_by_model(days: int = 30) -> list:
    """Breakdown by model/provider."""
    with get_conn() as conn:
        rows = conn.execute(
            """SELECT model, provider, COUNT(*) as requests,
                      SUM(input_tokens) as input_tokens, SUM(output_tokens) as output_tokens,
                      SUM(cost_usd) as cost, AVG(latency_ms) as avg_latency
               FROM ai_usage
               WHERE created_at >= datetime('now', ?)
               GROUP BY model, provider ORDER BY cost DESC""",
            (f"-{days} days",),
        ).fetchall()
        return [dict(r) for r in rows]


def get_recent_usage(limit: int = 50) -> list:
    """Recent individual LLM requests."""
    with get_conn() as conn:
        rows = conn.execute(
            """SELECT id, model, provider, input_tokens, output_tokens,
                      cost_usd, latency_ms, feature, error, created_at
               FROM ai_usage ORDER BY id DESC LIMIT ?""",
            (limit,),
        ).fetchall()
        return [dict(r) for r in rows]


def get_usage_budget() -> dict:
    """Read budget limits from memories table."""
    with get_conn() as conn:
        row = conn.execute(
            "SELECT value FROM memories WHERE category='system' AND key='usage_budget'"
        ).fetchone()
        if row:
            return json.loads(row["value"])
    return {"daily_limit": 5.0, "monthly_limit": 50.0}


def set_usage_budget(daily_limit: float, monthly_limit: float):
    """Save budget limits to memories table."""
    import uuid
    budget = json.dumps({"daily_limit": daily_limit, "monthly_limit": monthly_limit})
    with get_conn() as conn:
        conn.execute(
            """INSERT INTO memories (id, category, key, value, importance)
               VALUES (?, 'system', 'usage_budget', ?, 10)
               ON CONFLICT(category, key) DO UPDATE SET value=excluded.value, updated_at=datetime('now')""",
            (str(uuid.uuid4()), budget),
        )


def get_monthly_cost() -> float:
    """Total cost for current calendar month."""
    with get_conn() as conn:
        row = conn.execute(
            "SELECT COALESCE(SUM(cost_usd),0) as cost FROM ai_usage WHERE strftime('%Y-%m', created_at) = strftime('%Y-%m', 'now')"
        ).fetchone()
        return row["cost"] if row else 0.0


def log_activity(action: str, entity_type: str = None, entity_id: str = None, details: dict = None):
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO activity_log (action, entity_type, entity_id, details) VALUES (?, ?, ?, ?)",
            (action, entity_type, entity_id, json.dumps(details or {})),
        )


# Initialize on import
init_db()
