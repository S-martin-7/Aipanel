"""
Tests for payments module (Transbank integration).
"""

import pytest
from httpx import AsyncClient
from unittest.mock import patch, MagicMock
from uuid import uuid4


class TestPaymentsEndpoints:
    """Test payments API endpoints."""

    @pytest.mark.asyncio
    async def test_get_plans(self, client: AsyncClient):
        """Test getting available plans."""
        response = await client.get("/api/v1/payments/plans")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    @pytest.mark.asyncio
    async def test_get_subscription_requires_auth(self, client: AsyncClient):
        """Test that subscription endpoint requires authentication."""
        response = await client.get("/api/v1/payments/subscription")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_get_subscription(
        self, client: AsyncClient, auth_headers: dict
    ):
        """Test getting current subscription."""
        with patch("app.modules.payments.service.PaymentService.get_subscription") as mock:
            mock.return_value = {
                "id": str(uuid4()),
                "plan": "professional",
                "status": "active",
                "current_period_start": "2025-01-01T00:00:00Z",
                "current_period_end": "2025-02-01T00:00:00Z",
            }

            response = await client.get(
                "/api/v1/payments/subscription",
                headers=auth_headers,
            )

            assert response.status_code == 200
            data = response.json()
            assert "plan" in data
            assert "status" in data

    @pytest.mark.asyncio
    async def test_create_checkout(
        self, client: AsyncClient, auth_headers: dict
    ):
        """Test creating checkout session."""
        with patch("app.modules.payments.service.PaymentService.create_checkout") as mock:
            mock.return_value = {
                "token": "webpay_token_123",
                "redirect_url": "https://webpay.transbank.cl/...",
            }

            response = await client.post(
                "/api/v1/payments/checkout",
                headers=auth_headers,
                json={
                    "plan": "professional",
                    "return_url": "https://app.aipanel.cl/billing/callback",
                },
            )

            assert response.status_code == 200
            data = response.json()
            assert "redirect_url" in data

    @pytest.mark.asyncio
    async def test_checkout_invalid_plan(
        self, client: AsyncClient, auth_headers: dict
    ):
        """Test checkout with invalid plan."""
        response = await client.post(
            "/api/v1/payments/checkout",
            headers=auth_headers,
            json={
                "plan": "invalid_plan",
                "return_url": "https://app.aipanel.cl/billing/callback",
            },
        )
        assert response.status_code in [400, 404]

    @pytest.mark.asyncio
    async def test_confirm_payment(self, client: AsyncClient):
        """Test payment confirmation callback."""
        with patch("app.modules.payments.service.PaymentService.confirm_payment") as mock:
            mock.return_value = {
                "success": True,
                "transaction_id": "txn_123",
                "amount": 29900,
            }

            response = await client.post(
                "/api/v1/payments/confirm",
                json={"token_ws": "webpay_token_123"},
            )

            # Transbank confirmation can redirect
            assert response.status_code in [200, 302, 303]

    @pytest.mark.asyncio
    async def test_get_payment_history(
        self, client: AsyncClient, auth_headers: dict
    ):
        """Test getting payment history."""
        with patch("app.modules.payments.service.PaymentService.get_history") as mock:
            mock.return_value = {
                "payments": [
                    {
                        "id": str(uuid4()),
                        "amount": 29900,
                        "status": "completed",
                        "created_at": "2025-01-15T10:00:00Z",
                    },
                ],
                "total": 1,
            }

            response = await client.get(
                "/api/v1/payments/history",
                headers=auth_headers,
            )

            assert response.status_code == 200
            data = response.json()
            assert "payments" in data


