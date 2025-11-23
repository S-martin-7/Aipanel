"""
AI Execution Log Model.

Stores detailed logs of every AI request for debugging, analytics, and billing.
"""

from enum import Enum
from sqlalchemy import Column, String, Integer, Boolean, Text, ForeignKey, Numeric
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship

from .base import BaseModel, TimestampMixin


class ExecutionStatus(str, Enum):
    """Status of an AI execution."""
    SUCCESS = "success"
    ERROR = "error"
    TIMEOUT = "timeout"
    RATE_LIMITED = "rate_limited"
    PLAN_EXCEEDED = "plan_exceeded"


class RequestType(str, Enum):
    """Type of AI request."""
    CHAT = "chat"
    COMPLETION = "completion"
    EMBEDDING = "embedding"
    REALTIME = "realtime"
    STREAM = "stream"


class AIExecutionLog(BaseModel, TimestampMixin):
    """
    Detailed log of AI executions.

    Tracks every AI API call with full context for:
    - Debugging and error tracking
    - Performance monitoring (latency, TTFT)
    - Cost tracking and billing
    - Usage analytics per tenant/agent/model
    """

    __tablename__ = "ai_execution_logs"

    # Context
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), index=True)
    agent_id = Column(UUID(as_uuid=True), ForeignKey("agents.id", ondelete="SET NULL"))
    conversation_id = Column(UUID(as_uuid=True))

    # Route/Config used
    route_id = Column(UUID(as_uuid=True), ForeignKey("ai_routes.id", ondelete="SET NULL"))
    provider_id = Column(UUID(as_uuid=True), ForeignKey("ai_providers.id", ondelete="SET NULL"), index=True)
    model_id = Column(UUID(as_uuid=True), ForeignKey("ai_models.id", ondelete="SET NULL"), index=True)
    param_profile_id = Column(UUID(as_uuid=True), ForeignKey("ai_param_profiles.id", ondelete="SET NULL"))

    # Request info
    request_type = Column(String(50))  # chat, completion, embedding, etc.
    request_id = Column(String(100))  # External request ID for correlation

    # Token usage
    input_tokens = Column(Integer, default=0)
    output_tokens = Column(Integer, default=0)
    total_tokens = Column(Integer, default=0)

    # Performance metrics
    latency_ms = Column(Integer)  # Total latency
    ttft_ms = Column(Integer)  # Time to first token (for streaming)

    # Status
    status = Column(String(50), index=True)  # success, error, timeout, rate_limited
    error_code = Column(String(100))
    error_message = Column(Text)

    # Fallback info
    fallback_used = Column(Boolean, default=False)
    fallback_model_id = Column(UUID(as_uuid=True))
    retry_count = Column(Integer, default=0)

    # Cost tracking
    cost_usd = Column(Numeric(10, 6))

    # Request/Response details (for debugging)
    params_used = Column(JSONB, default={})  # Parameters sent to API
    metadata = Column(JSONB, default={})  # Additional metadata

    # Source info
    source = Column(String(50))  # panel, widget, api, webhook
    client_ip = Column(String(50))
    user_agent = Column(String(255))

    # Relationships
    tenant = relationship("Tenant", back_populates="execution_logs")
    agent = relationship("Agent", back_populates="execution_logs")

    def __repr__(self):
        return f"<AIExecutionLog {self.id} status={self.status} tokens={self.total_tokens}>"

    @property
    def is_success(self) -> bool:
        return self.status == ExecutionStatus.SUCCESS.value

    @property
    def is_error(self) -> bool:
        return self.status in [
            ExecutionStatus.ERROR.value,
            ExecutionStatus.TIMEOUT.value,
            ExecutionStatus.RATE_LIMITED.value,
        ]
