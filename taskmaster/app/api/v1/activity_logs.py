"""
Activity log routes.
"""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Query

from app.core.dependencies import AdminUser, CurrentUser, DBSession
from app.schemas.activity_log import ActivityLogRead
from app.schemas.pagination import PaginatedResponse
from sqlalchemy import func, select
from sqlalchemy.orm import selectinload

from app.models.activity_log import ActivityLog

router = APIRouter(prefix="/activity", tags=["Activity Logs"])


@router.get(
    "/",
    response_model=PaginatedResponse[ActivityLogRead],
    summary="Get my activity log",
)
async def my_activity(
    current_user: CurrentUser,
    db: DBSession,
    page: int = Query(default=1, ge=1),
    size: int = Query(default=20, ge=1, le=100),
) -> PaginatedResponse[ActivityLogRead]:
    skip = (page - 1) * size

    count_result = await db.execute(
        select(func.count())
        .select_from(ActivityLog)
        .where(ActivityLog.user_id == current_user.id)
    )
    total = count_result.scalar_one()

    result = await db.execute(
        select(ActivityLog)
        .options(selectinload(ActivityLog.user))
        .where(ActivityLog.user_id == current_user.id)
        .order_by(ActivityLog.created_at.desc())
        .offset(skip)
        .limit(size)
    )
    logs = list(result.scalars().all())

    return PaginatedResponse(
        items=[ActivityLogRead.model_validate(log) for log in logs],
        total=total,
        page=page,
        size=size,
    )


@router.get(
    "/task/{task_id}",
    response_model=PaginatedResponse[ActivityLogRead],
    summary="Get activity log for a specific task",
)
async def task_activity(
    task_id: uuid.UUID,
    current_user: CurrentUser,
    db: DBSession,
    page: int = Query(default=1, ge=1),
    size: int = Query(default=20, ge=1, le=100),
) -> PaginatedResponse[ActivityLogRead]:
    skip = (page - 1) * size

    count_result = await db.execute(
        select(func.count())
        .select_from(ActivityLog)
        .where(
            ActivityLog.entity_type == "task",
            ActivityLog.entity_id == task_id,
        )
    )
    total = count_result.scalar_one()

    result = await db.execute(
        select(ActivityLog)
        .options(selectinload(ActivityLog.user))
        .where(
            ActivityLog.entity_type == "task",
            ActivityLog.entity_id == task_id,
        )
        .order_by(ActivityLog.created_at.desc())
        .offset(skip)
        .limit(size)
    )
    logs = list(result.scalars().all())

    return PaginatedResponse(
        items=[ActivityLogRead.model_validate(log) for log in logs],
        total=total,
        page=page,
        size=size,
    )


@router.get(
    "/admin",
    response_model=PaginatedResponse[ActivityLogRead],
    summary="Get all system activity (admin only)",
)
async def admin_activity(
    _admin: AdminUser,
    db: DBSession,
    page: int = Query(default=1, ge=1),
    size: int = Query(default=20, ge=1, le=100),
    entity_type: str | None = Query(default=None),
    action: str | None = Query(default=None),
) -> PaginatedResponse[ActivityLogRead]:
    skip = (page - 1) * size

    query = select(ActivityLog).options(selectinload(ActivityLog.user))
    count_query = select(func.count()).select_from(ActivityLog)

    if entity_type:
        query = query.where(ActivityLog.entity_type == entity_type)
        count_query = count_query.where(ActivityLog.entity_type == entity_type)
    if action:
        query = query.where(ActivityLog.action == action)
        count_query = count_query.where(ActivityLog.action == action)

    count_result = await db.execute(count_query)
    total = count_result.scalar_one()

    result = await db.execute(
        query.order_by(ActivityLog.created_at.desc()).offset(skip).limit(size)
    )
    logs = list(result.scalars().all())

    return PaginatedResponse(
        items=[ActivityLogRead.model_validate(log) for log in logs],
        total=total,
        page=page,
        size=size,
    )
