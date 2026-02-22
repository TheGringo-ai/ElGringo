"""Business Coach router — goals, weekly reviews, accountability."""

from fastapi import APIRouter, HTTPException, Query
from products.fred_assistant.models import GoalCreate, GoalUpdate
from products.fred_assistant.services import coach_service

router = APIRouter(prefix="/coach", tags=["coach"])


# ── Goals ────────────────────────────────────────────────────────

@router.get("/goals")
def list_goals(status: str = Query(None), category: str = Query(None)):
    return coach_service.list_goals(status, category)


@router.get("/goals/{goal_id}")
def get_goal(goal_id: str):
    goal = coach_service.get_goal(goal_id)
    if not goal:
        raise HTTPException(404, "Goal not found")
    return goal


@router.post("/goals")
def create_goal(data: GoalCreate):
    return coach_service.create_goal(data.model_dump())


@router.patch("/goals/{goal_id}")
def update_goal(goal_id: str, data: GoalUpdate):
    goal = coach_service.update_goal(goal_id, data.model_dump(exclude_unset=True))
    if not goal:
        raise HTTPException(404, "Goal not found")
    return goal


@router.delete("/goals/{goal_id}", status_code=204)
def delete_goal(goal_id: str):
    coach_service.delete_goal(goal_id)


# ── Weekly Reviews ───────────────────────────────────────────────

@router.get("/reviews")
def list_reviews(limit: int = Query(10, ge=1, le=52)):
    return coach_service.list_reviews(limit)


@router.get("/reviews/current")
def current_review():
    review = coach_service.get_current_review()
    if not review:
        return {"week_start": None, "wins": [], "challenges": [], "lessons": [],
                "next_week_priorities": [], "ai_insights": "No review yet this week."}
    return review


@router.post("/reviews/generate")
async def generate_review():
    return await coach_service.generate_weekly_review()


@router.post("/reviews")
def save_review(data: dict):
    return coach_service.save_review(data)
