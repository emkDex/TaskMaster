"""
Task routes.
Full CRUD + filtering + pagination + assignment + team task listing.
"""
from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query, status

from app.core.dependencies import CurrentUser, DBSession
from app.crud.task import crud_task
from app.schemas.pagination import PaginatedResponse
from app.schemas.task import TaskAssign, TaskCreate, TaskFilter, TaskRead, TaskUpdate
from app.services.task_service import task_service

router = APIRouter(prefix="/tasks", tags=["Tasks"])


def _task_filter_params(
    status: str | None = Query(default=None),
    priority: str | None = Query(default=None),
    assigned_to_id: uuid.UUID | None = Query(default=None),
    team_id: uuid.UUID | None = Query(default=None),
    is_archived: bool = Query(default=False),
    due_date_from: str | None = Query(default=None),
    due_date_to: str | None = Query(default=None),
    search: str | None = Query(default=None, max_length=200),
    page: int = Query(default=1, ge=1),
    size: int = Query(default=20, ge=1, le=100),
) -> TaskFilter:
    from datetime import datetime

    def _parse_dt(s: str | None):
        if s is None:
            return None
        try:
            return datetime.fromisoformat(s)
        except ValueError:
            return None

    return TaskFilter(
        status=status,  # type: ignore[arg-type]
        priority=priority,  # type: ignore[arg-type]
        assigned_to_id=assigned_to_id,
        team_id=team_id,
        is_archived=is_archived,
        due_date_from=_parse_dt(due_date_from),
        due_date_to=_parse_dt(due_date_to),
        search=search,
        page=page,
        size=size,
    )


@router.get(
    "/",
    response_model=PaginatedResponse[TaskRead],
    summary="List tasks with filters and pagination",
)
async def list_tasks(
    current_user: CurrentUser,
    db: DBSession,
    filters: Annotated[TaskFilter, Depends(_task_filter_params)],
) -> PaginatedResponse[TaskRead]:
    tasks, total = await task_service.list_tasks(
        db, filters=filters, current_user=current_user
    )
    return PaginatedResponse(
        items=[TaskRead.model_validate(t) for t in tasks],
        total=total,
        page=filters.page,
        size=filters.size,
    )


@router.post(
    "/",
    response_model=TaskRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new task",
)
async def create_task(
    task_in: TaskCreate,
    current_user: CurrentUser,
    db: DBSession,
) -> TaskRead:
    task = await task_service.create_task(db, task_in=task_in, current_user=current_user)
    return TaskRead.model_validate(task)


@router.get(
    "/team/{team_id}",
    response_model=PaginatedResponse[TaskRead],
    summary="List tasks for a specific team",
)
async def list_team_tasks(
    team_id: uuid.UUID,
    current_user: CurrentUser,
    db: DBSession,
    page: int = Query(default=1, ge=1),
    size: int = Query(default=20, ge=1, le=100),
    include_archived: bool = Query(default=False),
) -> PaginatedResponse[TaskRead]:
    tasks, total = await crud_task.list_by_team(
        db,
        team_id=team_id,
        skip=(page - 1) * size,
        limit=size,
        include_archived=include_archived,
    )
    return PaginatedResponse(
        items=[TaskRead.model_validate(t) for t in tasks],
        total=total,
        page=page,
        size=size,
    )


@router.get(
    "/{task_id}",
    response_model=TaskRead,
    summary="Get a task by ID",
)
async def get_task(
    task_id: uuid.UUID,
    current_user: CurrentUser,
    db: DBSession,
) -> TaskRead:
    task = await task_service.get_task(db, task_id=task_id, current_user=current_user)
    return TaskRead.model_validate(task)


@router.put(
    "/{task_id}",
    response_model=TaskRead,
    summary="Update a task",
)
async def update_task(
    task_id: uuid.UUID,
    task_in: TaskUpdate,
    current_user: CurrentUser,
    db: DBSession,
) -> TaskRead:
    task = await task_service.update_task(
        db, task_id=task_id, task_in=task_in, current_user=current_user
    )
    return TaskRead.model_validate(task)


@router.delete(
    "/{task_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Archive (soft-delete) a task",
)
async def delete_task(
    task_id: uuid.UUID,
    current_user: CurrentUser,
    db: DBSession,
) -> None:
    await task_service.delete_task(db, task_id=task_id, current_user=current_user)


@router.post(
    "/{task_id}/assign",
    response_model=TaskRead,
    summary="Assign a task to a user",
)
async def assign_task(
    task_id: uuid.UUID,
    body: TaskAssign,
    current_user: CurrentUser,
    db: DBSession,
) -> TaskRead:
    task = await task_service.assign_task(
        db,
        task_id=task_id,
        assignee_id=body.assigned_to_id,
        current_user=current_user,
    )
    return TaskRead.model_validate(task)
