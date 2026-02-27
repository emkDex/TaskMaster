"""
Attachment Pydantic schemas.
"""
from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel

from app.schemas.user import UserReadPublic


class AttachmentRead(BaseModel):
    id: uuid.UUID
    filename: str
    file_url: str
    file_size: int
    mime_type: str
    task_id: uuid.UUID
    uploaded_by: uuid.UUID
    created_at: datetime
    uploader: UserReadPublic | None = None

    model_config = {"from_attributes": True}
