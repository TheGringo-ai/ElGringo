"""Quick capture — throw text at Fred and he turns it into a task."""

from fastapi import APIRouter

from products.fred_assistant.models import QuickCaptureRequest, TaskOut
from products.fred_assistant.services import task_service
from products.fred_assistant.services.nlp_parser import parse_capture_text

router = APIRouter(prefix="/capture", tags=["capture"])


@router.post("", response_model=TaskOut, status_code=201)
async def quick_capture(data: QuickCaptureRequest):
    """Parse natural text into a task using AI with heuristic fallback."""
    parsed = await parse_capture_text(data.text, data.board_id)
    parsed.pop("_parsed_by", None)
    if parsed.get("priority") is None:
        parsed["priority"] = 3
    if not parsed.get("board_id"):
        parsed["board_id"] = data.board_id or "work"
    return task_service.create_task(parsed)


@router.post("/preview")
async def preview_capture(data: QuickCaptureRequest):
    """Parse text and return structured fields without creating a task."""
    parsed = await parse_capture_text(data.text, data.board_id)
    if parsed.get("priority") is None:
        parsed["priority"] = 3
    if not parsed.get("board_id"):
        parsed["board_id"] = data.board_id or "work"
    return parsed
