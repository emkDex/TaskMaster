"""
ActivityLog Pydantic schemas.
"""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel

from app.schemas.user import UserReadPublic


class ActivityLogRead(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    action: str
    entity_type: str
    entity_id: uuid.UUID
    meta: dict[str, Any] | None
    created_at: datetime
    user: UserReadPublic | None = None

    model_config = {"from_attributes": True}
