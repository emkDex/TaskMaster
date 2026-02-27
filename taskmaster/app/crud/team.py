"""
Team CRUD operations.
"""
from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.crud.base import CRUDBase
from app.models.team import Team, TeamMember
from app.schemas.team import TeamCreate, TeamUpdate


class CRUDTeam(CRUDBase[Team, TeamCreate, TeamUpdate]):

    async def create_team(
        self,
        db: AsyncSession,
        *,
        obj_in: TeamCreate,
        owner_id: uuid.UUID,
    ) -> Team:
        team = Team(
            name=obj_in.name,
            description=obj_in.description,
            owner_id=owner_id,
        )
        db.add(team)
        await db.flush()
        await db.refresh(team)
        return team

    async def get_with_members(
        self, db: AsyncSession, team_id: uuid.UUID
    ) -> Team | None:
        result = await db.execute(
            select(Team)
            .options(
                selectinload(Team.owner),
                selectinload(Team.members).selectinload(TeamMember.user),
            )
            .where(Team.id == team_id)
        )
        return result.scalar_one_or_none()

    async def list_by_user(
        self,
        db: AsyncSession,
        *,
        user_id: uuid.UUID,
        skip: int = 0,
        limit: int = 100,
    ) -> list[Team]:
        """Return teams where the user is owner or member."""
        result = await db.execute(
            select(Team)
            .outerjoin(TeamMember, TeamMember.team_id == Team.id)
            .where(
                (Team.owner_id == user_id) | (TeamMember.user_id == user_id)
            )
            .distinct()
            .options(selectinload(Team.owner))
            .offset(skip)
            .limit(limit)
        )
        return list(result.scalars().all())

    async def get_member(
        self, db: AsyncSession, *, team_id: uuid.UUID, user_id: uuid.UUID
    ) -> TeamMember | None:
        result = await db.execute(
            select(TeamMember).where(
                TeamMember.team_id == team_id,
                TeamMember.user_id == user_id,
            )
        )
        return result.scalar_one_or_none()

    async def add_member(
        self,
        db: AsyncSession,
        *,
        team_id: uuid.UUID,
        user_id: uuid.UUID,
        role: str = "member",
    ) -> TeamMember:
        member = TeamMember(team_id=team_id, user_id=user_id, role=role)
        db.add(member)
        await db.flush()
        await db.refresh(member)
        return member

    async def remove_member(
        self, db: AsyncSession, *, team_id: uuid.UUID, user_id: uuid.UUID
    ) -> TeamMember | None:
        member = await self.get_member(db, team_id=team_id, user_id=user_id)
        if member is None:
            return None
        await db.delete(member)
        await db.flush()
        return member

    async def update_member_role(
        self,
        db: AsyncSession,
        *,
        team_id: uuid.UUID,
        user_id: uuid.UUID,
        role: str,
    ) -> TeamMember | None:
        member = await self.get_member(db, team_id=team_id, user_id=user_id)
        if member is None:
            return None
        member.role = role
        db.add(member)
        await db.flush()
        await db.refresh(member)
        return member

    async def get_user_team_ids(
        self, db: AsyncSession, *, user_id: uuid.UUID
    ) -> list[uuid.UUID]:
        """Return all team IDs the user belongs to (as owner or member)."""
        result = await db.execute(
            select(Team.id)
            .outerjoin(TeamMember, TeamMember.team_id == Team.id)
            .where(
                (Team.owner_id == user_id) | (TeamMember.user_id == user_id)
            )
            .distinct()
        )
        return [row[0] for row in result.all()]

    async def count_active_teams(self, db: AsyncSession) -> int:
        from sqlalchemy import func
        result = await db.execute(select(func.count()).select_from(Team))
        return result.scalar_one()


crud_team = CRUDTeam(Team)
