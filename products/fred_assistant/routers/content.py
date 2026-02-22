"""Content & Social Media router — create, schedule, manage content across platforms."""

from fastapi import APIRouter, HTTPException, Query
from products.fred_assistant.models import (
    ContentItemCreate, ContentGenerateRequest, SocialAccountUpdate,
)
from products.fred_assistant.services import content_service

router = APIRouter(prefix="/content", tags=["content"])


# ── Content Items ────────────────────────────────────────────────

@router.get("")
def list_content(
    status: str = Query(None),
    platform: str = Query(None),
    content_type: str = Query(None),
):
    return content_service.list_content(status, platform, content_type)


@router.get("/schedule")
def get_schedule(days: int = Query(30, ge=1, le=90)):
    return content_service.get_content_schedule(days)


@router.get("/{content_id}")
def get_content(content_id: str):
    item = content_service.get_content(content_id)
    if not item:
        raise HTTPException(404, "Content not found")
    return item


@router.post("")
def create_content(data: ContentItemCreate):
    return content_service.create_content(data.model_dump())


@router.post("/generate")
async def generate_content(data: ContentGenerateRequest):
    return await content_service.generate_content(
        topic=data.topic,
        content_type=data.content_type,
        platform=data.platform,
        tone=data.tone,
        length=data.length,
    )


@router.patch("/{content_id}")
def update_content(content_id: str, data: dict):
    item = content_service.update_content(content_id, data)
    if not item:
        raise HTTPException(404, "Content not found")
    return item


@router.post("/{content_id}/publish")
def publish_content(content_id: str):
    item = content_service.publish_content(content_id)
    if not item:
        raise HTTPException(404, "Content not found")
    return item


@router.delete("/{content_id}", status_code=204)
def delete_content(content_id: str):
    content_service.delete_content(content_id)


# ── Social Accounts ──────────────────────────────────────────────

@router.get("/social/accounts")
def list_accounts():
    return content_service.list_accounts()


@router.patch("/social/accounts/{account_id}")
def update_account(account_id: str, data: SocialAccountUpdate):
    account = content_service.update_account(account_id, data.model_dump(exclude_unset=True))
    if not account:
        raise HTTPException(404, "Account not found")
    return account
