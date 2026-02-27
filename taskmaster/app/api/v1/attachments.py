"""
Attachment routes nested under tasks.
/api/v1/tasks/{task_id}/attachments
Supports multipart/form-data file upload.
"""
from __future__ import annotations

import os
import uuid

from fastapi import APIRouter, Query, UploadFile, status
from fastapi.responses import FileResponse

from app.core.config import settings
from app.core.dependencies import CurrentUser, DBSession
from app.core.exceptions import FileTooLargeException, ForbiddenException, NotFoundException
from app.crud.attachment import crud_attachment
from app.crud.task import crud_task
from app.schemas.attachment import AttachmentRead
from app.schemas.pagination import PaginatedResponse
from app.services.activity_service import activity_service

router = APIRouter(tags=["Attachments"])


@router.get(
    "/tasks/{task_id}/attachments",
    response_model=PaginatedResponse[AttachmentRead],
    summary="List attachments for a task",
)
async def list_attachments(
    task_id: uuid.UUID,
    current_user: CurrentUser,
    db: DBSession,
    page: int = Query(default=1, ge=1),
    size: int = Query(default=20, ge=1, le=100),
) -> PaginatedResponse[AttachmentRead]:
    task = await crud_task.get(db, task_id)
    if task is None:
        raise NotFoundException("Task", str(task_id))

    attachments, total = await crud_attachment.list_by_task(
        db, task_id=task_id, skip=(page - 1) * size, limit=size
    )
    return PaginatedResponse(
        items=[AttachmentRead.model_validate(a) for a in attachments],
        total=total,
        page=page,
        size=size,
    )


@router.post(
    "/tasks/{task_id}/attachments",
    response_model=AttachmentRead,
    status_code=status.HTTP_201_CREATED,
    summary="Upload a file attachment to a task",
)
async def upload_attachment(
    task_id: uuid.UUID,
    file: UploadFile,
    current_user: CurrentUser,
    db: DBSession,
) -> AttachmentRead:
    task = await crud_task.get(db, task_id)
    if task is None:
        raise NotFoundException("Task", str(task_id))

    # Read file content and validate size
    content = await file.read()
    if len(content) > settings.max_file_size_bytes:
        raise FileTooLargeException(settings.MAX_FILE_SIZE_MB)

    # Persist file to upload directory
    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
    safe_filename = f"{uuid.uuid4()}_{file.filename}"
    file_path = os.path.join(settings.UPLOAD_DIR, safe_filename)

    with open(file_path, "wb") as f:
        f.write(content)

    attachment = await crud_attachment.create_attachment(
        db,
        filename=file.filename or "unknown",
        file_url=file_path,
        file_size=len(content),
        mime_type=file.content_type or "application/octet-stream",
        task_id=task_id,
        uploaded_by=current_user.id,
    )

    await activity_service.log(
        db,
        user_id=current_user.id,
        action="attachment_uploaded",
        entity_type="attachment",
        entity_id=attachment.id,
        meta={"task_id": str(task_id), "filename": file.filename},
    )

    return AttachmentRead.model_validate(attachment)


@router.delete(
    "/tasks/{task_id}/attachments/{attachment_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete an attachment",
)
async def delete_attachment(
    task_id: uuid.UUID,
    attachment_id: uuid.UUID,
    current_user: CurrentUser,
    db: DBSession,
) -> None:
    attachment = await crud_attachment.get(db, attachment_id)
    if attachment is None or attachment.task_id != task_id:
        raise NotFoundException("Attachment", str(attachment_id))

    if attachment.uploaded_by != current_user.id and current_user.role != "admin":
        raise ForbiddenException("Only the uploader can delete this attachment")

    # Remove file from disk
    if os.path.exists(attachment.file_url):
        os.remove(attachment.file_url)

    await crud_attachment.remove(db, id=attachment_id)
