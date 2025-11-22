"""
Token usage and billing models.

Tracks API usage for billing and analytics.
"""

from sqlalchemy import Column, String, Boolean, Enum, Integer, ForeignKey, Numeric, Date, DateTime, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from datetime import datetime

from .base import BaseModel
from .enums import AlertLevel, PaymentStatus


class SubscriptionStatus:
    """Subscription status constants."""
    ACTIVE = "ACTIVE"
    TRIAL = "TRIAL"
    PAST_DUE = "PAST_DUE"
    CANCELLED = "CANCELLED"
    SUSPENDED = "SUSPENDED"


class InvoiceStatus:
    """Invoice status constants."""
    DRAFT = "DRAFT"
    PENDING = "PENDING"
    PAID = "PAID"
    OVERDUE = "OVERDUE"
    CANCELLED = "CANCELLED"
    REFUNDED = "REFUNDED"


class Subscription(BaseModel):
    """
    Tenant subscription to a plan.

    Tracks active subscriptions, billing cycles, and payment history.
    """

    __tablename__ = "subscriptions"

    tenant_id = Column(String(36), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    plan_code = Column(String(50), nullable=False)  # References plans.code

    # Status
    status = Column(String(20), default=SubscriptionStatus.TRIAL, nullable=False)

    # Billing cycle
    billing_cycle = Column(String(20), default="monthly", nullable=False)  # monthly, yearly
    billing_day = Column(Integer, default=1, nullable=False)  # Day of month

    # Period dates
    current_period_start = Column(DateTime, nullable=True)
    current_period_end = Column(DateTime, nullable=True)

    # Trial
    trial_start = Column(DateTime, nullable=True)
    trial_end = Column(DateTime, nullable=True)

    # Cancellation
    cancelled_at = Column(DateTime, nullable=True)
    cancel_at_period_end = Column(Boolean, default=False, nullable=False)
    cancellation_reason = Column(Text, nullable=True)

    # Payment info
    payment_method_id = Column(String(100), nullable=True)  # Transbank token/method
    last_payment_date = Column(DateTime, nullable=True)
    next_payment_date = Column(DateTime, nullable=True)

    # Amounts
    base_amount = Column(Numeric(10, 2), default=0, nullable=False)  # Plan price
    discount_amount = Column(Numeric(10, 2), default=0, nullable=False)
    tax_amount = Column(Numeric(10, 2), default=0, nullable=False)  # IVA 19%
    total_amount = Column(Numeric(10, 2), default=0, nullable=False)
    currency = Column(String(3), default="CLP", nullable=False)

    # Metadata
    metadata = Column(JSONB, nullable=True)

    # Relationships
    tenant = relationship("Tenant", backref="subscriptions")
    invoices = relationship("Invoice", back_populates="subscription")

    @property
    def is_active(self) -> bool:
        """Check if subscription is active."""
        return self.status in [SubscriptionStatus.ACTIVE, SubscriptionStatus.TRIAL]

    @property
    def is_trial(self) -> bool:
        """Check if in trial period."""
        return self.status == SubscriptionStatus.TRIAL

    def __repr__(self):
        return f"<Subscription {self.tenant_id[:8]} {self.plan_code}>"


class Invoice(BaseModel):
    """
    Invoice for subscription billing.

    Generated for each billing period.
    """

    __tablename__ = "invoices"

    tenant_id = Column(String(36), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    subscription_id = Column(String(36), ForeignKey("subscriptions.id", ondelete="SET NULL"), nullable=True)

    # Invoice identification
    invoice_number = Column(String(50), unique=True, nullable=False)  # INV-2024-0001

    # Status
    status = Column(String(20), default=InvoiceStatus.DRAFT, nullable=False)

    # Period
    period_start = Column(DateTime, nullable=False)
    period_end = Column(DateTime, nullable=False)

    # Due date
    due_date = Column(DateTime, nullable=False)
    paid_at = Column(DateTime, nullable=True)

    # Amounts
    subtotal = Column(Numeric(10, 2), default=0, nullable=False)
    discount_amount = Column(Numeric(10, 2), default=0, nullable=False)
    tax_rate = Column(Numeric(5, 2), default=19, nullable=False)  # IVA Chile
    tax_amount = Column(Numeric(10, 2), default=0, nullable=False)
    total = Column(Numeric(10, 2), default=0, nullable=False)
    currency = Column(String(3), default="CLP", nullable=False)

    # Line items (JSON array)
    line_items = Column(JSONB, default=list, nullable=False)
    # Format: [{"description": "Plan Professional", "quantity": 1, "unit_price": 79990, "total": 79990}]

    # Payment info
    payment_id = Column(String(36), ForeignKey("payments.id", ondelete="SET NULL"), nullable=True)
    payment_method = Column(String(50), nullable=True)

    # Notes
    notes = Column(Text, nullable=True)

    # Metadata
    metadata = Column(JSONB, nullable=True)

    # Relationships
    tenant = relationship("Tenant", backref="invoices")
    subscription = relationship("Subscription", back_populates="invoices")

    @property
    def is_paid(self) -> bool:
        """Check if invoice is paid."""
        return self.status == InvoiceStatus.PAID

    @property
    def is_overdue(self) -> bool:
        """Check if invoice is overdue."""
        if self.status == InvoiceStatus.PAID:
            return False
        return datetime.utcnow() > self.due_date if self.due_date else False

    def __repr__(self):
        return f"<Invoice {self.invoice_number}>"


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
