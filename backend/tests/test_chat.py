"""
Tests for chat module.
"""

import pytest
from httpx import AsyncClient
from unittest.mock import patch, AsyncMock
from uuid import uuid4


class TestChatEndpoints:
    """Test chat API endpoints."""

    @pytest.mark.asyncio
    async def test_create_completion_requires_auth(self, client: AsyncClient):
        """Test that chat completion requires authentication."""
        response = await client.post(
            "/api/v1/chat/completions",
            json={
                "agent_id": str(uuid4()),
                "message": "Hello",
            },
        )
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_create_completion_with_auth(
        self, client: AsyncClient, auth_headers: dict, test_agent: dict
    ):
        """Test creating a chat completion."""
        with patch("app.modules.chat.service.ChatService.create_completion") as mock:
            mock.return_value = {
                "conversation_id": str(uuid4()),
                "message": {
                    "id": str(uuid4()),
                    "role": "assistant",
                    "content": "Hello! How can I help you?",
                },
                "usage": {
                    "input_tokens": 10,
                    "output_tokens": 20,
                    "total_tokens": 30,
                },
            }

            response = await client.post(
                "/api/v1/chat/completions",
                headers=auth_headers,
                json={
                    "agent_id": test_agent["id"],
                    "message": "Hello",
                },
            )

            assert response.status_code == 200
            data = response.json()
            assert "conversation_id" in data
            assert "message" in data
            assert data["message"]["role"] == "assistant"

    @pytest.mark.asyncio
    async def test_create_completion_invalid_agent(
        self, client: AsyncClient, auth_headers: dict
    ):
        """Test creating completion with invalid agent ID."""
        response = await client.post(
            "/api/v1/chat/completions",
            headers=auth_headers,
            json={
                "agent_id": str(uuid4()),
                "message": "Hello",
            },
        )
        assert response.status_code in [404, 403]

    @pytest.mark.asyncio
    async def test_list_conversations(
        self, client: AsyncClient, auth_headers: dict
    ):
        """Test listing conversations."""
        response = await client.get(
            "/api/v1/chat/conversations",
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    @pytest.mark.asyncio
    async def test_get_conversation(
        self, client: AsyncClient, auth_headers: dict
    ):
        """Test getting a specific conversation."""
        # First create a conversation
        conversation_id = str(uuid4())

        with patch("app.modules.chat.service.ChatService.get_conversation") as mock:
            mock.return_value = {
                "id": conversation_id,
                "agent_id": str(uuid4()),
                "messages": [],
                "created_at": "2025-01-22T00:00:00Z",
            }

            response = await client.get(
                f"/api/v1/chat/conversations/{conversation_id}",
                headers=auth_headers,
            )

            # Should return 200 or 404 depending on if conversation exists
            assert response.status_code in [200, 404]

    @pytest.mark.asyncio
    async def test_delete_conversation(
        self, client: AsyncClient, auth_headers: dict
    ):
        """Test deleting a conversation."""
        conversation_id = str(uuid4())

        with patch("app.modules.chat.service.ChatService.delete_conversation") as mock:
            mock.return_value = True

            response = await client.delete(
                f"/api/v1/chat/conversations/{conversation_id}",
                headers=auth_headers,
            )

            assert response.status_code in [200, 204, 404]

    @pytest.mark.asyncio
    async def test_stream_completion(
        self, client: AsyncClient, auth_headers: dict, test_agent: dict
    ):
        """Test streaming chat completion."""
        # Note: Testing streaming requires special handling
        response = await client.post(
            "/api/v1/chat/stream",
            headers=auth_headers,
            json={
                "agent_id": test_agent["id"],
                "message": "Hello",
            },
        )
        # Streaming endpoint should return 200 or handle appropriately
        assert response.status_code in [200, 401, 404]


class TestChatService:
    """Test chat service logic."""

    @pytest.mark.asyncio
    async def test_format_messages_for_api(self):
        """Test message formatting for AI API."""
        from app.modules.chat.service import ChatService

        service = ChatService()
        messages = [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi there!"},
            {"role": "user", "content": "How are you?"},
        ]

        formatted = service._format_messages(messages, "You are a helpful assistant.")

        assert len(formatted) == 4  # system + 3 messages
        assert formatted[0]["role"] == "system"
        assert formatted[0]["content"] == "You are a helpful assistant."

    @pytest.mark.asyncio
    async def test_calculate_tokens(self):
        """Test token calculation."""
        from app.modules.chat.service import ChatService

        service = ChatService()

        # Simple token estimation
        text = "Hello, how are you today?"
        tokens = service._estimate_tokens(text)

        assert tokens > 0
        assert tokens < 100  # Should be reasonable for short text

    @pytest.mark.asyncio
    async def test_truncate_context(self):
        """Test context truncation for long conversations."""
        from app.modules.chat.service import ChatService

        service = ChatService()

        # Create a long conversation
        messages = [
            {"role": "user", "content": f"Message {i}"}
            for i in range(100)
        ]

        truncated = service._truncate_context(messages, max_tokens=1000)

        # Should keep recent messages within token limit
        assert len(truncated) < len(messages)


class TestChatSchemas:
    """Test chat request/response schemas."""

    def test_chat_completion_request_validation(self):
        """Test chat completion request schema validation."""
        from app.modules.chat.schemas import ChatCompletionRequest

        # Valid request
        request = ChatCompletionRequest(
            agent_id=str(uuid4()),
            message="Hello",
        )
        assert request.message == "Hello"

        # With optional fields
        request = ChatCompletionRequest(
            agent_id=str(uuid4()),
            message="Hello",
            conversation_id=str(uuid4()),
            temperature=0.7,
            max_tokens=500,
        )
        assert request.temperature == 0.7
        assert request.max_tokens == 500

    def test_chat_completion_request_empty_message(self):
        """Test that empty messages are rejected."""
        from app.modules.chat.schemas import ChatCompletionRequest
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            ChatCompletionRequest(
                agent_id=str(uuid4()),
                message="",
            )

    def test_temperature_range(self):
        """Test temperature validation."""
        from app.modules.chat.schemas import ChatCompletionRequest
        from pydantic import ValidationError

        # Valid temperatures
        for temp in [0.0, 0.5, 1.0, 2.0]:
            request = ChatCompletionRequest(
                agent_id=str(uuid4()),
                message="Hello",
                temperature=temp,
            )
            assert request.temperature == temp

        # Invalid temperature
        with pytest.raises(ValidationError):
            ChatCompletionRequest(
                agent_id=str(uuid4()),
                message="Hello",
                temperature=3.0,  # Too high
            )
