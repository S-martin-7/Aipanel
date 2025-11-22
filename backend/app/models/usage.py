"""
Token usage and billing models.

Tracks API usage for billing and analytics.
"""

from sqlalchemy import Column, String, Boolean, Enum, Integer, ForeignKey, Numeric, Date
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship

from .base import BaseModel
from .enums import AlertLevel, PaymentStatus


class TokenUsage(BaseModel):
    """
    Individual API request token usage.

    Records every AI API call for tracking and billing.
    """

    __tablename__ = "token_usage"

    tenant_id = Column(String(36), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    agent_id = Column(String(36), ForeignKey("agents.id", ondelete="SET NULL"), nullable=True, index=True)
    conversation_id = Column(String(36), nullable=True, index=True)

    # Request identification
    request_id = Column(String(36), nullable=False, unique=True)
    endpoint = Column(String(100), nullable=True)

    # Model used
    model = Column(String(50), nullable=False)

    # Token breakdown
    input_tokens = Column(Integer, default=0, nullable=False)
    output_tokens = Column(Integer, default=0, nullable=False)
    reasoning_tokens = Column(Integer, default=0, nullable=False)  # For O-series
    cached_tokens = Column(Integer, default=0, nullable=False)
    total_tokens = Column(Integer, default=0, nullable=False)

    # Cost breakdown (USD)
    input_cost = Column(Numeric(10, 6), default=0, nullable=False)
    output_cost = Column(Numeric(10, 6), default=0, nullable=False)
    reasoning_cost = Column(Numeric(10, 6), default=0, nullable=False)
    cache_cost = Column(Numeric(10, 6), default=0, nullable=False)
    total_cost = Column(Numeric(10, 6), default=0, nullable=False)

    # Request metadata
    latency_ms = Column(Integer, nullable=True)
    success = Column(Boolean, default=True, nullable=False)
    error_code = Column(String(50), nullable=True)
    error_message = Column(String(500), nullable=True)

    # Relationships
    tenant = relationship("Tenant", back_populates="usage_records")

    def __repr__(self):
        return f"<TokenUsage {self.request_id[:8]}>"


class UsageSummary(BaseModel):
    """
    Aggregated daily usage summary per tenant.

    Pre-computed for faster dashboard queries.
    """

    __tablename__ = "usage_summaries"

    tenant_id = Column(String(36), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    date = Column(Date, nullable=False)

    # Request counts
    total_requests = Column(Integer, default=0, nullable=False)
    successful_requests = Column(Integer, default=0, nullable=False)
    failed_requests = Column(Integer, default=0, nullable=False)

    # Token totals
    total_input_tokens = Column(Integer, default=0, nullable=False)
    total_output_tokens = Column(Integer, default=0, nullable=False)
    total_tokens = Column(Integer, default=0, nullable=False)

    # Cost totals
    total_cost = Column(Numeric(10, 2), default=0, nullable=False)

    # Breakdown by model (JSON)
    model_breakdown = Column(JSONB, nullable=True)

    # Unique constraint
    __table_args__ = (
        # Unique per tenant per day
        {"sqlite_autoincrement": True},
    )

    def __repr__(self):
        return f"<UsageSummary {self.tenant_id[:8]} {self.date}>"


class UsageThreshold(BaseModel):
    """
    Configurable usage thresholds for alerts.

    Defines when to alert or take action on usage.
    """

    __tablename__ = "usage_thresholds"

    tenant_id = Column(String(36), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)

    # Type of threshold
    threshold_type = Column(String(20), nullable=False)  # daily, monthly, per_request

    # Limits
    max_tokens = Column(Integer, nullable=True)
    max_cost = Column(Numeric(10, 2), nullable=True)

    # Alert percentages
    warning_at = Column(Integer, default=75, nullable=False)   # % for warning
    critical_at = Column(Integer, default=90, nullable=False)  # % for critical

    # Auto-actions
    throttle_at = Column(Integer, nullable=True)  # % to start throttling
    suspend_at = Column(Integer, nullable=True)   # % to suspend

    # Throttling config
    throttle_delay_ms = Column(Integer, nullable=True)
    throttle_max_requests = Column(Integer, nullable=True)

    # Notifications
    notify_email = Column(Boolean, default=True, nullable=False)
    notify_dashboard = Column(Boolean, default=True, nullable=False)
    notify_webhook = Column(Boolean, default=False, nullable=False)
    webhook_url = Column(String(500), nullable=True)

    # Status
    is_active = Column(Boolean, default=True, nullable=False)

    def __repr__(self):
        return f"<UsageThreshold {self.tenant_id[:8]} {self.threshold_type}>"


class UsageAlert(BaseModel):
    """
    Generated usage alerts.

    Records when thresholds are exceeded.
    """

    __tablename__ = "usage_alerts"

    tenant_id = Column(String(36), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    threshold_id = Column(String(36), ForeignKey("usage_thresholds.id", ondelete="SET NULL"), nullable=True)

    # Alert details
    level = Column(Enum(AlertLevel), nullable=False)
    alert_type = Column(String(50), nullable=False)  # threshold_exceeded, daily_limit, etc.
    title = Column(String(200), nullable=False)
    message = Column(String(1000), nullable=False)

    # Usage data at time of alert
    current_usage = Column(Integer, nullable=False)
    limit_value = Column(Integer, nullable=False)
    percentage = Column(Integer, nullable=False)

    # Metadata
    metadata = Column(JSONB, nullable=True)

    # Status
    is_read = Column(Boolean, default=False, nullable=False)
    is_resolved = Column(Boolean, default=False, nullable=False)
    resolved_at = Column(String(50), nullable=True)

    # Action taken
    action_taken = Column(String(50), nullable=True)  # email_sent, throttled, suspended

    def __repr__(self):
        return f"<UsageAlert {self.level} {self.tenant_id[:8]}>"


class Payment(BaseModel):
    """
    Payment transaction records.

    Tracks payments via Transbank.
    """

    __tablename__ = "payments"

    tenant_id = Column(String(36), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)

    # Transaction details
    transaction_id = Column(String(100), nullable=False, unique=True)
    external_id = Column(String(100), nullable=True)  # Transbank token

    # Amount
    amount = Column(Numeric(10, 2), nullable=False)
    currency = Column(String(3), default="CLP", nullable=False)

    # Status
    status = Column(Enum(PaymentStatus), default=PaymentStatus.PENDING, nullable=False)

    # Payment method
    payment_method = Column(String(50), nullable=True)  # webpay, oneclick
    card_last_four = Column(String(4), nullable=True)

    # Description
    description = Column(String(500), nullable=True)

    # Metadata
    metadata = Column(JSONB, nullable=True)

    # Error info
    error_code = Column(String(50), nullable=True)
    error_message = Column(String(500), nullable=True)

    def __repr__(self):
        return f"<Payment {self.transaction_id}>"
