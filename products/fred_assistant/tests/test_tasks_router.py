"""Tests for tasks router — HTTP endpoint integration tests."""

import os

os.environ["FRED_DB_PATH"] = ":memory:"

from fastapi.testclient import TestClient

from products.fred_assistant.server import app

client = TestClient(app)


# ── GET /tasks ────────────────────────────────────────────────────

def test_list_tasks_empty():
    resp = client.get("/tasks")
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


def test_list_tasks_with_data():
    client.post("/tasks", json={"title": "Router task A"})
    client.post("/tasks", json={"title": "Router task B"})
    resp = client.get("/tasks")
    assert resp.status_code == 200
    assert len(resp.json()) >= 2


def test_list_tasks_filter_board_id():
    client.post("/tasks", json={"title": "Work task", "board_id": "work"})
    client.post("/tasks", json={"title": "Personal task", "board_id": "personal"})
    resp = client.get("/tasks", params={"board_id": "work"})
    assert resp.status_code == 200
    for t in resp.json():
        assert t["board_id"] == "work"


def test_list_tasks_filter_status():
    client.post("/tasks", json={"title": "Todo", "status": "todo"})
    resp = client.get("/tasks", params={"status": "todo"})
    assert resp.status_code == 200
    for t in resp.json():
        assert t["status"] == "todo"


# ── POST /tasks ───────────────────────────────────────────────────

def test_create_task():
    resp = client.post("/tasks", json={"title": "New task"})
    assert resp.status_code == 201
    data = resp.json()
    assert data["title"] == "New task"
    assert data["id"]
    assert data["status"] == "todo"


def test_create_task_with_all_fields():
    resp = client.post("/tasks", json={
        "title": "Full task",
        "description": "Detailed desc",
        "board_id": "personal",
        "priority": 1,
        "tags": ["important"],
    })
    assert resp.status_code == 201
    data = resp.json()
    assert data["board_id"] == "personal"
    assert data["priority"] == 1
    assert data["tags"] == ["important"]


def test_create_task_missing_title():
    resp = client.post("/tasks", json={})
    assert resp.status_code == 422


# ── GET /tasks/{task_id} ─────────────────────────────────────────

def test_get_task():
    create = client.post("/tasks", json={"title": "Get me"})
    task_id = create.json()["id"]
    resp = client.get(f"/tasks/{task_id}")
    assert resp.status_code == 200
    assert resp.json()["title"] == "Get me"


def test_get_task_not_found():
    resp = client.get("/tasks/nonexistent_id")
    assert resp.status_code == 404


# ── PATCH /tasks/{task_id} ───────────────────────────────────────

def test_update_task():
    create = client.post("/tasks", json={"title": "Update me"})
    task_id = create.json()["id"]
    resp = client.patch(f"/tasks/{task_id}", json={"status": "in_progress"})
    assert resp.status_code == 200
    assert resp.json()["status"] == "in_progress"


def test_update_task_not_found():
    resp = client.patch("/tasks/nonexistent_id", json={"status": "done"})
    assert resp.status_code == 404


# ── PATCH /tasks/{task_id}/move ──────────────────────────────────

def test_move_task():
    create = client.post("/tasks", json={"title": "Move me"})
    task_id = create.json()["id"]
    resp = client.patch(f"/tasks/{task_id}/move", json={"status": "done"})
    assert resp.status_code == 200
    assert resp.json()["status"] == "done"


def test_move_task_not_found():
    resp = client.patch("/tasks/nonexistent_id/move", json={"status": "done"})
    assert resp.status_code == 404


# ── DELETE /tasks/{task_id} ──────────────────────────────────────

def test_delete_task():
    create = client.post("/tasks", json={"title": "Delete me"})
    task_id = create.json()["id"]
    resp = client.delete(f"/tasks/{task_id}")
    assert resp.status_code == 204
    # Verify gone
    assert client.get(f"/tasks/{task_id}").status_code == 404


def test_delete_task_not_found():
    resp = client.delete("/tasks/nonexistent_id")
    assert resp.status_code == 404


# ── GET /tasks/stats ─────────────────────────────────────────────

def test_get_stats():
    resp = client.get("/tasks/stats")
    assert resp.status_code == 200
    data = resp.json()
    assert "total_tasks" in data
    assert "streak_days" in data


# ── GET /tasks/today ─────────────────────────────────────────────

def test_get_today():
    resp = client.get("/tasks/today")
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)
