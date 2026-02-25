"""Projects & Git router — browse projects from GitHub or local directory."""

import json

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import FileResponse, StreamingResponse
from products.fred_assistant.models import (
    FileWriteRequest, FileCreateRequest, FileRenameRequest,
    ProjectChatRequest, ProjectTasksRequest,
    ProjectNoteCreate, ProjectNoteUpdate,
)
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


# ── AI Chat & Task Generation ────────────────────────────────────────


@router.post("/{project_name}/chat")
async def project_chat(project_name: str, body: ProjectChatRequest):
    """Stream an AI response about a project."""
    async def generate():
        async for event in projects_service.stream_project_chat(
            body.message, project_name, body.context,
        ):
            event_type = event.get("type", "token")
            event_data = event.get("data", "")
            if event_type == "done":
                yield f"data: {json.dumps({'token': '', 'done': True})}\n\n"
            elif event_type == "tasks_created":
                yield f"data: {json.dumps({'tasks_created': event_data, 'done': False})}\n\n"
            else:
                yield f"data: {json.dumps({'token': event_data, 'done': False})}\n\n"

    return StreamingResponse(generate(), media_type="text/event-stream")


@router.post("/{project_name}/generate-tasks")
async def generate_tasks(project_name: str, body: ProjectTasksRequest):
    """AI generates tasks for a project and creates them on boards."""
    tasks = await projects_service.generate_project_tasks(
        project_name, body.instructions, body.board_id,
    )
    return {"tasks": tasks, "count": len(tasks), "project": project_name}


# ── File Browser ─────────────────────────────────────────────────────


@router.get("/{project_name}/files")
def list_files(project_name: str, path: str = Query("")):
    try:
        result = projects_service.list_project_files(project_name, path)
    except FileNotFoundError as e:
        raise HTTPException(404, str(e))
    except PermissionError as e:
        raise HTTPException(403, str(e))
    if "error" in result:
        raise HTTPException(400, result["error"])
    return result


@router.get("/{project_name}/files/read")
def read_file(project_name: str, path: str = Query(...)):
    try:
        result = projects_service.read_project_file(project_name, path)
    except FileNotFoundError as e:
        raise HTTPException(404, str(e))
    except PermissionError as e:
        raise HTTPException(403, str(e))
    if "error" in result:
        raise HTTPException(400, result["error"])
    return result


@router.put("/{project_name}/files/write")
def write_file(project_name: str, path: str = Query(...), data: FileWriteRequest = ...):
    try:
        result = projects_service.write_project_file(project_name, path, data.content)
    except FileNotFoundError as e:
        raise HTTPException(404, str(e))
    except PermissionError as e:
        raise HTTPException(403, str(e))
    if "error" in result:
        raise HTTPException(400, result["error"])
    return result


@router.post("/{project_name}/files/create")
def create_file(project_name: str, data: FileCreateRequest):
    try:
        result = projects_service.create_project_file(project_name, data.path, data.content)
    except FileNotFoundError as e:
        raise HTTPException(404, str(e))
    except PermissionError as e:
        raise HTTPException(403, str(e))
    if "error" in result:
        raise HTTPException(400, result["error"])
    return result


@router.delete("/{project_name}/files/delete")
def delete_file(project_name: str, path: str = Query(...)):
    try:
        result = projects_service.delete_project_file(project_name, path)
    except FileNotFoundError as e:
        raise HTTPException(404, str(e))
    except PermissionError as e:
        raise HTTPException(403, str(e))
    if "error" in result:
        raise HTTPException(400, result["error"])
    return result


@router.post("/{project_name}/files/rename")
def rename_file(project_name: str, data: FileRenameRequest):
    try:
        result = projects_service.rename_project_file(project_name, data.old_path, data.new_path)
    except FileNotFoundError as e:
        raise HTTPException(404, str(e))
    except PermissionError as e:
        raise HTTPException(403, str(e))
    if "error" in result:
        raise HTTPException(400, result["error"])
    return result


@router.get("/{project_name}/export")
def export_project(project_name: str):
    try:
        result = projects_service.export_project(project_name)
    except FileNotFoundError as e:
        raise HTTPException(404, str(e))
    if "error" in result:
        raise HTTPException(400, result["error"])
    return FileResponse(
        result["archive_path"],
        filename=result["archive_name"],
        media_type="application/gzip",
    )


# ── Project Notes ─────────────────────────────────────────────────


@router.get("/{project_name}/notes")
def list_notes(project_name: str):
    return projects_service.list_project_notes(project_name)


@router.post("/{project_name}/notes")
def create_note(project_name: str, body: ProjectNoteCreate):
    note = projects_service.create_project_note(project_name, body.model_dump())
    return note


@router.post("/{project_name}/notes/generate")
async def generate_notes(project_name: str):
    note = await projects_service.generate_project_notes(project_name)
    if not note:
        raise HTTPException(404, "Project not found or generation failed")
    return note


@router.get("/{project_name}/notes/{note_id}")
def get_note(project_name: str, note_id: str):
    note = projects_service.get_project_note(note_id)
    if not note:
        raise HTTPException(404, "Note not found")
    return note


@router.patch("/{project_name}/notes/{note_id}")
def update_note(project_name: str, note_id: str, body: ProjectNoteUpdate):
    note = projects_service.update_project_note(note_id, body.model_dump(exclude_none=True))
    if not note:
        raise HTTPException(404, "Note not found")
    return note


@router.delete("/{project_name}/notes/{note_id}")
def delete_note(project_name: str, note_id: str):
    if not projects_service.delete_project_note(note_id):
        raise HTTPException(404, "Note not found")
    return {"status": "ok"}
