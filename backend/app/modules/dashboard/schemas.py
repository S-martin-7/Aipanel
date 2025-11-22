"""
Dashboard schemas for analytics and statistics.
"""
from datetime import datetime, date
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


# ============ Overview Stats ============

class OverviewStats(BaseModel):
    """Main dashboard overview statistics."""
    # Conversations
    total_conversations: int
    conversations_today: int
    conversations_this_week: int
    conversations_this_month: int
    conversations_change_percent: float  # vs previous period

    # Messages
    total_messages: int
    messages_today: int
    avg_messages_per_conversation: float

    # Agents
    total_agents: int
    active_agents: int

    # Documents
    total_documents: int
    total_document_chunks: int

    # Users
    total_users: int
    active_users_today: int

    # Usage
    total_tokens_used: int
    tokens_this_month: int
    estimated_cost_this_month: float
    currency: str = "CLP"


# ============ Time Series Data ============

class TimeSeriesPoint(BaseModel):
    """Single point in a time series."""
    date: date
    value: float


class TimeSeriesData(BaseModel):
    """Time series data for charts."""
    label: str
    data: List[TimeSeriesPoint]
    total: float
    average: float


class ConversationsTimeSeries(BaseModel):
    """Conversations over time."""
    period: str  # "day", "week", "month"
    conversations: List[TimeSeriesPoint]
    total: int
    average_per_day: float


class MessagesTimeSeries(BaseModel):
    """Messages over time."""
    period: str
    messages: List[TimeSeriesPoint]
    total: int
    average_per_day: float


class TokensTimeSeries(BaseModel):
    """Token usage over time."""
    period: str
    tokens: List[TimeSeriesPoint]
    total: int
    cost: float
    currency: str = "CLP"


# ============ Agent Stats ============

class AgentStats(BaseModel):
    """Statistics for a single agent."""
    agent_id: str
    agent_name: str
    total_conversations: int
    total_messages: int
    avg_response_time_ms: Optional[float]
    total_tokens: int
    total_cost: float
    satisfaction_score: Optional[float]  # If feedback collected


class AgentStatsResponse(BaseModel):
    """List of agent statistics."""
    agents: List[AgentStats]
    period_start: datetime
    period_end: datetime


# ============ Usage Stats ============

class UsageByModel(BaseModel):
    """Token usage breakdown by AI model."""
    model: str
    provider: str
    input_tokens: int
    output_tokens: int
    total_tokens: int
    cost: float
    percentage: float


class UsageBreakdown(BaseModel):
    """Detailed usage breakdown."""
    by_model: List[UsageByModel]
    by_agent: List[Dict[str, Any]]
    total_input_tokens: int
    total_output_tokens: int
    total_tokens: int
    total_cost: float
    currency: str = "CLP"


# ============ Top Items ============

class TopAgent(BaseModel):
    """Top performing agent."""
    agent_id: str
    agent_name: str
    metric_value: float
    metric_name: str


class TopDocument(BaseModel):
    """Most used document."""
    document_id: str
    document_name: str
    query_count: int
    agent_id: str
    agent_name: str


class TopItemsResponse(BaseModel):
    """Top items across various metrics."""
    top_agents_by_conversations: List[TopAgent]
    top_agents_by_messages: List[TopAgent]
    top_documents_by_queries: List[TopDocument]


# ============ Real-time Stats ============

class RealtimeStats(BaseModel):
    """Real-time activity statistics."""
    active_conversations: int
    messages_last_hour: int
    messages_last_5_min: int
    active_users: int
    avg_response_time_ms: float
    error_rate_percent: float


# ============ Period Comparison ============

class PeriodComparison(BaseModel):
    """Compare two time periods."""
    metric: str
    current_value: float
    previous_value: float
    change_value: float
    change_percent: float
    trend: str  # "up", "down", "stable"


class ComparisonResponse(BaseModel):
    """Period comparison response."""
    period: str
    current_start: date
    current_end: date
    previous_start: date
    previous_end: date
    comparisons: List[PeriodComparison]


# ============ Admin Stats (Platform-wide) ============

class PlatformStats(BaseModel):
    """Platform-wide statistics for super admins."""
    total_tenants: int
    active_tenants: int
    total_users: int
    total_agents: int
    total_conversations: int
    total_messages: int
    total_documents: int
    total_tokens: int
    total_revenue: float
    mrr: float
    arr: float
    currency: str = "CLP"
    tenants_by_plan: Dict[str, int]
    growth_rate_percent: float
