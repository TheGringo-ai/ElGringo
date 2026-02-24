"""
Platform Services — HTTP client for FredAI specialist services.
Connects Fred Assistant (the hub) to Code Audit, Test Gen, Doc Gen, PR Bot, and Fred API.
"""

import json
import logging
import os
import time
import uuid

import httpx

from products.fred_assistant.database import get_conn, log_activity

logger = logging.getLogger(__name__)

# ── Service Registry ─────────────────────────────────────────────

SERVICES = {
    "code_audit": {
        "port": int(os.getenv("CODE_AUDIT_PORT", "8081")),
        "prefix": "/audit",
        "health": "/audit/health",
        "label": "Code Audit",
    },
    "test_gen": {
        "port": int(os.getenv("TEST_GEN_PORT", "8082")),
        "prefix": "/tests",
        "health": "/tests/health",
        "label": "Test Generator",
    },
    "doc_gen": {
        "port": int(os.getenv("DOC_GEN_PORT", "8083")),
        "prefix": "/docs",
        "health": "/docs/health",
        "label": "Doc Generator",
    },
    "pr_bot": {
        "port": int(os.getenv("PR_BOT_PORT", "8001")),
        "prefix": "",
        "health": "/health",
        "label": "PR Review Bot",
    },
    "fred_api": {
        "port": int(os.getenv("FRED_API_PORT", "8080")),
        "prefix": "/v1",
        "health": "/v1/health",
        "label": "Fred API",
    },
}

BASE_HOST = os.getenv("PLATFORM_HOST", "http://localhost")
TIMEOUT = float(os.getenv("PLATFORM_TIMEOUT", "120"))
HEALTH_TIMEOUT = 3.0

# ── Cached status (avoid hammering health endpoints) ─────────────

_status_cache: dict = {}
_status_cache_time: float = 0
STATUS_CACHE_TTL = 30  # seconds


# ── Core Functions ───────────────────────────────────────────────

def get_service_url(service_name: str) -> str:
    """Get the base URL for a service."""
    svc = SERVICES.get(service_name)
    if not svc:
        raise ValueError(f"Unknown service: {service_name}")
    return f"{BASE_HOST}:{svc['port']}"


async def call_service(
    service_name: str,
    method: str,
    path: str,
    data: dict | None = None,
    timeout: float | None = None,
) -> dict:
    """Call a specialist service and return the response."""
    svc = SERVICES.get(service_name)
    if not svc:
        return {"error": f"Unknown service: {service_name}"}

    url = f"{BASE_HOST}:{svc['port']}{path}"
    timeout = timeout or TIMEOUT

    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            if method.upper() == "GET":
                resp = await client.get(url)
            else:
                resp = await client.post(url, json=data or {})

            if resp.status_code >= 400:
                return {
                    "error": f"{service_name} returned {resp.status_code}: {resp.text[:500]}"
                }

            return resp.json()

    except httpx.ConnectError:
        return {"error": f"{svc['label']} is not running (port {svc['port']})"}
    except httpx.TimeoutException:
        return {"error": f"{svc['label']} timed out after {timeout}s"}
    except Exception as e:
        return {"error": f"{svc['label']} call failed: {str(e)}"}


def check_service_health(service_name: str) -> dict:
    """Synchronous health check for a single service."""
    svc = SERVICES.get(service_name)
    if not svc:
        return {"service": service_name, "healthy": False, "error": "unknown service"}

    url = f"{BASE_HOST}:{svc['port']}{svc['health']}"
    try:
        resp = httpx.get(url, timeout=HEALTH_TIMEOUT)
        return {
            "service": service_name,
            "label": svc["label"],
            "healthy": resp.status_code == 200,
            "port": svc["port"],
            "details": resp.json() if resp.status_code == 200 else {},
        }
    except Exception:
        return {
            "service": service_name,
            "label": svc["label"],
            "healthy": False,
            "port": svc["port"],
            "details": {},
        }


def check_all_services() -> dict:
    """Check health of all platform services."""
    results = {}
    for name in SERVICES:
        results[name] = check_service_health(name)
    return results


def get_cached_status() -> dict | None:
    """Get cached service status (refreshes every STATUS_CACHE_TTL seconds)."""
    global _status_cache, _status_cache_time
    now = time.time()
    if now - _status_cache_time > STATUS_CACHE_TTL:
        try:
            _status_cache = check_all_services()
            _status_cache_time = now
        except Exception:
            pass
    return _status_cache if _status_cache else None


# ── Result Storage ───────────────────────────────────────────────

def store_service_result(
    service: str,
    action: str,
    project_name: str | None,
    result_data: dict,
) -> str:
    """Store a service result in the database. Returns the result ID."""
    result_id = str(uuid.uuid4())[:12]
    with get_conn() as conn:
        conn.execute(
            """INSERT INTO service_results
               (id, service, action, project_name, input_summary, result, agents_used, total_time)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                result_id,
                service,
                action,
                project_name or "",
                result_data.get("input_summary", ""),
                json.dumps(result_data) if isinstance(result_data, dict) else str(result_data),
                json.dumps(result_data.get("agents_used", [])),
                result_data.get("total_time", 0),
            ),
        )
    log_activity(f"service_result:{service}:{action}", "service_result", result_id, {
        "project_name": project_name,
    })
    # Index in RAG (fire-and-forget)
    try:
        from products.fred_assistant.services.rag_service import get_rag
        get_rag().index_service_result({
            "id": result_id,
            "service": service,
            "action": action,
            "project_name": project_name or "",
            "input_summary": result_data.get("input_summary", ""),
            "result": str(result_data)[:500],
        })
    except Exception:
        pass
    return result_id


def get_recent_results(
    service: str | None = None,
    project_name: str | None = None,
    limit: int = 10,
) -> list[dict]:
    """Get recent service results, optionally filtered."""
    query = "SELECT * FROM service_results WHERE 1=1"
    params: list = []
    if service:
        query += " AND service = ?"
        params.append(service)
    if project_name:
        query += " AND project_name = ?"
        params.append(project_name)
    query += " ORDER BY created_at DESC LIMIT ?"
    params.append(limit)

    with get_conn() as conn:
        rows = conn.execute(query, params).fetchall()

    results = []
    for row in rows:
        d = dict(row)
        try:
            d["agents_used"] = json.loads(d.get("agents_used", "[]"))
        except (json.JSONDecodeError, TypeError):
            d["agents_used"] = []
        results.append(d)
    return results
