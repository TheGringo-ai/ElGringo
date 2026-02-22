"""AI chat router with SSE streaming support."""

import json
import logging

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from products.command_center.models import ChatRequest, ChatResponse, PersonaOut
from products.command_center.services import get_ai_team, get_persona_library, get_sprint_manager

logger = logging.getLogger(__name__)
router = APIRouter(tags=["chat"])


def _build_context(persona_name: str, extra_context: str = "") -> str:
    """Build chat context with persona system prompt + current sprint state."""
    parts = []

    # Persona system prompt
    lib = get_persona_library()
    prompt = lib.get_system_prompt(persona_name)
    if prompt:
        parts.append(prompt)

    # Inject current sprint context so AI gives task-aware answers
    try:
        sm = get_sprint_manager()
        sprint = sm.get_current_sprint()
        if sprint:
            stats = sm.get_summary_stats()
            in_progress = [t.title for t in sm.tasks if t.status == "in_progress"]
            review = [t.title for t in sm.tasks if t.status == "review"]
            parts.append(
                f"Current sprint: {sprint.name} ({stats['tasks_done']}/{stats['tasks_total']} done). "
                f"In progress: {', '.join(in_progress) or 'none'}. "
                f"In review: {', '.join(review) or 'none'}."
            )
    except Exception:
        pass

    if extra_context:
        parts.append(extra_context)

    return "\n\n".join(parts)


@router.post("/chat", response_model=ChatResponse)
async def chat(req: ChatRequest):
    """Non-streaming AI chat."""
    context = _build_context(req.persona, req.context)
    team = get_ai_team()
    try:
        response = await team.ask(req.message, context=context)
        return ChatResponse(
            content=response.content if hasattr(response, "content") else str(response),
            agent_name=getattr(response, "agent_name", None),
            confidence=getattr(response, "confidence", None),
            response_time=getattr(response, "response_time", None),
        )
    except Exception as e:
        logger.error(f"Chat error: {e}")
        raise HTTPException(500, f"AI chat failed: {e}")


@router.post("/chat/stream")
async def chat_stream(req: ChatRequest):
    """SSE streaming AI chat."""
    context = _build_context(req.persona, req.context)
    team = get_ai_team()

    async def event_generator():
        try:
            # Try streaming if agent supports it
            agent = next(iter(team.agents.values()), None)
            if agent and hasattr(agent, "generate_stream"):
                full_content = ""
                async for token in agent.generate_stream(req.message):
                    full_content += token
                    yield f"data: {json.dumps({'token': token, 'done': False})}\n\n"
                yield f"data: {json.dumps({'token': '', 'done': True, 'full_content': full_content, 'agent_name': agent.name})}\n\n"
            else:
                # Fallback: get full response then emit as single chunk
                response = await team.ask(req.message, context=context)
                content = response.content if hasattr(response, "content") else str(response)
                yield f"data: {json.dumps({'token': content, 'done': True, 'full_content': content, 'agent_name': getattr(response, 'agent_name', None)})}\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'error': str(e), 'done': True})}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.get("/personas", response_model=list[PersonaOut])
async def list_personas():
    lib = get_persona_library()
    personas = []
    for name in lib.list_personas():
        p = lib.get_persona(name)
        if p:
            personas.append(PersonaOut(
                name=p.name, role=p.role,
                capabilities=p.capabilities,
                output_format=p.output_format,
                temperature=p.temperature,
            ))
    return personas
