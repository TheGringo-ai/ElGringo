"""Tests for playbook_service — Agent Playbooks."""

import pytest
from products.fred_assistant.services import playbook_service


def test_create_playbook():
    pb = playbook_service.create_playbook({
        "name": "Test Playbook",
        "description": "A test",
        "category": "general",
        "steps": [{"action": "list_tasks", "params": {}, "label": "List all tasks"}],
    })
    assert pb["name"] == "Test Playbook"
    assert len(pb["steps"]) == 1
    assert pb["category"] == "general"


def test_get_playbook():
    pb = playbook_service.create_playbook({"name": "Get Test"})
    fetched = playbook_service.get_playbook(pb["id"])
    assert fetched["name"] == "Get Test"


def test_get_playbook_by_name():
    playbook_service.create_playbook({"name": "Find Me"})
    found = playbook_service.get_playbook_by_name("Find Me")
    assert found is not None
    assert found["name"] == "Find Me"


def test_get_playbook_by_name_case_insensitive():
    playbook_service.create_playbook({"name": "Case Test"})
    found = playbook_service.get_playbook_by_name("case test")
    assert found is not None


def test_update_playbook():
    pb = playbook_service.create_playbook({"name": "Update Me"})
    updated = playbook_service.update_playbook(pb["id"], {"description": "Updated description"})
    assert updated["description"] == "Updated description"


def test_delete_playbook():
    pb = playbook_service.create_playbook({"name": "Delete Me"})
    playbook_service.delete_playbook(pb["id"])
    assert playbook_service.get_playbook(pb["id"]) is None


def test_list_playbooks():
    playbook_service.create_playbook({"name": "List A", "category": "autopilot"})
    playbook_service.create_playbook({"name": "List B", "category": "project"})
    all_pbs = playbook_service.list_playbooks()
    assert len(all_pbs) >= 2
    autopilot = playbook_service.list_playbooks("autopilot")
    assert all(p["category"] == "autopilot" for p in autopilot)


def test_seed_default_playbooks():
    # seed_default_playbooks runs on import, but we can call it again
    playbook_service.seed_default_playbooks()
    pbs = playbook_service.list_playbooks()
    names = [p["name"] for p in pbs]
    assert "Morning Standup" in names
    assert "End of Day" in names
    assert "Weekly Review" in names


@pytest.mark.asyncio
async def test_run_playbook():
    pb = playbook_service.create_playbook({
        "name": "Run Test",
        "steps": [{"action": "list_tasks", "params": {}, "label": "List tasks"}],
    })
    result = await playbook_service.run_playbook(pb["id"])
    assert result["status"] in ("completed", "partial")
    assert len(result["steps"]) == 1


@pytest.mark.asyncio
async def test_run_playbook_not_found():
    result = await playbook_service.run_playbook("nonexistent")
    assert "error" in result
