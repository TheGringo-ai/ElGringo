"""Agent Playbooks — Reusable multi-step action sequences with autopilot support."""

import json
import uuid
from datetime import datetime

from products.fred_assistant.database import get_conn, log_activity


def list_playbooks(category: str = None) -> list[dict]:
    with get_conn() as conn:
        if category:
            rows = conn.execute(
                "SELECT * FROM playbooks WHERE category=? ORDER BY name", (category,)
            ).fetchall()
        else:
            rows = conn.execute("SELECT * FROM playbooks ORDER BY name").fetchall()
    results = []
    for r in rows:
        d = dict(r)
        try:
            d["steps"] = json.loads(d.get("steps") or "[]")
        except (json.JSONDecodeError, TypeError):
            d["steps"] = []
        results.append(d)
    return results


def get_playbook(playbook_id: str) -> dict | None:
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM playbooks WHERE id=?", (playbook_id,)).fetchone()
        if not row:
            return None
        d = dict(row)
        try:
            d["steps"] = json.loads(d.get("steps") or "[]")
        except (json.JSONDecodeError, TypeError):
            d["steps"] = []
        return d


def get_playbook_by_name(name: str) -> dict | None:
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM playbooks WHERE name=? COLLATE NOCASE", (name,)).fetchone()
        if not row:
            return None
        d = dict(row)
        try:
            d["steps"] = json.loads(d.get("steps") or "[]")
        except (json.JSONDecodeError, TypeError):
            d["steps"] = []
        return d


def create_playbook(data: dict) -> dict:
    playbook_id = uuid.uuid4().hex[:8]
    now = datetime.now().isoformat()
    steps = json.dumps(data.get("steps", []))
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO playbooks (id, name, description, category, steps, created_at, updated_at) VALUES (?,?,?,?,?,?,?)",
            (
                playbook_id,
                data.get("name", "Untitled"),
                data.get("description", ""),
                data.get("category", "general"),
                steps,
                now,
                now,
            ),
        )
    log_activity("playbook_created", "playbook", playbook_id, {"name": data.get("name")})
    return get_playbook(playbook_id)


def update_playbook(playbook_id: str, data: dict) -> dict | None:
    pb = get_playbook(playbook_id)
    if not pb:
        return None
    fields = []
    params = []
    for key in ["name", "description", "category"]:
        if key in data:
            fields.append(f"{key}=?")
            params.append(data[key])
    if "steps" in data:
        fields.append("steps=?")
        params.append(json.dumps(data["steps"]))
    if not fields:
        return pb
    fields.append("updated_at=?")
    params.append(datetime.now().isoformat())
    params.append(playbook_id)
    with get_conn() as conn:
        conn.execute(f"UPDATE playbooks SET {', '.join(fields)} WHERE id=?", params)
    return get_playbook(playbook_id)


def delete_playbook(playbook_id: str):
    with get_conn() as conn:
        conn.execute("DELETE FROM playbook_runs WHERE playbook_id=?", (playbook_id,))
        conn.execute("DELETE FROM playbooks WHERE id=?", (playbook_id,))
    log_activity("playbook_deleted", "playbook", playbook_id)


async def run_playbook(playbook_id: str) -> dict:
    """Execute a playbook's steps via fred_tools. Returns run results."""
    from products.fred_assistant.services.fred_tools import execute_action

    pb = get_playbook(playbook_id)
    if not pb:
        return {"error": "Playbook not found"}

    run_id = uuid.uuid4().hex[:8]
    now = datetime.now().isoformat()

    with get_conn() as conn:
        conn.execute(
            "INSERT INTO playbook_runs (id, playbook_id, status, started_at) VALUES (?,?,?,?)",
            (run_id, playbook_id, "running", now),
        )

    step_results = []
    for i, step in enumerate(pb.get("steps", [])):
        action_name = step.get("action", "")
        action_params = step.get("params", {})
        label = step.get("label", f"Step {i+1}: {action_name}")

        if step.get("requires_approval"):
            step_results.append({
                "step": i + 1,
                "label": label,
                "action": action_name,
                "status": "proposed",
                "message": f"Requires approval: {label}",
                "params": action_params,
            })
            continue

        try:
            result = await execute_action({"name": action_name, "params": action_params})
            step_results.append({
                "step": i + 1,
                "label": label,
                "action": action_name,
                "status": "ok" if result.get("success") else "failed",
                "message": result.get("message", result.get("error", "")),
            })
        except Exception as e:
            step_results.append({
                "step": i + 1,
                "label": label,
                "action": action_name,
                "status": "error",
                "message": str(e),
            })

    completed_at = datetime.now().isoformat()
    status = "completed" if all(r["status"] in ("ok", "proposed") for r in step_results) else "partial"

    with get_conn() as conn:
        conn.execute(
            "UPDATE playbook_runs SET status=?, step_results=?, completed_at=? WHERE id=?",
            (status, json.dumps(step_results), completed_at, run_id),
        )

    log_activity("playbook_run", "playbook", playbook_id, {"run_id": run_id, "status": status})
    return {
        "run_id": run_id,
        "playbook_id": playbook_id,
        "playbook_name": pb["name"],
        "status": status,
        "steps": step_results,
        "started_at": now,
        "completed_at": completed_at,
    }


