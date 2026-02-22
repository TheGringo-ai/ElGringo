import json
from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from products.fred_assistant.models import ChatRequest, ChatMessage
from products.fred_assistant.services import assistant

router = APIRouter(prefix="/chat", tags=["chat"])


@router.get("/history", response_model=list[ChatMessage])
async def get_history():
    return assistant.get_history(limit=100)


@router.post("")
async def chat(data: ChatRequest):
    reply = await assistant.chat(data.message, data.persona)
    return {"role": "assistant", "content": reply}


@router.post("/stream")
async def stream_chat(data: ChatRequest):
    async def generate():
        async for event in assistant.stream_chat(data.message, data.persona):
            event_type = event.get("type", "token")
            event_data = event.get("data", "")

            if event_type == "thinking":
                yield f"data: {json.dumps({'thinking': True, 'actions': event_data, 'done': False})}\n\n"
            elif event_type == "thinking_done":
                yield f"data: {json.dumps({'thinking': False, 'result': event_data, 'done': False})}\n\n"
            else:
                yield f"data: {json.dumps({'token': event_data, 'done': False})}\n\n"

        yield f"data: {json.dumps({'token': '', 'done': True})}\n\n"

    return StreamingResponse(generate(), media_type="text/event-stream")


@router.delete("/history", status_code=204)
async def clear_history():
    assistant.clear_history()
