"""
User CRUD operations.
Extends CRUDBase with user-specific queries.
"""
from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.crud.base import CRUDBase
from app.models.user import User
from app.schemas.user import UserCreate, UserUpdate


class CRUDUser(CRUDBase[User, UserCreate, UserUpdate]):

    async def get_by_email(self, db: AsyncSession, email: str) -> User | None:
        result = await db.execute(select(User).where(User.email == email))
        return result.scalar_one_or_none()

    async def get_by_username(self, db: AsyncSession, username: str) -> User | None:
        result = await db.execute(select(User).where(User.username == username))
        return result.scalar_one_or_none()

    async def get_active_by_email(self, db: AsyncSession, email: str) -> User | None:
        result = await db.execute(
            select(User).where(User.email == email, User.is_active.is_(True))
        )
        return result.scalar_one_or_none()

    async def create_user(
        self,
        db: AsyncSession,
        *,
        email: str,
        username: str,
        hashed_password: str,
        full_name: str | None = None,
        role: str = "user",
    ) -> User:
        user = User(
            email=email,
            username=username,
            hashed_password=hashed_password,
            full_name=full_name,
            role=role,
        )
        db.add(user)
        await db.flush()
        await db.refresh(user)
        return user

    async def set_refresh_token_hash(
        self, db: AsyncSession, *, user: User, token_hash: str | None
    ) -> User:
        user.refresh_token_hash = token_hash
        db.add(user)
        await db.flush()
        await db.refresh(user)
        return user

    async def deactivate(self, db: AsyncSession, *, user: User) -> User:
        user.is_active = False
        db.add(user)
        await db.flush()
        await db.refresh(user)
        return user

    async def list_users(
        self,
        db: AsyncSession,
        *,
        skip: int = 0,
        limit: int = 100,
        include_inactive: bool = False,
    ) -> tuple[list[User], int]:
        from sqlalchemy import func

        query = select(User)
        count_query = select(func.count()).select_from(User)

        if not include_inactive:
            query = query.where(User.is_active.is_(True))
            count_query = count_query.where(User.is_active.is_(True))

        total_result = await db.execute(count_query)
        total = total_result.scalar_one()

        result = await db.execute(
            query.order_by(User.created_at.desc()).offset(skip).limit(limit)
        )
        users = list(result.scalars().all())
        return users, total


crud_user = CRUDUser(User)
