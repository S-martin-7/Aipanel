"""
Tests for usage module.
"""

import pytest
from httpx import AsyncClient
from unittest.mock import patch
from uuid import uuid4
from datetime import datetime, timedelta


class TestUsageEndpoints:
    """Test usage API endpoints."""

    @pytest.mark.asyncio
    async def test_get_quota_requires_auth(self, client: AsyncClient):
        """Test that quota endpoint requires authentication."""
        response = await client.get("/api/v1/usage/quota")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_get_quota(self, client: AsyncClient, auth_headers: dict):
        """Test getting usage quota."""
        with patch("app.modules.usage.service.UsageService.get_quota") as mock:
            mock.return_value = {
                "tokens_used": 5000,
                "tokens_limit": 100000,
                "requests_used": 50,
                "requests_limit": 1000,
                "period_start": "2025-01-01T00:00:00Z",
                "period_end": "2025-01-31T23:59:59Z",
            }

            response = await client.get(
                "/api/v1/usage/quota",
                headers=auth_headers,
            )

            assert response.status_code == 200
            data = response.json()
            assert "tokens_used" in data
            assert "tokens_limit" in data
            assert data["tokens_used"] == 5000

    @pytest.mark.asyncio
    async def test_get_summary(self, client: AsyncClient, auth_headers: dict):
        """Test getting usage summary."""
        with patch("app.modules.usage.service.UsageService.get_summary") as mock:
            mock.return_value = {
                "total_tokens": 10000,
                "total_requests": 100,
                "total_cost": 0.50,
                "by_model": {
                    "gpt-4o-mini": {"tokens": 8000, "cost": 0.40},
                    "claude-3-haiku": {"tokens": 2000, "cost": 0.10},
                },
            }

            response = await client.get(
                "/api/v1/usage/summary",
                headers=auth_headers,
            )

            assert response.status_code == 200
            data = response.json()
            assert "total_tokens" in data
            assert "by_model" in data

    @pytest.mark.asyncio
    async def test_get_summary_with_period(
        self, client: AsyncClient, auth_headers: dict
    ):
        """Test getting usage summary for specific period."""
        response = await client.get(
            "/api/v1/usage/summary",
            headers=auth_headers,
            params={"period": "week"},
        )
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_get_chart_data(self, client: AsyncClient, auth_headers: dict):
        """Test getting usage chart data."""
        with patch("app.modules.usage.service.UsageService.get_chart_data") as mock:
            mock.return_value = {
                "data_points": [
                    {"date": "2025-01-20", "tokens": 1000, "requests": 10},
                    {"date": "2025-01-21", "tokens": 1500, "requests": 15},
                    {"date": "2025-01-22", "tokens": 2000, "requests": 20},
                ],
            }

            response = await client.get(
                "/api/v1/usage/chart",
                headers=auth_headers,
                params={"days": 7},
            )

            assert response.status_code == 200
            data = response.json()
            assert "data_points" in data
            assert len(data["data_points"]) == 3

    @pytest.mark.asyncio
    async def test_get_history(self, client: AsyncClient, auth_headers: dict):
        """Test getting usage history."""
        response = await client.get(
            "/api/v1/usage/history",
            headers=auth_headers,
        )
        assert response.status_code == 200


