"""
Usage Analytics API
===================

FastAPI router exposing analytics data from the shared AnalyticsStore.

For FastAPI products:
    from middleware.analytics_api import analytics_router
    app.include_router(analytics_router)

For Flask (api_server.py):
    Uses dedicated Flask endpoints registered by ``register_flask_analytics_routes()``.
"""

import logging
import os
from typing import Any, Dict, List

from fastapi import APIRouter, Depends, HTTPException, Request

from .analytics import AnalyticsStore, get_analytics_store

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Auth helper (reuses the same Bearer token pattern as other FredAI services)
# ---------------------------------------------------------------------------

FREDAI_API_TOKEN = os.getenv("FREDAI_API_TOKEN", "")


async def _verify_analytics_auth(request: Request):
    """Verify Bearer token for analytics endpoints.

    Skips auth when:
    - No FREDAI_API_TOKEN is configured (dev mode)
    - Request comes from localhost
    """
    if not FREDAI_API_TOKEN:
        return

    client_host = request.client.host if request.client else ""
    if client_host in ("127.0.0.1", "::1", "localhost"):
        return

    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing Authorization header")
    if auth[7:] != FREDAI_API_TOKEN:
        raise HTTPException(status_code=401, detail="Invalid API token")


# ---------------------------------------------------------------------------
# FastAPI Router
# ---------------------------------------------------------------------------

analytics_router = APIRouter(
    prefix="/api/usage",
    tags=["usage-analytics"],
    dependencies=[Depends(_verify_analytics_auth)],
)


@analytics_router.get("/summary")
async def usage_summary() -> Dict[str, Any]:
    """Overall usage statistics: total requests, 24h counts, avg response
    time, top endpoints, error rate."""
    store = get_analytics_store()
    return {"success": True, "data": store.get_summary()}


@analytics_router.get("/endpoints")
async def usage_endpoints(endpoint: str = "") -> Dict[str, Any]:
    """Per-endpoint breakdown.

    If ``endpoint`` query param is provided, returns stats for that single
    endpoint.  Otherwise returns stats for all tracked endpoints.
    """
    store = get_analytics_store()
    if endpoint:
        return {"success": True, "data": store.get_endpoint_stats(endpoint)}
    return {"success": True, "data": store.get_all_endpoint_stats()}


@analytics_router.get("/hourly")
async def usage_hourly() -> Dict[str, Any]:
    """Hourly request counts for the last 24 hours (chart data)."""
    store = get_analytics_store()
    return {"success": True, "data": store.get_hourly_breakdown()}


# ---------------------------------------------------------------------------
# Flask route registrar
# ---------------------------------------------------------------------------

def register_flask_analytics_routes(flask_app, store: AnalyticsStore = None):
    """Register /api/usage/* endpoints on a Flask app.

    This mirrors the FastAPI router above so the Flask API server exposes
    the same analytics endpoints.
    """
    from flask import jsonify, request as flask_request

    _store = store or get_analytics_store()

    def _check_auth():
        """Inline auth check matching the Flask global auth pattern."""
        token = os.getenv("FREDAI_API_TOKEN", "")
        if not token:
            return None
        remote = flask_request.remote_addr or ""
        if remote in ("127.0.0.1", "::1", "localhost"):
            return None
        auth = flask_request.headers.get("Authorization", "")
        if not auth.startswith("Bearer "):
            return jsonify({"error": "Missing Authorization header"}), 401
        if auth[7:] != token:
            return jsonify({"error": "Invalid API token"}), 401
        return None

    @flask_app.route("/api/usage/summary", methods=["GET"])
    def flask_usage_summary():
        err = _check_auth()
        if err:
            return err
        return jsonify({"success": True, "data": _store.get_summary()})

    @flask_app.route("/api/usage/endpoints", methods=["GET"])
    def flask_usage_endpoints():
        err = _check_auth()
        if err:
            return err
        endpoint = flask_request.args.get("endpoint", "")
        if endpoint:
            return jsonify({"success": True, "data": _store.get_endpoint_stats(endpoint)})
        return jsonify({"success": True, "data": _store.get_all_endpoint_stats()})

    @flask_app.route("/api/usage/hourly", methods=["GET"])
    def flask_usage_hourly():
        err = _check_auth()
        if err:
            return err
        return jsonify({"success": True, "data": _store.get_hourly_breakdown()})

    logger.info("Flask analytics routes registered at /api/usage/*")
