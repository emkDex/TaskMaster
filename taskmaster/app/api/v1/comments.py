"""
Comment routes nested under tasks.
/api/v1/tasks/{task_id}/comments
"""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Query, status

from app.core.dependencies import CurrentUser, DBSession
from app.core.exceptions import ForbiddenException, NotFoundException
from app.crud.comment import crud_comment
from app.crud.task import crud_task
from app.schemas.comment import CommentCreate, CommentRead, CommentUpdate
from app.schemas.pagination import PaginatedResponse
from app.services.activity_service import activity_service
from app.services.notification_service import notification_service

router = APIRouter(tags=["Comments"])


@router.get(
    "/tasks/{task_id}/comments",
    response_model=PaginatedResponse[CommentRead],
    summary="List comments on a task",
)
async def list_comments(
    task_id: uuid.UUID,
    current_user: CurrentUser,
    db: DBSession,
    page: int = Query(default=1, ge=1),
    size: int = Query(default=50, ge=1, le=200),
) -> PaginatedResponse[CommentRead]:
    task = await crud_task.get(db, task_id)
    if task is None:
        raise NotFoundException("Task", str(task_id))

    comments, total = await crud_comment.list_by_task(
        db, task_id=task_id, skip=(page - 1) * size, limit=size
    )
    return PaginatedResponse(
        items=[CommentRead.model_validate(c) for c in comments],
        total=total,
        page=page,
        size=size,
    )


@router.post(
    "/tasks/{task_id}/comments",
    response_model=CommentRead,
    status_code=status.HTTP_201_CREATED,
    summary="Add a comment to a task",
)
async def create_comment(
    task_id: uuid.UUID,
    comment_in: CommentCreate,
    current_user: CurrentUser,
    db: DBSession,
) -> CommentRead:
    task = await crud_task.get(db, task_id)
    if task is None:
        raise NotFoundException("Task", str(task_id))

    comment = await crud_comment.create_comment(
        db,
        content=comment_in.content,
        task_id=task_id,
        author_id=current_user.id,
    )

    # Notify task owner if commenter is different
    if task.owner_id != current_user.id:
        await notification_service.notify_comment_added(
            db,
            task_owner_id=task.owner_id,
            task_id=task_id,
            task_title=task.title,
            commenter_name=current_user.username,
        )

    await activity_service.log(
        db,
        user_id=current_user.id,
        action="comment_created",
        entity_type="comment",
        entity_id=comment.id,
        meta={"task_id": str(task_id)},
    )

    result = await crud_comment.get_with_author(db, comment.id)
    return CommentRead.model_validate(result)


@router.put(
    "/tasks/{task_id}/comments/{comment_id}",
    response_model=CommentRead,
    summary="Edit a comment",
)
async def update_comment(
    task_id: uuid.UUID,
    comment_id: uuid.UUID,
    comment_in: CommentUpdate,
    current_user: CurrentUser,
    db: DBSession,
) -> CommentRead:
    comment = await crud_comment.get_with_author(db, comment_id)
    if comment is None or comment.task_id != task_id:
        raise NotFoundException("Comment", str(comment_id))

    if comment.author_id != current_user.id and current_user.role != "admin":
        raise ForbiddenException("Only the comment author can edit this comment")

    updated = await crud_comment.update(db, db_obj=comment, obj_in=comment_in)
    return CommentRead.model_validate(updated)


@router.delete(
    "/tasks/{task_id}/comments/{comment_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a comment",
)
async def delete_comment(
    task_id: uuid.UUID,
    comment_id: uuid.UUID,
    current_user: CurrentUser,
    db: DBSession,
) -> None:
    comment = await crud_comment.get(db, comment_id)
    if comment is None or comment.task_id != task_id:
        raise NotFoundException("Comment", str(comment_id))

    if comment.author_id != current_user.id and current_user.role != "admin":
        raise ForbiddenException("Only the comment author can delete this comment")

    await crud_comment.remove(db, id=comment_id)
