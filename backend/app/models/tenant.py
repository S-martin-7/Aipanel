"""
Tenant models for multi-tenancy (Level 2).

Tenants are the business accounts that use AI agents.
"""

from sqlalchemy import Column, String, Boolean, Enum, Integer, Text, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from datetime import datetime

from .base import BaseModel
from .enums import TenantStatus, TenantUserRole


class Tenant(BaseModel):
    """
    Tenant model - Business account.

    Each tenant has their own agents, documents, and usage limits.
    """

    __tablename__ = "tenants"

    # Basic info
    name = Column(String(100), nullable=False)
    slug = Column(String(50), unique=True, nullable=False, index=True)
    email = Column(String(255), nullable=False)

    # Status
    status = Column(Enum(TenantStatus), default=TenantStatus.ACTIVE, nullable=False)

    # Plan (references plans.code)
    plan_code = Column(String(50), default="demo", nullable=False, index=True)

    # Trial/Subscription dates
    trial_start = Column(DateTime, nullable=True)
    trial_end = Column(DateTime, nullable=True)
    subscription_start = Column(DateTime, nullable=True)
    subscription_end = Column(DateTime, nullable=True)

    # Payment status
    is_paid = Column(Boolean, default=False, nullable=False)
    payment_required = Column(Boolean, default=True, nullable=False)  # False for internal/special plans

    # Usage limits (can be overridden from plan)
    monthly_token_limit = Column(Integer, default=50000, nullable=False)
    current_month_usage = Column(Integer, default=0, nullable=False)
    max_agents = Column(Integer, default=1, nullable=False)
    max_documents = Column(Integer, default=20, nullable=False)
    max_users = Column(Integer, default=2, nullable=False)

    # Billing
    auto_suspend_on_overage = Column(Boolean, default=True, nullable=False)
    suspend_on_trial_end = Column(Boolean, default=True, nullable=False)

    # Suspension info
    suspended_at = Column(DateTime, nullable=True)
    suspension_reason = Column(Text, nullable=True)

    # Branding (optional)
    logo_url = Column(String(500), nullable=True)
    primary_color = Column(String(7), nullable=True)  # Hex color

    # API access
    api_key_hash = Column(String(255), nullable=True, unique=True)

    # Relationships
    users = relationship("TenantUser", back_populates="tenant", cascade="all, delete-orphan")
    agents = relationship("Agent", back_populates="tenant", cascade="all, delete-orphan")
    documents = relationship("Document", back_populates="tenant", cascade="all, delete-orphan")
    usage_records = relationship("TokenUsage", back_populates="tenant", cascade="all, delete-orphan")
    api_keys = relationship("TenantAPIKey", back_populates="tenant", cascade="all, delete-orphan")
    webhooks = relationship("Webhook", back_populates="tenant", cascade="all, delete-orphan")

    @property
    def is_trial_active(self) -> bool:
        """Check if trial is still active."""
        if not self.trial_end:
            return False
        return datetime.utcnow() < self.trial_end

    @property
    def is_trial_expired(self) -> bool:
        """Check if trial has expired."""
        if not self.trial_end:
            return False
        return datetime.utcnow() >= self.trial_end

    @property
    def days_until_trial_end(self) -> int:
        """Get days remaining in trial."""
        if not self.trial_end:
            return 0
        delta = self.trial_end - datetime.utcnow()
        return max(0, delta.days)

    @property
    def needs_payment(self) -> bool:
        """Check if tenant needs to pay to continue."""
        if not self.payment_required:
            return False
        if self.is_paid:
            return False
        return self.is_trial_expired

    def __repr__(self):
        return f"<Tenant {self.slug}>"


class TenantUser(BaseModel):
    """
    Users within a tenant (Level 2 users).

    These users interact with the tenant's agents and resources.
    """

    __tablename__ = "tenant_users"

    tenant_id = Column(String(36), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    email = Column(String(255), nullable=False)
    password_hash = Column(String(255), nullable=False)
    name = Column(String(100), nullable=False)
    role = Column(Enum(TenantUserRole), default=TenantUserRole.MEMBER, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)

    # Optional
    phone = Column(String(20), nullable=True)
    avatar_url = Column(String(500), nullable=True)

    # Last login tracking
    last_login = Column(DateTime, nullable=True)

    # Relationships
    tenant = relationship("Tenant", back_populates="users")

    # Unique constraint: email unique per tenant
    __table_args__ = (
        # Index for faster lookups
        {"sqlite_autoincrement": True},
    )

    def __repr__(self):
        return f"<TenantUser {self.email} @ {self.tenant_id}>"
