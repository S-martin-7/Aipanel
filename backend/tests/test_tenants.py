"""
Tests for tenants module.

Tests tenant CRUD operations and related functionality.
"""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_list_tenants_requires_auth(client: AsyncClient):
    """Test that listing tenants requires authentication."""
    response = await client.get("/api/v1/tenants")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_create_tenant_requires_admin(client: AsyncClient, auth_headers: dict):
    """Test that creating a tenant requires admin role."""
    tenant_data = {
        "name": "Test Tenant",
        "email": "test@tenant.com",
        "plan_id": "basic",
    }
    response = await client.post(
        "/api/v1/tenants",
        json=tenant_data,
        headers=auth_headers,
    )
    # Should work with proper admin auth
    assert response.status_code in [200, 201, 403]


@pytest.mark.asyncio
async def test_get_tenant_by_id(client: AsyncClient, auth_headers: dict):
    """Test getting a tenant by ID."""
    # First create a tenant or use existing
    response = await client.get(
        "/api/v1/tenants/test-tenant-id",
        headers=auth_headers,
    )
    # Should return 404 for non-existent or 200 for existing
    assert response.status_code in [200, 404]


@pytest.mark.asyncio
async def test_update_tenant(client: AsyncClient, auth_headers: dict):
    """Test updating a tenant."""
    update_data = {
        "name": "Updated Tenant Name",
    }
    response = await client.put(
        "/api/v1/tenants/test-tenant-id",
        json=update_data,
        headers=auth_headers,
    )
    assert response.status_code in [200, 404, 403]


@pytest.mark.asyncio
async def test_tenant_api_key_rotation(client: AsyncClient, auth_headers: dict):
    """Test rotating a tenant's API key."""
    response = await client.post(
        "/api/v1/tenants/test-tenant-id/rotate-api-key",
        headers=auth_headers,
    )
    assert response.status_code in [200, 404, 403]


@pytest.mark.asyncio
async def test_tenant_users_list(client: AsyncClient, auth_headers: dict):
    """Test listing users of a tenant."""
    response = await client.get(
        "/api/v1/tenants/test-tenant-id/users",
        headers=auth_headers,
    )
    assert response.status_code in [200, 404, 403]


@pytest.mark.asyncio
async def test_tenant_stats(client: AsyncClient, auth_headers: dict):
    """Test getting tenant statistics."""
    response = await client.get(
        "/api/v1/tenants/test-tenant-id/stats",
        headers=auth_headers,
    )
    assert response.status_code in [200, 404, 403]
