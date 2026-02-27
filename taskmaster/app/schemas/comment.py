"""
Comment Pydantic schemas.
"""
from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, Field

from app.schemas.user import UserReadPublic


class CommentCreate(BaseModel):
    content: str = Field(min_length=1, max_length=10000)


class CommentUpdate(BaseModel):
    content: str = Field(min_length=1, max_length=10000)


class CommentRead(BaseModel):
    id: uuid.UUID
    content: str
    task_id: uuid.UUID
    author_id: uuid.UUID
    created_at: datetime
    updated_at: datetime
    author: UserReadPublic | None = None

    model_config = {"from_attributes": True}
