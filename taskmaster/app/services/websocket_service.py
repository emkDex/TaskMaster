"""
WebSocket connection manager.
Manages active WebSocket connections and provides message broadcasting.
"""
from __future__ import annotations

import asyncio
import json
import logging
from typing import Any

from fastapi import WebSocket

logger = logging.getLogger(__name__)


class ConnectionManager:
    """
    Manages active WebSocket connections keyed by user_id (string).
    Supports personal messages and broadcast to all connected clients.
    """

    def __init__(self) -> None:
        # user_id → list of active WebSocket connections (a user may have multiple tabs)
        self._connections: dict[str, list[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, user_id: str) -> None:
        await websocket.accept()
        if user_id not in self._connections:
            self._connections[user_id] = []
        self._connections[user_id].append(websocket)
        logger.info("WebSocket connected: user_id=%s", user_id)

    def disconnect(self, websocket: WebSocket, user_id: str) -> None:
        if user_id in self._connections:
            try:
                self._connections[user_id].remove(websocket)
            except ValueError:
                pass
            if not self._connections[user_id]:
                del self._connections[user_id]
        logger.info("WebSocket disconnected: user_id=%s", user_id)

    def is_connected(self, user_id: str) -> bool:
        return user_id in self._connections and bool(self._connections[user_id])

    async def send_personal_message(
        self, user_id: str, data: dict[str, Any]
    ) -> None:
        """Send a JSON message to all connections for a specific user."""
        connections = self._connections.get(user_id, [])
        if not connections:
            return
        message = json.dumps(data)
        dead: list[WebSocket] = []
        for ws in connections:
            try:
                await ws.send_text(message)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self.disconnect(ws, user_id)

    async def broadcast(self, data: dict[str, Any]) -> None:
        """Send a JSON message to every connected client."""
        message = json.dumps(data)
        all_dead: list[tuple[WebSocket, str]] = []
        for user_id, connections in list(self._connections.items()):
            for ws in connections:
                try:
                    await ws.send_text(message)
                except Exception:
                    all_dead.append((ws, user_id))
        for ws, user_id in all_dead:
            self.disconnect(ws, user_id)

    async def send_ping(self, websocket: WebSocket) -> None:
        """Send a heartbeat ping frame."""
        try:
            await websocket.send_text(json.dumps({"type": "ping"}))
        except Exception:
            pass

    @property
    def connected_user_count(self) -> int:
        return len(self._connections)


# Singleton instance shared across the application
ws_manager = ConnectionManager()
