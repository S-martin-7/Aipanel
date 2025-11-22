"""
Chat Module - WebSocket Manager

Handles real-time WebSocket connections for chat.
"""

import json
from typing import Optional
from datetime import datetime

from fastapi import WebSocket, WebSocketDisconnect
from sqlalchemy.ext.asyncio import AsyncSession

from app.utils.logger import get_logger
from .service import ChatService
from .schemas import ChatCompletionRequest

logger = get_logger(__name__)


class ConnectionManager:
    """
    Manages WebSocket connections for real-time chat.

    Features:
    - Connection tracking by user and conversation
    - Message broadcasting
    - Heartbeat monitoring
    """

    def __init__(self):
        """Initialize connection manager."""
        # Active connections: {user_id: {conversation_id: WebSocket}}
        self.active_connections: dict[str, dict[str, WebSocket]] = {}
        # Connection metadata
        self.connection_info: dict[str, dict] = {}

    async def connect(
        self,
        websocket: WebSocket,
        user_id: str,
        conversation_id: Optional[str] = None,
    ) -> None:
        """
        Accept and register a new connection.

        Args:
            websocket: WebSocket connection
            user_id: User ID
            conversation_id: Optional conversation ID
        """
        await websocket.accept()

        if user_id not in self.active_connections:
            self.active_connections[user_id] = {}

        conn_key = conversation_id or "global"
        self.active_connections[user_id][conn_key] = websocket

        # Store connection metadata
        self.connection_info[f"{user_id}:{conn_key}"] = {
            "connected_at": datetime.utcnow().isoformat(),
            "last_activity": datetime.utcnow().isoformat(),
        }

        logger.info(f"WebSocket connected: user={user_id}, conversation={conversation_id}")

    def disconnect(
        self,
        user_id: str,
        conversation_id: Optional[str] = None,
    ) -> None:
        """
        Remove a connection.

        Args:
            user_id: User ID
            conversation_id: Optional conversation ID
        """
        conn_key = conversation_id or "global"

        if user_id in self.active_connections:
            self.active_connections[user_id].pop(conn_key, None)
            if not self.active_connections[user_id]:
                del self.active_connections[user_id]

        self.connection_info.pop(f"{user_id}:{conn_key}", None)
        logger.info(f"WebSocket disconnected: user={user_id}, conversation={conversation_id}")

    async def send_message(
        self,
        message: dict,
        user_id: str,
        conversation_id: Optional[str] = None,
    ) -> None:
        """
        Send message to a specific connection.

        Args:
            message: Message to send
            user_id: Target user ID
            conversation_id: Target conversation ID
        """
        conn_key = conversation_id or "global"

        if (
            user_id in self.active_connections
            and conn_key in self.active_connections[user_id]
        ):
            websocket = self.active_connections[user_id][conn_key]
            try:
                await websocket.send_json(message)
                # Update activity
                info_key = f"{user_id}:{conn_key}"
                if info_key in self.connection_info:
                    self.connection_info[info_key]["last_activity"] = datetime.utcnow().isoformat()
            except Exception as e:
                logger.error(f"Failed to send message: {e}")
                self.disconnect(user_id, conversation_id)

    async def broadcast_to_conversation(
        self,
        message: dict,
        conversation_id: str,
    ) -> None:
        """
        Broadcast message to all connections in a conversation.

        Args:
            message: Message to broadcast
            conversation_id: Conversation ID
        """
        for user_id, connections in self.active_connections.items():
            if conversation_id in connections:
                await self.send_message(message, user_id, conversation_id)

    def get_connection_count(self) -> int:
        """Get total number of active connections."""
        return sum(len(conns) for conns in self.active_connections.values())

    def is_connected(
        self,
        user_id: str,
        conversation_id: Optional[str] = None,
    ) -> bool:
        """Check if a user is connected."""
        conn_key = conversation_id or "global"
        return (
            user_id in self.active_connections
            and conn_key in self.active_connections[user_id]
        )


# Global connection manager instance
manager = ConnectionManager()


async def handle_websocket_chat(
    websocket: WebSocket,
    user_id: str,
    tenant_id: str,
    db: AsyncSession,
) -> None:
    """
    Handle WebSocket chat connection.

    Protocol:
    - Client sends: {"type": "message", "agent_id": "...", "content": "..."}
    - Server sends: {"type": "chunk", "content": "..."} or {"type": "done"}
    - Server sends: {"type": "error", "message": "..."}

    Args:
        websocket: WebSocket connection
        user_id: Authenticated user ID
        tenant_id: Tenant ID
        db: Database session
    """
    await manager.connect(websocket, user_id)
    service = ChatService(db)

    try:
        while True:
            # Receive message from client
            data = await websocket.receive_json()

            msg_type = data.get("type")

            if msg_type == "ping":
                await websocket.send_json({"type": "pong"})
                continue

            if msg_type == "message":
                agent_id = data.get("agent_id")
                content = data.get("content")
                conversation_id = data.get("conversation_id")

                if not agent_id or not content:
                    await websocket.send_json({
                        "type": "error",
                        "message": "Missing agent_id or content"
                    })
                    continue

                # Create completion request
                request = ChatCompletionRequest(
                    agent_id=agent_id,
                    conversation_id=conversation_id,
                    message=content,
                    stream=True,
                )

                # Stream response
                try:
                    # Create a mock user object with tenant_id
                    class MockUser:
                        def __init__(self, uid, tid):
                            self.id = uid
                            self.tenant_id = tid

                    mock_user = MockUser(user_id, tenant_id)

                    async for chunk in service.stream_completion(
                        request=request,
                        user=mock_user,
                        tenant_id=tenant_id,
                    ):
                        # Parse SSE format and send as JSON
                        if chunk.startswith("data: "):
                            chunk_data = chunk[6:].strip()
                            if chunk_data == "[DONE]":
                                await websocket.send_json({"type": "done"})
                            else:
                                try:
                                    parsed = json.loads(chunk_data)
                                    await websocket.send_json({
                                        "type": "chunk",
                                        "conversation_id": parsed.get("conversation_id"),
                                        "content": parsed.get("delta", ""),
                                        "finish_reason": parsed.get("finish_reason"),
                                    })
                                except json.JSONDecodeError:
                                    pass

                except Exception as e:
                    logger.error(f"WebSocket stream error: {e}")
                    await websocket.send_json({
                        "type": "error",
                        "message": str(e)
                    })

    except WebSocketDisconnect:
        manager.disconnect(user_id)
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        manager.disconnect(user_id)