def seed_default_playbooks():
    """Create built-in playbooks on first run (idempotent)."""
    defaults = [
        {
            "name": "Weekly Marketing Batch",
            "description": "Generate 3 LinkedIn posts and create review tasks",
            "category": "autopilot",
            "steps": [
                {"action": "generate_content", "params": {"topic": "AI in business", "platform": "linkedin", "tone": "professional"}, "label": "Generate LinkedIn post 1", "requires_approval": True},
                {"action": "generate_content", "params": {"topic": "productivity tips", "platform": "linkedin", "tone": "casual"}, "label": "Generate LinkedIn post 2", "requires_approval": True},
                {"action": "generate_content", "params": {"topic": "tech industry trends", "platform": "linkedin", "tone": "professional"}, "label": "Generate LinkedIn post 3", "requires_approval": True},
                {"action": "create_task", "params": {"title": "Review and schedule weekly content", "board": "work", "priority": 2}, "label": "Create review task"},
            ],
        },
        {
            "name": "Book 5 Demos",
            "description": "Create outreach tasks for top cold leads",
            "category": "autopilot",
            "steps": [
                {"action": "list_leads", "params": {"stage": "cold"}, "label": "List cold leads"},
                {"action": "create_task", "params": {"title": "Outreach: Demo outreach batch", "board": "work", "priority": 1}, "label": "Create outreach task"},
            ],
        },
        {
            "name": "Ship Stripe This Week",
            "description": "Sprint tasks for Stripe integration",
            "category": "project",
            "steps": [
                {"action": "create_task", "params": {"title": "Build pricing page", "board": "work", "priority": 1}, "label": "Pricing page"},
                {"action": "create_task", "params": {"title": "Integrate Stripe checkout API", "board": "work", "priority": 1}, "label": "Stripe API"},
                {"action": "create_task", "params": {"title": "Add webhook handlers for payment events", "board": "work", "priority": 2}, "label": "Webhooks"},
                {"action": "create_task", "params": {"title": "Test payment flow end-to-end", "board": "work", "priority": 2}, "label": "E2E test"},
                {"action": "create_task", "params": {"title": "Deploy Stripe integration", "board": "work", "priority": 2}, "label": "Deploy"},
            ],
        },
        {
            "name": "Weekly Review",
            "description": "Generate weekly review, snapshot metrics, plan next week",
            "category": "autopilot",
            "steps": [
                {"action": "generate_review", "params": {}, "label": "Generate weekly review"},
                {"action": "ceo_lens", "params": {}, "label": "Snapshot CEO metrics"},
                {"action": "accountability_check", "params": {}, "label": "Run accountability check"},
            ],
        },
        {
            "name": "Morning Standup",
            "description": "Generate briefing, check inbox, review today's tasks",
            "category": "routine",
            "steps": [
                {"action": "daily_briefing", "params": {}, "label": "Generate daily briefing"},
                {"action": "list_tasks", "params": {"status": "in_progress"}, "label": "Check in-progress tasks"},
                {"action": "inbox", "params": {}, "label": "Check inbox"},
            ],
        },
        {
            "name": "End of Day",
            "description": "Run shutdown, snapshot metrics, check overdue",
            "category": "routine",
            "steps": [
                {"action": "daily_shutdown", "params": {}, "label": "Daily shutdown review"},
                {"action": "ceo_lens", "params": {}, "label": "Log today's metrics"},
                {"action": "list_tasks", "params": {"status": "todo"}, "label": "Check remaining todos"},
            ],
        },
    ]

    for pb_data in defaults:
        existing = get_playbook_by_name(pb_data["name"])
        if not existing:
            create_playbook(pb_data)


# Seed on import
seed_default_playbooks()
