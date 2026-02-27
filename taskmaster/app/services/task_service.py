"""
Task business logic service.
Enforces ownership, team membership, and fires notifications/activity logs.
"""
from __future__ import annotations

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ForbiddenException, NotFoundException
from app.crud.task import crud_task
from app.crud.team import crud_team
from app.models.task import Task
from app.models.user import User
from app.schemas.task import TaskCreate, TaskFilter, TaskUpdate
from app.services.activity_service import activity_service
from app.services.notification_service import notification_service


class TaskService:

    async def create_task(
        self,
        db: AsyncSession,
        *,
        task_in: TaskCreate,
        current_user: User,
    ) -> Task:
        """
        Create a task.
        If team_id is provided, validates the user is a member of that team.
        Fires a notification to the assignee if different from the creator.
        """
        if task_in.team_id is not None:
            member = await crud_team.get_member(
                db, team_id=task_in.team_id, user_id=current_user.id
            )
            if member is None and current_user.role != "admin":
                raise ForbiddenException(
                    "You must be a member of the team to create tasks for it"
                )

        task = await crud_task.create_task(
            db, obj_in=task_in, owner_id=current_user.id
        )

        await activity_service.log(
            db,
            user_id=current_user.id,
            action="task_created",
            entity_type="task",
            entity_id=task.id,
            meta={"title": task.title, "status": task.status, "priority": task.priority},
        )

        # Notify assignee if different from creator
        if task.assigned_to_id and task.assigned_to_id != current_user.id:
            await notification_service.notify_task_assigned(
                db,
                assignee_id=task.assigned_to_id,
                task_id=task.id,
                task_title=task.title,
                assigner_name=current_user.username,
            )

        return task

    async def get_task(
        self,
        db: AsyncSession,
        *,
        task_id: uuid.UUID,
        current_user: User,
    ) -> Task:
        """Fetch a task, enforcing visibility rules."""
        task = await crud_task.get_with_relations(db, task_id)
        if task is None:
            raise NotFoundException("Task", str(task_id))

        await self._assert_can_view(db, task=task, user=current_user)
        return task

    async def update_task(
        self,
        db: AsyncSession,
        *,
        task_id: uuid.UUID,
        task_in: TaskUpdate,
        current_user: User,
    ) -> Task:
        """Update a task. Only owner, team manager, or admin may update."""
        task = await crud_task.get_with_relations(db, task_id)
        if task is None:
            raise NotFoundException("Task", str(task_id))

        await self._assert_can_modify(db, task=task, user=current_user)

        old_assignee = task.assigned_to_id
        updated = await crud_task.update(db, db_obj=task, obj_in=task_in)

        await activity_service.log(
            db,
            user_id=current_user.id,
            action="task_updated",
            entity_type="task",
            entity_id=task.id,
            meta=task_in.model_dump(exclude_unset=True),
        )

        # Notify new assignee
        new_assignee = task_in.assigned_to_id
        if (
            new_assignee is not None
            and new_assignee != old_assignee
            and new_assignee != current_user.id
        ):
            await notification_service.notify_task_assigned(
                db,
                assignee_id=new_assignee,
                task_id=task.id,
                task_title=task.title,
                assigner_name=current_user.username,
            )

        # Notify owner if someone else updated their task
        if task.owner_id != current_user.id:
            await notification_service.notify_task_updated(
                db,
                user_id=task.owner_id,
                task_id=task.id,
                task_title=task.title,
                updater_name=current_user.username,
            )

        return updated

    async def delete_task(
        self,
        db: AsyncSession,
        *,
        task_id: uuid.UUID,
        current_user: User,
    ) -> Task:
        """Soft-delete (archive) a task."""
        task = await crud_task.get_with_relations(db, task_id)
        if task is None:
            raise NotFoundException("Task", str(task_id))

        await self._assert_can_modify(db, task=task, user=current_user)

        archived = await crud_task.archive(db, task=task)

        await activity_service.log(
            db,
            user_id=current_user.id,
            action="task_archived",
            entity_type="task",
            entity_id=task.id,
        )

        return archived

    async def list_tasks(
        self,
        db: AsyncSession,
        *,
        filters: TaskFilter,
        current_user: User,
    ) -> tuple[list[Task], int]:
        """List tasks visible to the current user with filters applied."""
        if current_user.role == "admin":
            # Admins see all tasks
            return await crud_task.list_with_filters(db, filters=filters)

        team_ids = await crud_team.get_user_team_ids(db, user_id=current_user.id)
        return await crud_task.list_with_filters(
            db,
            filters=filters,
            owner_id=current_user.id,
            team_ids=team_ids,
        )

    async def assign_task(
        self,
        db: AsyncSession,
        *,
        task_id: uuid.UUID,
        assignee_id: uuid.UUID,
        current_user: User,
    ) -> Task:
        """Reassign a task to a different user."""
        task = await crud_task.get_with_relations(db, task_id)
        if task is None:
            raise NotFoundException("Task", str(task_id))

        await self._assert_can_modify(db, task=task, user=current_user)

        updated = await crud_task.update(
            db, db_obj=task, obj_in={"assigned_to_id": assignee_id}
        )

        if assignee_id != current_user.id:
            await notification_service.notify_task_assigned(
                db,
                assignee_id=assignee_id,
                task_id=task.id,
                task_title=task.title,
                assigner_name=current_user.username,
            )

        await activity_service.log(
            db,
            user_id=current_user.id,
            action="task_assigned",
            entity_type="task",
            entity_id=task.id,
            meta={"assigned_to_id": str(assignee_id)},
        )

        return updated

    # ── Private helpers ───────────────────────────────────────────────────────

    async def _assert_can_view(
        self, db: AsyncSession, *, task: Task, user: User
    ) -> None:
        if user.role == "admin":
            return
        if task.owner_id == user.id or task.assigned_to_id == user.id:
            return
        if task.team_id is not None:
            member = await crud_team.get_member(
                db, team_id=task.team_id, user_id=user.id
            )
            if member is not None:
                return
        raise ForbiddenException("You do not have access to this task")

    async def _assert_can_modify(
        self, db: AsyncSession, *, task: Task, user: User
    ) -> None:
        if user.role == "admin":
            return
        if task.owner_id == user.id:
            return
        if task.team_id is not None:
            member = await crud_team.get_member(
                db, team_id=task.team_id, user_id=user.id
            )
            if member is not None and member.role == "manager":
                return
        raise ForbiddenException(
            "Only the task owner, team manager, or admin can modify this task"
        )


task_service = TaskService()
