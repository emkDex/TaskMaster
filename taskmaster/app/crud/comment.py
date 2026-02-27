"""
Comment CRUD operations.
"""
from __future__ import annotations

import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.crud.base import CRUDBase
from app.models.comment import Comment
from app.schemas.comment import CommentCreate, CommentUpdate


class CRUDComment(CRUDBase[Comment, CommentCreate, CommentUpdate]):

    async def create_comment(
        self,
        db: AsyncSession,
        *,
        content: str,
        task_id: uuid.UUID,
        author_id: uuid.UUID,
    ) -> Comment:
        comment = Comment(content=content, task_id=task_id, author_id=author_id)
        db.add(comment)
        await db.flush()
        await db.refresh(comment)
        return comment

    async def list_by_task(
        self,
        db: AsyncSession,
        *,
        task_id: uuid.UUID,
        skip: int = 0,
        limit: int = 100,
    ) -> tuple[list[Comment], int]:
        count_result = await db.execute(
            select(func.count()).select_from(Comment).where(Comment.task_id == task_id)
        )
        total = count_result.scalar_one()

        result = await db.execute(
            select(Comment)
            .options(selectinload(Comment.author))
            .where(Comment.task_id == task_id)
            .order_by(Comment.created_at.asc())
            .offset(skip)
            .limit(limit)
        )
        return list(result.scalars().all()), total

    async def get_with_author(
        self, db: AsyncSession, comment_id: uuid.UUID
    ) -> Comment | None:
        result = await db.execute(
            select(Comment)
            .options(selectinload(Comment.author))
            .where(Comment.id == comment_id)
        )
        return result.scalar_one_or_none()


crud_comment = CRUDComment(Comment)
