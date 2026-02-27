"""
Attachment CRUD operations.
"""
from __future__ import annotations

import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.crud.base import CRUDBase
from app.models.attachment import Attachment
from app.schemas.attachment import AttachmentRead


class CRUDAttachment(CRUDBase[Attachment, AttachmentRead, AttachmentRead]):

    async def create_attachment(
        self,
        db: AsyncSession,
        *,
        filename: str,
        file_url: str,
        file_size: int,
        mime_type: str,
        task_id: uuid.UUID,
        uploaded_by: uuid.UUID,
    ) -> Attachment:
        attachment = Attachment(
            filename=filename,
            file_url=file_url,
            file_size=file_size,
            mime_type=mime_type,
            task_id=task_id,
            uploaded_by=uploaded_by,
        )
        db.add(attachment)
        await db.flush()
        await db.refresh(attachment)
        return attachment

    async def list_by_task(
        self,
        db: AsyncSession,
        *,
        task_id: uuid.UUID,
        skip: int = 0,
        limit: int = 100,
    ) -> tuple[list[Attachment], int]:
        count_result = await db.execute(
            select(func.count())
            .select_from(Attachment)
            .where(Attachment.task_id == task_id)
        )
        total = count_result.scalar_one()

        result = await db.execute(
            select(Attachment)
            .options(selectinload(Attachment.uploader))
            .where(Attachment.task_id == task_id)
            .order_by(Attachment.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        return list(result.scalars().all()), total


crud_attachment = CRUDAttachment(Attachment)
