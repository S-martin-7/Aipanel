"""
AI Lab Admin Router.

Admin endpoints for managing the dynamic AI configuration.
Provides CRUD for providers, models, profiles, routes, and feature flags.
"""

from typing import Optional, List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Body
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, Field

from app.core.database import get_db
from app.core.dependencies import AdminUser
from app.modules.ai_lab.admin_service import AILabAdminService

router = APIRouter()


def get_service(db: AsyncSession = Depends(get_db)) -> AILabAdminService:
    return AILabAdminService(db)


# ==========================================
# Request/Response Schemas
# ==========================================

class ProviderCreate(BaseModel):
    code: str = Field(..., max_length=50)
    name: str = Field(..., max_length=100)
    description: Optional[str] = None
    provider_class: str = Field(..., max_length=200)
    base_url: Optional[str] = None
    supports_streaming: bool = True
    supports_functions: bool = True
    supports_vision: bool = False
    supports_realtime: bool = False
    is_active: bool = True
    priority: int = 100


class ProviderUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    base_url: Optional[str] = None
    supports_streaming: Optional[bool] = None
    supports_functions: Optional[bool] = None
    supports_vision: Optional[bool] = None
    supports_realtime: Optional[bool] = None
    is_active: Optional[bool] = None
    priority: Optional[int] = None


class ModelCreate(BaseModel):
    provider_id: UUID
    code: str = Field(..., max_length=100)
    name: str = Field(..., max_length=200)
    description: Optional[str] = None
    model_type: str = "chat"
    context_window: int = 4096
    max_output_tokens: int = 4096
    input_price_per_1k: Optional[float] = None
    output_price_per_1k: Optional[float] = None
    supports_streaming: bool = True
    supports_functions: bool = True
    supports_vision: bool = False
    supports_json_mode: bool = False
    supports_realtime: bool = False
    is_active: bool = True
    priority: int = 100


class ModelUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    context_window: Optional[int] = None
    max_output_tokens: Optional[int] = None
    input_price_per_1k: Optional[float] = None
    output_price_per_1k: Optional[float] = None
    supports_streaming: Optional[bool] = None
    supports_functions: Optional[bool] = None
    supports_vision: Optional[bool] = None
    supports_json_mode: Optional[bool] = None
    is_active: Optional[bool] = None
    priority: Optional[int] = None


class ParamProfileCreate(BaseModel):
    tenant_id: Optional[UUID] = None
    code: str = Field(..., max_length=100)
    name: str = Field(..., max_length=200)
    description: Optional[str] = None
    temperature: float = 0.7
    top_p: float = 1.0
    top_k: Optional[int] = None
    frequency_penalty: float = 0.0
    presence_penalty: float = 0.0
    max_tokens: int = 2048
    is_default: bool = False


class RouteCreate(BaseModel):
    tenant_id: Optional[UUID] = None
    code: str = Field(..., max_length=100)
    name: str = Field(..., max_length=200)
    description: Optional[str] = None
    route_type: str = "chat"
    primary_model_id: UUID
    fallback_model_ids: List[UUID] = []
    param_profile_id: Optional[UUID] = None
    conditions: dict = {}
    priority: int = 100
    timeout_ms: int = 30000
    retry_count: int = 2
    is_active: bool = True


class TestChatRequest(BaseModel):
    provider_code: str
    model_code: str
    messages: List[dict]
    params: Optional[dict] = None


class FeatureFlagSet(BaseModel):
    code: str
    is_enabled: bool
    tenant_id: Optional[UUID] = None


# ==========================================
# PROVIDERS
# ==========================================

@router.get("/providers")
async def list_providers(
    is_active: Optional[bool] = None,
    limit: int = Query(50, le=100),
    offset: int = 0,
    current_user: AdminUser = Depends(),
    service: AILabAdminService = Depends(get_service),
):
    """List all AI providers."""
    return await service.list_providers(is_active=is_active, limit=limit, offset=offset)


@router.get("/providers/{provider_id}")
async def get_provider(
    provider_id: UUID,
    current_user: AdminUser = Depends(),
    service: AILabAdminService = Depends(get_service),
):
    """Get a provider by ID."""
    provider = await service.get_provider(provider_id)
    if not provider:
        raise HTTPException(status_code=404, detail="Provider not found")
    return provider


@router.post("/providers")
async def create_provider(
    data: ProviderCreate,
    current_user: AdminUser = Depends(),
    service: AILabAdminService = Depends(get_service),
):
    """Create a new AI provider."""
    return await service.create_provider(data.model_dump())


@router.patch("/providers/{provider_id}")
async def update_provider(
    provider_id: UUID,
    data: ProviderUpdate,
    current_user: AdminUser = Depends(),
    service: AILabAdminService = Depends(get_service),
):
    """Update a provider."""
    provider = await service.update_provider(
        provider_id, data.model_dump(exclude_unset=True)
    )
    if not provider:
        raise HTTPException(status_code=404, detail="Provider not found")
    return provider


@router.delete("/providers/{provider_id}")
async def delete_provider(
    provider_id: UUID,
    current_user: AdminUser = Depends(),
    service: AILabAdminService = Depends(get_service),
):
    """Delete a provider."""
    success = await service.delete_provider(provider_id)
    if not success:
        raise HTTPException(status_code=404, detail="Provider not found")
    return {"success": True}


