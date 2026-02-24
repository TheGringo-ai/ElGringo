"""Tests for content_service — content creation and social media management."""

import pytest
from products.fred_assistant.services import content_service


# ── Content CRUD ────────────────────────────────────────────────

def test_create_content_minimal():
    item = content_service.create_content({"title": "My Post"})
    assert item["title"] == "My Post"
    assert item["status"] == "draft"
    assert item["platform"] == "linkedin"
    assert item["content_type"] == "post"
    assert item["id"]


def test_create_content_all_fields():
    item = content_service.create_content({
        "title": "Full Post",
        "body": "This is the body",
        "content_type": "article",
        "platform": "twitter",
        "status": "scheduled",
        "scheduled_date": "2026-03-01",
        "scheduled_time": "10:00",
        "tags": ["ai", "dev"],
        "ai_generated": True,
    })
    assert item["title"] == "Full Post"
    assert item["body"] == "This is the body"
    assert item["content_type"] == "article"
    assert item["platform"] == "twitter"
    assert item["tags"] == ["ai", "dev"]
    assert item["ai_generated"] is True


def test_get_content():
    item = content_service.create_content({"title": "Fetch Me"})
    fetched = content_service.get_content(item["id"])
    assert fetched["title"] == "Fetch Me"


def test_get_content_not_found():
    assert content_service.get_content("nonexistent") is None


def test_update_content_status():
    item = content_service.create_content({"title": "Update Status"})
    updated = content_service.update_content(item["id"], {"status": "scheduled"})
    assert updated["status"] == "scheduled"


def test_update_content_body():
    item = content_service.create_content({"title": "Update Body", "body": "old"})
    updated = content_service.update_content(item["id"], {"body": "new body text"})
    assert updated["body"] == "new body text"


def test_update_content_tags():
    item = content_service.create_content({"title": "Tag Update", "tags": ["old"]})
    updated = content_service.update_content(item["id"], {"tags": ["new", "fresh"]})
    assert updated["tags"] == ["new", "fresh"]


def test_update_content_not_found():
    result = content_service.update_content("nonexistent", {"status": "published"})
    assert result is None


def test_delete_content():
    item = content_service.create_content({"title": "Delete Me"})
    content_service.delete_content(item["id"])
    assert content_service.get_content(item["id"]) is None


# ── Listing + filtering ──────────────────────────────────────────

def test_list_content_empty():
    assert content_service.list_content() == []


def test_list_content_returns_all():
    content_service.create_content({"title": "A"})
    content_service.create_content({"title": "B"})
    assert len(content_service.list_content()) == 2


def test_list_content_filter_by_status():
    content_service.create_content({"title": "Draft"})
    content_service.create_content({"title": "Scheduled", "status": "scheduled"})
    drafts = content_service.list_content(status="draft")
    assert all(c["status"] == "draft" for c in drafts)


def test_list_content_filter_by_platform():
    content_service.create_content({"title": "LinkedIn", "platform": "linkedin"})
    content_service.create_content({"title": "Twitter", "platform": "twitter"})
    linkedin = content_service.list_content(platform="linkedin")
    assert len(linkedin) == 1
    assert linkedin[0]["platform"] == "linkedin"


def test_list_content_filter_by_type():
    content_service.create_content({"title": "Post", "content_type": "post"})
    content_service.create_content({"title": "Article", "content_type": "article"})
    posts = content_service.list_content(content_type="post")
    assert len(posts) == 1
    assert posts[0]["content_type"] == "post"


# ── Publish ──────────────────────────────────────────────────────

def test_publish_content():
    item = content_service.create_content({"title": "Publish Me"})
    published = content_service.publish_content(item["id"])
    assert published["status"] == "published"
    assert published["published_at"] is not None


def test_publish_nonexistent_content():
    # publish_content doesn't guard against missing IDs, returns None via get_content
    result = content_service.publish_content("nonexistent")
    assert result is None


# ── Schedule ─────────────────────────────────────────────────────

def test_get_content_schedule():
    from datetime import date, timedelta
    tomorrow = (date.today() + timedelta(days=1)).isoformat()
    content_service.create_content({
        "title": "Scheduled Post",
        "scheduled_date": tomorrow,
    })
    schedule = content_service.get_content_schedule(days=7)
    assert len(schedule) >= 1
    assert schedule[0]["title"] == "Scheduled Post"


def test_get_content_schedule_excludes_past():
    content_service.create_content({
        "title": "Past Post",
        "scheduled_date": "2020-01-01",
    })
    schedule = content_service.get_content_schedule(days=7)
    past = [s for s in schedule if s["title"] == "Past Post"]
    assert len(past) == 0