class TestTransbankIntegration:
    """Test Transbank integration."""

    @pytest.mark.asyncio
    async def test_create_transaction(self):
        """Test creating Transbank transaction."""
        from app.integrations.transbank_client import TransbankClient

        client = TransbankClient()

        with patch.object(client, "webpay") as mock_webpay:
            mock_transaction = MagicMock()
            mock_transaction.create.return_value = MagicMock(
                token="token_123",
                url="https://webpay.transbank.cl/...",
            )
            mock_webpay.transaction = mock_transaction

            result = await client.create_transaction(
                buy_order="order_123",
                session_id="session_123",
                amount=29900,
                return_url="https://app.aipanel.cl/callback",
            )

            assert "token" in result

    @pytest.mark.asyncio
    async def test_confirm_transaction(self):
        """Test confirming Transbank transaction."""
        from app.integrations.transbank_client import TransbankClient

        client = TransbankClient()

        with patch.object(client, "webpay") as mock_webpay:
            mock_transaction = MagicMock()
            mock_transaction.commit.return_value = MagicMock(
                response_code=0,
                authorization_code="123456",
                amount=29900,
                buy_order="order_123",
            )
            mock_webpay.transaction = mock_transaction

            result = await client.confirm_transaction("token_123")

            assert result["success"] is True
            assert result["amount"] == 29900


class TestPaymentService:
    """Test payment service logic."""

    @pytest.mark.asyncio
    async def test_calculate_plan_price(self):
        """Test plan price calculation."""
        from app.modules.payments.service import PaymentService

        service = PaymentService()

        # Monthly price
        price = service.get_plan_price("professional", "monthly")
        assert price > 0

        # Annual price (should have discount)
        annual_price = service.get_plan_price("professional", "annual")
        assert annual_price > 0
        assert annual_price < price * 12  # Should be less than 12 months

    @pytest.mark.asyncio
    async def test_validate_plan(self):
        """Test plan validation."""
        from app.modules.payments.service import PaymentService

        service = PaymentService()

        # Valid plans
        assert service.is_valid_plan("starter") is True
        assert service.is_valid_plan("professional") is True
        assert service.is_valid_plan("enterprise") is True

        # Invalid plan
        assert service.is_valid_plan("invalid") is False

    @pytest.mark.asyncio
    async def test_can_upgrade_plan(self):
        """Test plan upgrade validation."""
        from app.modules.payments.service import PaymentService

        service = PaymentService()

        # Upgrade allowed
        assert service.can_upgrade("starter", "professional") is True
        assert service.can_upgrade("professional", "enterprise") is True

        # Downgrade not allowed through upgrade endpoint
        assert service.can_upgrade("professional", "starter") is False

        # Same plan
        assert service.can_upgrade("professional", "professional") is False


class TestPaymentSchemas:
    """Test payment schemas."""

    def test_checkout_request(self):
        """Test checkout request schema."""
        from app.modules.payments.schemas import CheckoutRequest

        request = CheckoutRequest(
            plan="professional",
            return_url="https://app.aipanel.cl/billing/callback",
        )
        assert request.plan == "professional"

    def test_checkout_request_invalid_url(self):
        """Test checkout with invalid URL."""
        from app.modules.payments.schemas import CheckoutRequest
        from pydantic import ValidationError

        # Should validate URL format
        with pytest.raises(ValidationError):
            CheckoutRequest(
                plan="professional",
                return_url="not-a-valid-url",
            )

    def test_payment_response(self):
        """Test payment response schema."""
        from app.modules.payments.schemas import PaymentResponse

        response = PaymentResponse(
            id=str(uuid4()),
            amount=29900,
            currency="CLP",
            status="completed",
            transaction_id="txn_123",
        )
        assert response.amount == 29900
        assert response.status == "completed"


class TestPaymentWebhooks:
    """Test payment webhook handling."""

    @pytest.mark.asyncio
    async def test_handle_transbank_ipn(self, client: AsyncClient):
        """Test Transbank IPN (Instant Payment Notification)."""
        # Transbank sends notifications for payment status changes
        response = await client.post(
            "/api/v1/payments/webhook/transbank",
            json={
                "token": "token_123",
                "tbk_orden_compra": "order_123",
                "tbk_id_sesion": "session_123",
            },
        )
        # Should handle gracefully even without valid token
        assert response.status_code in [200, 400, 404]

    @pytest.mark.asyncio
    async def test_payment_notification_sent(self):
        """Test that payment notification is sent after successful payment."""
        from app.modules.payments.service import PaymentService

        service = PaymentService()

        with patch("app.integrations.notification_service.notification_service.notify_payment") as mock:
            mock.return_value = [{"success": True}]

            await service.send_payment_notification(
                tenant_id=str(uuid4()),
                amount=29900,
                success=True,
            )

            mock.assert_called_once()
