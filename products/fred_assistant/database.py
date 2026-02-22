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

        -- Seed default social accounts
        INSERT OR IGNORE INTO social_accounts (id, platform, handle, display_name, connected)
        VALUES
            ('linkedin', 'linkedin', '', 'LinkedIn', 0),
            ('twitter', 'twitter', '', 'X / Twitter', 0),
            ('github', 'github', 'TheGringo-ai', 'GitHub', 1),
            ('youtube', 'youtube', '', 'YouTube', 0);
        """)


def log_activity(action: str, entity_type: str = None, entity_id: str = None, details: dict = None):
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO activity_log (action, entity_type, entity_id, details) VALUES (?, ?, ?, ?)",
            (action, entity_type, entity_id, json.dumps(details or {})),
        )


# Initialize on import
init_db()
