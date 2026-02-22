"""Health check router."""

from fastapi import APIRouter

from products.command_center.models import HealthOut

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthOut)
async def health():
    from products.command_center.services import (
        get_sprint_manager,
        get_scheduler,
        get_standup_generator,
    )
    services = {}
    try:
        get_sprint_manager()
        services["sprint_manager"] = True
    except Exception:
        services["sprint_manager"] = False
    try:
        get_scheduler()
        services["scheduler"] = True
    except Exception:
        services["scheduler"] = False
    try:
        get_standup_generator()
        services["standup_generator"] = True
    except Exception:
        services["standup_generator"] = False

    return HealthOut(status="healthy", version="0.1.0", services=services)
