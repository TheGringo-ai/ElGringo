"""Tests for coach_service — goals, weekly reviews, accountability."""

from products.fred_assistant.services import coach_service


# ── Goals CRUD ────────────────────────────────────────────────────

def test_create_goal_minimal():
    goal = coach_service.create_goal({"title": "Launch product"})
    assert goal["title"] == "Launch product"
    assert goal["status"] == "active"
    assert goal["progress"] == 0
    assert goal["category"] == "business"
    assert goal["id"]


def test_create_goal_all_fields():
    goal = coach_service.create_goal({
        "title": "Revenue target",
        "description": "Hit 10k MRR",
        "category": "revenue",
        "target_date": "2026-06-01",
        "milestones": [{"title": "5k MRR", "done": False}],
    })
    assert goal["title"] == "Revenue target"
    assert goal["category"] == "revenue"
    assert goal["target_date"] == "2026-06-01"
    assert len(goal["milestones"]) == 1


def test_get_goal():
    goal = coach_service.create_goal({"title": "Fetch me"})
    fetched = coach_service.get_goal(goal["id"])
    assert fetched["title"] == "Fetch me"


def test_get_goal_not_found():
    assert coach_service.get_goal("nonexistent") is None


def test_update_goal_progress():
    goal = coach_service.create_goal({"title": "Progress goal"})
    updated = coach_service.update_goal(goal["id"], {"progress": 50})
    assert updated["progress"] == 50


def test_update_goal_status():
    goal = coach_service.create_goal({"title": "Complete me"})
    updated = coach_service.update_goal(goal["id"], {"status": "completed"})
    assert updated["status"] == "completed"


def test_update_goal_milestones():
    goal = coach_service.create_goal({"title": "Milestones"})
    updated = coach_service.update_goal(goal["id"], {
        "milestones": [{"title": "Step 1", "done": True}],
    })
    assert updated["milestones"] == [{"title": "Step 1", "done": True}]


def test_update_goal_not_found():
    result = coach_service.update_goal("nonexistent", {"progress": 100})
    assert result is None


def test_delete_goal():
    goal = coach_service.create_goal({"title": "Delete me"})
    coach_service.delete_goal(goal["id"])
    assert coach_service.get_goal(goal["id"]) is None


# ── Listing + filtering ──────────────────────────────────────────

def test_list_goals_empty():
    assert coach_service.list_goals() == []


def test_list_goals_returns_all():
    coach_service.create_goal({"title": "A"})
    coach_service.create_goal({"title": "B"})
    assert len(coach_service.list_goals()) == 2


def test_list_goals_filter_by_status():
    coach_service.create_goal({"title": "Active"})
    g = coach_service.create_goal({"title": "Done"})
    coach_service.update_goal(g["id"], {"status": "completed"})
    active = coach_service.list_goals(status="active")
    assert len(active) == 1
    assert active[0]["title"] == "Active"


def test_list_goals_filter_by_category():
    coach_service.create_goal({"title": "Biz", "category": "business"})
    coach_service.create_goal({"title": "Health", "category": "health"})
    biz = coach_service.list_goals(category="business")
    assert len(biz) == 1
    assert biz[0]["title"] == "Biz"


# ── Weekly Reviews ────────────────────────────────────────────────

def test_save_review():
    review = coach_service.save_review({
        "wins": ["Shipped feature"],
        "challenges": ["Time management"],
        "lessons": ["Start early"],
        "next_week_priorities": ["Finish tests"],
        "ai_insights": "Good progress overall.",
    })
    assert review is not None
    # save_review returns get_current_review() or a dict with id+week_start
    assert "week_start" in review or "id" in review


def test_get_current_review_none():
    # Fresh DB, no reviews saved
    review = coach_service.get_current_review()
    assert review is None


def test_get_current_review_after_save():
    coach_service.save_review({"wins": ["Win!"]})
    review = coach_service.get_current_review()
    assert review is not None
    assert "Win!" in review.get("wins", [])


def test_list_reviews():
    coach_service.save_review({"wins": ["First review"]})
    reviews = coach_service.list_reviews(limit=10)
    assert len(reviews) >= 1


def test_list_reviews_respects_limit():
    coach_service.save_review({"wins": ["Review 1"]})
    coach_service.save_review({"wins": ["Review 2"], "week_start": "2026-01-06"})
    reviews = coach_service.list_reviews(limit=1)
    assert len(reviews) == 1
