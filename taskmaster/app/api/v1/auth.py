"""
Authentication routes.
POST /auth/register, /auth/login, /auth/refresh, /auth/logout
"""
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Request, status
from slowapi import Limiter
from slowapi.util import get_remote_address

from app.core.config import settings
from app.core.dependencies import CurrentUser, DBSession
from app.schemas.user import LoginRequest, RefreshTokenRequest, Token, UserCreate, UserRead
from app.services.auth_service import auth_service

router = APIRouter(prefix="/auth", tags=["Authentication"])

limiter = Limiter(key_func=get_remote_address)


@router.post(
    "/register",
    response_model=UserRead,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user account",
)
async def register(
    user_in: UserCreate,
    db: DBSession,
) -> UserRead:
    user = await auth_service.register_user(db, user_in=user_in)
    return UserRead.model_validate(user)


@router.post(
    "/login",
    response_model=Token,
    summary="Authenticate and receive JWT token pair",
)
@limiter.limit(settings.RATE_LIMIT_LOGIN)
async def login(
    request: Request,
    credentials: LoginRequest,
    db: DBSession,
) -> Token:
    return await auth_service.authenticate_user(
        db, email=credentials.email, password=credentials.password
    )


@router.post(
    "/refresh",
    response_model=Token,
    summary="Refresh access token using a valid refresh token",
)
async def refresh(
    body: RefreshTokenRequest,
    db: DBSession,
) -> Token:
    return await auth_service.refresh_access_token(
        db, refresh_token=body.refresh_token
    )


@router.post(
    "/logout",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Invalidate the current refresh token",
)
async def logout(
    current_user: CurrentUser,
    db: DBSession,
) -> None:
    await auth_service.logout(db, user=current_user)
