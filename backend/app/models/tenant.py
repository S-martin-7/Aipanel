"""
Tenant models for multi-tenancy (Level 2).

Tenants are the business accounts that use AI agents.
"""

from sqlalchemy import Column, String, Boolean, Enum, Integer, Text, ForeignKey, Numeric
from sqlalchemy.orm import relationship

from .base import BaseModel
from .enums import TenantStatus, TenantPlan, TenantUserRole


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

    # Status and plan
    status = Column(Enum(TenantStatus), default=TenantStatus.ACTIVE, nullable=False)
    plan = Column(Enum(TenantPlan), default=TenantPlan.FREE, nullable=False)

    # Usage limits
    monthly_token_limit = Column(Integer, default=100000, nullable=False)
    current_month_usage = Column(Integer, default=0, nullable=False)
    max_agents = Column(Integer, default=3, nullable=False)
    max_documents = Column(Integer, default=50, nullable=False)

    # Billing
    auto_suspend_on_overage = Column(Boolean, default=True, nullable=False)

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

    # Relationships
    tenant = relationship("Tenant", back_populates="users")

    # Unique constraint: email unique per tenant
    __table_args__ = (
        # Index for faster lookups
        {"sqlite_autoincrement": True},
    )

    def __repr__(self):
        return f"<TenantUser {self.email} @ {self.tenant_id}>"
