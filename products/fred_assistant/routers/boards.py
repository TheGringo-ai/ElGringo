from fastapi import APIRouter, HTTPException

from products.fred_assistant.models import BoardOut, BoardCreate
from products.fred_assistant.services import task_service

router = APIRouter(prefix="/boards", tags=["boards"])


@router.get("", response_model=list[BoardOut])
async def list_boards():
    return task_service.list_boards()


@router.get("/{board_id}", response_model=BoardOut)
async def get_board(board_id: str):
    board = task_service.get_board(board_id)
    if not board:
        raise HTTPException(404, "Board not found")
    return board


@router.post("", response_model=BoardOut, status_code=201)
async def create_board(data: BoardCreate):
    return task_service.create_board(data.name, data.icon, data.color, data.columns)