# ==========================================
# MODELS
# ==========================================

@router.get("/models")
async def list_models(
    provider_id: Optional[UUID] = None,
    model_type: Optional[str] = None,
    is_active: Optional[bool] = None,
    limit: int = Query(50, le=100),
    offset: int = 0,
    current_user: AdminUser = Depends(),
    service: AILabAdminService = Depends(get_service),
):
    """List AI models."""
    return await service.list_models(
        provider_id=provider_id,
        model_type=model_type,
        is_active=is_active,
        limit=limit,
        offset=offset,
    )


@router.get("/models/{model_id}")
async def get_model(
    model_id: UUID,
    current_user: AdminUser = Depends(),
    service: AILabAdminService = Depends(get_service),
):
    """Get a model by ID."""
    model = await service.get_model(model_id)
    if not model:
        raise HTTPException(status_code=404, detail="Model not found")
    return model


@router.post("/models")
async def create_model(
    data: ModelCreate,
    current_user: AdminUser = Depends(),
    service: AILabAdminService = Depends(get_service),
):
    """Create a new AI model."""
    return await service.create_model(data.model_dump())


@router.patch("/models/{model_id}")
async def update_model(
    model_id: UUID,
    data: ModelUpdate,
    current_user: AdminUser = Depends(),
    service: AILabAdminService = Depends(get_service),
):
    """Update a model."""
    model = await service.update_model(model_id, data.model_dump(exclude_unset=True))
    if not model:
        raise HTTPException(status_code=404, detail="Model not found")
    return model


@router.delete("/models/{model_id}")
async def delete_model(
    model_id: UUID,
    current_user: AdminUser = Depends(),
    service: AILabAdminService = Depends(get_service),
):
    """Delete a model."""
    success = await service.delete_model(model_id)
    if not success:
        raise HTTPException(status_code=404, detail="Model not found")
    return {"success": True}


# ==========================================
# PARAMETER PROFILES
# ==========================================

@router.get("/param-profiles")
async def list_param_profiles(
    tenant_id: Optional[UUID] = None,
    current_user: AdminUser = Depends(),
    service: AILabAdminService = Depends(get_service),
):
    """List parameter profiles."""
    return await service.list_param_profiles(tenant_id=tenant_id)


@router.post("/param-profiles")
async def create_param_profile(
    data: ParamProfileCreate,
    current_user: AdminUser = Depends(),
    service: AILabAdminService = Depends(get_service),
):
    """Create a parameter profile."""
    return await service.create_param_profile(data.model_dump())


# ==========================================
# ROUTES
# ==========================================

@router.get("/routes")
async def list_routes(
    tenant_id: Optional[UUID] = None,
    route_type: Optional[str] = None,
    is_active: Optional[bool] = None,
    current_user: AdminUser = Depends(),
    service: AILabAdminService = Depends(get_service),
):
    """List AI routes."""
    return await service.list_routes(
        tenant_id=tenant_id,
        route_type=route_type,
        is_active=is_active,
    )


@router.post("/routes")
async def create_route(
    data: RouteCreate,
    current_user: AdminUser = Depends(),
    service: AILabAdminService = Depends(get_service),
):
    """Create an AI route."""
    return await service.create_route(data.model_dump())


# ==========================================
# FEATURE FLAGS
# ==========================================

@router.get("/feature-flags")
async def list_feature_flags(
    tenant_id: Optional[UUID] = None,
    category: Optional[str] = None,
    current_user: AdminUser = Depends(),
    service: AILabAdminService = Depends(get_service),
):
    """List feature flags."""
    return await service.list_feature_flags(tenant_id=tenant_id, category=category)


@router.post("/feature-flags")
async def set_feature_flag(
    data: FeatureFlagSet,
    current_user: AdminUser = Depends(),
    service: AILabAdminService = Depends(get_service),
):
    """Set a feature flag."""
    return await service.set_feature_flag(
        code=data.code,
        is_enabled=data.is_enabled,
        tenant_id=data.tenant_id,
    )


# ==========================================
# CACHE & HOT RELOAD
# ==========================================

@router.post("/config/invalidate-cache")
async def invalidate_cache(
    current_user: AdminUser = Depends(),
    service: AILabAdminService = Depends(get_service),
):
    """
    Invalidate all AI configuration caches.

    This forces a reload of providers, models, and routes
    without requiring a server restart.
    """
    return await service.invalidate_cache()


# ==========================================
# TEST CHAT
# ==========================================

@router.post("/test-chat")
async def test_chat(
    request: TestChatRequest,
    current_user: AdminUser = Depends(),
    service: AILabAdminService = Depends(get_service),
):
    """
    Test a model with a chat request.

    Used for testing providers and models before publishing to production.
    """
    return await service.test_chat(
        provider_code=request.provider_code,
        model_code=request.model_code,
        messages=request.messages,
        params=request.params,
    )


# ==========================================
# STATS
# ==========================================

@router.get("/stats")
async def get_stats(
    current_user: AdminUser = Depends(),
    service: AILabAdminService = Depends(get_service),
):
    """Get AI Lab statistics."""
    return await service.get_stats()
