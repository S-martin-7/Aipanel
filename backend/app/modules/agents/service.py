"""
Agents Module - Service

Business logic for agent management.
"""

from typing import Optional
from datetime import datetime

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Agent
from app.models.enums import AgentStatus
from app.utils.logger import get_logger

from .schemas import (
    CreateAgentRequest,
    UpdateAgentRequest,
    AgentResponse,
    AgentListResponse,
)

logger = get_logger(__name__)


class AgentService:
    """Service for agent CRUD operations."""

    def __init__(self, db: AsyncSession):
        """Initialize with database session."""
        self.db = db

    async def create_agent(
        self,
        request: CreateAgentRequest,
        tenant_id: str,
    ) -> AgentResponse:
        """Create a new agent."""
        agent = Agent(
            tenant_id=tenant_id,
            name=request.name,
            description=request.description,
            system_prompt=request.system_prompt,
            model=request.model,
            temperature=request.temperature,
            max_tokens=request.max_tokens,
            status=AgentStatus.ACTIVE,
        )
        self.db.add(agent)
        await self.db.commit()
        await self.db.refresh(agent)

        logger.info(f"Agent created: {agent.id} for tenant {tenant_id}")
        return self._to_response(agent)

    async def get_agent(
        self,
        agent_id: str,
        tenant_id: str,
    ) -> Optional[AgentResponse]:
        """Get agent by ID."""
        result = await self.db.execute(
            select(Agent).where(
                Agent.id == agent_id,
                Agent.tenant_id == tenant_id,
            )
        )
        agent = result.scalar_one_or_none()

        if not agent:
            return None

        return self._to_response(agent)

    async def list_agents(
        self,
        tenant_id: str,
        include_archived: bool = False,
    ) -> AgentListResponse:
        """List all agents for a tenant."""
        query = select(Agent).where(Agent.tenant_id == tenant_id)

        if not include_archived:
            query = query.where(Agent.status != AgentStatus.ARCHIVED)

        query = query.order_by(Agent.created_at.desc())

        result = await self.db.execute(query)
        agents = result.scalars().all()

        return AgentListResponse(
            agents=[self._to_response(a) for a in agents],
            total=len(agents),
        )

    async def update_agent(
        self,
        agent_id: str,
        tenant_id: str,
        request: UpdateAgentRequest,
    ) -> Optional[AgentResponse]:
        """Update an agent."""
        result = await self.db.execute(
            select(Agent).where(
                Agent.id == agent_id,
                Agent.tenant_id == tenant_id,
            )
        )
        agent = result.scalar_one_or_none()

        if not agent:
            return None

        # Update fields
        update_data = request.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            if hasattr(agent, field):
                setattr(agent, field, value)

        agent.updated_at = datetime.utcnow()
        await self.db.commit()
        await self.db.refresh(agent)

        logger.info(f"Agent updated: {agent_id}")
        return self._to_response(agent)

    async def delete_agent(
        self,
        agent_id: str,
        tenant_id: str,
    ) -> bool:
        """Delete (archive) an agent."""
        result = await self.db.execute(
            select(Agent).where(
                Agent.id == agent_id,
                Agent.tenant_id == tenant_id,
            )
        )
        agent = result.scalar_one_or_none()

        if not agent:
            return False

        agent.status = AgentStatus.ARCHIVED
        agent.updated_at = datetime.utcnow()
        await self.db.commit()

        logger.info(f"Agent archived: {agent_id}")
        return True

    def _to_response(self, agent: Agent) -> AgentResponse:
        """Convert agent model to response."""
        return AgentResponse(
            id=agent.id,
            tenant_id=agent.tenant_id,
            name=agent.name,
            description=agent.description,
            system_prompt=agent.system_prompt,
            model=agent.model,
            temperature=agent.temperature or 0.7,
            max_tokens=agent.max_tokens or 4096,
            status=agent.status,
            created_at=agent.created_at,
            updated_at=agent.updated_at,
        )
