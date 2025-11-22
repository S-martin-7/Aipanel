"""
Webhook model for event notifications to external URLs.
"""
from sqlalchemy import Column, String, Boolean, Integer, Text, DateTime, ForeignKey, Enum
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.orm import relationship
from app.models.base import BaseModel
import enum


class WebhookEvent(str, enum.Enum):
    """Available webhook events."""
    # Conversation events
    CONVERSATION_STARTED = "conversation.started"
    CONVERSATION_ENDED = "conversation.ended"
    MESSAGE_RECEIVED = "message.received"
    MESSAGE_SENT = "message.sent"

    # Agent events
    AGENT_CREATED = "agent.created"
    AGENT_UPDATED = "agent.updated"
    AGENT_DELETED = "agent.deleted"

    # Document events
    DOCUMENT_UPLOADED = "document.uploaded"
    DOCUMENT_PROCESSED = "document.processed"
    DOCUMENT_DELETED = "document.deleted"

    # User events
    USER_CREATED = "user.created"
    USER_UPDATED = "user.updated"
    USER_DELETED = "user.deleted"

    # Billing events
    SUBSCRIPTION_CREATED = "subscription.created"
    SUBSCRIPTION_UPDATED = "subscription.updated"
    SUBSCRIPTION_CANCELLED = "subscription.cancelled"
    INVOICE_CREATED = "invoice.created"
    INVOICE_PAID = "invoice.paid"


class Webhook(BaseModel):
    """Webhook configuration for a tenant."""
    __tablename__ = "webhooks"

    tenant_id = Column(String(36), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)

    # Configuration
    name = Column(String(100), nullable=False)
    url = Column(String(500), nullable=False)
    secret = Column(String(64), nullable=False)  # For HMAC signature

    # Events to subscribe to
    events = Column(ARRAY(String), nullable=False, default=[])

    # Optional filters
    agent_id = Column(String(36), ForeignKey("agents.id", ondelete="SET NULL"), nullable=True)

    # Status
    is_active = Column(Boolean, default=True, nullable=False)

    # Retry configuration
    max_retries = Column(Integer, default=3, nullable=False)
    retry_delay_seconds = Column(Integer, default=60, nullable=False)

    # Headers to include
    custom_headers = Column(JSONB, nullable=True)

    # Stats
    total_deliveries = Column(Integer, default=0, nullable=False)
    successful_deliveries = Column(Integer, default=0, nullable=False)
    failed_deliveries = Column(Integer, default=0, nullable=False)
    last_triggered_at = Column(DateTime, nullable=True)
    last_success_at = Column(DateTime, nullable=True)
    last_failure_at = Column(DateTime, nullable=True)
    last_failure_reason = Column(Text, nullable=True)

    # Relationships
    tenant = relationship("Tenant", back_populates="webhooks")
    agent = relationship("Agent")
    deliveries = relationship("WebhookDelivery", back_populates="webhook", cascade="all, delete-orphan")


class DeliveryStatus(str, enum.Enum):
    """Webhook delivery status."""
    PENDING = "pending"
    SUCCESS = "success"
    FAILED = "failed"
    RETRYING = "retrying"


class WebhookDelivery(BaseModel):
    """Record of a webhook delivery attempt."""
    __tablename__ = "webhook_deliveries"

    webhook_id = Column(String(36), ForeignKey("webhooks.id", ondelete="CASCADE"), nullable=False, index=True)

    # Event info
    event_type = Column(String(50), nullable=False)
    event_id = Column(String(36), nullable=False, unique=True)  # Idempotency key
    payload = Column(JSONB, nullable=False)

    # Delivery status
    status = Column(String(20), default=DeliveryStatus.PENDING.value, nullable=False)
    attempts = Column(Integer, default=0, nullable=False)
    next_retry_at = Column(DateTime, nullable=True)

    # Response info
    response_status_code = Column(Integer, nullable=True)
    response_body = Column(Text, nullable=True)
    response_time_ms = Column(Integer, nullable=True)

    # Error info
    error_message = Column(Text, nullable=True)

    # Timestamps
    delivered_at = Column(DateTime, nullable=True)

    # Relationships
    webhook = relationship("Webhook", back_populates="deliveries")
