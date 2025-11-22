"""
Settings Module - Schemas.

Pydantic schemas for settings management.
"""

from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field

from app.models.enums import AIProviderType


# ============================================================
# API Keys Schemas
# ============================================================

class APIKeyBase(BaseModel):
    """Base schema for API keys."""
    provider_type: AIProviderType
    provider_name: str = Field(..., min_length=1, max_length=50)
    organization_id: Optional[str] = None
    base_url: Optional[str] = None


class CreateAPIKeyRequest(APIKeyBase):
    """Request to create/update an API key."""
    api_key: str = Field(..., min_length=10, description="The API key (will be encrypted)")


class UpdateAPIKeyRequest(BaseModel):
    """Request to update an API key."""
    api_key: Optional[str] = Field(None, min_length=10)
    organization_id: Optional[str] = None
    base_url: Optional[str] = None
    is_active: Optional[bool] = None


class APIKeyResponse(BaseModel):
    """Response for API key (masked)."""
    id: str
    provider_type: AIProviderType
    provider_name: str
    organization_id: Optional[str] = None
    base_url: Optional[str] = None
    is_active: bool
    is_valid: bool
    api_key_masked: str = Field(..., description="Masked API key showing only last 4 chars")
    last_validated_at: Optional[datetime] = None
    last_error: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class APIKeyListResponse(BaseModel):
    """Response for listing API keys."""
    items: List[APIKeyResponse]
    total: int


class ValidateAPIKeyResponse(BaseModel):
    """Response for API key validation."""
    is_valid: bool
    message: str
    provider_type: AIProviderType


# ============================================================
# Provider Info Schemas
# ============================================================

class ProviderInfo(BaseModel):
    """Information about an AI provider."""
    provider_type: AIProviderType
    provider_name: str
    description: str
    config_help: str
    is_configured: bool = False


class AvailableProvidersResponse(BaseModel):
    """Response listing available AI providers."""
    providers: List[ProviderInfo]


# ============================================================
# Tenant Settings Schemas
# ============================================================

class TenantSettingsResponse(BaseModel):
    """Response with tenant settings summary."""
    tenant_id: str
    tenant_name: str
    plan: str
    api_keys_configured: int
    has_openai: bool
    has_anthropic: bool
    monthly_token_limit: int
    current_usage: int
