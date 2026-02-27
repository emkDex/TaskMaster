"""
Notification Pydantic schemas.
"""
from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel


class NotificationRead(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    message: str
    type: str
    is_read: bool
    reference_id: uuid.UUID | None
    created_at: datetime

    model_config = {"from_attributes": True}
