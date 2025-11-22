"""
Agents Module - Router

CRUD operations for AI agent management.
"""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import TenantUser
from app.utils.logger import get_logger

from .schemas import (
    CreateAgentRequest,
    UpdateAgentRequest,
    AgentResponse,
    AgentListResponse,
)
from .service import AgentService

logger = get_logger(__name__)
router = APIRouter()


def get_agent_service(db: AsyncSession = Depends(get_db)) -> AgentService:
    """Dependency to get agent service."""
    return AgentService(db)


@router.get("/", response_model=AgentListResponse)
async def list_agents(
    current_user: TenantUser,
    include_archived: bool = Query(False, description="Include archived agents"),
    service: AgentService = Depends(get_agent_service),
):
    """List all agents for current tenant."""
    tenant_id = getattr(current_user, "tenant_id", None)
    if not tenant_id:
        raise HTTPException(status_code=400, detail="User not associated with a tenant")

    return await service.list_agents(tenant_id, include_archived)


@router.post("/", response_model=AgentResponse, status_code=status.HTTP_201_CREATED)
async def create_agent(
    request: CreateAgentRequest,
    current_user: TenantUser,
    service: AgentService = Depends(get_agent_service),
):
    """Create a new AI agent."""
    tenant_id = getattr(current_user, "tenant_id", None)
    if not tenant_id:
        raise HTTPException(status_code=400, detail="User not associated with a tenant")

    return await service.create_agent(request, tenant_id)


@router.get("/{agent_id}", response_model=AgentResponse)
async def get_agent(
    agent_id: str,
    current_user: TenantUser,
    service: AgentService = Depends(get_agent_service),
):
    """Get agent by ID."""
    tenant_id = getattr(current_user, "tenant_id", None)
    if not tenant_id:
        raise HTTPException(status_code=400, detail="User not associated with a tenant")

    agent = await service.get_agent(agent_id, tenant_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")

    return agent


@router.patch("/{agent_id}", response_model=AgentResponse)
async def update_agent(
    agent_id: str,
    request: UpdateAgentRequest,
    current_user: TenantUser,
    service: AgentService = Depends(get_agent_service),
):
    """Update agent configuration."""
    tenant_id = getattr(current_user, "tenant_id", None)
    if not tenant_id:
        raise HTTPException(status_code=400, detail="User not associated with a tenant")

    agent = await service.update_agent(agent_id, tenant_id, request)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")

    return agent


@router.delete("/{agent_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_agent(
    agent_id: str,
    current_user: TenantUser,
    service: AgentService = Depends(get_agent_service),
):
    """Delete (archive) an agent."""
    tenant_id = getattr(current_user, "tenant_id", None)
    if not tenant_id:
        raise HTTPException(status_code=400, detail="User not associated with a tenant")

    deleted = await service.delete_agent(agent_id, tenant_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Agent not found")
