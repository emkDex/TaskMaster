"""
Task Pydantic schemas.
Includes create/update/read variants plus a filter schema for list endpoints.
"""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

from app.schemas.user import UserReadPublic

TaskStatus = Literal["pending", "in_progress", "completed", "cancelled"]
TaskPriority = Literal["low", "medium", "high", "critical"]


# ── Create ────────────────────────────────────────────────────────────────────

class TaskCreate(BaseModel):
    title: str = Field(min_length=1, max_length=500)
    description: str | None = Field(default=None, max_length=10000)
    status: TaskStatus = "pending"
    priority: TaskPriority = "medium"
    due_date: datetime | None = None
    assigned_to_id: uuid.UUID | None = None
    team_id: uuid.UUID | None = None
    tags: list[str] = Field(default_factory=list, max_length=20)


# ── Update ────────────────────────────────────────────────────────────────────

class TaskUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=500)
    description: str | None = None
    status: TaskStatus | None = None
    priority: TaskPriority | None = None
    due_date: datetime | None = None
    assigned_to_id: uuid.UUID | None = None
    team_id: uuid.UUID | None = None
    tags: list[str] | None = None


# ── Assign ────────────────────────────────────────────────────────────────────

class TaskAssign(BaseModel):
    assigned_to_id: uuid.UUID


# ── Read ──────────────────────────────────────────────────────────────────────

class TaskRead(BaseModel):
    id: uuid.UUID
    title: str
    description: str | None
    status: str
    priority: str
    due_date: datetime | None
    owner_id: uuid.UUID
    assigned_to_id: uuid.UUID | None
    team_id: uuid.UUID | None
    tags: list[str] | None
    is_archived: bool
    created_at: datetime
    updated_at: datetime
    owner: UserReadPublic | None = None
    assignee: UserReadPublic | None = None

    model_config = {"from_attributes": True}


# ── Filter ────────────────────────────────────────────────────────────────────

class TaskFilter(BaseModel):
    """Query parameters for filtering task list endpoints."""

    status: TaskStatus | None = None
    priority: TaskPriority | None = None
    assigned_to_id: uuid.UUID | None = None
    team_id: uuid.UUID | None = None
    is_archived: bool = False
    due_date_from: datetime | None = None
    due_date_to: datetime | None = None
    search: str | None = Field(default=None, max_length=200)
    page: int = Field(default=1, ge=1)
    size: int = Field(default=20, ge=1, le=100)