class TestUsageService:
    """Test usage service logic."""

    @pytest.mark.asyncio
    async def test_calculate_usage_percentage(self):
        """Test usage percentage calculation."""
        from app.modules.usage.service import UsageService

        service = UsageService()

        # 50% usage
        percentage = service.calculate_percentage(5000, 10000)
        assert percentage == 50

        # 0% usage
        percentage = service.calculate_percentage(0, 10000)
        assert percentage == 0

        # 100% usage
        percentage = service.calculate_percentage(10000, 10000)
        assert percentage == 100

        # Over limit
        percentage = service.calculate_percentage(15000, 10000)
        assert percentage == 150

    @pytest.mark.asyncio
    async def test_get_alert_level(self):
        """Test alert level determination."""
        from app.modules.usage.service import UsageService

        service = UsageService()

        # Normal usage
        level = service.get_alert_level(50)
        assert level == "ok"

        # Warning level
        level = service.get_alert_level(80)
        assert level == "warning"

        # Critical level
        level = service.get_alert_level(95)
        assert level == "critical"

    @pytest.mark.asyncio
    async def test_calculate_cost(self):
        """Test cost calculation."""
        from app.modules.usage.service import UsageService

        service = UsageService()

        # GPT-4o-mini pricing (example)
        cost = service.calculate_cost(
            model="gpt-4o-mini",
            input_tokens=1000,
            output_tokens=500,
        )
        assert cost > 0

    @pytest.mark.asyncio
    async def test_aggregate_by_model(self):
        """Test aggregation by model."""
        from app.modules.usage.service import UsageService

        service = UsageService()

        usage_records = [
            {"model": "gpt-4o-mini", "tokens": 1000, "cost": 0.10},
            {"model": "gpt-4o-mini", "tokens": 2000, "cost": 0.20},
            {"model": "claude-3-haiku", "tokens": 500, "cost": 0.05},
        ]

        aggregated = service.aggregate_by_model(usage_records)

        assert "gpt-4o-mini" in aggregated
        assert aggregated["gpt-4o-mini"]["tokens"] == 3000
        assert aggregated["gpt-4o-mini"]["cost"] == 0.30


class TestUsageTracking:
    """Test usage tracking functionality."""

    @pytest.mark.asyncio
    async def test_record_usage(self):
        """Test recording usage."""
        from app.modules.usage.service import UsageService

        service = UsageService()

        # Mock database session
        with patch.object(service, "db") as mock_db:
            mock_db.execute = AsyncMock()
            mock_db.commit = AsyncMock()

            await service.record_usage(
                tenant_id=str(uuid4()),
                agent_id=str(uuid4()),
                model="gpt-4o-mini",
                input_tokens=100,
                output_tokens=50,
            )

            # Verify database was called
            mock_db.execute.assert_called()

    @pytest.mark.asyncio
    async def test_check_quota_exceeded(self):
        """Test quota exceeded check."""
        from app.modules.usage.service import UsageService

        service = UsageService()

        # Under limit
        exceeded = service.is_quota_exceeded(
            tokens_used=5000,
            tokens_limit=10000,
        )
        assert exceeded is False

        # At limit
        exceeded = service.is_quota_exceeded(
            tokens_used=10000,
            tokens_limit=10000,
        )
        assert exceeded is True

        # Over limit
        exceeded = service.is_quota_exceeded(
            tokens_used=15000,
            tokens_limit=10000,
        )
        assert exceeded is True


class TestUsageSchemas:
    """Test usage schemas."""

    def test_usage_quota_response(self):
        """Test usage quota response schema."""
        from app.modules.usage.schemas import UsageQuotaResponse

        response = UsageQuotaResponse(
            tokens_used=5000,
            tokens_limit=100000,
            requests_used=50,
            requests_limit=1000,
            period_start=datetime.now(),
            period_end=datetime.now() + timedelta(days=30),
        )

        assert response.tokens_used == 5000
        assert response.usage_percentage == 5.0

    def test_usage_summary_response(self):
        """Test usage summary response schema."""
        from app.modules.usage.schemas import UsageSummaryResponse

        response = UsageSummaryResponse(
            total_tokens=10000,
            total_requests=100,
            total_cost=0.50,
            by_model={
                "gpt-4o-mini": {"tokens": 8000, "cost": 0.40},
            },
            period="month",
        )

        assert response.total_tokens == 10000
        assert "gpt-4o-mini" in response.by_model


# Helper mock
class AsyncMock:
    def __init__(self, return_value=None):
        self.return_value = return_value
        self.called = False
        self.call_count = 0

    async def __call__(self, *args, **kwargs):
        self.called = True
        self.call_count += 1
        return self.return_value

    def assert_called(self):
        assert self.called, "Expected mock to be called"
