"""
User profile routes.
GET/PUT /users/me, PUT /users/me/password, admin CRUD on /users/
"""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Query, status

from app.core.dependencies import AdminUser, CurrentUser, DBSession
from app.core.exceptions import BadRequestException, ConflictException, NotFoundException
from app.core.security import hash_password, verify_password
from app.crud.user import crud_user
from app.schemas.pagination import PaginatedResponse
from app.schemas.user import PasswordChange, UserAdminUpdate, UserRead, UserUpdate

router = APIRouter(prefix="/users", tags=["Users"])


@router.get("/me", response_model=UserRead, summary="Get current user profile")
async def get_me(current_user: CurrentUser) -> UserRead:
    return UserRead.model_validate(current_user)


@router.put("/me", response_model=UserRead, summary="Update current user profile")
async def update_me(
    user_in: UserUpdate,
    current_user: CurrentUser,
    db: DBSession,
) -> UserRead:
    # Check username uniqueness if changing
    if user_in.username and user_in.username != current_user.username:
        if await crud_user.exists(db, username=user_in.username):
            raise ConflictException("Username already taken")

    updated = await crud_user.update(db, db_obj=current_user, obj_in=user_in)
    return UserRead.model_validate(updated)


@router.put(
    "/me/password",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Change current user password",
)
async def change_password(
    body: PasswordChange,
    current_user: CurrentUser,
    db: DBSession,
) -> None:
    if not verify_password(body.current_password, current_user.hashed_password):
        raise BadRequestException("Current password is incorrect")
    if body.current_password == body.new_password:
        raise BadRequestException("New password must differ from current password")

    await crud_user.update(
        db,
        db_obj=current_user,
        obj_in={"hashed_password": hash_password(body.new_password)},
    )


@router.get(
    "/",
    response_model=PaginatedResponse[UserRead],
    summary="List all users (admin only)",
)
async def list_users(
    _admin: AdminUser,
    db: DBSession,
    page: int = Query(default=1, ge=1),
    size: int = Query(default=20, ge=1, le=100),
    include_inactive: bool = Query(default=False),
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
    "/{user_id}",
    response_model=UserRead,
    summary="Get user by ID (admin only)",
)
async def get_user(
    user_id: uuid.UUID,
    _admin: AdminUser,
    db: DBSession,
) -> UserRead:
    user = await crud_user.get(db, user_id)
    if user is None:
        raise NotFoundException("User", str(user_id))
    return UserRead.model_validate(user)


@router.patch(
    "/{user_id}",
    response_model=UserRead,
    summary="Update user role/status (admin only)",
)
async def admin_update_user(
    user_id: uuid.UUID,
    user_in: UserAdminUpdate,
    _admin: AdminUser,
    db: DBSession,
) -> UserRead:
    user = await crud_user.get(db, user_id)
    if user is None:
        raise NotFoundException("User", str(user_id))
    updated = await crud_user.update(db, db_obj=user, obj_in=user_in)
    return UserRead.model_validate(updated)


@router.delete(
    "/{user_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Deactivate user (admin only)",
)
async def deactivate_user(
    user_id: uuid.UUID,
    _admin: AdminUser,
    db: DBSession,
) -> None:
    user = await crud_user.get(db, user_id)
    if user is None:
        raise NotFoundException("User", str(user_id))
    await crud_user.deactivate(db, user=user)
