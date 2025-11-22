"""
Tenants Module - Schemas

Complete schemas for tenant and tenant user management.
"""

from pydantic import BaseModel, Field, EmailStr
from typing import Optional, List
from datetime import datetime
from enum import Enum


class TenantStatus(str, Enum):
    ACTIVE = "active"
    SUSPENDED = "suspended"
    PENDING = "pending"
    CANCELLED = "cancelled"


class TenantPlan(str, Enum):
    FREE = "free"
    STARTER = "starter"
    PROFESSIONAL = "professional"
    ENTERPRISE = "enterprise"


class TenantUserRole(str, Enum):
    OWNER = "owner"
    ADMIN = "admin"
    MEMBER = "member"
    VIEWER = "viewer"


# ============================================================
# Tenant Schemas
# ============================================================

class CreateTenantRequest(BaseModel):
    """Request to create a new tenant with admin user."""
    name: str = Field(..., min_length=1, max_length=100)
    slug: Optional[str] = Field(None, min_length=3, max_length=50, pattern="^[a-z0-9-]+$")
    admin_email: EmailStr = Field(..., description="Email for tenant admin")
    admin_name: str = Field(..., min_length=1, max_length=100)
    admin_password: str = Field(..., min_length=8)
    plan: TenantPlan = TenantPlan.FREE


class UpdateTenantRequest(BaseModel):
    """Request to update tenant details."""
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    plan: Optional[TenantPlan] = None
    monthly_token_limit: Optional[int] = Field(None, ge=0)
    max_agents: Optional[int] = Field(None, ge=1)
    max_documents: Optional[int] = Field(None, ge=0)
    logo_url: Optional[str] = None
    primary_color: Optional[str] = Field(None, pattern="^#[0-9A-Fa-f]{6}$")


class SuspendTenantRequest(BaseModel):
    """Request to suspend a tenant."""
    reason: str = Field(..., min_length=1, max_length=500)
    notify_users: bool = True


class TenantResponse(BaseModel):
    """Response with tenant details."""
    id: str
    name: str
    slug: Optional[str] = None
    plan: str
    status: TenantStatus
    monthly_token_limit: int = 100000
    current_month_usage: int = 0
    max_agents: int = 3
    max_documents: int = 50
    logo_url: Optional[str] = None
    primary_color: Optional[str] = None
    user_count: int = 0
    agent_count: int = 0
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class TenantListResponse(BaseModel):
    """Response with list of tenants."""
    tenants: List[TenantResponse]
    total: int


class TenantAccountOverview(BaseModel):
    """Complete tenant account overview with billing info."""
    id: str
    name: str
    slug: Optional[str] = None
    status: TenantStatus
    plan: str

    # Usage
    monthly_token_limit: int
    current_month_usage: int
    usage_percentage: float

    # Resources
    max_agents: int
    current_agents: int
    max_documents: int
    current_documents: int
    max_users: int
    current_users: int

    # Billing
    has_payment_method: bool = False
    last_payment_date: Optional[datetime] = None
    next_billing_date: Optional[datetime] = None
    outstanding_balance: int = 0  # CLP

    # API Keys configured
    api_keys_configured: int = 0
    has_openai: bool = False
    has_anthropic: bool = False

    # Dates
    created_at: datetime
    suspended_at: Optional[datetime] = None
    suspension_reason: Optional[str] = None


# ============================================================
# Tenant User Schemas
# ============================================================

class CreateTenantUserRequest(BaseModel):
    """Request to create a user within a tenant."""
    email: EmailStr
    name: str = Field(..., min_length=1, max_length=100)
    password: str = Field(..., min_length=8)
    role: TenantUserRole = TenantUserRole.MEMBER
    phone: Optional[str] = Field(None, max_length=20)


class UpdateTenantUserRequest(BaseModel):
    """Request to update a tenant user."""
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    role: Optional[TenantUserRole] = None
    phone: Optional[str] = Field(None, max_length=20)
    is_active: Optional[bool] = None


class TenantUserResponse(BaseModel):
    """Response with tenant user details."""
    id: str
    tenant_id: str
    email: str
    name: str
    role: TenantUserRole
    is_active: bool
    phone: Optional[str] = None
    avatar_url: Optional[str] = None
    last_login: Optional[datetime] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class TenantUserListResponse(BaseModel):
    """Response with list of tenant users."""
    users: List[TenantUserResponse]
    total: int


# ============================================================
# API Key Rotation Schemas
# ============================================================

class RotateAPIKeyResponse(BaseModel):
    """Response after rotating tenant API key."""
    api_key: str = Field(..., description="New API key (shown only once)")
    message: str = "API key rotated successfully. Save this key securely."
