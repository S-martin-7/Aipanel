"""
Usage Module - Schemas

Pydantic schemas for usage tracking and analytics.
"""

from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime, date
from enum import Enum


class UsagePeriod(str, Enum):
    """Usage aggregation period."""
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"


class TokenUsageRecord(BaseModel):
    """Single token usage record."""
    id: str
    tenant_id: str
    agent_id: Optional[str] = None
    model: str
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    cost_usd: float
    created_at: datetime

    class Config:
        from_attributes = True


class UsageSummaryResponse(BaseModel):
    """Usage summary for a period."""
    tenant_id: str
    period: UsagePeriod
    start_date: date
    end_date: date
    total_requests: int
    total_tokens: int
    prompt_tokens: int
    completion_tokens: int
    estimated_cost_usd: float
    by_model: dict[str, "ModelUsage"]
    by_agent: dict[str, "AgentUsage"]


class ModelUsage(BaseModel):
    """Usage breakdown by model."""
    model: str
    requests: int
    total_tokens: int
    cost_usd: float


class AgentUsage(BaseModel):
    """Usage breakdown by agent."""
    agent_id: str
    agent_name: str
    requests: int
    total_tokens: int


class UsageQuota(BaseModel):
    """Usage quota and limits."""
    tenant_id: str
    plan: str
    tokens_limit: int
    tokens_used: int
    tokens_remaining: int
    usage_percentage: float
    reset_date: date
    is_exceeded: bool


class UsageAlert(BaseModel):
    """Usage alert."""
    id: str
    tenant_id: str
    alert_type: str  # warning, limit_reached, overage
    threshold_percent: int
    current_percent: float
    message: str
    created_at: datetime
    acknowledged: bool = False


class DailyUsagePoint(BaseModel):
    """Single day usage point for charts."""
    date: date
    tokens: int
    requests: int
    cost_usd: float


class UsageChartResponse(BaseModel):
    """Usage chart data."""
    tenant_id: str
    period: UsagePeriod
    data_points: list[DailyUsagePoint]
    total_tokens: int
    total_requests: int
    total_cost_usd: float


class RecordUsageRequest(BaseModel):
    """Request to record token usage."""
    agent_id: str
    model: str
    prompt_tokens: int = Field(..., ge=0)
    completion_tokens: int = Field(..., ge=0)


# Update forward references
UsageSummaryResponse.model_rebuild()
