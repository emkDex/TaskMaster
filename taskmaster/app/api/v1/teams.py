"""
Team management routes.
"""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Query, status

from app.core.dependencies import CurrentUser, DBSession
from app.crud.team import crud_team
from app.schemas.pagination import PaginatedResponse
from app.schemas.team import (
    TeamCreate,
    TeamMemberAdd,
    TeamMemberRead,
    TeamMemberUpdateRole,
    TeamRead,
    TeamReadWithMembers,
    TeamUpdate,
)
from app.services.team_service import team_service

router = APIRouter(prefix="/teams", tags=["Teams"])


@router.post(
    "/",
    response_model=TeamRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new team",
)
async def create_team(
    team_in: TeamCreate,
    current_user: CurrentUser,
    db: DBSession,
) -> TeamRead:
    team = await team_service.create_team(db, team_in=team_in, current_user=current_user)
    return TeamRead.model_validate(team)


@router.get(
    "/",
    response_model=PaginatedResponse[TeamRead],
    summary="List teams I belong to",
)
async def list_my_teams(
    current_user: CurrentUser,
    db: DBSession,
    page: int = Query(default=1, ge=1),
    size: int = Query(default=20, ge=1, le=100),
) -> PaginatedResponse[TeamRead]:
    teams = await crud_team.list_by_user(
        db, user_id=current_user.id, skip=(page - 1) * size, limit=size
    )
    return PaginatedResponse(
        items=[TeamRead.model_validate(t) for t in teams],
        total=len(teams),
        page=page,
        size=size,
    )


@router.get(
    "/{team_id}",
    response_model=TeamReadWithMembers,
    summary="Get team details with members",
)
async def get_team(
    team_id: uuid.UUID,
    current_user: CurrentUser,
    db: DBSession,
) -> TeamReadWithMembers:
    team = await team_service.get_team(db, team_id=team_id, current_user=current_user)
    return TeamReadWithMembers.model_validate(team)


@router.put(
    "/{team_id}",
    response_model=TeamRead,
    summary="Update team details",
)
async def update_team(
    team_id: uuid.UUID,
    team_in: TeamUpdate,
    current_user: CurrentUser,
    db: DBSession,
) -> TeamRead:
    team = await team_service.update_team(
        db, team_id=team_id, team_in=team_in, current_user=current_user
    )
    return TeamRead.model_validate(team)


@router.delete(
    "/{team_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a team",
)
async def delete_team(
    team_id: uuid.UUID,
    current_user: CurrentUser,
    db: DBSession,
) -> None:
    await team_service.delete_team(db, team_id=team_id, current_user=current_user)


@router.post(
    "/{team_id}/members",
    response_model=TeamMemberRead,
    status_code=status.HTTP_201_CREATED,
    summary="Add a member to the team",
)
async def add_member(
    team_id: uuid.UUID,
    member_in: TeamMemberAdd,
    current_user: CurrentUser,
    db: DBSession,
) -> TeamMemberRead:
    member = await team_service.add_member(
        db, team_id=team_id, member_in=member_in, current_user=current_user
    )
    return TeamMemberRead.model_validate(member)


@router.patch(
    "/{team_id}/members/{user_id}",
    response_model=TeamMemberRead,
    summary="Update a member's role",
)
async def update_member_role(
    team_id: uuid.UUID,
    user_id: uuid.UUID,
    role_in: TeamMemberUpdateRole,
    current_user: CurrentUser,
    db: DBSession,
) -> TeamMemberRead:
    member = await team_service.update_member_role(
        db,
        team_id=team_id,
        user_id=user_id,
        role=role_in.role,
        current_user=current_user,
    )
    return TeamMemberRead.model_validate(member)


@router.delete(
    "/{team_id}/members/{user_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Remove a member from the team",
)
async def remove_member(
    team_id: uuid.UUID,
    user_id: uuid.UUID,
    current_user: CurrentUser,
    db: DBSession,
) -> None:
    await team_service.remove_member(
        db, team_id=team_id, user_id=user_id, current_user=current_user
    )
