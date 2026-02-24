"""
AI Usage Router — track costs, tokens, latency across all LLM providers.
"""

from fastapi import APIRouter, Query
from pydantic import BaseModel
from typing import Optional

from products.fred_assistant.database import (
    get_usage_today,
    get_usage_summary,
    get_usage_by_model,
    get_recent_usage,
    get_usage_budget,
    set_usage_budget,
    get_monthly_cost,
)

router = APIRouter(prefix="/usage", tags=["usage"])


# ── Schemas ────────────────────────────────────────────────────────

class BudgetUpdate(BaseModel):
    daily_limit: float
    monthly_limit: float


class ProviderPrefs(BaseModel):
    preferred_provider: Optional[str] = None
    enabled_providers: Optional[list] = None


# ── Endpoints ──────────────────────────────────────────────────────

@router.get("/today")
async def usage_today():
    """Today's total cost, token count, request count."""
    return get_usage_today()


@router.get("/summary")
async def usage_summary(days: int = Query(30, ge=1, le=365)):
    """Daily aggregates for charting."""
    return get_usage_summary(days)


@router.get("/by-model")
async def usage_by_model(days: int = Query(30, ge=1, le=365)):
    """Breakdown by model/provider."""
    return get_usage_by_model(days)


@router.get("/budget")
async def usage_budget():
    """Budget status — daily/monthly limits + current spend."""
    budget = get_usage_budget()
    today = get_usage_today()
    monthly = get_monthly_cost()
    daily_cost = today.get("cost", 0) if today else 0
    return {
        "daily_limit": budget["daily_limit"],
        "monthly_limit": budget["monthly_limit"],
        "daily_spent": round(daily_cost, 6),
        "monthly_spent": round(monthly, 6),
        "daily_remaining": round(max(0, budget["daily_limit"] - daily_cost), 6),
        "monthly_remaining": round(max(0, budget["monthly_limit"] - monthly), 6),
        "daily_pct": round(daily_cost / max(budget["daily_limit"], 0.01) * 100, 1),
        "monthly_pct": round(monthly / max(budget["monthly_limit"], 0.01) * 100, 1),
    }


@router.post("/budget")
async def update_budget(body: BudgetUpdate):
    """Update daily/monthly budget limits."""
    set_usage_budget(body.daily_limit, body.monthly_limit)
    return {"status": "ok", "daily_limit": body.daily_limit, "monthly_limit": body.monthly_limit}


@router.get("/recent")
async def recent_usage(limit: int = Query(50, ge=1, le=500)):
    """Recent individual LLM requests."""
    return get_recent_usage(limit)


# ── Provider Config (Phase 2) ────────────────────────────────────

@router.get("/providers")
async def list_providers():
    """List available providers and their status."""
    try:
        from products.fred_assistant.services.model_router import get_router
        mr = get_router()
        return {
            "providers": await mr.available_providers(),
            "preferences": mr.get_preferences(),
        }
    except ImportError:
        return {"providers": [], "preferences": {}}


@router.post("/providers/preferences")
async def update_provider_prefs(body: ProviderPrefs):
    """Update provider preferences (preferred provider, enabled list)."""
    try:
        from products.fred_assistant.services.model_router import get_router
        mr = get_router()
        mr.set_preferences(
            preferred=body.preferred_provider,
            enabled=body.enabled_providers,
        )
        return {"status": "ok", "preferences": mr.get_preferences()}
    except ImportError:
        return {"status": "error", "message": "Model router not available"}


# ── Sync Status (Phase 3) ────────────────────────────────────────

@router.get("/sync/status")
async def sync_status():
    """Current sync status for the UI indicator."""
    try:
        from products.fred_assistant.services.sync_service import get_sync_service
        svc = get_sync_service()
        return svc.status()
    except ImportError:
        return {"configured": False, "last_sync": None, "pending": 0}
