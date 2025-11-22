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


# ============================================================
# External API Keys Schemas (for integrations)
# ============================================================

class CreateExternalAPIKeyRequest(BaseModel):
    """Request to create an external API key for integrations."""
    name: str = Field(..., min_length=1, max_length=100, description="Name for the API key (e.g., 'WhatsApp Bot')")
    description: Optional[str] = Field(None, max_length=500)
    scopes: Optional[List[str]] = Field(None, description="Permission scopes (empty = all)")
    agent_id: Optional[str] = Field(None, description="Restrict to specific agent")
    rate_limit: int = Field(60, ge=0, description="Requests per minute (0 = unlimited)")
    expires_at: Optional[datetime] = Field(None, description="Expiration date (optional)")
    allowed_ips: Optional[str] = Field(None, description="Comma-separated IPs (optional)")


class UpdateExternalAPIKeyRequest(BaseModel):
    """Request to update an external API key."""
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = None
    scopes: Optional[List[str]] = None
    agent_id: Optional[str] = None
    rate_limit: Optional[int] = Field(None, ge=0)
    is_active: Optional[bool] = None
    expires_at: Optional[datetime] = None
    allowed_ips: Optional[str] = None


class ExternalAPIKeyResponse(BaseModel):
    """Response for external API key (without the actual key)."""
    id: str
    name: str
    description: Optional[str] = None
    key_prefix: str = Field(..., description="First 12 chars of the key for identification")
    scopes: Optional[List[str]] = None
    agent_id: Optional[str] = None
    rate_limit: int
    is_active: bool
    last_used_at: Optional[datetime] = None
    total_requests: int
    expires_at: Optional[datetime] = None
    allowed_ips: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class ExternalAPIKeyCreatedResponse(ExternalAPIKeyResponse):
    """Response when creating an external API key (includes the actual key)."""
    api_key: str = Field(..., description="The full API key (only shown once!)")


class ExternalAPIKeyListResponse(BaseModel):
    """Response for listing external API keys."""
    items: List[ExternalAPIKeyResponse]
    total: int


class AvailableScopesResponse(BaseModel):
    """Response listing available API key scopes."""
    scopes: List[str]
