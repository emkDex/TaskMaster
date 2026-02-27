"""
Team management service.
Handles team creation, member invitation, removal, and role updates.
"""
from __future__ import annotations

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictException, ForbiddenException, NotFoundException
from app.crud.team import crud_team
from app.crud.user import crud_user
from app.models.team import Team, TeamMember
from app.models.user import User
from app.schemas.team import TeamCreate, TeamMemberAdd, TeamUpdate
from app.services.activity_service import activity_service
from app.services.notification_service import notification_service


class TeamService:

    async def create_team(
        self,
        db: AsyncSession,
        *,
        team_in: TeamCreate,
        current_user: User,
    ) -> Team:
        team = await crud_team.create_team(
            db, obj_in=team_in, owner_id=current_user.id
        )
        # Auto-add owner as manager
        await crud_team.add_member(
            db, team_id=team.id, user_id=current_user.id, role="manager"
        )
        await activity_service.log(
            db,
            user_id=current_user.id,
            action="team_created",
            entity_type="team",
            entity_id=team.id,
            meta={"name": team.name},
        )
        return team

    async def get_team(
        self,
        db: AsyncSession,
        *,
        team_id: uuid.UUID,
        current_user: User,
    ) -> Team:
        team = await crud_team.get_with_members(db, team_id)
        if team is None:
            raise NotFoundException("Team", str(team_id))
        await self._assert_member_or_admin(db, team=team, user=current_user)
        return team

    async def update_team(
        self,
        db: AsyncSession,
        *,
        team_id: uuid.UUID,
        team_in: TeamUpdate,
        current_user: User,
    ) -> Team:
        team = await crud_team.get(db, team_id)
        if team is None:
            raise NotFoundException("Team", str(team_id))
        await self._assert_owner_or_admin(team=team, user=current_user)
        updated = await crud_team.update(db, db_obj=team, obj_in=team_in)
        await activity_service.log(
            db,
            user_id=current_user.id,
            action="team_updated",
            entity_type="team",
            entity_id=team.id,
            meta=team_in.model_dump(exclude_unset=True),
        )
        return updated

    async def delete_team(
        self,
        db: AsyncSession,
        *,
        team_id: uuid.UUID,
        current_user: User,
    ) -> Team:
        team = await crud_team.get(db, team_id)
        if team is None:
            raise NotFoundException("Team", str(team_id))
        await self._assert_owner_or_admin(team=team, user=current_user)
        deleted = await crud_team.remove(db, id=team_id)
        await activity_service.log(
            db,
            user_id=current_user.id,
            action="team_deleted",
            entity_type="team",
            entity_id=team_id,
        )
        return deleted  # type: ignore[return-value]

    async def add_member(
        self,
        db: AsyncSession,
        *,
        team_id: uuid.UUID,
        member_in: TeamMemberAdd,
        current_user: User,
    ) -> TeamMember:
        team = await crud_team.get(db, team_id)
        if team is None:
            raise NotFoundException("Team", str(team_id))

        await self._assert_manager_or_admin(db, team=team, user=current_user)

        # Verify target user exists
        target_user = await crud_user.get(db, member_in.user_id)
        if target_user is None:
            raise NotFoundException("User", str(member_in.user_id))

        # Check not already a member
        existing = await crud_team.get_member(
            db, team_id=team_id, user_id=member_in.user_id
        )
        if existing is not None:
            raise ConflictException("User is already a member of this team")

        member = await crud_team.add_member(
            db,
            team_id=team_id,
            user_id=member_in.user_id,
            role=member_in.role,
        )

        await notification_service.notify_team_invite(
            db,
            user_id=member_in.user_id,
            team_id=team_id,
            team_name=team.name,
            inviter_name=current_user.username,
        )

        await activity_service.log(
            db,
            user_id=current_user.id,
            action="team_member_added",
            entity_type="team",
            entity_id=team_id,
            meta={"user_id": str(member_in.user_id), "role": member_in.role},
        )

        return member

    async def remove_member(
        self,
        db: AsyncSession,
        *,
        team_id: uuid.UUID,
        user_id: uuid.UUID,
        current_user: User,
    ) -> None:
        team = await crud_team.get(db, team_id)
        if team is None:
            raise NotFoundException("Team", str(team_id))

        # Owner cannot be removed
        if team.owner_id == user_id:
            raise ForbiddenException("Cannot remove the team owner")

        await self._assert_manager_or_admin(db, team=team, user=current_user)

        removed = await crud_team.remove_member(db, team_id=team_id, user_id=user_id)
        if removed is None:
            raise NotFoundException("TeamMember")

        await notification_service.notify_team_removed(
            db,
            user_id=user_id,
            team_id=team_id,
            team_name=team.name,
        )

        await activity_service.log(
            db,
            user_id=current_user.id,
            action="team_member_removed",
            entity_type="team",
            entity_id=team_id,
            meta={"user_id": str(user_id)},
        )

    async def update_member_role(
        self,
        db: AsyncSession,
        *,
        team_id: uuid.UUID,
        user_id: uuid.UUID,
        role: str,
        current_user: User,
    ) -> TeamMember:
        team = await crud_team.get(db, team_id)
        if team is None:
            raise NotFoundException("Team", str(team_id))

        await self._assert_owner_or_admin(team=team, user=current_user)

        member = await crud_team.update_member_role(
            db, team_id=team_id, user_id=user_id, role=role
        )
        if member is None:
            raise NotFoundException("TeamMember")

        return member

    # ── Private helpers ───────────────────────────────────────────────────────

    async def _assert_member_or_admin(
        self, db: AsyncSession, *, team: Team, user: User
    ) -> None:
        if user.role == "admin":
            return
        member = await crud_team.get_member(db, team_id=team.id, user_id=user.id)
        if member is None and team.owner_id != user.id:
            raise ForbiddenException("You are not a member of this team")

    async def _assert_manager_or_admin(
        self, db: AsyncSession, *, team: Team, user: User
    ) -> None:
        if user.role == "admin" or team.owner_id == user.id:
            return
        member = await crud_team.get_member(db, team_id=team.id, user_id=user.id)
        if member is None or member.role != "manager":
            raise ForbiddenException(
                "Only team managers or admins can perform this action"
            )

    def _assert_owner_or_admin(self, *, team: Team, user: User) -> None:
        if user.role == "admin" or team.owner_id == user.id:
            return
        raise ForbiddenException("Only the team owner or admin can perform this action")


team_service = TeamService()
