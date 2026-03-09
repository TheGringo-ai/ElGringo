"""
El Gringo Command Center API
==========================

FastAPI backend for the Command Center dashboard.
Exposes sprint board, content queue, AI chat, and automation
endpoints backed by existing elgringo workflow modules.

Run: uvicorn products.command_center.server:app --port 7862
"""

import logging
import os

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware

logger = logging.getLogger(__name__)

# ── App ──────────────────────────────────────────────────────────────

app = FastAPI(
    title="El Gringo Command Center",
    description="Unified dashboard API for daily founder operations",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

_cors_origins = os.getenv(
    "COMMAND_CENTER_CORS_ORIGINS",
    "http://localhost:7863,http://localhost:5173,http://localhost:3000,https://ai.chatterfix.com",
).split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in _cors_origins],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Auth ─────────────────────────────────────────────────────────────
# Bearer token auth, same pattern as fred_api.
# Skips auth for localhost requests (Streamlit UI calls from same machine).

COMMAND_API_KEYS: set = set()
_raw = os.getenv("COMMAND_CENTER_API_KEYS", os.getenv("ELGRINGO_API_TOKEN", ""))
if _raw:
    COMMAND_API_KEYS = {k.strip() for k in _raw.split(",") if k.strip()}


@app.middleware("http")
async def auth_middleware(request: Request, call_next):
    # Skip auth for health check
    if request.url.path == "/health":
        return await call_next(request)

    # Skip auth for localhost (Streamlit UI on same machine)
    client_host = request.client.host if request.client else ""
    if client_host in ("127.0.0.1", "::1", "localhost"):
        return await call_next(request)

    # Skip auth if no keys configured (dev mode)
    if not COMMAND_API_KEYS:
        return await call_next(request)

    # Verify Bearer token
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        raise HTTPException(401, "Missing API key")
    if auth[7:] not in COMMAND_API_KEYS:
        raise HTTPException(401, "Invalid API key")

    return await call_next(request)


# ── Current User (hardcoded, swap to JWT later) ─────────────────────

async def get_current_user() -> dict:
    """Returns current user. Hardcoded now, swap to JWT/Firebase later."""
    return {"uid": "fred", "name": "Fred Taylor", "role": "admin"}


# ── Routers ──────────────────────────────────────────────────────────

from products.command_center.routers.health import router as health_router
from products.command_center.routers.sprints import router as sprints_router
from products.command_center.routers.content import router as content_router
from products.command_center.routers.chat import router as chat_router
from products.command_center.routers.automation import router as automation_router

app.include_router(health_router)
app.include_router(sprints_router)
app.include_router(content_router)
app.include_router(chat_router)
app.include_router(automation_router)


# ── Entry point ──────────────────────────────────────────────────────

def main():
    """Launch the Command Center API server."""
    import uvicorn

    port = int(os.getenv("PORT", "7862"))
    logger.info(f"Starting Command Center API on port {port}")
    uvicorn.run(app, host="0.0.0.0", port=port)


if __name__ == "__main__":
    main()
