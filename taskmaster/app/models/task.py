"""
Task ORM model.
Central entity of TaskMaster Pro. Supports status/priority enums,
PostgreSQL native arrays for tags, and soft-delete via is_archived.
"""
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, Index, String, Text, func
from sqlalchemy.dialects.postgresql import ARRAY, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Task(Base):
    __tablename__ = "tasks"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(
        Enum("pending", "in_progress", "completed", "cancelled", name="task_status_enum"),
        nullable=False,
        default="pending",
        server_default="pending",
    )
    priority: Mapped[str] = mapped_column(
        Enum("low", "medium", "high", "critical", name="task_priority_enum"),
        nullable=False,
        default="medium",
        server_default="medium",
    )
    due_date: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    owner_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    assigned_to_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    team_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("teams.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    tags: Mapped[list[str] | None] = mapped_column(
        ARRAY(String(100)),
        nullable=True,
        default=list,
    )
    is_archived: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="false"
    )
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
    owner: Mapped["User"] = relationship(  # type: ignore[name-defined]  # noqa: F821
        "User",
        foreign_keys=[owner_id],
        back_populates="owned_tasks",
    )
    assignee: Mapped["User | None"] = relationship(  # type: ignore[name-defined]  # noqa: F821
        "User",
        foreign_keys=[assigned_to_id],
        back_populates="assigned_tasks",
    )
    team: Mapped["Team | None"] = relationship(  # type: ignore[name-defined]  # noqa: F821
        "Team",
        back_populates="tasks",
    )
    comments: Mapped[list["Comment"]] = relationship(  # type: ignore[name-defined]  # noqa: F821
        "Comment",
        back_populates="task",
        cascade="all, delete-orphan",
    )
    attachments: Mapped[list["Attachment"]] = relationship(  # type: ignore[name-defined]  # noqa: F821
        "Attachment",
        back_populates="task",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        Index("ix_tasks_owner_id", "owner_id"),
        Index("ix_tasks_status", "status"),
        Index("ix_tasks_priority", "priority"),
        Index("ix_tasks_due_date", "due_date"),
        Index("ix_tasks_team_id", "team_id"),
        Index("ix_tasks_assigned_to_id", "assigned_to_id"),
        Index("ix_tasks_is_archived", "is_archived"),
        Index("ix_tasks_status_priority", "status", "priority"),
    )

    def __repr__(self) -> str:
        return f"<Task id={self.id} title={self.title!r} status={self.status}>"
