"""Platform router — cross-service integration endpoints."""

import json
import os

from fastapi import APIRouter, Query

from products.fred_assistant.models import (
    PlatformAuditRequest,
    PlatformDocsRequest,
    PRReviewCallback,
)
from products.fred_assistant.services import platform_services, repo_intelligence_service, task_service
from products.fred_assistant.services.fred_tools import _resolve_project_path, _read_project_files
from products.fred_assistant.database import get_conn, log_activity

router = APIRouter(prefix="/platform", tags=["platform"])


@router.get("/status")
def get_platform_status():
    """Health check all platform services."""
    status = platform_services.check_all_services()
    online = sum(1 for s in status.values() if s["healthy"])
    return {"services": status, "online": online, "total": len(status)}


@router.post("/{project_name}/audit")
async def audit_project(project_name: str, body: PlatformAuditRequest = PlatformAuditRequest()):
    """Run a code audit on a project via the Code Audit service."""
    proj_path = _resolve_project_path(project_name)
    if not proj_path:
        return {"error": f"Project not found: {project_name}"}

    files = _read_project_files(proj_path, max_files=5)
    if not files:
        return {"error": f"No source files found in {project_name}"}

    combined = "\n\n".join(f"# {f['path']}\n{f['content']}" for f in files)
    endpoint = "/audit/full" if body.audit_type == "full" else f"/audit/{body.audit_type}"

    result = await platform_services.call_service("code_audit", "POST", endpoint, {
        "code": combined, "language": files[0]["language"], "filename": project_name,
    })

    if "error" in result:
        return {"error": result["error"]}

    result_id = platform_services.store_service_result("code_audit", body.audit_type, project_name, result)
    return {**result, "result_id": result_id, "project_name": project_name}


@router.post("/{project_name}/tests")
async def generate_project_tests(project_name: str):
    """Generate or analyze tests for a project via the Test Generator service."""
    proj_path = _resolve_project_path(project_name)
    if not proj_path:
        return {"error": f"Project not found: {project_name}"}

    files = _read_project_files(proj_path, max_files=5)
    if not files:
        return {"error": f"No source files found in {project_name}"}

    combined = "\n\n".join(f"# {f['path']}\n{f['content']}" for f in files)
    result = await platform_services.call_service("test_gen", "POST", "/tests/generate", {
        "code": combined, "language": files[0]["language"], "filename": project_name,
    })

    if "error" in result:
        return {"error": result["error"]}

    result_id = platform_services.store_service_result("test_gen", "generate", project_name, result)
    return {**result, "result_id": result_id, "project_name": project_name}


@router.post("/{project_name}/docs")
async def generate_project_docs(project_name: str, body: PlatformDocsRequest = PlatformDocsRequest()):
    """Generate documentation for a project via the Doc Generator service."""
    proj_path = _resolve_project_path(project_name)
    if not proj_path:
        return {"error": f"Project not found: {project_name}"}

    files = _read_project_files(proj_path, max_files=8)
    if not files:
        return {"error": f"No source files found in {project_name}"}

    file_entries = [{"path": f["path"], "content": f["content"]} for f in files]
    endpoint = f"/docs/{body.doc_type}"
    data = {"project_name": project_name, "files": file_entries}

    result = await platform_services.call_service("doc_gen", "POST", endpoint, data)

    if "error" in result:
        return {"error": result["error"]}

    result_id = platform_services.store_service_result("doc_gen", body.doc_type, project_name, result)
    return {**result, "result_id": result_id, "project_name": project_name}


@router.post("/{project_name}/full-review")
async def full_project_review(project_name: str):
    """Run a full integrated review: repo analysis + code audit + test analysis + create tasks."""
    from products.fred_assistant.services.fred_tools import _exec_full_project_review
    result = await _exec_full_project_review({"name": project_name})
    return result


@router.get("/results")
def list_service_results(
    project_name: str = Query(None),
    service: str = Query(None),
    limit: int = Query(20, ge=1, le=100),
):
    """List stored service results."""
    return platform_services.get_recent_results(
        service=service, project_name=project_name, limit=limit,
    )


@router.post("/pr-review-callback")
def pr_review_callback(body: PRReviewCallback):
    """Receive PR review results from the PR Bot."""
    result_id = platform_services.store_service_result(
        "pr_review",
        body.verdict,
        body.repo,
        {
            "pr_number": body.pr_number,
            "verdict": body.verdict,
            "summary": body.summary,
            "confidence": body.confidence,
            "agents_used": body.agents_used,
            "total_time": body.review_time,
        },
    )

    # Create task for REQUEST_CHANGES verdicts
    tasks_created = 0
    if body.verdict == "REQUEST_CHANGES":
        task_service.create_task({
            "title": f"Fix PR #{body.pr_number} review issues ({body.repo})",
            "description": f"PR review requested changes:\n{body.summary[:500]}",
            "board_id": "work",
            "priority": 2,
        })
        tasks_created = 1

    log_activity("pr_review_received", "pr_review", result_id, {
        "repo": body.repo, "pr_number": body.pr_number, "verdict": body.verdict,
    })

    return {
        "status": "stored",
        "result_id": result_id,
        "tasks_created": tasks_created,
    }
