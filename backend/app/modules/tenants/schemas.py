"""
Tenants Module - Schemas
"""

from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
from enum import Enum


class TenantStatus(str, Enum):
    ACTIVE = "active"
    SUSPENDED = "suspended"
    CANCELLED = "cancelled"


class CreateTenantRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    admin_email: str = Field(..., description="Email for tenant admin")
    admin_name: str = Field(..., min_length=1, max_length=100)
    admin_password: str = Field(..., min_length=8)


class UpdateTenantRequest(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    status: Optional[TenantStatus] = None
    plan: Optional[str] = None


class TenantResponse(BaseModel):
    id: str
    name: str
    plan: str
    status: TenantStatus
    tokens_used_this_period: int
    current_period_start: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class TenantListResponse(BaseModel):
    tenants: list[TenantResponse]
    total: int
