"""Revenue CRM Lite — Leads, outreach, pipeline management."""

import json
import uuid
from datetime import date, datetime, timedelta

from products.fred_assistant.database import get_conn, log_activity

PIPELINE_STAGES = ["cold", "contacted", "call_booked", "trial", "paid", "churned"]


def list_leads(stage: str = None, source: str = None) -> list[dict]:
    with get_conn() as conn:
        query = "SELECT * FROM leads WHERE 1=1"
        params = []
        if stage:
            query += " AND pipeline_stage=?"
            params.append(stage)
        if source:
            query += " AND source=?"
            params.append(source)
        query += " ORDER BY updated_at DESC"
        rows = conn.execute(query, params).fetchall()
    results = []
    for r in rows:
        d = dict(r)
        try:
            d["tags"] = json.loads(d.get("tags") or "[]")
        except (json.JSONDecodeError, TypeError):
            d["tags"] = []
        results.append(d)
    return results


def get_lead(lead_id: str) -> dict | None:
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM leads WHERE id=?", (lead_id,)).fetchone()
        if not row:
            return None
        d = dict(row)
        try:
            d["tags"] = json.loads(d.get("tags") or "[]")
        except (json.JSONDecodeError, TypeError):
            d["tags"] = []
        return d


def create_lead(data: dict) -> dict:
    lead_id = uuid.uuid4().hex[:8]
    now = datetime.now().isoformat()
    tags = json.dumps(data.get("tags", []))
    with get_conn() as conn:
        conn.execute(
            """INSERT INTO leads (id, name, company, email, phone, source, pipeline_stage, deal_value, notes, next_followup, tags, created_at, updated_at)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (
                lead_id,
                data.get("name", ""),
                data.get("company", ""),
                data.get("email", ""),
                data.get("phone", ""),
                data.get("source", ""),
                data.get("pipeline_stage", "cold"),
                data.get("deal_value", 0),
                data.get("notes", ""),
                data.get("next_followup"),
                tags,
                now,
                now,
            ),
        )
    log_activity("lead_created", "lead", lead_id, {"name": data.get("name")})
    return get_lead(lead_id)


def update_lead(lead_id: str, data: dict) -> dict | None:
    lead = get_lead(lead_id)
    if not lead:
        return None
    fields = []
    params = []
    for key in ["name", "company", "email", "phone", "source", "pipeline_stage", "deal_value", "notes", "next_followup"]:
        if key in data:
            fields.append(f"{key}=?")
            params.append(data[key])
    if "tags" in data:
        fields.append("tags=?")
        params.append(json.dumps(data["tags"]))
    if not fields:
        return lead
    fields.append("updated_at=?")
    params.append(datetime.now().isoformat())
    params.append(lead_id)
    with get_conn() as conn:
        conn.execute(f"UPDATE leads SET {', '.join(fields)} WHERE id=?", params)
    log_activity("lead_updated", "lead", lead_id, data)
    return get_lead(lead_id)


def delete_lead(lead_id: str):
    with get_conn() as conn:
        conn.execute("DELETE FROM outreach_log WHERE lead_id=?", (lead_id,))
        conn.execute("DELETE FROM leads WHERE id=?", (lead_id,))
    log_activity("lead_deleted", "lead", lead_id)


def log_outreach(lead_id: str, outreach_type: str = "email", content: str = "", result: str = "") -> dict:
    entry_id = uuid.uuid4().hex[:8]
    now = datetime.now().isoformat()
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO outreach_log (id, lead_id, outreach_type, content, result, created_at) VALUES (?,?,?,?,?,?)",
            (entry_id, lead_id, outreach_type, content, result, now),
        )
    log_activity("outreach_logged", "lead", lead_id, {"type": outreach_type})
    return {"id": entry_id, "lead_id": lead_id, "outreach_type": outreach_type, "content": content, "result": result, "created_at": now}


def get_outreach_history(lead_id: str) -> list[dict]:
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM outreach_log WHERE lead_id=? ORDER BY created_at DESC", (lead_id,)
        ).fetchall()
    return [dict(r) for r in rows]


def schedule_followup(lead_id: str, followup_date: str, notes: str = "") -> dict | None:
    updates = {"next_followup": followup_date}
    if notes:
        lead = get_lead(lead_id)
        if lead:
            existing = lead.get("notes", "")
            updates["notes"] = f"{existing}\n[Followup {followup_date}] {notes}".strip()
    return update_lead(lead_id, updates)


def move_lead(lead_id: str, new_stage: str) -> dict | None:
    if new_stage not in PIPELINE_STAGES:
        return None
    return update_lead(lead_id, {"pipeline_stage": new_stage})


def get_pipeline_summary() -> dict:
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT pipeline_stage, COUNT(*) as count, COALESCE(SUM(deal_value), 0) as total_value FROM leads GROUP BY pipeline_stage"
        ).fetchall()
    summary = {stage: {"count": 0, "total_value": 0} for stage in PIPELINE_STAGES}
    for r in rows:
        stage = r["pipeline_stage"]
        if stage in summary:
            summary[stage] = {"count": r["count"], "total_value": r["total_value"]}
    total_leads = sum(s["count"] for s in summary.values())
    total_pipeline = sum(s["total_value"] for s in summary.values())
    return {"stages": summary, "total_leads": total_leads, "total_pipeline_value": total_pipeline}


def get_followups_due(days: int = 3) -> list[dict]:
    cutoff = (date.today() + timedelta(days=days)).isoformat()
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM leads WHERE next_followup IS NOT NULL AND next_followup <= ? AND pipeline_stage NOT IN ('paid', 'churned') ORDER BY next_followup",
            (cutoff,),
        ).fetchall()
    results = []
    for r in rows:
        d = dict(r)
        try:
            d["tags"] = json.loads(d.get("tags") or "[]")
        except (json.JSONDecodeError, TypeError):
            d["tags"] = []
        results.append(d)
    return results
