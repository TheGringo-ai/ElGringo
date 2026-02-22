"""
Fred Assistant — Local AI Personal Assistant
=============================================
Runs on your Mac. Manages tasks, boards, memory, chat, daily briefings.
Backed by SQLite (fast, private, zero config) and the FredAI orchestrator.

Run: uvicorn products.fred_assistant.server:app --port 7870 --reload
"""

import os
import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

logger = logging.getLogger(__name__)

app = FastAPI(
    title="Fred Assistant",
    description="Your local AI personal assistant",
    version="1.0.0",
    docs_url="/docs",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5174", "http://localhost:7870", "http://127.0.0.1:5174"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routers ───────────────────────────────────────────────────────

from products.fred_assistant.routers.health import router as health_router
from products.fred_assistant.routers.boards import router as boards_router
from products.fred_assistant.routers.tasks import router as tasks_router
from products.fred_assistant.routers.memory import router as memory_router
from products.fred_assistant.routers.chat import router as chat_router
from products.fred_assistant.routers.briefing import router as briefing_router
from products.fred_assistant.routers.capture import router as capture_router
from products.fred_assistant.routers.projects import router as projects_router
from products.fred_assistant.routers.calendar import router as calendar_router
from products.fred_assistant.routers.content import router as content_router
from products.fred_assistant.routers.coach import router as coach_router
from products.fred_assistant.routers.focus import router as focus_router
from products.fred_assistant.routers.crm import router as crm_router
from products.fred_assistant.routers.metrics import router as metrics_router
from products.fred_assistant.routers.inbox import router as inbox_router
from products.fred_assistant.routers.playbooks import router as playbooks_router

app.include_router(health_router)
app.include_router(boards_router)
app.include_router(tasks_router)
app.include_router(memory_router)
app.include_router(chat_router)
app.include_router(briefing_router)
app.include_router(capture_router)
app.include_router(projects_router)
app.include_router(calendar_router)
app.include_router(content_router)
app.include_router(coach_router)
app.include_router(focus_router)
app.include_router(crm_router)
app.include_router(metrics_router)
app.include_router(inbox_router)
app.include_router(playbooks_router)

# ── Static files (serve React build in production) ────────────────

DIST_DIR = os.path.join(os.path.dirname(__file__), "frontend", "dist")
if os.path.isdir(DIST_DIR):
    from fastapi.responses import FileResponse

    @app.get("/app/{rest:path}")
    async def serve_spa(rest: str = ""):
        filepath = os.path.join(DIST_DIR, rest)
        if os.path.isfile(filepath):
            return FileResponse(filepath)
        return FileResponse(os.path.join(DIST_DIR, "index.html"))

    app.mount("/assets", StaticFiles(directory=os.path.join(DIST_DIR, "assets")), name="assets")


def main():
    import uvicorn
    port = int(os.getenv("PORT", "7870"))
    logger.info(f"Starting Fred Assistant on port {port}")
    uvicorn.run(app, host="127.0.0.1", port=port)


if __name__ == "__main__":
    main()
