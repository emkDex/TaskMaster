"""
Team and TeamMember Pydantic schemas.
"""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

from app.schemas.user import UserReadPublic

TeamMemberRole = Literal["member", "manager"]


# ── Team Create / Update / Read ───────────────────────────────────────────────

class TeamCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=1000)


class TeamUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = None


class TeamRead(BaseModel):
    id: uuid.UUID
    name: str
    description: str | None
    owner_id: uuid.UUID
    created_at: datetime
    updated_at: datetime
    owner: UserReadPublic | None = None

    model_config = {"from_attributes": True}


class TeamReadWithMembers(TeamRead):
    members: list["TeamMemberRead"] = []


# ── TeamMember schemas ────────────────────────────────────────────────────────

class TeamMemberAdd(BaseModel):
    user_id: uuid.UUID
    role: TeamMemberRole = "member"


class TeamMemberUpdateRole(BaseModel):
    role: TeamMemberRole


class TeamMemberRead(BaseModel):
    team_id: uuid.UUID
    user_id: uuid.UUID
    role: str
    joined_at: datetime
    user: UserReadPublic | None = None

    model_config = {"from_attributes": True}
