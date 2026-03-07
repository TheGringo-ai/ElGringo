"""Tests for platform router — cross-service integration endpoints."""

import os
from unittest.mock import patch, AsyncMock

os.environ["FRED_DB_PATH"] = ":memory:"

from fastapi.testclient import TestClient

from products.fred_assistant.server import app
from products.fred_assistant.services import platform_services, task_service

client = TestClient(app)


# ── GET /platform/status ─────────────────────────────────────────

def test_get_platform_status():
    mock_status = {
        "code_audit": {"healthy": True, "port": 8081, "label": "Code Audit"},
        "test_gen": {"healthy": False, "port": 8082, "label": "Test Generator"},
    }
    with patch.object(platform_services, "check_all_services", return_value=mock_status):
        resp = client.get("/platform/status")
    assert resp.status_code == 200
    data = resp.json()
    assert data["online"] == 1
    assert data["total"] == 2
    assert "code_audit" in data["services"]


# ── POST /platform/{project}/audit ──────────────────────────────

def test_audit_project_not_found():
    with patch("products.fred_assistant.routers.platform._resolve_project_path", return_value=None):
        resp = client.post("/platform/nonexistent/audit")
    assert resp.status_code == 200
    assert "error" in resp.json()


def test_audit_project_no_files():
    with patch("products.fred_assistant.routers.platform._resolve_project_path", return_value="/some/path"), \
         patch("products.fred_assistant.routers.platform._read_project_files", return_value=[]):
        resp = client.post("/platform/myproject/audit")
    assert resp.status_code == 200
    assert "error" in resp.json()


def test_audit_project_success():
    mock_files = [{"path": "main.py", "content": "print('hello')", "language": "python"}]
    mock_result = {"score": 85, "issues": []}

    with patch("products.fred_assistant.routers.platform._resolve_project_path", return_value="/some/path"), \
         patch("products.fred_assistant.routers.platform._read_project_files", return_value=mock_files), \
         patch.object(platform_services, "call_service", new_callable=AsyncMock, return_value=mock_result), \
         patch.object(platform_services, "store_service_result", return_value="result-123"):
        resp = client.post("/platform/myproject/audit", json={"audit_type": "full"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["score"] == 85
    assert data["result_id"] == "result-123"


def test_audit_project_service_error():
    mock_files = [{"path": "main.py", "content": "code", "language": "python"}]

    with patch("products.fred_assistant.routers.platform._resolve_project_path", return_value="/some/path"), \
         patch("products.fred_assistant.routers.platform._read_project_files", return_value=mock_files), \
         patch.object(platform_services, "call_service", new_callable=AsyncMock, return_value={"error": "Service down"}):
        resp = client.post("/platform/myproject/audit")
    assert resp.status_code == 200
    assert resp.json()["error"] == "Service down"


# ── POST /platform/{project}/tests ──────────────────────────────

def test_generate_tests_success():
    mock_files = [{"path": "app.py", "content": "def foo(): pass", "language": "python"}]
    mock_result = {"tests": "def test_foo(): ..."}

    with patch("products.fred_assistant.routers.platform._resolve_project_path", return_value="/some/path"), \
         patch("products.fred_assistant.routers.platform._read_project_files", return_value=mock_files), \
         patch.object(platform_services, "call_service", new_callable=AsyncMock, return_value=mock_result), \
         patch.object(platform_services, "store_service_result", return_value="result-456"):
        resp = client.post("/platform/myproject/tests")
    assert resp.status_code == 200
    data = resp.json()
    assert data["result_id"] == "result-456"


# ── POST /platform/{project}/docs ───────────────────────────────

def test_generate_docs_success():
    mock_files = [{"path": "main.py", "content": "code", "language": "python"}]
    mock_result = {"content": "# README\n..."}

    with patch("products.fred_assistant.routers.platform._resolve_project_path", return_value="/some/path"), \
         patch("products.fred_assistant.routers.platform._read_project_files", return_value=mock_files), \
         patch.object(platform_services, "call_service", new_callable=AsyncMock, return_value=mock_result), \
         patch.object(platform_services, "store_service_result", return_value="result-789"):
        resp = client.post("/platform/myproject/docs", json={"doc_type": "readme"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["result_id"] == "result-789"


# ── GET /platform/results ───────────────────────────────────────

def test_list_results():
    mock_results = [{"id": "r1", "service": "code_audit", "action": "full"}]
    with patch.object(platform_services, "get_recent_results", return_value=mock_results):
        resp = client.get("/platform/results")
    assert resp.status_code == 200
    assert len(resp.json()) == 1


def test_list_results_with_filters():
    with patch.object(platform_services, "get_recent_results", return_value=[]) as mock_get:
        resp = client.get("/platform/results", params={"service": "test_gen", "project_name": "myproj", "limit": 5})
    assert resp.status_code == 200
    mock_get.assert_called_once_with(service="test_gen", project_name="myproj", limit=5)


# ── POST /platform/pr-review-callback ───────────────────────────

def test_pr_review_callback_approve():
    with patch.object(platform_services, "store_service_result", return_value="pr-result-1"):
        resp = client.post("/platform/pr-review-callback", json={
            "repo": "TheGringo-ai/ManagersDashboard",
            "pr_number": 42,
            "verdict": "APPROVE",
            "summary": "Looks good!",
            "confidence": 0.95,
            "agents_used": ["security", "quality"],
            "review_time": 12.5,
        })
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "stored"
    assert data["tasks_created"] == 0


def test_pr_review_callback_request_changes():
    with patch.object(platform_services, "store_service_result", return_value="pr-result-2"):
        resp = client.post("/platform/pr-review-callback", json={
            "repo": "TheGringo-ai/ManagersDashboard",
            "pr_number": 43,
            "verdict": "REQUEST_CHANGES",
            "summary": "Fix the SQL injection vulnerability",
            "confidence": 0.9,
        })
    assert resp.status_code == 200
    data = resp.json()
    assert data["tasks_created"] == 1

    # Verify the task was created
    tasks = task_service.list_tasks()
    fix_tasks = [t for t in tasks if "PR #43" in t["title"]]
    assert len(fix_tasks) >= 1
    assert fix_tasks[0]["priority"] == 2
