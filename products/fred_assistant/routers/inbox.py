"""Unified Inbox router — prioritized action-needed feed."""

from fastapi import APIRouter

from products.fred_assistant.services import inbox_service

router = APIRouter(prefix="/inbox", tags=["inbox"])


@router.get("")
def get_inbox():
    return inbox_service.get_inbox()


@router.get("/count")
def get_count():
    return inbox_service.get_inbox_count()
