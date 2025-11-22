"""
Email models for notifications and templates.
"""
from sqlalchemy import Column, String, Boolean, Text, DateTime, ForeignKey, Integer
from sqlalchemy.dialects.postgresql import JSONB, ARRAY
from sqlalchemy.orm import relationship
from app.models.base import BaseModel
import enum


class EmailStatus(str, enum.Enum):
    """Email delivery status."""
    PENDING = "pending"
    QUEUED = "queued"
    SENDING = "sending"
    SENT = "sent"
    DELIVERED = "delivered"
    FAILED = "failed"
    BOUNCED = "bounced"


class EmailType(str, enum.Enum):
    """Types of system emails."""
    # Auth
    WELCOME = "welcome"
    EMAIL_VERIFICATION = "email_verification"
    PASSWORD_RESET = "password_reset"
    PASSWORD_CHANGED = "password_changed"

    # User management
    USER_INVITED = "user_invited"
    USER_REMOVED = "user_removed"
    ROLE_CHANGED = "role_changed"

    # Billing
    TRIAL_STARTED = "trial_started"
    TRIAL_ENDING = "trial_ending"  # 7 days, 3 days, 1 day before
    TRIAL_EXPIRED = "trial_expired"
    SUBSCRIPTION_CREATED = "subscription_created"
    SUBSCRIPTION_RENEWED = "subscription_renewed"
    SUBSCRIPTION_CANCELLED = "subscription_cancelled"
    PAYMENT_RECEIVED = "payment_received"
    PAYMENT_FAILED = "payment_failed"
    INVOICE_CREATED = "invoice_created"

    # Usage alerts
    USAGE_WARNING = "usage_warning"  # 80% of limit
    USAGE_LIMIT_REACHED = "usage_limit_reached"

    # System
    SECURITY_ALERT = "security_alert"
    API_KEY_CREATED = "api_key_created"
    WEBHOOK_FAILING = "webhook_failing"

    # Custom
    CUSTOM = "custom"


class EmailTemplate(BaseModel):
    """Email template for customization."""
    __tablename__ = "email_templates"

    # Can be tenant-specific or system-wide (tenant_id = NULL)
    tenant_id = Column(String(36), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=True, index=True)

    # Template info
    email_type = Column(String(50), nullable=False, index=True)
    name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)

    # Content (supports variables like {{user_name}}, {{tenant_name}}, etc.)
    subject = Column(String(255), nullable=False)
    body_html = Column(Text, nullable=False)
    body_text = Column(Text, nullable=True)  # Plain text fallback

    # Styling
    header_image_url = Column(String(500), nullable=True)
    footer_text = Column(Text, nullable=True)
    primary_color = Column(String(7), nullable=True)  # Hex color

    # Available variables for this template
    available_variables = Column(ARRAY(String), nullable=True)

    # Status
    is_active = Column(Boolean, default=True, nullable=False)
    is_default = Column(Boolean, default=False, nullable=False)

    # Relationships
    tenant = relationship("Tenant")


class EmailLog(BaseModel):
    """Log of sent emails."""
    __tablename__ = "email_logs"

    tenant_id = Column(String(36), ForeignKey("tenants.id", ondelete="SET NULL"), nullable=True, index=True)

    # Recipients
    to_email = Column(String(255), nullable=False, index=True)
    to_name = Column(String(100), nullable=True)
    cc_emails = Column(ARRAY(String), nullable=True)
    bcc_emails = Column(ARRAY(String), nullable=True)

    # Email info
    email_type = Column(String(50), nullable=False, index=True)
    template_id = Column(String(36), ForeignKey("email_templates.id", ondelete="SET NULL"), nullable=True)
    subject = Column(String(255), nullable=False)
    body_html = Column(Text, nullable=True)  # Rendered content

    # Variables used
    variables = Column(JSONB, nullable=True)

    # Delivery status
    status = Column(String(20), default=EmailStatus.PENDING.value, nullable=False, index=True)
    attempts = Column(Integer, default=0, nullable=False)
    last_attempt_at = Column(DateTime, nullable=True)
    sent_at = Column(DateTime, nullable=True)
    delivered_at = Column(DateTime, nullable=True)

    # Provider info
    provider = Column(String(50), nullable=True)  # smtp, sendgrid, ses, etc.
    provider_message_id = Column(String(255), nullable=True)

    # Error info
    error_message = Column(Text, nullable=True)
    error_code = Column(String(50), nullable=True)

    # Tracking
    opened_at = Column(DateTime, nullable=True)
    clicked_at = Column(DateTime, nullable=True)

    # Related resource
    related_type = Column(String(50), nullable=True)  # invoice, user, etc.
    related_id = Column(String(36), nullable=True)

    # Relationships
    tenant = relationship("Tenant")
    template = relationship("EmailTemplate")


class EmailPreference(BaseModel):
    """User email preferences."""
    __tablename__ = "email_preferences"

    # Can be for tenant user or system-wide settings
    tenant_id = Column(String(36), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=True, index=True)
    user_id = Column(String(36), nullable=True, index=True)
    email = Column(String(255), nullable=False, index=True)

    # Preferences by category
    marketing_emails = Column(Boolean, default=True, nullable=False)
    billing_emails = Column(Boolean, default=True, nullable=False)
    security_emails = Column(Boolean, default=True, nullable=False)  # Always sent regardless
    usage_alerts = Column(Boolean, default=True, nullable=False)
    product_updates = Column(Boolean, default=True, nullable=False)
    weekly_summary = Column(Boolean, default=False, nullable=False)

    # Unsubscribe
    unsubscribed_all = Column(Boolean, default=False, nullable=False)
    unsubscribe_token = Column(String(64), nullable=True, unique=True)

    # Relationships
    tenant = relationship("Tenant")
