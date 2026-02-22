from fastapi import APIRouter, HTTPException, Query
from typing import Optional

from products.fred_assistant.models import MemoryOut, MemoryCreate
from products.fred_assistant.services import memory_service

router = APIRouter(prefix="/memory", tags=["memory"])


@router.get("", response_model=list[MemoryOut])
async def list_memories(category: Optional[str] = Query(None)):
    return memory_service.list_memories(category=category)


@router.get("/categories")
async def get_categories():
    return memory_service.get_categories()


@router.get("/search", response_model=list[MemoryOut])
async def search_memories(q: str = Query(...)):
    return memory_service.search_memories(q)


@router.post("", response_model=MemoryOut, status_code=201)
async def remember(data: MemoryCreate):
    return memory_service.remember(
        category=data.category,
        key=data.key,
        value=data.value,
        context=data.context,
        importance=data.importance,
    )


@router.delete("/{memory_id}", status_code=204)
async def forget(memory_id: str):
    mem = memory_service.get_memory(memory_id)
    if not mem:
        raise HTTPException(404, "Memory not found")
    memory_service.forget(memory_id)
