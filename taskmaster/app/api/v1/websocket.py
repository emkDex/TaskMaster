"""
WebSocket endpoint.
Clients connect with a valid JWT access token as a query parameter.
Heartbeat ping/pong every 30 seconds keeps connections alive.
"""
from __future__ import annotations

import asyncio
import logging

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from jose import JWTError

from app.core.security import decode_access_token
from app.services.websocket_service import ws_manager

logger = logging.getLogger(__name__)

router = APIRouter(tags=["WebSocket"])

HEARTBEAT_INTERVAL = 30  # seconds


@router.websocket("/ws/{user_id}")
async def websocket_endpoint(websocket: WebSocket, user_id: str) -> None:
    """
    WebSocket endpoint for real-time notifications.

    Query parameters:
        token: A valid JWT access token.

    The server sends:
        - {"type": "ping"} every 30 seconds as a heartbeat.
        - {"type": "notification", "data": {...}} when a notification is created.
        - {"type": "connected", "user_id": "..."} on successful connection.

    The client should respond to pings with {"type": "pong"}.
    """
    # Validate token before accepting
    token = websocket.query_params.get("token")
    if not token:
        await websocket.close(code=4001, reason="Missing authentication token")
        return

    try:
        payload = decode_access_token(token)
        token_user_id = payload.get("sub")
    except JWTError:
        await websocket.close(code=4001, reason="Invalid or expired token")
        return

    # Ensure the token subject matches the path parameter
    if token_user_id != user_id:
        await websocket.close(code=4003, reason="Token user_id mismatch")
        return

    await ws_manager.connect(websocket, user_id)

    try:
        # Send connection confirmation
        await websocket.send_json({"type": "connected", "user_id": user_id})

        # Start heartbeat task
        heartbeat_task = asyncio.create_task(_heartbeat(websocket, user_id))

        try:
            while True:
                # Wait for messages from client (e.g., pong responses)
                data = await websocket.receive_json()
                if data.get("type") == "pong":
                    logger.debug("Received pong from user_id=%s", user_id)
        finally:
            heartbeat_task.cancel()
            try:
                await heartbeat_task
            except asyncio.CancelledError:
                pass

    except WebSocketDisconnect:
        logger.info("WebSocket client disconnected: user_id=%s", user_id)
    except Exception as exc:
        logger.error("WebSocket error for user_id=%s: %s", user_id, exc)
    finally:
        ws_manager.disconnect(websocket, user_id)


async def _heartbeat(websocket: WebSocket, user_id: str) -> None:
    """Send periodic ping frames to keep the connection alive."""
    while True:
        await asyncio.sleep(HEARTBEAT_INTERVAL)
        try:
            await websocket.send_json({"type": "ping"})
        except Exception:
            break
