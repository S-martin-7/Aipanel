"""
Authentication endpoint tests.
"""
import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_login_invalid_credentials(client: AsyncClient):
    """Test login with invalid credentials."""
    response = await client.post(
        "/api/v1/auth/login",
        json={
            "email": "invalid@email.com",
            "password": "wrongpassword"
        }
    )
    assert response.status_code in [401, 422]


@pytest.mark.asyncio
async def test_login_missing_fields(client: AsyncClient):
    """Test login with missing fields."""
    response = await client.post(
        "/api/v1/auth/login",
        json={}
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_register_missing_fields(client: AsyncClient):
    """Test registration with missing fields."""
    response = await client.post(
        "/api/v1/auth/register",
        json={"email": "test@test.com"}
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_protected_endpoint_without_token(client: AsyncClient):
    """Test accessing protected endpoint without token."""
    response = await client.get("/api/v1/agents")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_protected_endpoint_invalid_token(client: AsyncClient):
    """Test accessing protected endpoint with invalid token."""
    response = await client.get(
        "/api/v1/agents",
        headers={"Authorization": "Bearer invalid_token"}
    )
    assert response.status_code == 401
