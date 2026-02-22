"""Quick capture — throw text at Fred and he turns it into a task."""

from fastapi import APIRouter

from products.fred_assistant.models import QuickCaptureRequest, TaskOut
from products.fred_assistant.services import task_service

router = APIRouter(prefix="/capture", tags=["capture"])


@router.post("", response_model=TaskOut, status_code=201)
async def quick_capture(data: QuickCaptureRequest):
    """Parse natural text into a task. For now, creates directly.
    TODO: Wire AI to parse priority, due date, board from natural language."""
    task_data = {
        "board_id": data.board_id,
        "title": data.text.strip(),
        "status": "todo",
        "priority": 3,
    }

    # Simple heuristic parsing
    text = data.text.lower()
    if any(w in text for w in ["urgent", "asap", "critical"]):
        task_data["priority"] = 1
    elif any(w in text for w in ["important", "high"]):
        task_data["priority"] = 2
    elif any(w in text for w in ["low", "eventually", "someday"]):
        task_data["priority"] = 5

    # Board detection
    if any(w in text for w in ["gym", "workout", "run", "health", "doctor"]):
        task_data["board_id"] = "health"
    elif any(w in text for w in ["idea", "research", "explore", "investigate"]):
        task_data["board_id"] = "ideas"
    elif any(w in text for w in ["personal", "home", "groceries", "call", "appointment"]):
        task_data["board_id"] = "personal"
    elif any(w in text for w in ["fredai", "deploy", "code", "fix", "build", "feature"]):
        task_data["board_id"] = "fredai"

    return task_service.create_task(task_data)
