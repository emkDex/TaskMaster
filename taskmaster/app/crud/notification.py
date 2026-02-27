"""
Notification CRUD operations.
"""
from __future__ import annotations

import uuid

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.crud.base import CRUDBase
from app.models.notification import Notification
from app.schemas.notification import NotificationRead


class CRUDNotification(CRUDBase[Notification, NotificationRead, NotificationRead]):

    async def create_notification(
        self,
        db: AsyncSession,
        *,
        user_id: uuid.UUID,
        message: str,
        type: str,
        reference_id: uuid.UUID | None = None,
    ) -> Notification:
        notification = Notification(
            user_id=user_id,
            message=message,
            type=type,
            reference_id=reference_id,
        )
        db.add(notification)
        await db.flush()
        await db.refresh(notification)
        return notification

    async def list_by_user(
        self,
        db: AsyncSession,
        *,
        user_id: uuid.UUID,
        skip: int = 0,
        limit: int = 50,
        unread_only: bool = False,
    ) -> tuple[list[Notification], int]:
        query = select(Notification).where(Notification.user_id == user_id)
        count_query = (
            select(func.count())
            .select_from(Notification)
            .where(Notification.user_id == user_id)
        )

        if unread_only:
            query = query.where(Notification.is_read.is_(False))
            count_query = count_query.where(Notification.is_read.is_(False))

        total_result = await db.execute(count_query)
        total = total_result.scalar_one()

        result = await db.execute(
            query.order_by(Notification.created_at.desc()).offset(skip).limit(limit)
        )
        return list(result.scalars().all()), total

    async def mark_as_read(
        self, db: AsyncSession, *, notification_id: uuid.UUID, user_id: uuid.UUID
    ) -> Notification | None:
        notification = await db.execute(
            select(Notification).where(
                Notification.id == notification_id,
                Notification.user_id == user_id,
            )
        )
        obj = notification.scalar_one_or_none()
        if obj is None:
            return None
        obj.is_read = True
        db.add(obj)
        await db.flush()
        await db.refresh(obj)
        return obj

    async def mark_all_read(
        self, db: AsyncSession, *, user_id: uuid.UUID
    ) -> int:
        """Mark all unread notifications for a user as read. Returns count updated."""
        result = await db.execute(
            update(Notification)
            .where(
                Notification.user_id == user_id,
                Notification.is_read.is_(False),
            )
            .values(is_read=True)
        )
        return result.rowcount  # type: ignore[return-value]

    async def count_unread(self, db: AsyncSession, *, user_id: uuid.UUID) -> int:
        result = await db.execute(
            select(func.count())
            .select_from(Notification)
            .where(Notification.user_id == user_id, Notification.is_read.is_(False))
        )
        return result.scalar_one()


crud_notification = CRUDNotification(Notification)
