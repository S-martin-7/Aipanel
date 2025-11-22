"""
Settings Module - Router.

API endpoints for settings management.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.auth import get_current_user, get_current_tenant_id
from app.models import User

from .service import SettingsService
from .schemas import (
    CreateAPIKeyRequest,
    UpdateAPIKeyRequest,
    APIKeyResponse,
    APIKeyListResponse,
    ValidateAPIKeyResponse,
    AvailableProvidersResponse,
    TenantSettingsResponse,
    CreateExternalAPIKeyRequest,
    UpdateExternalAPIKeyRequest,
    ExternalAPIKeyResponse,
    ExternalAPIKeyCreatedResponse,
    ExternalAPIKeyListResponse,
    AvailableScopesResponse,
)

router = APIRouter(prefix="/settings", tags=["settings"])


# ============================================================
# API Keys Endpoints (for AI providers - OpenAI, Anthropic, etc.)
# ============================================================

@router.get("/api-keys", response_model=APIKeyListResponse)
async def list_api_keys(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant_id: str = Depends(get_current_tenant_id),
):
    """
    List all configured API keys for the current tenant.

    Keys are returned with masked values (only last 4 characters visible).
    """
    service = SettingsService(db)
    return await service.get_api_keys(tenant_id)


@router.post("/api-keys", response_model=APIKeyResponse, status_code=status.HTTP_201_CREATED)
async def create_api_key(
    request: CreateAPIKeyRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant_id: str = Depends(get_current_tenant_id),
):
    """
    Create or update an API key for an AI provider.

    If a key already exists for the provider type, it will be updated.
    The API key is stored encrypted.
    """
    service = SettingsService(db)
    return await service.create_api_key(tenant_id, request)


@router.patch("/api-keys/{key_id}", response_model=APIKeyResponse)
async def update_api_key(
    key_id: str,
    request: UpdateAPIKeyRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant_id: str = Depends(get_current_tenant_id),
):
    """
    Update an API key.

    Only provided fields will be updated.
    """
    service = SettingsService(db)
    result = await service.update_api_key(tenant_id, key_id, request)

    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="API key not found"
        )

    return result


@router.delete("/api-keys/{key_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_api_key(
    key_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant_id: str = Depends(get_current_tenant_id),
):
    """
    Delete an API key.
    """
    service = SettingsService(db)
    deleted = await service.delete_api_key(tenant_id, key_id)

    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="API key not found"
        )


@router.post("/api-keys/{key_id}/validate", response_model=ValidateAPIKeyResponse)
async def validate_api_key(
    key_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant_id: str = Depends(get_current_tenant_id),
):
    """
    Validate an API key by testing it with the provider.

    This will update the key's validation status.
    """
    service = SettingsService(db)
    return await service.validate_api_key(tenant_id, key_id)


# ============================================================
# External API Keys (for integrations - WhatsApp, voice bots, etc.)
# ============================================================

@router.get("/external-keys", response_model=ExternalAPIKeyListResponse)
async def list_external_api_keys(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant_id: str = Depends(get_current_tenant_id),
):
    """
    List all external API keys for the current tenant.

    External API keys allow third-party integrations (WhatsApp bots, voice
    assistants, etc.) to authenticate with the AIPanel API.
    """
    service = SettingsService(db)
    return await service.get_external_api_keys(tenant_id)


@router.post(
    "/external-keys",
    response_model=ExternalAPIKeyCreatedResponse,
    status_code=status.HTTP_201_CREATED
)
async def create_external_api_key(
    request: CreateExternalAPIKeyRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant_id: str = Depends(get_current_tenant_id),
):
    """
    Create a new external API key.

    IMPORTANT: The full API key is only returned once at creation time.
    Store it securely as it cannot be retrieved again.
    """
    service = SettingsService(db)
    try:
        return await service.create_external_api_key(tenant_id, request)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/external-keys/{key_id}", response_model=ExternalAPIKeyResponse)
async def get_external_api_key(
    key_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant_id: str = Depends(get_current_tenant_id),
):
    """
    Get details of a specific external API key.
    """
    service = SettingsService(db)
    result = await service.get_external_api_key(tenant_id, key_id)

    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="External API key not found"
        )

    return result


@router.patch("/external-keys/{key_id}", response_model=ExternalAPIKeyResponse)
async def update_external_api_key(
    key_id: str,
    request: UpdateExternalAPIKeyRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant_id: str = Depends(get_current_tenant_id),
):
    """
    Update an external API key.

    Only provided fields will be updated.
    Note: The key itself cannot be changed - create a new one instead.
    """
    service = SettingsService(db)
    try:
        result = await service.update_external_api_key(tenant_id, key_id, request)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="External API key not found"
        )

    return result


@router.delete("/external-keys/{key_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_external_api_key(
    key_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant_id: str = Depends(get_current_tenant_id),
):
    """
    Delete an external API key.

    This action is immediate and cannot be undone.
    Any integrations using this key will stop working.
    """
    service = SettingsService(db)
    deleted = await service.delete_external_api_key(tenant_id, key_id)

    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="External API key not found"
        )


@router.get("/external-keys-scopes", response_model=AvailableScopesResponse)
async def get_available_scopes(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get list of available scopes for external API keys.

    Scopes control what actions an API key can perform.
    """
    service = SettingsService(db)
    return service.get_available_scopes()


# ============================================================
# Providers Info Endpoints
# ============================================================

@router.get("/providers", response_model=AvailableProvidersResponse)
async def get_available_providers(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get list of available AI providers.

    Returns information about each provider and configuration help.
    """
    service = SettingsService(db)
    return await service.get_available_providers()


# ============================================================
# Tenant Settings Endpoints
# ============================================================

@router.get("", response_model=TenantSettingsResponse)
async def get_settings(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant_id: str = Depends(get_current_tenant_id),
):
    """
    Get tenant settings summary.

    Includes API key status, usage limits, and plan information.
    """
    service = SettingsService(db)
    result = await service.get_tenant_settings(tenant_id)

    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tenant not found"
        )

    return result
