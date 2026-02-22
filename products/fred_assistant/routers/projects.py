"""Projects & Git router — browse local dev projects, git status, commits."""

from fastapi import APIRouter, Query
from products.fred_assistant.services import projects_service

router = APIRouter(prefix="/projects", tags=["projects"])


@router.get("")
def list_projects(path: str = Query(None, description="Custom projects directory")):
    return projects_service.list_projects(path)


@router.get("/{project_name}")
def get_project(project_name: str):
    import os
    full = os.path.join(projects_service.PROJECTS_DIR, project_name)
    if not os.path.isdir(full):
        return {"error": "Project not found"}
    return projects_service.get_project_info(full)


@router.get("/{project_name}/commits")
def get_commits(project_name: str, count: int = Query(10, ge=1, le=50)):
    import os
    full = os.path.join(projects_service.PROJECTS_DIR, project_name)
    return projects_service.get_recent_commits(full, count)


@router.get("/{project_name}/branches")
def get_branches(project_name: str):
    import os
    full = os.path.join(projects_service.PROJECTS_DIR, project_name)
    return projects_service.get_branches(full)
