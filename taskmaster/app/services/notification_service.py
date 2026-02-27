"""
Notification fan-out service.
Creates DB notification records and pushes real-time messages via WebSocket.
"""
from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.crud.notification import crud_notification
from app.services.websocket_service import ws_manager


class NotificationService:

    async def notify_user(
        self,
        db: AsyncSession,
        *,
        user_id: uuid.UUID,
        message: str,
        type: str,
        reference_id: uuid.UUID | None = None,
    ) -> None:
        """
        Persist a notification to the database and push it via WebSocket
        if the user is currently connected.
        """
        notification = await crud_notification.create_notification(
            db,
            user_id=user_id,
            message=message,
            type=type,
            reference_id=reference_id,
        )

        # Push real-time if connected
        if ws_manager.is_connected(str(user_id)):
            payload: dict[str, Any] = {
                "type": "notification",
                "data": {
                    "id": str(notification.id),
                    "message": message,
                    "notification_type": type,
                    "reference_id": str(reference_id) if reference_id else None,
                    "is_read": False,
                    "created_at": notification.created_at.isoformat(),
                },
            }
            await ws_manager.send_personal_message(str(user_id), payload)

    async def notify_task_assigned(
        self,
        db: AsyncSession,
        *,
        assignee_id: uuid.UUID,
        task_id: uuid.UUID,
        task_title: str,
        assigner_name: str,
    ) -> None:
        await self.notify_user(
            db,
            user_id=assignee_id,
            message=f"{assigner_name} assigned you to task: {task_title!r}",
            type="task_assigned",
            reference_id=task_id,
        )

    async def notify_task_updated(
        self,
        db: AsyncSession,
        *,
        user_id: uuid.UUID,
        task_id: uuid.UUID,
        task_title: str,
        updater_name: str,
    ) -> None:
        await self.notify_user(
            db,
            user_id=user_id,
            message=f"{updater_name} updated task: {task_title!r}",
            type="task_updated",
            reference_id=task_id,
        )

    async def notify_comment_added(
        self,
        db: AsyncSession,
        *,
        task_owner_id: uuid.UUID,
        task_id: uuid.UUID,
        task_title: str,
        commenter_name: str,
    ) -> None:
        await self.notify_user(
            db,
            user_id=task_owner_id,
            message=f"{commenter_name} commented on task: {task_title!r}",
            type="comment_added",
            reference_id=task_id,
        )

    async def notify_team_invite(
        self,
        db: AsyncSession,
        *,
        user_id: uuid.UUID,
        team_id: uuid.UUID,
        team_name: str,
        inviter_name: str,
    ) -> None:
        await self.notify_user(
            db,
            user_id=user_id,
            message=f"{inviter_name} added you to team: {team_name!r}",
            type="team_invite",
            reference_id=team_id,
        )

    async def notify_team_removed(
        self,
        db: AsyncSession,
        *,
        user_id: uuid.UUID,
        team_id: uuid.UUID,
        team_name: str,
    ) -> None:
        await self.notify_user(
            db,
            user_id=user_id,
            message=f"You have been removed from team: {team_name!r}",
            type="team_removed",
            reference_id=team_id,
        )


notification_service = NotificationService()
