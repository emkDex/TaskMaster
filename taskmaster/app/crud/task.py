"""
Task CRUD operations.
Extends CRUDBase with filtering, pagination, and ownership queries.
"""
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.crud.base import CRUDBase
from app.models.task import Task
from app.schemas.task import TaskCreate, TaskFilter, TaskUpdate


class CRUDTask(CRUDBase[Task, TaskCreate, TaskUpdate]):

    async def get_with_relations(
        self, db: AsyncSession, task_id: uuid.UUID
    ) -> Task | None:
        """Fetch a task with owner and assignee eagerly loaded."""
        result = await db.execute(
            select(Task)
            .options(selectinload(Task.owner), selectinload(Task.assignee))
            .where(Task.id == task_id)
        )
        return result.scalar_one_or_none()

    async def create_task(
        self,
        db: AsyncSession,
        *,
        obj_in: TaskCreate,
        owner_id: uuid.UUID,
    ) -> Task:
        task = Task(
            title=obj_in.title,
            description=obj_in.description,
            status=obj_in.status,
            priority=obj_in.priority,
            due_date=obj_in.due_date,
            owner_id=owner_id,
            assigned_to_id=obj_in.assigned_to_id,
            team_id=obj_in.team_id,
            tags=obj_in.tags or [],
        )
        db.add(task)
        await db.flush()
        await db.refresh(task)
        return task

    async def list_with_filters(
        self,
        db: AsyncSession,
        *,
        filters: TaskFilter,
        owner_id: uuid.UUID | None = None,
        team_ids: list[uuid.UUID] | None = None,
    ) -> tuple[list[Task], int]:
        """
        Return (tasks, total) applying all filter criteria.
        If owner_id is provided, restricts to tasks owned by or assigned to that user.
        If team_ids is provided, also includes tasks belonging to those teams.
        """
        query = (
            select(Task)
            .options(selectinload(Task.owner), selectinload(Task.assignee))
        )
        count_query = select(func.count()).select_from(Task)

        # Ownership / visibility filter
        if owner_id is not None:
            conditions = [Task.owner_id == owner_id, Task.assigned_to_id == owner_id]
            if team_ids:
                conditions.append(Task.team_id.in_(team_ids))
            visibility_filter = or_(*conditions)
            query = query.where(visibility_filter)
            count_query = count_query.where(visibility_filter)

        # Archived filter
        query = query.where(Task.is_archived == filters.is_archived)
        count_query = count_query.where(Task.is_archived == filters.is_archived)

        # Status filter
        if filters.status is not None:
            query = query.where(Task.status == filters.status)
            count_query = count_query.where(Task.status == filters.status)

        # Priority filter
        if filters.priority is not None:
            query = query.where(Task.priority == filters.priority)
            count_query = count_query.where(Task.priority == filters.priority)

        # Assigned-to filter
        if filters.assigned_to_id is not None:
            query = query.where(Task.assigned_to_id == filters.assigned_to_id)
            count_query = count_query.where(Task.assigned_to_id == filters.assigned_to_id)

        # Team filter
        if filters.team_id is not None:
            query = query.where(Task.team_id == filters.team_id)
            count_query = count_query.where(Task.team_id == filters.team_id)

        # Due date range
        if filters.due_date_from is not None:
            query = query.where(Task.due_date >= filters.due_date_from)
            count_query = count_query.where(Task.due_date >= filters.due_date_from)
        if filters.due_date_to is not None:
            query = query.where(Task.due_date <= filters.due_date_to)
            count_query = count_query.where(Task.due_date <= filters.due_date_to)

        # Full-text search on title and description
        if filters.search:
            search_term = f"%{filters.search}%"
            search_filter = or_(
                Task.title.ilike(search_term),
                Task.description.ilike(search_term),
            )
            query = query.where(search_filter)
            count_query = count_query.where(search_filter)

        # Count
        total_result = await db.execute(count_query)
        total = total_result.scalar_one()

        # Paginate
        skip = (filters.page - 1) * filters.size
        query = query.order_by(Task.created_at.desc()).offset(skip).limit(filters.size)

        result = await db.execute(query)
        tasks = list(result.scalars().all())
        return tasks, total

    async def list_by_team(
        self,
        db: AsyncSession,
        *,
        team_id: uuid.UUID,
        skip: int = 0,
        limit: int = 100,
        include_archived: bool = False,
    ) -> tuple[list[Task], int]:
        query = (
            select(Task)
            .options(selectinload(Task.owner), selectinload(Task.assignee))
            .where(Task.team_id == team_id)
        )
        count_query = select(func.count()).select_from(Task).where(Task.team_id == team_id)

        if not include_archived:
            query = query.where(Task.is_archived.is_(False))
            count_query = count_query.where(Task.is_archived.is_(False))

        total_result = await db.execute(count_query)
        total = total_result.scalar_one()

        result = await db.execute(
            query.order_by(Task.created_at.desc()).offset(skip).limit(limit)
        )
        return list(result.scalars().all()), total

    async def archive(self, db: AsyncSession, *, task: Task) -> Task:
        task.is_archived = True
        db.add(task)
        await db.flush()
        await db.refresh(task)
        return task

    async def count_by_status(self, db: AsyncSession) -> dict[str, int]:
        """Return a dict mapping status → count for all non-archived tasks."""
        result = await db.execute(
            select(Task.status, func.count(Task.id))
            .where(Task.is_archived.is_(False))
            .group_by(Task.status)
        )
        return {row[0]: row[1] for row in result.all()}


crud_task = CRUDTask(Task)
