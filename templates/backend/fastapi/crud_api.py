"""
FastAPI CRUD API Template
=========================
Complete REST API with Pydantic models, validation, and error handling.

Usage:
    1. Copy this template
    2. Replace 'Item' with your model name
    3. Customize fields in the Pydantic models
    4. Run with: uvicorn app:app --reload
"""

from fastapi import FastAPI, HTTPException, Query, Path, Depends
from pydantic import BaseModel, Field, validator
from typing import List, Optional, Dict, Any
from datetime import datetime
from enum import Enum
import uuid

app = FastAPI(
    title="API Template",
    description="Production-ready CRUD API",
    version="1.0.0"
)

# ============================================================================
# MODELS - Customize these for your domain
# ============================================================================

class ItemStatus(str, Enum):
    DRAFT = "draft"
    ACTIVE = "active"
    ARCHIVED = "archived"

class ItemBase(BaseModel):
    """Base model with shared fields"""
    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    tags: List[str] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)

class ItemCreate(ItemBase):
    """Model for creating items"""
    pass

class ItemUpdate(BaseModel):
    """Model for updating items (all fields optional)"""
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    status: Optional[ItemStatus] = None
    tags: Optional[List[str]] = None
    metadata: Optional[Dict[str, Any]] = None

class Item(ItemBase):
    """Complete item model with all fields"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    status: ItemStatus = ItemStatus.DRAFT
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        from_attributes = True

# ============================================================================
# STORAGE - Replace with database in production
# ============================================================================

class Storage:
    def __init__(self):
        self.items: Dict[str, Item] = {}

    def create(self, data: ItemCreate) -> Item:
        item = Item(**data.model_dump())
        self.items[item.id] = item
        return item

    def get(self, id: str) -> Optional[Item]:
        return self.items.get(id)

    def list(self, skip: int = 0, limit: int = 100,
             status: Optional[ItemStatus] = None,
             tag: Optional[str] = None) -> List[Item]:
        items = list(self.items.values())
        if status:
            items = [i for i in items if i.status == status]
        if tag:
            items = [i for i in items if tag in i.tags]
        return items[skip:skip + limit]

    def update(self, id: str, data: ItemUpdate) -> Optional[Item]:
        if id not in self.items:
            return None
        item = self.items[id]
        update_data = data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(item, field, value)
        item.updated_at = datetime.utcnow()
        return item

    def delete(self, id: str) -> bool:
        if id in self.items:
            del self.items[id]
            return True
        return False

    def count(self) -> int:
        return len(self.items)

storage = Storage()

# ============================================================================
# API ENDPOINTS
# ============================================================================

@app.post("/items", response_model=Item, status_code=201)
async def create_item(data: ItemCreate):
    """Create a new item"""
    return storage.create(data)

@app.get("/items", response_model=List[Item])
async def list_items(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    status: Optional[ItemStatus] = None,
    tag: Optional[str] = None
):
    """List items with optional filtering"""
    return storage.list(skip=skip, limit=limit, status=status, tag=tag)

@app.get("/items/{id}", response_model=Item)
async def get_item(id: str = Path(...)):
    """Get a specific item by ID"""
    item = storage.get(id)
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    return item

@app.put("/items/{id}", response_model=Item)
async def update_item(id: str, data: ItemUpdate):
    """Update an existing item"""
    item = storage.update(id, data)
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    return item

@app.delete("/items/{id}", status_code=204)
async def delete_item(id: str):
    """Delete an item"""
    if not storage.delete(id):
        raise HTTPException(status_code=404, detail="Item not found")

@app.post("/items/{id}/archive", response_model=Item)
async def archive_item(id: str):
    """Archive an item"""
    item = storage.update(id, ItemUpdate(status=ItemStatus.ARCHIVED))
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    return item

@app.get("/stats")
async def get_stats():
    """Get storage statistics"""
    return {"total_items": storage.count()}

# ============================================================================
# HEALTH CHECK
# ============================================================================

@app.get("/health")
async def health_check():
    return {"status": "healthy", "timestamp": datetime.utcnow().isoformat()}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
