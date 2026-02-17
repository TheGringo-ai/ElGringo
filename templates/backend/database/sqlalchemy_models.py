"""
SQLAlchemy Models Template
==========================
Production-ready database models with relationships, mixins, and utilities.

Dependencies:
    pip install sqlalchemy asyncpg alembic

Usage:
    1. Set DATABASE_URL environment variable
    2. Customize models for your domain
    3. Run migrations with Alembic
"""

from datetime import datetime
from typing import Optional, List
from sqlalchemy import (
    Column, String, Integer, Float, Boolean, DateTime, Text,
    ForeignKey, JSON, Enum as SQLEnum, Index, UniqueConstraint
)
from sqlalchemy.orm import relationship, declarative_base, Mapped, mapped_column
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.sql import func
import enum
import uuid
import os

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+asyncpg://user:pass@localhost/db")

engine = create_async_engine(DATABASE_URL, echo=True)
async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

Base = declarative_base()

# ============================================================================
# MIXINS - Reusable model components
# ============================================================================

class TimestampMixin:
    """Adds created_at and updated_at timestamps"""
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

class SoftDeleteMixin:
    """Adds soft delete capability"""
    deleted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False)

class UUIDMixin:
    """Uses UUID as primary key"""
    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )

# ============================================================================
# ENUMS
# ============================================================================

class UserRole(enum.Enum):
    USER = "user"
    ADMIN = "admin"
    MODERATOR = "moderator"

class Status(enum.Enum):
    DRAFT = "draft"
    ACTIVE = "active"
    ARCHIVED = "archived"

# ============================================================================
# MODELS
# ============================================================================

class User(Base, UUIDMixin, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "users"

    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255))
    full_name: Mapped[Optional[str]] = mapped_column(String(255))
    role: Mapped[UserRole] = mapped_column(SQLEnum(UserRole), default=UserRole.USER)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    email_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    profile_image: Mapped[Optional[str]] = mapped_column(String(500))
    settings: Mapped[Optional[dict]] = mapped_column(JSON)

    # Relationships
    projects: Mapped[List["Project"]] = relationship(back_populates="owner")
    tasks: Mapped[List["Task"]] = relationship(back_populates="assignee")

    def __repr__(self):
        return f"<User {self.email}>"

class Project(Base, UUIDMixin, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "projects"

    name: Mapped[str] = mapped_column(String(255))
    description: Mapped[Optional[str]] = mapped_column(Text)
    status: Mapped[Status] = mapped_column(SQLEnum(Status), default=Status.DRAFT)
    owner_id: Mapped[str] = mapped_column(ForeignKey("users.id"))
    settings: Mapped[Optional[dict]] = mapped_column(JSON)
    metadata_: Mapped[Optional[dict]] = mapped_column("metadata", JSON)

    # Relationships
    owner: Mapped["User"] = relationship(back_populates="projects")
    tasks: Mapped[List["Task"]] = relationship(back_populates="project", cascade="all, delete-orphan")
    tags: Mapped[List["Tag"]] = relationship(secondary="project_tags", back_populates="projects")

    __table_args__ = (
        Index("ix_projects_owner_status", "owner_id", "status"),
    )

    def __repr__(self):
        return f"<Project {self.name}>"

class Task(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "tasks"

    title: Mapped[str] = mapped_column(String(255))
    description: Mapped[Optional[str]] = mapped_column(Text)
    status: Mapped[Status] = mapped_column(SQLEnum(Status), default=Status.DRAFT)
    priority: Mapped[int] = mapped_column(Integer, default=0)
    due_date: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id"))
    assignee_id: Mapped[Optional[str]] = mapped_column(ForeignKey("users.id"))
    order: Mapped[int] = mapped_column(Integer, default=0)

    # Relationships
    project: Mapped["Project"] = relationship(back_populates="tasks")
    assignee: Mapped[Optional["User"]] = relationship(back_populates="tasks")

    __table_args__ = (
        Index("ix_tasks_project_status", "project_id", "status"),
    )

class Tag(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "tags"

    name: Mapped[str] = mapped_column(String(50), unique=True)
    color: Mapped[Optional[str]] = mapped_column(String(7))  # Hex color

    # Relationships
    projects: Mapped[List["Project"]] = relationship(secondary="project_tags", back_populates="tags")

class ProjectTag(Base):
    """Association table for Project-Tag many-to-many"""
    __tablename__ = "project_tags"

    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id"), primary_key=True)
    tag_id: Mapped[str] = mapped_column(ForeignKey("tags.id"), primary_key=True)

# ============================================================================
# DATABASE UTILITIES
# ============================================================================

async def get_db():
    """Dependency for getting database session"""
    async with async_session() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise

async def init_db():
    """Create all tables"""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

async def drop_db():
    """Drop all tables (use with caution!)"""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

# ============================================================================
# REPOSITORY PATTERN EXAMPLE
# ============================================================================

class BaseRepository:
    """Base repository with common CRUD operations"""

    def __init__(self, session: AsyncSession, model):
        self.session = session
        self.model = model

    async def create(self, **kwargs):
        instance = self.model(**kwargs)
        self.session.add(instance)
        await self.session.flush()
        return instance

    async def get(self, id: str):
        return await self.session.get(self.model, id)

    async def delete(self, id: str):
        instance = await self.get(id)
        if instance:
            await self.session.delete(instance)
        return instance

class UserRepository(BaseRepository):
    def __init__(self, session: AsyncSession):
        super().__init__(session, User)

    async def get_by_email(self, email: str) -> Optional[User]:
        from sqlalchemy import select
        result = await self.session.execute(
            select(User).where(User.email == email)
        )
        return result.scalar_one_or_none()

if __name__ == "__main__":
    import asyncio
    asyncio.run(init_db())
    print("Database initialized!")
