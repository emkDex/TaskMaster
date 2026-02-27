"""001_initial_tables

Revision ID: 001
Revises:
Create Date: 2024-01-01 00:00:00.000000

Creates all initial tables for TaskMaster Pro:
  - users
  - teams
  - team_members
  - tasks
  - comments
  - attachments
  - notifications
  - activity_logs
"""
from __future__ import annotations

import uuid

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "001"
down_revision: str | None = None
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    # ── Enums ─────────────────────────────────────────────────────────────────
    user_role_enum = postgresql.ENUM("user", "admin", name="user_role_enum", create_type=False)
    user_role_enum.create(op.get_bind(), checkfirst=True)

    task_status_enum = postgresql.ENUM(
        "pending", "in_progress", "completed", "cancelled",
        name="task_status_enum", create_type=False
    )
    task_status_enum.create(op.get_bind(), checkfirst=True)

    task_priority_enum = postgresql.ENUM(
        "low", "medium", "high", "critical",
        name="task_priority_enum", create_type=False
    )
    task_priority_enum.create(op.get_bind(), checkfirst=True)

    team_member_role_enum = postgresql.ENUM(
        "member", "manager",
        name="team_member_role_enum", create_type=False
    )
    team_member_role_enum.create(op.get_bind(), checkfirst=True)

    notification_type_enum = postgresql.ENUM(
        "task_assigned", "task_updated", "task_completed",
        "comment_added", "team_invite", "team_removed", "system",
        name="notification_type_enum", create_type=False
    )
    notification_type_enum.create(op.get_bind(), checkfirst=True)

    # ── users ─────────────────────────────────────────────────────────────────
    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("username", sa.String(100), nullable=False),
        sa.Column("hashed_password", sa.String(255), nullable=False),
        sa.Column("full_name", sa.String(255), nullable=True),
        sa.Column(
            "role",
            sa.Enum("user", "admin", name="user_role_enum"),
            nullable=False,
            server_default="user",
        ),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("is_verified", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("avatar_url", sa.String(500), nullable=True),
        sa.Column("refresh_token_hash", sa.String(64), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.PrimaryKeyConstraint("id", name="pk_users"),
        sa.UniqueConstraint("email", name="uq_users_email"),
        sa.UniqueConstraint("username", name="uq_users_username"),
    )
    op.create_index("ix_users_email", "users", ["email"])
    op.create_index("ix_users_username", "users", ["username"])
    op.create_index("ix_users_email_active", "users", ["email", "is_active"])
    op.create_index("ix_users_role", "users", ["role"])

    # ── teams ─────────────────────────────────────────────────────────────────
    op.create_table(
        "teams",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("description", sa.String(1000), nullable=True),
        sa.Column("owner_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.ForeignKeyConstraint(
            ["owner_id"], ["users.id"],
            name="fk_teams_owner_id_users",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_teams"),
    )
    op.create_index("ix_teams_owner_id", "teams", ["owner_id"])

    # ── team_members ──────────────────────────────────────────────────────────
    op.create_table(
        "team_members",
        sa.Column("team_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "role",
            sa.Enum("member", "manager", name="team_member_role_enum"),
            nullable=False,
            server_default="member",
        ),
        sa.Column(
            "joined_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.ForeignKeyConstraint(
            ["team_id"], ["teams.id"],
            name="fk_team_members_team_id_teams",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"],
            name="fk_team_members_user_id_users",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("team_id", "user_id", name="pk_team_members"),
    )
    op.create_index("ix_team_members_user_id", "team_members", ["user_id"])
    op.create_index("ix_team_members_team_id", "team_members", ["team_id"])

    # ── tasks ─────────────────────────────────────────────────────────────────
    op.create_table(
        "tasks",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column(
            "status",
            sa.Enum("pending", "in_progress", "completed", "cancelled", name="task_status_enum"),
            nullable=False,
            server_default="pending",
        ),
        sa.Column(
            "priority",
            sa.Enum("low", "medium", "high", "critical", name="task_priority_enum"),
            nullable=False,
            server_default="medium",
        ),
        sa.Column("due_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("owner_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("assigned_to_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("team_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("tags", postgresql.ARRAY(sa.String(100)), nullable=True),
        sa.Column("is_archived", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.ForeignKeyConstraint(
            ["owner_id"], ["users.id"],
            name="fk_tasks_owner_id_users",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["assigned_to_id"], ["users.id"],
            name="fk_tasks_assigned_to_id_users",
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["team_id"], ["teams.id"],
            name="fk_tasks_team_id_teams",
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_tasks"),
    )
    op.create_index("ix_tasks_owner_id", "tasks", ["owner_id"])
    op.create_index("ix_tasks_status", "tasks", ["status"])
    op.create_index("ix_tasks_priority", "tasks", ["priority"])
    op.create_index("ix_tasks_due_date", "tasks", ["due_date"])
    op.create_index("ix_tasks_team_id", "tasks", ["team_id"])
    op.create_index("ix_tasks_assigned_to_id", "tasks", ["assigned_to_id"])
    op.create_index("ix_tasks_is_archived", "tasks", ["is_archived"])
    op.create_index("ix_tasks_status_priority", "tasks", ["status", "priority"])

    # ── comments ──────────────────────────────────────────────────────────────
    op.create_table(
        "comments",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("task_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("author_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.ForeignKeyConstraint(
            ["task_id"], ["tasks.id"],
            name="fk_comments_task_id_tasks",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["author_id"], ["users.id"],
            name="fk_comments_author_id_users",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_comments"),
    )
    op.create_index("ix_comments_task_id", "comments", ["task_id"])
    op.create_index("ix_comments_author_id", "comments", ["author_id"])

    # ── attachments ───────────────────────────────────────────────────────────
    op.create_table(
        "attachments",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column("filename", sa.String(500), nullable=False),
        sa.Column("file_url", sa.String(2000), nullable=False),
        sa.Column("file_size", sa.BigInteger(), nullable=False),
        sa.Column("mime_type", sa.String(200), nullable=False),
        sa.Column("task_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("uploaded_by", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.ForeignKeyConstraint(
            ["task_id"], ["tasks.id"],
            name="fk_attachments_task_id_tasks",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["uploaded_by"], ["users.id"],
            name="fk_attachments_uploaded_by_users",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_attachments"),
    )
    op.create_index("ix_attachments_task_id", "attachments", ["task_id"])
    op.create_index("ix_attachments_uploaded_by", "attachments", ["uploaded_by"])

    # ── notifications ─────────────────────────────────────────────────────────
    op.create_table(
        "notifications",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("message", sa.String(1000), nullable=False),
        sa.Column(
            "type",
            sa.Enum(
                "task_assigned", "task_updated", "task_completed",
                "comment_added", "team_invite", "team_removed", "system",
                name="notification_type_enum",
            ),
            nullable=False,
        ),
        sa.Column("is_read", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("reference_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"],
            name="fk_notifications_user_id_users",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_notifications"),
    )
    op.create_index("ix_notifications_user_id", "notifications", ["user_id"])
    op.create_index("ix_notifications_user_is_read", "notifications", ["user_id", "is_read"])
    op.create_index("ix_notifications_created_at", "notifications", ["created_at"])

    # ── activity_logs ─────────────────────────────────────────────────────────
    op.create_table(
        "activity_logs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("action", sa.String(200), nullable=False),
        sa.Column("entity_type", sa.String(100), nullable=False),
        sa.Column("entity_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("meta", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"],
            name="fk_activity_logs_user_id_users",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_activity_logs"),
    )
    op.create_index("ix_activity_logs_user_id", "activity_logs", ["user_id"])
    op.create_index(
        "ix_activity_logs_entity_type_id", "activity_logs", ["entity_type", "entity_id"]
    )
    op.create_index("ix_activity_logs_created_at", "activity_logs", ["created_at"])
    op.create_index("ix_activity_logs_action", "activity_logs", ["action"])


def downgrade() -> None:
    # Drop tables in reverse dependency order
    op.drop_table("activity_logs")
    op.drop_table("notifications")
    op.drop_table("attachments")
    op.drop_table("comments")
    op.drop_table("tasks")
    op.drop_table("team_members")
    op.drop_table("teams")
    op.drop_table("users")

    # Drop enums
    for enum_name in [
        "notification_type_enum",
        "team_member_role_enum",
        "task_priority_enum",
        "task_status_enum",
        "user_role_enum",
    ]:
        op.execute(f"DROP TYPE IF EXISTS {enum_name}")
