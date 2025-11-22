"""
Agents Module - Schemas

Pydantic schemas for agent management.
"""

from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
from enum import Enum


class AgentStatus(str, Enum):
    """Agent status."""
    ACTIVE = "active"
    INACTIVE = "inactive"
    ARCHIVED = "archived"


class CreateAgentRequest(BaseModel):
    """Request to create an agent."""
    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    system_prompt: Optional[str] = Field(None, max_length=10000)
    model: str = Field(default="gpt-4o")
    temperature: float = Field(default=0.7, ge=0.0, le=2.0)
    max_tokens: int = Field(default=4096, ge=1, le=32000)


class UpdateAgentRequest(BaseModel):
    """Request to update an agent."""
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    system_prompt: Optional[str] = Field(None, max_length=10000)
    model: Optional[str] = None
    temperature: Optional[float] = Field(None, ge=0.0, le=2.0)
    max_tokens: Optional[int] = Field(None, ge=1, le=32000)
    status: Optional[AgentStatus] = None


class AgentResponse(BaseModel):
    """Agent response."""
    id: str
    tenant_id: str
    name: str
    description: Optional[str] = None
    system_prompt: Optional[str] = None
    model: str
    temperature: float
    max_tokens: int
    status: AgentStatus
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class AgentListResponse(BaseModel):
    """List of agents response."""
    agents: list[AgentResponse]
    total: int
