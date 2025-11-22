"""
AI Lab Module - Router.

API endpoints for testing and experimenting with AI models.
Admin only.
"""

from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import AdminUser

from .service import AILabService
from .schemas import (
    ProviderResponse,
    ProviderListResponse,
    ModelResponse,
    ModelListResponse,
    TestCompletionRequest,
    TestCompletionResponse,
    CompareModelsRequest,
    CompareModelsResponse,
    ParamProfileListResponse,
    AILabStats,
)

router = APIRouter()


def get_ai_lab_service(db: AsyncSession = Depends(get_db)) -> AILabService:
    return AILabService(db)


# ============================================================
# Providers
# ============================================================

@router.get("/providers", response_model=ProviderListResponse)
async def list_providers(
    current_user: AdminUser,
    service: AILabService = Depends(get_ai_lab_service),
    include_inactive: bool = Query(False, description="Include inactive providers"),
):
    """
    List all AI providers.

    Admin only.
    """
    return await service.list_providers(include_inactive=include_inactive)


@router.get("/providers/{provider_id}", response_model=ProviderResponse)
async def get_provider(
    provider_id: str,
    current_user: AdminUser,
    service: AILabService = Depends(get_ai_lab_service),
):
    """Get provider details."""
    provider = await service.get_provider(provider_id)
    if not provider:
        raise HTTPException(status_code=404, detail="Provider not found")
    return provider


# ============================================================
# Models
# ============================================================

@router.get("/models", response_model=ModelListResponse)
async def list_models(
    current_user: AdminUser,
    service: AILabService = Depends(get_ai_lab_service),
    provider_id: Optional[str] = Query(None, description="Filter by provider"),
    status: Optional[str] = Query(None, description="Filter by status"),
    capability: Optional[str] = Query(None, description="Filter by capability (chat, vision, etc.)"),
    include_inactive: bool = Query(False, description="Include models from inactive providers"),
):
    """
    List all AI models.

    Admin only.
    """
    return await service.list_models(
        provider_id=provider_id,
        status=status,
        capability=capability,
        include_inactive=include_inactive,
    )


@router.get("/models/{model_id}", response_model=ModelResponse)
async def get_model(
    model_id: str,
    current_user: AdminUser,
    service: AILabService = Depends(get_ai_lab_service),
):
    """Get model details."""
    model = await service.get_model(model_id)
    if not model:
        raise HTTPException(status_code=404, detail="Model not found")
    return model


# ============================================================
# Test Completions
# ============================================================

@router.post("/test", response_model=TestCompletionResponse)
async def test_completion(
    request: TestCompletionRequest,
    current_user: AdminUser,
    service: AILabService = Depends(get_ai_lab_service),
):
    """
    Test a completion with a specific model.

    Useful for:
    - Testing new models before deployment
    - Validating API key configurations
    - Comparing model outputs

    Admin only.
    """
    try:
        return await service.test_completion(request)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/test/stream")
async def test_stream_completion(
    request: TestCompletionRequest,
    current_user: AdminUser,
    service: AILabService = Depends(get_ai_lab_service),
):
    """
    Test a streaming completion.

    Returns Server-Sent Events stream.
    Admin only.
    """
    return StreamingResponse(
        service.stream_test_completion(request),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


# ============================================================
# Compare Models
# ============================================================

@router.post("/compare", response_model=CompareModelsResponse)
async def compare_models(
    request: CompareModelsRequest,
    current_user: AdminUser,
    service: AILabService = Depends(get_ai_lab_service),
):
    """
    Compare responses from multiple models.

    Runs the same prompt through 2-5 models concurrently
    and returns results with timing and cost comparison.

    Admin only.
    """
    return await service.compare_models(request)


# ============================================================
# Param Profiles
# ============================================================

@router.get("/profiles", response_model=ParamProfileListResponse)
async def list_param_profiles(
    current_user: AdminUser,
    service: AILabService = Depends(get_ai_lab_service),
):
    """
    List all parameter profiles.

    Profiles are preset configurations (creative, precise, balanced, etc.)
    that can be applied to agents.

    Admin only.
    """
    return await service.list_param_profiles()


# ============================================================
# Stats
# ============================================================

@router.get("/stats", response_model=AILabStats)
async def get_stats(
    current_user: AdminUser,
    service: AILabService = Depends(get_ai_lab_service),
):
    """
    Get AI Lab statistics.

    Admin only.
    """
    return await service.get_stats()
