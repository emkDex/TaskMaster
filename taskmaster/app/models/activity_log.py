"""
ActivityLog ORM model.
Immutable audit trail of all significant actions in the system.
Uses JSONB for flexible metadata storage.
"""
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, String, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class ActivityLog(Base):
    __tablename__ = "activity_logs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    action: Mapped[str] = mapped_column(String(200), nullable=False)
    entity_type: Mapped[str] = mapped_column(String(100), nullable=False)
    entity_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    meta: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    # ── Relationships ─────────────────────────────────────────────────────────
    user: Mapped["User"] = relationship(  # type: ignore[name-defined]  # noqa: F821
        "User",
        back_populates="activity_logs",
    )

    __table_args__ = (
        Index("ix_activity_logs_user_id", "user_id"),
        Index("ix_activity_logs_entity_type_id", "entity_type", "entity_id"),
        Index("ix_activity_logs_created_at", "created_at"),
        Index("ix_activity_logs_action", "action"),
    )

    def __repr__(self) -> str:
        return (
            f"<ActivityLog id={self.id} user_id={self.user_id} "
            f"action={self.action!r} entity_type={self.entity_type!r}>"
        )
