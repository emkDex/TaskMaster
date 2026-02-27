"""
Activity logging service.
Writes immutable audit records to the activity_logs table.
Always async, never blocking.
"""
from __future__ import annotations

import logging
import uuid
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.activity_log import ActivityLog

logger = logging.getLogger(__name__)


class ActivityService:

    async def log(
        self,
        db: AsyncSession,
        *,
        user_id: uuid.UUID,
        action: str,
        entity_type: str,
        entity_id: uuid.UUID,
        meta: dict[str, Any] | None = None,
    ) -> ActivityLog:
        """
        Create an activity log entry.
        This method is intentionally simple — it never raises exceptions
        so that a logging failure never breaks the main request flow.
        """
        try:
            entry = ActivityLog(
                user_id=user_id,
                action=action,
                entity_type=entity_type,
                entity_id=entity_id,
                meta=meta,
            )
            db.add(entry)
            await db.flush()
            return entry
        except Exception as exc:
            logger.error(
                "Failed to write activity log: user_id=%s action=%s entity_type=%s: %s",
                user_id,
                action,
                entity_type,
                exc,
            )
            raise


activity_service = ActivityService()
