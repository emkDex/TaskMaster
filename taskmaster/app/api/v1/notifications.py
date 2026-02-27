"""
Notification routes.
"""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Query, status

from app.core.dependencies import CurrentUser, DBSession
from app.core.exceptions import NotFoundException
from app.crud.notification import crud_notification
from app.schemas.notification import NotificationRead
from app.schemas.pagination import PaginatedResponse

router = APIRouter(prefix="/notifications", tags=["Notifications"])


@router.get(
    "/",
    response_model=PaginatedResponse[NotificationRead],
    summary="List my notifications",
)
async def list_notifications(
    current_user: CurrentUser,
    db: DBSession,
    page: int = Query(default=1, ge=1),
    size: int = Query(default=20, ge=1, le=100),
    unread_only: bool = Query(default=False),
) -> PaginatedResponse[NotificationRead]:
    notifications, total = await crud_notification.list_by_user(
        db,
        user_id=current_user.id,
        skip=(page - 1) * size,
        limit=size,
        unread_only=unread_only,
    )
    return PaginatedResponse(
        items=[NotificationRead.model_validate(n) for n in notifications],
        total=total,
        page=page,
        size=size,
    )


@router.put(
    "/read-all",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Mark all notifications as read",
)
async def mark_all_read(
    current_user: CurrentUser,
    db: DBSession,
) -> None:
    await crud_notification.mark_all_read(db, user_id=current_user.id)


@router.put(
    "/{notification_id}/read",
    response_model=NotificationRead,
    summary="Mark a notification as read",
)
async def mark_as_read(
    notification_id: uuid.UUID,
    current_user: CurrentUser,
    db: DBSession,
) -> NotificationRead:
    notification = await crud_notification.mark_as_read(
        db, notification_id=notification_id, user_id=current_user.id
    )
    if notification is None:
        raise NotFoundException("Notification", str(notification_id))
    return NotificationRead.model_validate(notification)
