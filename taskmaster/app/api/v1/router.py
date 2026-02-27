"""
Aggregates all v1 API routers into a single APIRouter.
"""
from __future__ import annotations

from fastapi import APIRouter

from app.api.v1 import (
    activity_logs,
    admin,
    attachments,
    auth,
    comments,
    notifications,
    tasks,
    teams,
    users,
    websocket,
)

api_router = APIRouter()

api_router.include_router(auth.router)
api_router.include_router(users.router)
api_router.include_router(tasks.router)
api_router.include_router(teams.router)
api_router.include_router(comments.router)
api_router.include_router(attachments.router)
api_router.include_router(notifications.router)
api_router.include_router(activity_logs.router)
api_router.include_router(admin.router)
api_router.include_router(websocket.router)
