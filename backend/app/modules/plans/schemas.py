"""
Plans Module - Schemas.

Pydantic schemas for plan management.
"""

from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field


class PlanFeatures(BaseModel):
    """Features included in a plan."""
    streaming: bool = True
    rag: bool = True
    realtime: bool = False
    priority_support: bool = False
    dedicated_support: bool = False
    custom_integrations: bool = False


class CreatePlanRequest(BaseModel):
    """Request to create a new plan."""
    code: str = Field(..., min_length=2, max_length=50, pattern="^[a-z0-9-]+$")
    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = None
    plan_type: str = Field(default="starter", pattern="^(demo|starter|professional|enterprise|custom)$")

    # Pricing
    price_monthly: int = Field(default=0, ge=0)
    price_yearly: int = Field(default=0, ge=0)

    # Payment
    requires_payment: bool = True
    is_trial: bool = False
    trial_days: int = Field(default=0, ge=0)

    # Limits
    max_tokens_monthly: int = Field(default=100000, ge=0)
    max_agents: int = Field(default=1, ge=1)
    max_documents: int = Field(default=20, ge=0)
    max_users: int = Field(default=2, ge=1)
    max_storage_mb: int = Field(default=100, ge=0)

    # Features
    features: Optional[Dict[str, Any]] = None

    # Display
    is_public: bool = True
    display_order: int = Field(default=0, ge=0)
    badge_text: Optional[str] = None
    badge_color: Optional[str] = Field(None, pattern="^#[0-9A-Fa-f]{6}$")


class UpdatePlanRequest(BaseModel):
    """Request to update a plan."""
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = None
    price_monthly: Optional[int] = Field(None, ge=0)
    price_yearly: Optional[int] = Field(None, ge=0)
    requires_payment: Optional[bool] = None
    trial_days: Optional[int] = Field(None, ge=0)
    max_tokens_monthly: Optional[int] = Field(None, ge=0)
    max_agents: Optional[int] = Field(None, ge=1)
    max_documents: Optional[int] = Field(None, ge=0)
    max_users: Optional[int] = Field(None, ge=1)
    max_storage_mb: Optional[int] = Field(None, ge=0)
    features: Optional[Dict[str, Any]] = None
    is_active: Optional[bool] = None
    is_public: Optional[bool] = None
    display_order: Optional[int] = Field(None, ge=0)
    badge_text: Optional[str] = None
    badge_color: Optional[str] = Field(None, pattern="^#[0-9A-Fa-f]{6}$")


class PlanResponse(BaseModel):
    """Response with plan details."""
    id: str
    code: str
    name: str
    description: Optional[str] = None
    plan_type: str

    # Pricing
    price_monthly: int
    price_yearly: int
    currency: str = "CLP"

    # Payment
    requires_payment: bool
    is_trial: bool
    trial_days: int

    # Limits
    max_tokens_monthly: int
    max_agents: int
    max_documents: int
    max_users: int
    max_storage_mb: int

    # Features
    features: Optional[Dict[str, Any]] = None

    # Display
    is_active: bool
    is_public: bool
    display_order: int
    badge_text: Optional[str] = None
    badge_color: Optional[str] = None

    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class PlanListResponse(BaseModel):
    """Response with list of plans."""
    plans: List[PlanResponse]
    total: int


class PublicPlanResponse(BaseModel):
    """Public plan info for pricing page."""
    code: str
    name: str
    description: Optional[str] = None
    price_monthly: int
    price_yearly: int
    currency: str = "CLP"
    is_trial: bool
    trial_days: int

    # Limits for display
    max_tokens_monthly: int
    max_agents: int
    max_documents: int
    max_users: int

    # Features
    features: Optional[Dict[str, Any]] = None

    # Badge
    badge_text: Optional[str] = None
    badge_color: Optional[str] = None


class AssignPlanRequest(BaseModel):
    """Request to assign a plan to a tenant."""
    plan_code: str
    start_trial: bool = True  # Start trial if plan has trial
    payment_required: Optional[bool] = None  # Override plan's payment requirement
