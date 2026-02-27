"""
Admin-only dashboard routes.
"""
from __future__ import annotations

from fastapi import APIRouter, Query
from pydantic import BaseModel

from app.core.dependencies import AdminUser, DBSession
from app.crud.task import crud_task
from app.crud.team import crud_team
from app.crud.user import crud_user
from app.schemas.pagination import PaginatedResponse
from app.schemas.task import TaskRead
from app.schemas.user import UserRead

router = APIRouter(prefix="/admin", tags=["Admin"])


class AdminStats(BaseModel):
    total_users: int
    active_users: int
    total_tasks: int
    tasks_by_status: dict[str, int]
    active_teams: int
    connected_websocket_users: int


@router.get(
    "/stats",
    response_model=AdminStats,
    summary="Dashboard statistics",
)
async def get_stats(
    _admin: AdminUser,
    db: DBSession,
) -> AdminStats:
    from app.services.websocket_service import ws_manager

    total_users = await crud_user.get_count(db)
    _, active_users = await crud_user.list_users(db, skip=0, limit=1, include_inactive=False)
    total_tasks = await crud_task.get_count(db)
    tasks_by_status = await crud_task.count_by_status(db)
    active_teams = await crud_team.count_active_teams(db)

    return AdminStats(
        total_users=total_users,
        active_users=active_users,
        total_tasks=total_tasks,
        tasks_by_status=tasks_by_status,
        active_teams=active_teams,
        connected_websocket_users=ws_manager.connected_user_count,
    )


@router.get(
    "/users",
    response_model=PaginatedResponse[UserRead],
    summary="Full user list with stats (admin only)",
)
async def list_all_users(
    _admin: AdminUser,
    db: DBSession,
    page: int = Query(default=1, ge=1),
    size: int = Query(default=20, ge=1, le=100),
    include_inactive: bool = Query(default=True),
) -> PaginatedResponse[UserRead]:
    skip = (page - 1) * size
    users, total = await crud_user.list_users(
        db, skip=skip, limit=size, include_inactive=include_inactive
    )
    return PaginatedResponse(
        items=[UserRead.model_validate(u) for u in users],
        total=total,
        page=page,
        size=size,
    )


@router.get(
    "/tasks",
    response_model=PaginatedResponse[TaskRead],
    summary="All tasks across the system (admin only)",
)
async def list_all_tasks(
    _admin: AdminUser,
    db: DBSession,
    page: int = Query(default=1, ge=1),
    size: int = Query(default=20, ge=1, le=100),
    include_archived: bool = Query(default=False),
) -> PaginatedResponse[TaskRead]:
    from app.schemas.task import TaskFilter

    filters = TaskFilter(
        is_archived=include_archived,
        page=page,
        size=size,
    )
    tasks, total = await crud_task.list_with_filters(db, filters=filters)
    return PaginatedResponse(
        items=[TaskRead.model_validate(t) for t in tasks],
        total=total,
        page=page,
        size=size,
    )
