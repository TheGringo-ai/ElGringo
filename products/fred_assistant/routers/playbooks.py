"""Playbook router — CRUD + execute multi-step playbooks."""

from fastapi import APIRouter, HTTPException, Query

from products.fred_assistant.models import PlaybookCreate, PlaybookUpdate
from products.fred_assistant.services import playbook_service

router = APIRouter(prefix="/playbooks", tags=["playbooks"])


@router.get("")
def list_playbooks(category: str = Query(None)):
    return playbook_service.list_playbooks(category)


@router.get("/{playbook_id}")
def get_playbook(playbook_id: str):
    pb = playbook_service.get_playbook(playbook_id)
    if not pb:
        raise HTTPException(404, "Playbook not found")
    return pb


@router.post("")
def create_playbook(data: PlaybookCreate):
    return playbook_service.create_playbook(data.model_dump())


@router.patch("/{playbook_id}")
def update_playbook(playbook_id: str, data: PlaybookUpdate):
    pb = playbook_service.update_playbook(playbook_id, data.model_dump(exclude_unset=True))
    if not pb:
        raise HTTPException(404, "Playbook not found")
    return pb


@router.delete("/{playbook_id}", status_code=204)
def delete_playbook(playbook_id: str):
    playbook_service.delete_playbook(playbook_id)


@router.post("/{playbook_id}/run")
async def run_playbook(playbook_id: str):
    result = await playbook_service.run_playbook(playbook_id)
    if "error" in result:
        raise HTTPException(404, result["error"])
    return result
