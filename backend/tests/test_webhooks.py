"""
Tests for webhooks module.
"""

import pytest
from httpx import AsyncClient
from unittest.mock import patch, AsyncMock
from uuid import uuid4
import hmac
import hashlib
import json


class TestWebhookEndpoints:
    """Test webhook API endpoints."""

    @pytest.mark.asyncio
    async def test_list_webhooks_requires_auth(self, client: AsyncClient):
        """Test that webhook listing requires authentication."""
        response = await client.get("/api/v1/webhooks")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_list_webhooks(
        self, client: AsyncClient, auth_headers: dict
    ):
        """Test listing webhooks."""
        with patch("app.modules.webhooks.service.WebhookService.list_webhooks") as mock:
            mock.return_value = [
                {
                    "id": str(uuid4()),
                    "url": "https://example.com/webhook",
                    "events": ["chat.message", "document.processed"],
                    "is_active": True,
                },
            ]

            response = await client.get(
                "/api/v1/webhooks",
                headers=auth_headers,
            )

            assert response.status_code == 200
            data = response.json()
            assert isinstance(data, list)

    @pytest.mark.asyncio
    async def test_create_webhook(
        self, client: AsyncClient, auth_headers: dict
    ):
        """Test creating a webhook."""
        with patch("app.modules.webhooks.service.WebhookService.create_webhook") as mock:
            webhook_id = str(uuid4())
            mock.return_value = {
                "id": webhook_id,
                "url": "https://example.com/webhook",
                "events": ["chat.message"],
                "secret": "whsec_test123",
                "is_active": True,
            }

            response = await client.post(
                "/api/v1/webhooks",
                headers=auth_headers,
                json={
                    "url": "https://example.com/webhook",
                    "events": ["chat.message"],
                },
            )

            assert response.status_code in [200, 201]
            data = response.json()
            assert "id" in data
            assert "secret" in data

    @pytest.mark.asyncio
    async def test_create_webhook_invalid_url(
        self, client: AsyncClient, auth_headers: dict
    ):
        """Test creating webhook with invalid URL."""
        response = await client.post(
            "/api/v1/webhooks",
            headers=auth_headers,
            json={
                "url": "not-a-valid-url",
                "events": ["chat.message"],
            },
        )
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_update_webhook(
        self, client: AsyncClient, auth_headers: dict
    ):
        """Test updating a webhook."""
        webhook_id = str(uuid4())

        with patch("app.modules.webhooks.service.WebhookService.update_webhook") as mock:
            mock.return_value = {
                "id": webhook_id,
                "url": "https://example.com/new-webhook",
                "events": ["chat.message", "document.processed"],
                "is_active": True,
            }

            response = await client.patch(
                f"/api/v1/webhooks/{webhook_id}",
                headers=auth_headers,
                json={
                    "url": "https://example.com/new-webhook",
                },
            )

            assert response.status_code in [200, 404]

    @pytest.mark.asyncio
    async def test_delete_webhook(
        self, client: AsyncClient, auth_headers: dict
    ):
        """Test deleting a webhook."""
        webhook_id = str(uuid4())

        with patch("app.modules.webhooks.service.WebhookService.delete_webhook") as mock:
            mock.return_value = True

            response = await client.delete(
                f"/api/v1/webhooks/{webhook_id}",
                headers=auth_headers,
            )

            assert response.status_code in [200, 204, 404]

    @pytest.mark.asyncio
    async def test_get_webhook_deliveries(
        self, client: AsyncClient, auth_headers: dict
    ):
        """Test getting webhook delivery history."""
        webhook_id = str(uuid4())

        with patch("app.modules.webhooks.service.WebhookService.get_deliveries") as mock:
            mock.return_value = [
                {
                    "id": str(uuid4()),
                    "event": "chat.message",
                    "status": "delivered",
                    "response_code": 200,
                    "delivered_at": "2025-01-22T10:00:00Z",
                },
            ]

            response = await client.get(
                f"/api/v1/webhooks/{webhook_id}/deliveries",
                headers=auth_headers,
            )

            assert response.status_code in [200, 404]

    @pytest.mark.asyncio
    async def test_retry_webhook_delivery(
        self, client: AsyncClient, auth_headers: dict
    ):
        """Test retrying a failed webhook delivery."""
        webhook_id = str(uuid4())
        delivery_id = str(uuid4())

        with patch("app.modules.webhooks.service.WebhookService.retry_delivery") as mock:
            mock.return_value = {"queued": True}

            response = await client.post(
                f"/api/v1/webhooks/{webhook_id}/deliveries/{delivery_id}/retry",
                headers=auth_headers,
            )

            assert response.status_code in [200, 202, 404]


