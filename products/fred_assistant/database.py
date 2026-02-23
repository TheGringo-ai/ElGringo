"""
SQLite database for Fred Assistant.
All data stays local on your Mac — fast, private, zero setup.
"""

import sqlite3
import json
import os
from contextlib import contextmanager
from datetime import datetime

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
            ('fredai', 'FredAI Dev', '🤖', 'purple', 2, '["backlog","in_progress","review","done"]'),
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

        -- Seed default social accounts
        INSERT OR IGNORE INTO social_accounts (id, platform, handle, display_name, connected)
        VALUES
            ('linkedin', 'linkedin', '', 'LinkedIn', 0),
            ('twitter', 'twitter', '', 'X / Twitter', 0),
            ('github', 'github', 'TheGringo-ai', 'GitHub', 1),
            ('youtube', 'youtube', '', 'YouTube', 0);
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


def log_activity(action: str, entity_type: str = None, entity_id: str = None, details: dict = None):
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO activity_log (action, entity_type, entity_id, details) VALUES (?, ?, ?, ?)",
            (action, entity_type, entity_id, json.dumps(details or {})),
        )


# Initialize on import
init_db()
