"""Factory router — Build, launch & monetize apps from FredAI."""

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import FileResponse

from products.fred_assistant.models import (
    AppCreate, AppUpdate, AppGenerateRequest,
    FileWriteRequest, FileCreateRequest, FileRenameRequest,
)
from products.fred_assistant.services import factory_service

router = APIRouter(prefix="/factory", tags=["factory"])


@router.get("/apps")
def list_apps():
    return factory_service.list_apps()


@router.post("/apps")
def create_app(data: AppCreate):
    return factory_service.create_app(data.model_dump())


@router.get("/apps/{app_id}")
def get_app(app_id: str):
    app = factory_service.get_app(app_id)
    if not app:
        raise HTTPException(404, "App not found")
    return app


@router.patch("/apps/{app_id}")
def update_app(app_id: str, data: AppUpdate):
    app = factory_service.update_app(app_id, data.model_dump(exclude_unset=True))
    if not app:
        raise HTTPException(404, "App not found")
    return app


@router.post("/apps/{app_id}/generate")
async def generate_app(app_id: str, data: AppGenerateRequest = None):
    if data is None:
        data = AppGenerateRequest()
    result = await factory_service.generate_app(
        app_id, enrich=data.enrich, template=data.template
    )
    if "error" in result:
        raise HTTPException(400, result["error"])
    return result


@router.post("/apps/{app_id}/build")
async def build_app(app_id: str):
    result = await factory_service.build_app(app_id)
    if "error" in result:
        raise HTTPException(400, result["error"])
    return result


@router.post("/apps/{app_id}/deploy")
async def deploy_app(app_id: str):
    result = await factory_service.deploy_app(app_id)
    if "error" in result:
        raise HTTPException(400, result["error"])
    return result


@router.delete("/apps/{app_id}", status_code=204)
def archive_app(app_id: str):
    factory_service.archive_app(app_id)


@router.get("/apps/{app_id}/builds")
def list_builds(app_id: str):
    return factory_service.list_builds(app_id)


@router.get("/templates")
def list_templates():
    return factory_service.list_templates()


@router.get("/portfolio")
def get_portfolio():
    return factory_service.get_portfolio_summary()


# ── File Browser ─────────────────────────────────────────────────────


@router.get("/apps/{app_id}/files")
def list_files(app_id: str, path: str = Query("")):
    try:
        result = factory_service.list_files(app_id, path)
    except FileNotFoundError as e:
        raise HTTPException(404, str(e))
    except PermissionError as e:
        raise HTTPException(403, str(e))
    if "error" in result:
        raise HTTPException(400, result["error"])
    return result


@router.get("/apps/{app_id}/files/read")
def read_file(app_id: str, path: str = Query(...)):
    try:
        result = factory_service.read_file(app_id, path)
    except FileNotFoundError as e:
        raise HTTPException(404, str(e))
    except PermissionError as e:
        raise HTTPException(403, str(e))
    if "error" in result:
        raise HTTPException(400, result["error"])
    return result


@router.put("/apps/{app_id}/files/write")
def write_file(app_id: str, path: str = Query(...), data: FileWriteRequest = ...):
    try:
        result = factory_service.write_file(app_id, path, data.content)
    except FileNotFoundError as e:
        raise HTTPException(404, str(e))
    except PermissionError as e:
        raise HTTPException(403, str(e))
    if "error" in result:
        raise HTTPException(400, result["error"])
    return result


@router.post("/apps/{app_id}/files/create")
def create_file(app_id: str, data: FileCreateRequest):
    try:
        result = factory_service.create_file(app_id, data.path, data.content)
    except FileNotFoundError as e:
        raise HTTPException(404, str(e))
    except PermissionError as e:
        raise HTTPException(403, str(e))
    if "error" in result:
        raise HTTPException(400, result["error"])
    return result


@router.delete("/apps/{app_id}/files/delete")
def delete_file(app_id: str, path: str = Query(...)):
    try:
        result = factory_service.delete_file(app_id, path)
    except FileNotFoundError as e:
        raise HTTPException(404, str(e))
    except PermissionError as e:
        raise HTTPException(403, str(e))
    if "error" in result:
        raise HTTPException(400, result["error"])
    return result


@router.post("/apps/{app_id}/files/rename")
def rename_file(app_id: str, data: FileRenameRequest):
    try:
        result = factory_service.rename_file(app_id, data.old_path, data.new_path)
    except FileNotFoundError as e:
        raise HTTPException(404, str(e))
    except PermissionError as e:
        raise HTTPException(403, str(e))
    if "error" in result:
        raise HTTPException(400, result["error"])
    return result


@router.get("/apps/{app_id}/export")
def export_app(app_id: str):
    result = factory_service.export_app(app_id)
    if "error" in result:
        raise HTTPException(400, result["error"])
    return FileResponse(
        result["archive_path"],
        filename=result["archive_name"],
        media_type="application/gzip",
    )
