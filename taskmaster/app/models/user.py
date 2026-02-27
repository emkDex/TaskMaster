"""
User ORM model.
Stores authentication credentials, profile data, and role information.
"""
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Enum, Index, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class UserRole(str):
    USER = "user"
    ADMIN = "admin"


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        index=True,
    )
    email: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        nullable=False,
        index=True,
    )
    username: Mapped[str] = mapped_column(
        String(100),
        unique=True,
        nullable=False,
        index=True,
    )
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    role: Mapped[str] = mapped_column(
        Enum("user", "admin", name="user_role_enum"),
        nullable=False,
        default="user",
        server_default="user",
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default="true"
    )
    is_verified: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="false"
    )
    avatar_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    refresh_token_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    # ── Relationships ─────────────────────────────────────────────────────────
    owned_tasks: Mapped[list["Task"]] = relationship(  # type: ignore[name-defined]  # noqa: F821
        "Task",
        foreign_keys="Task.owner_id",
        back_populates="owner",
        cascade="all, delete-orphan",
    )
    assigned_tasks: Mapped[list["Task"]] = relationship(  # type: ignore[name-defined]  # noqa: F821
        "Task",
        foreign_keys="Task.assigned_to_id",
        back_populates="assignee",
    )
    owned_teams: Mapped[list["Team"]] = relationship(  # type: ignore[name-defined]  # noqa: F821
        "Team",
        back_populates="owner",
        cascade="all, delete-orphan",
    )
    team_memberships: Mapped[list["TeamMember"]] = relationship(  # type: ignore[name-defined]  # noqa: F821
        "TeamMember",
        back_populates="user",
        cascade="all, delete-orphan",
    )
    comments: Mapped[list["Comment"]] = relationship(  # type: ignore[name-defined]  # noqa: F821
        "Comment",
        back_populates="author",
        cascade="all, delete-orphan",
    )
    attachments: Mapped[list["Attachment"]] = relationship(  # type: ignore[name-defined]  # noqa: F821
        "Attachment",
        back_populates="uploader",
        cascade="all, delete-orphan",
    )
    notifications: Mapped[list["Notification"]] = relationship(  # type: ignore[name-defined]  # noqa: F821
        "Notification",
        back_populates="user",
        cascade="all, delete-orphan",
    )
    activity_logs: Mapped[list["ActivityLog"]] = relationship(  # type: ignore[name-defined]  # noqa: F821
        "ActivityLog",
        back_populates="user",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        Index("ix_users_email_active", "email", "is_active"),
        Index("ix_users_role", "role"),
    )

    def __repr__(self) -> str:
        return f"<User id={self.id} email={self.email} role={self.role}>"
