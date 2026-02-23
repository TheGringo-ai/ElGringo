"""Repo Intelligence router — deep analysis endpoints for dev projects."""

from fastapi import APIRouter, Query
from products.fred_assistant.models import RepoAnalyzeRequest, RepoTasksRequest
from products.fred_assistant.services import repo_intelligence_service as ris

router = APIRouter(prefix="/repo-intel", tags=["repo-intelligence"])


@router.post("/{project_name}/analyze")
def analyze_repo(project_name: str, body: RepoAnalyzeRequest = RepoAnalyzeRequest()):
    result = ris.analyze_repo(project_name, depth=body.depth)
    if "error" in result:
        return {"error": result["error"]}, 404
    return result


@router.get("/{project_name}/latest")
def get_latest_analysis(project_name: str):
    result = ris.get_latest_analysis(project_name)
    if not result:
        return {"error": f"No analysis found for {project_name}"}
    return result


@router.post("/{project_name}/generate-tasks")
def generate_tasks(project_name: str, body: RepoTasksRequest = RepoTasksRequest()):
    latest = ris.get_latest_analysis(project_name)
    if not latest:
        return {"error": f"No analysis found for {project_name}. Run analyze first."}
    tasks = ris.generate_tasks_from_analysis(latest["id"], create_tasks=body.create_tasks)
    return {"project_name": project_name, "analysis_id": latest["id"], "tasks": tasks, "count": len(tasks)}


@router.post("/{project_name}/review")
def review_repo(project_name: str):
    result = ris.review_repo(project_name)
    if "error" in result:
        return {"error": result["error"]}
    return result


@router.get("/analyses")
def list_analyses(project_name: str = Query(None), limit: int = Query(20, ge=1, le=100)):
    return ris.list_analyses(project_name=project_name, limit=limit)
