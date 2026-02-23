"""Projects & Git router — browse projects from GitHub or local directory."""

from fastapi import APIRouter, Query
from products.fred_assistant.services import projects_service

router = APIRouter(prefix="/projects", tags=["projects"])


@router.get("")
def list_projects(path: str = Query(None, description="Custom projects directory")):
    return projects_service.list_projects(path)


@router.get("/{project_name}")
def get_project(project_name: str):
    project = projects_service.get_project(project_name)
    if not project:
        return {"error": "Project not found"}
    return project


@router.get("/{project_name}/commits")
def get_commits(project_name: str, count: int = Query(10, ge=1, le=50)):
    return projects_service.get_recent_commits(project_name, count)


@router.get("/{project_name}/branches")
def get_branches(project_name: str):
    return projects_service.get_branches(project_name)
