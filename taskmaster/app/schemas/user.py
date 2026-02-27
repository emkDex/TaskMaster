"""
User Pydantic schemas.
Covers registration, login, profile reads/updates, and token responses.
"""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, EmailStr, Field, field_validator

from app.core.security import validate_password_strength


# ── Enums (string literals for Pydantic v2) ───────────────────────────────────

UserRole = Annotated[str, Field(pattern="^(user|admin)$")]


# ── Create ────────────────────────────────────────────────────────────────────

class UserCreate(BaseModel):
    email: EmailStr
    username: str = Field(min_length=3, max_length=100, pattern=r"^[a-zA-Z0-9_\-]+$")
    password: str = Field(min_length=8, max_length=128)
    full_name: str | None = Field(default=None, max_length=255)

    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        return validate_password_strength(v)


# ── Update ────────────────────────────────────────────────────────────────────

class UserUpdate(BaseModel):
    full_name: str | None = Field(default=None, max_length=255)
    avatar_url: str | None = Field(default=None, max_length=500)
    username: str | None = Field(
        default=None, min_length=3, max_length=100, pattern=r"^[a-zA-Z0-9_\-]+$"
    )


class PasswordChange(BaseModel):
    current_password: str
    new_password: str = Field(min_length=8, max_length=128)

    @field_validator("new_password")
    @classmethod
    def validate_new_password(cls, v: str) -> str:
        return validate_password_strength(v)


# ── Read ──────────────────────────────────────────────────────────────────────

class UserRead(BaseModel):
    id: uuid.UUID
    email: EmailStr
    username: str
    full_name: str | None
    role: str
    is_active: bool
    is_verified: bool
    avatar_url: str | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class UserReadPublic(BaseModel):
    """Minimal public profile — safe to expose in task/comment responses."""

    id: uuid.UUID
    username: str
    full_name: str | None
    avatar_url: str | None

    model_config = {"from_attributes": True}


# ── Admin update ──────────────────────────────────────────────────────────────

class UserAdminUpdate(BaseModel):
    role: str | None = Field(default=None, pattern="^(user|admin)$")
    is_active: bool | None = None
    is_verified: bool | None = None


# ── Token schemas ─────────────────────────────────────────────────────────────

class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class AccessToken(BaseModel):
    access_token: str
    token_type: str = "bearer"


class TokenPayload(BaseModel):
    sub: str
    type: str
    role: str | None = None
    exp: int
    iat: int
    jti: str


class RefreshTokenRequest(BaseModel):
    refresh_token: str


class LoginRequest(BaseModel):
    email: EmailStr
    password: str
