"""
Authentication service.
Handles registration, login, token refresh, and logout.
Business logic lives here; routes only call these methods.
"""
from __future__ import annotations

import logging

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import (
    BadRequestException,
    ConflictException,
    InvalidTokenException,
    UnauthorizedException,
)
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_refresh_token,
    hash_password,
    hash_token,
    verify_password,
)
from app.crud.user import crud_user
from app.models.user import User
from app.schemas.user import Token, UserCreate
from app.services.activity_service import activity_service

logger = logging.getLogger(__name__)


class AuthService:

    async def register_user(
        self, db: AsyncSession, *, user_in: UserCreate
    ) -> User:
        """
        Register a new user.
        Validates email/username uniqueness, hashes password, creates user,
        and logs the registration activity.
        """
        # Check email uniqueness
        if await crud_user.exists(db, email=user_in.email):
            raise ConflictException("A user with this email already exists")

        # Check username uniqueness
        if await crud_user.exists(db, username=user_in.username):
            raise ConflictException("A user with this username already exists")

        hashed = hash_password(user_in.password)
        user = await crud_user.create_user(
            db,
            email=user_in.email,
            username=user_in.username,
            hashed_password=hashed,
            full_name=user_in.full_name,
        )

        await activity_service.log(
            db,
            user_id=user.id,
            action="user_registered",
            entity_type="user",
            entity_id=user.id,
            meta={"email": user.email, "username": user.username},
        )

        return user

    async def authenticate_user(
        self, db: AsyncSession, *, email: str, password: str
    ) -> Token:
        """
        Verify credentials and issue an access + refresh token pair.
        Stores the refresh token hash in the DB for rotation/revocation.
        """
        user = await crud_user.get_active_by_email(db, email)
        if user is None or not verify_password(password, user.hashed_password):
            raise UnauthorizedException("Invalid email or password")

        access_token = create_access_token(str(user.id), user.role)
        refresh_token = create_refresh_token(str(user.id))

        # Store hash for later validation
        await crud_user.set_refresh_token_hash(
            db, user=user, token_hash=hash_token(refresh_token)
        )

        await activity_service.log(
            db,
            user_id=user.id,
            action="user_login",
            entity_type="user",
            entity_id=user.id,
        )

        return Token(access_token=access_token, refresh_token=refresh_token)

    async def refresh_access_token(
        self, db: AsyncSession, *, refresh_token: str
    ) -> Token:
        """
        Validate the refresh token, issue a new access token,
        and rotate the refresh token.
        """
        try:
            payload = decode_refresh_token(refresh_token)
        except Exception:
            raise InvalidTokenException("Invalid or expired refresh token")

        user_id = payload.get("sub")
        if not user_id:
            raise InvalidTokenException("Malformed refresh token")

        import uuid
        user = await crud_user.get(db, uuid.UUID(user_id))
        if user is None or not user.is_active:
            raise UnauthorizedException("User not found or inactive")

        # Validate stored hash
        if user.refresh_token_hash != hash_token(refresh_token):
            raise InvalidTokenException("Refresh token has been revoked")

        new_access = create_access_token(str(user.id), user.role)
        new_refresh = create_refresh_token(str(user.id))

        await crud_user.set_refresh_token_hash(
            db, user=user, token_hash=hash_token(new_refresh)
        )

        return Token(access_token=new_access, refresh_token=new_refresh)

    async def logout(
        self, db: AsyncSession, *, user: User
    ) -> None:
        """Invalidate the stored refresh token hash."""
        await crud_user.set_refresh_token_hash(db, user=user, token_hash=None)
        await activity_service.log(
            db,
            user_id=user.id,
            action="user_logout",
            entity_type="user",
            entity_id=user.id,
        )


auth_service = AuthService()
