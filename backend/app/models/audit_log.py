"""
Audit Log model for tracking all important actions in the system.
"""
from sqlalchemy import Column, String, Text, DateTime, ForeignKey, Index
from sqlalchemy.dialects.postgresql import JSONB, INET
from sqlalchemy.orm import relationship
from app.models.base import BaseModel
import enum


class AuditAction(str, enum.Enum):
    """Available audit actions."""
    # Auth actions
    LOGIN = "auth.login"
    LOGOUT = "auth.logout"
    LOGIN_FAILED = "auth.login_failed"
    PASSWORD_CHANGED = "auth.password_changed"
    PASSWORD_RESET = "auth.password_reset"
    API_KEY_CREATED = "auth.api_key_created"
    API_KEY_REVOKED = "auth.api_key_revoked"

    # User actions
    USER_CREATED = "user.created"
    USER_UPDATED = "user.updated"
    USER_DELETED = "user.deleted"
    USER_INVITED = "user.invited"
    USER_ROLE_CHANGED = "user.role_changed"

    # Agent actions
    AGENT_CREATED = "agent.created"
    AGENT_UPDATED = "agent.updated"
    AGENT_DELETED = "agent.deleted"
    AGENT_ACTIVATED = "agent.activated"
    AGENT_DEACTIVATED = "agent.deactivated"

    # Document actions
    DOCUMENT_UPLOADED = "document.uploaded"
    DOCUMENT_PROCESSED = "document.processed"
    DOCUMENT_DELETED = "document.deleted"

    # Conversation actions
    CONVERSATION_STARTED = "conversation.started"
    CONVERSATION_DELETED = "conversation.deleted"
    CONVERSATION_EXPORTED = "conversation.exported"

    # Settings actions
    SETTINGS_UPDATED = "settings.updated"
    WEBHOOK_CREATED = "webhook.created"
    WEBHOOK_UPDATED = "webhook.updated"
    WEBHOOK_DELETED = "webhook.deleted"

    # Billing actions
    SUBSCRIPTION_CREATED = "billing.subscription_created"
    SUBSCRIPTION_UPDATED = "billing.subscription_updated"
    SUBSCRIPTION_CANCELLED = "billing.subscription_cancelled"
    PAYMENT_RECEIVED = "billing.payment_received"
    PAYMENT_FAILED = "billing.payment_failed"

    # Admin actions
    TENANT_CREATED = "admin.tenant_created"
    TENANT_UPDATED = "admin.tenant_updated"
    TENANT_SUSPENDED = "admin.tenant_suspended"
    TENANT_ACTIVATED = "admin.tenant_activated"
    PLAN_CHANGED = "admin.plan_changed"


class AuditLog(BaseModel):
    """Audit log entry for tracking actions."""
    __tablename__ = "audit_logs"

    # Who performed the action
    tenant_id = Column(String(36), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=True, index=True)
    user_id = Column(String(36), nullable=True, index=True)  # Can be TenantUser or Admin
    user_email = Column(String(255), nullable=True)
    user_type = Column(String(20), nullable=True)  # "admin", "tenant_user", "api_key", "system"

    # What action was performed
    action = Column(String(50), nullable=False, index=True)
    resource_type = Column(String(50), nullable=True)  # "agent", "document", "user", etc.
    resource_id = Column(String(36), nullable=True, index=True)
    resource_name = Column(String(255), nullable=True)

    # Details
    description = Column(Text, nullable=True)
    old_values = Column(JSONB, nullable=True)  # Previous state
    new_values = Column(JSONB, nullable=True)  # New state
    metadata = Column(JSONB, nullable=True)  # Additional context

    # Request info
    ip_address = Column(INET, nullable=True)
    user_agent = Column(String(500), nullable=True)
    request_id = Column(String(36), nullable=True)

    # Status
    status = Column(String(20), default="success", nullable=False)  # success, failed, warning
    error_message = Column(Text, nullable=True)

    # Relationships
    tenant = relationship("Tenant")

    __table_args__ = (
        Index('ix_audit_logs_tenant_action', 'tenant_id', 'action'),
        Index('ix_audit_logs_tenant_created', 'tenant_id', 'created_at'),
        Index('ix_audit_logs_resource', 'resource_type', 'resource_id'),
    )
