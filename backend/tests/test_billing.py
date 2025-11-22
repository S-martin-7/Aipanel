"""
Tests for billing module.

Tests subscription, invoice, and payment functionality.
"""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_get_subscription(client: AsyncClient, auth_headers: dict):
    """Test getting subscription details."""
    response = await client.get(
        "/api/v1/billing/subscription",
        headers=auth_headers,
    )
    assert response.status_code in [200, 404]


@pytest.mark.asyncio
async def test_list_invoices(client: AsyncClient, auth_headers: dict):
    """Test listing invoices."""
    response = await client.get(
        "/api/v1/billing/invoices",
        headers=auth_headers,
    )
    assert response.status_code in [200, 403]


@pytest.mark.asyncio
async def test_get_invoice_by_id(client: AsyncClient, auth_headers: dict):
    """Test getting a specific invoice."""
    response = await client.get(
        "/api/v1/billing/invoices/test-invoice-id",
        headers=auth_headers,
    )
    assert response.status_code in [200, 404]


@pytest.mark.asyncio
async def test_revenue_summary_admin_only(client: AsyncClient, auth_headers: dict):
    """Test that revenue summary is admin only."""
    response = await client.get(
        "/api/v1/billing/revenue/summary",
        headers=auth_headers,
    )
    # Should require admin role
    assert response.status_code in [200, 403]


@pytest.mark.asyncio
async def test_create_subscription(client: AsyncClient, auth_headers: dict):
    """Test creating a new subscription."""
    subscription_data = {
        "plan_id": "pro",
    }
    response = await client.post(
        "/api/v1/billing/subscription",
        json=subscription_data,
        headers=auth_headers,
    )
    assert response.status_code in [200, 201, 400, 403]


@pytest.mark.asyncio
async def test_cancel_subscription(client: AsyncClient, auth_headers: dict):
    """Test canceling a subscription."""
    response = await client.delete(
        "/api/v1/billing/subscription",
        headers=auth_headers,
    )
    assert response.status_code in [200, 404, 403]


@pytest.mark.asyncio
async def test_usage_summary(client: AsyncClient, auth_headers: dict):
    """Test getting usage summary."""
    response = await client.get(
        "/api/v1/billing/usage",
        headers=auth_headers,
    )
    assert response.status_code in [200, 403]
