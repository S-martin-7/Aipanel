"""
Agent endpoint tests.
"""
import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_list_agents_unauthorized(client: AsyncClient):
    """Test listing agents without authentication."""
    response = await client.get("/api/v1/agents")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_create_agent_unauthorized(client: AsyncClient):
    """Test creating agent without authentication."""
    response = await client.post(
        "/api/v1/agents",
        json={
            "name": "Test Agent",
            "system_prompt": "You are helpful."
        }
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_get_agent_not_found(client: AsyncClient):
    """Test getting non-existent agent."""
    response = await client.get(
        "/api/v1/agents/non-existent-id",
        headers={"Authorization": "Bearer test_token"}
    )
    assert response.status_code in [401, 404]
