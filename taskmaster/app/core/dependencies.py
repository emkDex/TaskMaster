"""
FastAPI dependency injection functions.
Provides get_db, get_current_user, and require_admin.
"""
from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ForbiddenException, InvalidTokenException, UnauthorizedException
from app.core.security import decode_access_token
from app.crud.user import crud_user
from app.db.session import get_db
from app.models.user import User

# Re-export get_db so routes can import from one place
__all__ = ["get_db", "get_current_user", "require_admin", "DBSession", "CurrentUser"]

bearer_scheme = HTTPBearer(auto_error=False)


async def get_current_user(
    db: Annotated[AsyncSession, Depends(get_db)],
    credentials: Annotated[
        HTTPAuthorizationCredentials | None, Depends(bearer_scheme)
    ] = None,
) -> User:
    """
    Extract and validate the JWT access token from the Authorization header.
    Returns the authenticated User model.
    """
    if credentials is None:
        raise UnauthorizedException("Missing authentication token")

    token = credentials.credentials
    try:
        payload = decode_access_token(token)
    except JWTError:
        raise InvalidTokenException("Invalid or expired access token")

    user_id_str = payload.get("sub")
    if not user_id_str:
        raise InvalidTokenException("Malformed token: missing subject")

    try:
        user_id = uuid.UUID(user_id_str)
    except ValueError:
        raise InvalidTokenException("Malformed token: invalid subject format")

    user = await crud_user.get(db, user_id)
    if user is None:
        raise UnauthorizedException("User not found")
    if not user.is_active:
        raise UnauthorizedException("User account is deactivated")

    return user


async def require_admin(
    current_user: Annotated[User, Depends(get_current_user)],
) -> User:
    """Dependency that requires the current user to have the 'admin' role."""
    if current_user.role != "admin":
        raise ForbiddenException("Admin privileges required")
    return current_user


# Convenience type aliases for route signatures
DBSession = Annotated[AsyncSession, Depends(get_db)]
CurrentUser = Annotated[User, Depends(get_current_user)]
AdminUser = Annotated[User, Depends(require_admin)]