class TestWebhookService:
    """Test webhook service logic."""

    @pytest.mark.asyncio
    async def test_generate_signature(self):
        """Test webhook signature generation."""
        from app.modules.webhooks.service import WebhookService

        service = WebhookService()

        secret = "whsec_test123"
        payload = {"event": "chat.message", "data": {"message": "Hello"}}
        timestamp = "1705916400"

        signature = service.generate_signature(
            secret=secret,
            payload=payload,
            timestamp=timestamp,
        )

        assert signature is not None
        assert signature.startswith("v1=")

    @pytest.mark.asyncio
    async def test_verify_signature(self):
        """Test webhook signature verification."""
        from app.modules.webhooks.service import WebhookService

        service = WebhookService()

        secret = "whsec_test123"
        payload = {"event": "chat.message", "data": {"message": "Hello"}}
        timestamp = "1705916400"

        # Generate signature
        signature = service.generate_signature(secret, payload, timestamp)

        # Verify signature
        is_valid = service.verify_signature(
            secret=secret,
            payload=payload,
            timestamp=timestamp,
            signature=signature,
        )

        assert is_valid is True

        # Invalid signature should fail
        is_valid = service.verify_signature(
            secret=secret,
            payload=payload,
            timestamp=timestamp,
            signature="v1=invalid",
        )

        assert is_valid is False

    @pytest.mark.asyncio
    async def test_should_retry(self):
        """Test retry decision logic."""
        from app.modules.webhooks.service import WebhookService

        service = WebhookService()

        # Should retry on 5xx errors
        assert service.should_retry(500, attempts=1) is True
        assert service.should_retry(502, attempts=1) is True
        assert service.should_retry(503, attempts=1) is True

        # Should not retry on 4xx errors (except 429)
        assert service.should_retry(400, attempts=1) is False
        assert service.should_retry(404, attempts=1) is False

        # Should retry on 429 (rate limited)
        assert service.should_retry(429, attempts=1) is True

        # Should not retry after max attempts
        assert service.should_retry(500, attempts=5) is False

    @pytest.mark.asyncio
    async def test_calculate_backoff(self):
        """Test exponential backoff calculation."""
        from app.modules.webhooks.service import WebhookService

        service = WebhookService()

        # First retry: 1 minute
        delay = service.calculate_backoff(attempt=1)
        assert delay == 60

        # Second retry: 2 minutes
        delay = service.calculate_backoff(attempt=2)
        assert delay == 120

        # Third retry: 4 minutes
        delay = service.calculate_backoff(attempt=3)
        assert delay == 240

        # Should cap at max delay
        delay = service.calculate_backoff(attempt=10)
        assert delay <= 3600  # Max 1 hour


class TestWebhookDelivery:
    """Test webhook delivery functionality."""

    @pytest.mark.asyncio
    async def test_deliver_webhook(self):
        """Test delivering a webhook."""
        from app.modules.webhooks.service import WebhookService

        service = WebhookService()

        with patch("httpx.AsyncClient.post") as mock_post:
            mock_response = AsyncMock()
            mock_response.status_code = 200
            mock_response.text = "OK"
            mock_post.return_value = mock_response

            result = await service.deliver(
                url="https://example.com/webhook",
                event="chat.message",
                payload={"message": "Hello"},
                secret="whsec_test123",
            )

            assert result["success"] is True
            assert result["status_code"] == 200

    @pytest.mark.asyncio
    async def test_deliver_webhook_failure(self):
        """Test webhook delivery failure handling."""
        from app.modules.webhooks.service import WebhookService

        service = WebhookService()

        with patch("httpx.AsyncClient.post") as mock_post:
            mock_response = AsyncMock()
            mock_response.status_code = 500
            mock_response.text = "Internal Server Error"
            mock_post.return_value = mock_response

            result = await service.deliver(
                url="https://example.com/webhook",
                event="chat.message",
                payload={"message": "Hello"},
                secret="whsec_test123",
            )

            assert result["success"] is False
            assert result["status_code"] == 500

    @pytest.mark.asyncio
    async def test_deliver_webhook_timeout(self):
        """Test webhook delivery timeout handling."""
        from app.modules.webhooks.service import WebhookService
        import httpx

        service = WebhookService()

        with patch("httpx.AsyncClient.post") as mock_post:
            mock_post.side_effect = httpx.TimeoutException("Timeout")

            result = await service.deliver(
                url="https://example.com/webhook",
                event="chat.message",
                payload={"message": "Hello"},
                secret="whsec_test123",
            )

            assert result["success"] is False
            assert "timeout" in result["error"].lower()


class TestWebhookSchemas:
    """Test webhook schemas."""

    def test_webhook_create_request(self):
        """Test webhook creation request schema."""
        from app.modules.webhooks.schemas import WebhookCreateRequest

        request = WebhookCreateRequest(
            url="https://example.com/webhook",
            events=["chat.message", "document.processed"],
        )
        assert request.url == "https://example.com/webhook"
        assert len(request.events) == 2

    def test_webhook_create_invalid_event(self):
        """Test webhook creation with invalid event."""
        from app.modules.webhooks.schemas import WebhookCreateRequest
        from pydantic import ValidationError

        # Invalid event type should be rejected
        with pytest.raises(ValidationError):
            WebhookCreateRequest(
                url="https://example.com/webhook",
                events=["invalid.event"],
            )

    def test_webhook_response(self):
        """Test webhook response schema."""
        from app.modules.webhooks.schemas import WebhookResponse

        response = WebhookResponse(
            id=str(uuid4()),
            url="https://example.com/webhook",
            events=["chat.message"],
            is_active=True,
            created_at="2025-01-22T00:00:00Z",
        )
        assert response.is_active is True


class TestWebhookEvents:
    """Test webhook event types."""

    def test_valid_event_types(self):
        """Test all valid webhook event types."""
        from app.modules.webhooks.schemas import WebhookEvent

        valid_events = [
            "chat.message",
            "chat.conversation.created",
            "chat.conversation.deleted",
            "document.uploaded",
            "document.processed",
            "document.deleted",
            "agent.created",
            "agent.updated",
            "agent.deleted",
            "usage.threshold.warning",
            "usage.threshold.critical",
            "payment.success",
            "payment.failed",
        ]

        for event in valid_events:
            assert WebhookEvent.is_valid(event) is True
