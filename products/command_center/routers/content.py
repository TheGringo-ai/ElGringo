"""Content queue and generation router."""

import asyncio
import concurrent.futures
import json
import logging
import uuid
from pathlib import Path
from typing import Dict, Optional

from fastapi import APIRouter, HTTPException, Query

from products.command_center.models import (
    ContentGenerateRequest,
    ContentItemOut,
    ContentJobOut,
    ContentStatusUpdate,
)
from products.command_center.services import get_content_generator, get_content_queue

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/content", tags=["content"])

CONTENT_DIR = Path.home() / ".ai-dev-team" / "workflow" / "content"

# In-memory job tracker for async content generation
_jobs: Dict[str, Dict] = {}


def _load_content_files(status_filter: Optional[str] = None) -> list[ContentItemOut]:
    items = []
    if not CONTENT_DIR.exists():
        return items
    for fp in sorted(CONTENT_DIR.glob("*.json")):
        try:
            with fp.open() as f:
                raw = json.load(f)
            item_id = raw.get("id", fp.stem)
            item_status = raw.get("status", "draft")
            if status_filter and item_status != status_filter:
                continue
            items.append(ContentItemOut(
                id=item_id,
                type=raw.get("type", "unknown"),
                status=item_status,
                created_at=raw.get("created_at", ""),
                data=raw.get("data", raw),
            ))
        except (json.JSONDecodeError, OSError):
            continue
    return items


def _update_content_file(item_id: str, new_status: str) -> bool:
    if not CONTENT_DIR.exists():
        return False
    for fp in CONTENT_DIR.glob("*.json"):
        try:
            with fp.open() as f:
                raw = json.load(f)
            if raw.get("id") == item_id or fp.stem == item_id:
                raw["status"] = new_status
                with fp.open("w") as f:
                    json.dump(raw, f, indent=2)
                return True
        except (json.JSONDecodeError, OSError):
            continue
    return False


@router.get("", response_model=list[ContentItemOut])
async def list_content(status: Optional[str] = Query(None)):
    return _load_content_files(status_filter=status)


@router.post("/generate", response_model=ContentJobOut, status_code=202)
async def generate_content(req: ContentGenerateRequest):
    valid_types = ("linkedin_post", "blog_post", "newsletter", "release_notes")
    if req.type not in valid_types:
        raise HTTPException(400, f"Invalid type: '{req.type}'. Must be one of: {', '.join(valid_types)}")

    job_id = f"gen_{uuid.uuid4().hex[:8]}"
    _jobs[job_id] = {"status": "running", "type": req.type, "item_id": None, "result": None, "error": None}

    def _run_sync():
        """Run content generation in a thread with its own event loop.

        ContentGenerator._generate() internally calls asyncio.get_event_loop()
        and asyncio.run(), so it needs a proper event loop in its thread.
        Using asyncio.to_thread() fails because the bare thread has no loop.
        """
        try:
            cg = get_content_generator()
            params = req.params
            if req.type == "linkedin_post":
                result = cg.generate_linkedin_post(
                    topic=params.get("topic", ""),
                    tone=params.get("tone", "professional"),
                    context=params.get("context", ""),
                )
            elif req.type == "blog_post":
                result = cg.generate_blog_post(
                    topic=params.get("topic", ""),
                    audience=params.get("audience", "developers"),
                    key_points=params.get("key_points"),
                )
            elif req.type == "newsletter":
                result = cg.generate_newsletter(
                    topic=params.get("topic", ""),
                    highlights=params.get("highlights"),
                    metrics=params.get("metrics"),
                )
            else:
                result = cg.generate_release_notes(
                    commits=params.get("commits"),
                    sprint_data=params.get("sprint_data"),
                )
            item_id = result.pop("_item_id", None)
            _jobs[job_id]["status"] = "completed"
            _jobs[job_id]["item_id"] = item_id
            _jobs[job_id]["result"] = result
        except Exception as e:
            logger.error(f"Content generation failed for job {job_id}: {e}")
            _jobs[job_id]["status"] = "failed"
            _jobs[job_id]["error"] = str(e)

    # Run in a real thread (not asyncio.to_thread) so ContentGenerator can
    # create its own event loop internally via asyncio.run() / get_event_loop()
    executor = concurrent.futures.ThreadPoolExecutor(max_workers=1)
    executor.submit(_run_sync)
    return ContentJobOut(job_id=job_id, status="running", type=req.type)


@router.get("/jobs/{job_id}", response_model=ContentJobOut)
async def get_job_status(job_id: str):
    if job_id not in _jobs:
        raise HTTPException(404, f"Job not found: {job_id}")
    j = _jobs[job_id]
    return ContentJobOut(
        job_id=job_id,
        status=j["status"],
        type=j["type"],
        item_id=j.get("item_id"),
        result=j.get("result"),
        error=j.get("error"),
    )


@router.post("/{item_id}/approve")
async def approve_content(item_id: str):
    if not _update_content_file(item_id, "approved"):
        raise HTTPException(404, f"Content item not found: {item_id}")
    get_content_queue().approve(item_id)
    return {"success": True, "item_id": item_id, "new_status": "approved"}


@router.post("/{item_id}/reject")
async def reject_content(item_id: str):
    if not _update_content_file(item_id, "rejected"):
        raise HTTPException(404, f"Content item not found: {item_id}")
    get_content_queue().reject(item_id)
    return {"success": True, "item_id": item_id, "new_status": "rejected"}
