"""
AI Lab Module - Service.

Business logic for AI testing and experimentation.
"""

import asyncio
import time
import uuid
from decimal import Decimal
from typing import Optional, List, AsyncIterator

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import AIProvider, AIModel, AIParamProfile
from app.integrations import AIEngine
from app.utils.logger import get_logger

from .schemas import (
    ProviderResponse,
    ProviderListResponse,
    ModelResponse,
    ModelListResponse,
    TestCompletionRequest,
    TestCompletionResponse,
    CompareModelsRequest,
    CompareModelsResponse,
    ModelComparisonResult,
    ParamProfileResponse,
    ParamProfileListResponse,
    AILabStats,
)

logger = get_logger(__name__)


class AILabService:
    """Service for AI Lab operations."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.ai_engine = AIEngine(db)

    # ============================================================
    # Providers
    # ============================================================

    async def list_providers(
        self,
        include_inactive: bool = False
    ) -> ProviderListResponse:
        """List all AI providers."""
        query = select(AIProvider)
        if not include_inactive:
            query = query.where(AIProvider.is_active == True)
        query = query.order_by(AIProvider.name)

        result = await self.db.execute(query)
        providers = result.scalars().all()

        items = []
        for provider in providers:
            # Count models
            model_count = await self.db.execute(
                select(func.count(AIModel.id)).where(
                    AIModel.provider_id == provider.id
                )
            )
            count = model_count.scalar() or 0

            items.append(ProviderResponse(
                id=provider.id,
                name=provider.name,
                display_name=provider.display_name,
                is_active=provider.is_active,
                allowed_in_prod=provider.allowed_in_prod,
                models_count=count,
                config=provider.config_json if provider.config_json else None,
            ))

        return ProviderListResponse(items=items, total=len(items))

    async def get_provider(self, provider_id: str) -> Optional[ProviderResponse]:
        """Get provider by ID."""
        result = await self.db.execute(
            select(AIProvider).where(AIProvider.id == provider_id)
        )
        provider = result.scalar_one_or_none()
        if not provider:
            return None

        model_count = await self.db.execute(
            select(func.count(AIModel.id)).where(
                AIModel.provider_id == provider.id
            )
        )
        count = model_count.scalar() or 0

        return ProviderResponse(
            id=provider.id,
            name=provider.name,
            display_name=provider.display_name,
            is_active=provider.is_active,
            allowed_in_prod=provider.allowed_in_prod,
            models_count=count,
            config=provider.config_json,
        )

    # ============================================================
    # Models
    # ============================================================

    async def list_models(
        self,
        provider_id: Optional[str] = None,
        status: Optional[str] = None,
        capability: Optional[str] = None,
        include_inactive: bool = False
    ) -> ModelListResponse:
        """List AI models with optional filters."""
        query = select(AIModel)

        if provider_id:
            query = query.where(AIModel.provider_id == provider_id)
        if status:
            query = query.where(AIModel.status == status)
        if not include_inactive:
            # Get only models from active providers
            query = query.join(AIProvider).where(AIProvider.is_active == True)

        query = query.order_by(AIModel.name)

        result = await self.db.execute(query)
        models = result.scalars().all()

        # Filter by capability if specified
        if capability:
            models = [m for m in models if m.capabilities and capability in m.capabilities]

        items = []
        for model in models:
            # Get provider name
            provider_result = await self.db.execute(
                select(AIProvider.name).where(AIProvider.id == model.provider_id)
            )
            provider_name = provider_result.scalar()

            items.append(ModelResponse(
                id=model.id,
                provider_id=model.provider_id,
                provider_name=provider_name,
                name=model.name,
                display_name=model.display_name,
                description=model.description,
                capabilities=model.capabilities,
                status=model.status.value if hasattr(model.status, 'value') else str(model.status),
                pricing_input=model.pricing_input,
                pricing_output=model.pricing_output,
                max_tokens=model.max_tokens,
                context_window=model.context_window,
                supports_streaming=model.supports_streaming,
                supports_vision=model.supports_vision,
                supports_tools=model.supports_tools,
            ))

        return ModelListResponse(items=items, total=len(items))

    async def get_model(self, model_id: str) -> Optional[ModelResponse]:
        """Get model by ID."""
        result = await self.db.execute(
            select(AIModel).where(AIModel.id == model_id)
        )
        model = result.scalar_one_or_none()
        if not model:
            return None

        provider_result = await self.db.execute(
            select(AIProvider.name).where(AIProvider.id == model.provider_id)
        )
        provider_name = provider_result.scalar()

        return ModelResponse(
            id=model.id,
            provider_id=model.provider_id,
            provider_name=provider_name,
            name=model.name,
            display_name=model.display_name,
            description=model.description,
            capabilities=model.capabilities,
            status=model.status.value if hasattr(model.status, 'value') else str(model.status),
            pricing_input=model.pricing_input,
            pricing_output=model.pricing_output,
            max_tokens=model.max_tokens,
            context_window=model.context_window,
            supports_streaming=model.supports_streaming,
            supports_vision=model.supports_vision,
            supports_tools=model.supports_tools,
        )

    # ============================================================
    # Test Completions
    # ============================================================

    async def test_completion(
        self,
        request: TestCompletionRequest
    ) -> TestCompletionResponse:
        """Test a completion with a specific model."""
        # Get model info
        model = await self.get_model(request.model_id)
        if not model:
            raise ValueError(f"Model {request.model_id} not found")

        # Convert messages
        messages = [{"role": m.role, "content": m.content} for m in request.messages]

        # Time the request
        start_time = time.time()

        # Call AI engine (using global API keys for lab testing)
        try:
            response = await self.ai_engine.chat_completion(
                messages=messages,
                model_id=request.model_id,
                temperature=request.temperature,
                max_tokens=request.max_tokens,
            )
        except Exception as e:
            logger.error(f"AI Lab test failed: {e}")
            raise ValueError(f"Completion failed: {str(e)}")

        latency_ms = int((time.time() - start_time) * 1000)

        # Calculate estimated cost
        usage = response.usage or {}
        input_tokens = usage.get("prompt_tokens", 0)
        output_tokens = usage.get("completion_tokens", 0)

        input_cost = Decimal(input_tokens) * (model.pricing_input or Decimal(0)) / 1000
        output_cost = Decimal(output_tokens) * (model.pricing_output or Decimal(0)) / 1000
        estimated_cost = input_cost + output_cost

        return TestCompletionResponse(
            id=str(uuid.uuid4()),
            model=model.name,
            provider=model.provider_name or "unknown",
            content=response.content,
            finish_reason=response.finish_reason,
            usage={
                "prompt_tokens": input_tokens,
                "completion_tokens": output_tokens,
                "total_tokens": input_tokens + output_tokens,
            },
            latency_ms=latency_ms,
            estimated_cost=estimated_cost,
        )

    async def stream_test_completion(
        self,
        request: TestCompletionRequest
    ) -> AsyncIterator[str]:
        """Stream a test completion."""
        model = await self.get_model(request.model_id)
        if not model:
            yield f"data: {{\"error\": \"Model not found\"}}\n\n"
            return

        messages = [{"role": m.role, "content": m.content} for m in request.messages]
        chunk_id = str(uuid.uuid4())

        try:
            async for chunk in self.ai_engine.stream_completion(
                messages=messages,
                model_id=request.model_id,
                temperature=request.temperature,
                max_tokens=request.max_tokens,
            ):
                yield f"data: {{\"id\": \"{chunk_id}\", \"delta\": \"{self._escape_json(chunk)}\"}}\n\n"

            yield f"data: {{\"id\": \"{chunk_id}\", \"delta\": \"\", \"finish_reason\": \"stop\"}}\n\n"
            yield "data: [DONE]\n\n"

        except Exception as e:
            logger.error(f"Stream test error: {e}")
            yield f"data: {{\"error\": \"{self._escape_json(str(e))}\"}}\n\n"

    # ============================================================
    # Compare Models
    # ============================================================

    async def compare_models(
        self,
        request: CompareModelsRequest
    ) -> CompareModelsResponse:
        """Compare responses from multiple models."""
        results = []
        messages = [{"role": m.role, "content": m.content} for m in request.messages]

        # Run all models concurrently
        async def test_model(model_id: str) -> ModelComparisonResult:
            model = await self.get_model(model_id)
            if not model:
                return ModelComparisonResult(
                    model_id=model_id,
                    model_name="Unknown",
                    provider="Unknown",
                    content="",
                    usage={},
                    latency_ms=0,
                    estimated_cost=Decimal(0),
                    error=f"Model {model_id} not found"
                )

            start_time = time.time()

            try:
                response = await self.ai_engine.chat_completion(
                    messages=messages,
                    model_id=model_id,
                    temperature=request.temperature,
                    max_tokens=request.max_tokens,
                )

                latency_ms = int((time.time() - start_time) * 1000)
                usage = response.usage or {}
                input_tokens = usage.get("prompt_tokens", 0)
                output_tokens = usage.get("completion_tokens", 0)

                input_cost = Decimal(input_tokens) * (model.pricing_input or Decimal(0)) / 1000
                output_cost = Decimal(output_tokens) * (model.pricing_output or Decimal(0)) / 1000

                return ModelComparisonResult(
                    model_id=model_id,
                    model_name=model.display_name or model.name,
                    provider=model.provider_name or "Unknown",
                    content=response.content,
                    usage={
                        "prompt_tokens": input_tokens,
                        "completion_tokens": output_tokens,
                        "total_tokens": input_tokens + output_tokens,
                    },
                    latency_ms=latency_ms,
                    estimated_cost=input_cost + output_cost,
                )

            except Exception as e:
                latency_ms = int((time.time() - start_time) * 1000)
                return ModelComparisonResult(
                    model_id=model_id,
                    model_name=model.display_name or model.name,
                    provider=model.provider_name or "Unknown",
                    content="",
                    usage={},
                    latency_ms=latency_ms,
                    estimated_cost=Decimal(0),
                    error=str(e)
                )

        # Execute concurrently
        results = await asyncio.gather(*[test_model(mid) for mid in request.model_ids])

        # Find fastest and cheapest (excluding errors)
        valid_results = [r for r in results if not r.error]

        fastest_model = min(valid_results, key=lambda x: x.latency_ms).model_id if valid_results else ""
        cheapest_model = min(valid_results, key=lambda x: x.estimated_cost).model_id if valid_results else ""

        return CompareModelsResponse(
            results=list(results),
            fastest_model=fastest_model,
            cheapest_model=cheapest_model,
        )

    # ============================================================
    # Param Profiles
    # ============================================================

    async def list_param_profiles(self) -> ParamProfileListResponse:
        """List all parameter profiles."""
        result = await self.db.execute(
            select(AIParamProfile).order_by(AIParamProfile.name)
        )
        profiles = result.scalars().all()

        items = [
            ParamProfileResponse(
                id=p.id,
                name=p.name,
                description=p.description,
                temperature=p.temperature,
                max_tokens=p.max_tokens,
                top_p=p.top_p,
                frequency_penalty=p.frequency_penalty,
                presence_penalty=p.presence_penalty,
                is_active=p.is_active,
            )
            for p in profiles
        ]

        return ParamProfileListResponse(items=items, total=len(items))

    # ============================================================
    # Stats
    # ============================================================

    async def get_stats(self) -> AILabStats:
        """Get AI Lab statistics."""
        # Providers
        total_providers = await self.db.execute(select(func.count(AIProvider.id)))
        active_providers = await self.db.execute(
            select(func.count(AIProvider.id)).where(AIProvider.is_active == True)
        )

        # Models
        total_models = await self.db.execute(select(func.count(AIModel.id)))
        active_models = await self.db.execute(
            select(func.count(AIModel.id)).where(AIModel.status == "STABLE")
        )

        # Profiles
        total_profiles = await self.db.execute(select(func.count(AIParamProfile.id)))

        return AILabStats(
            total_providers=total_providers.scalar() or 0,
            active_providers=active_providers.scalar() or 0,
            total_models=total_models.scalar() or 0,
            active_models=active_models.scalar() or 0,
            total_param_profiles=total_profiles.scalar() or 0,
            tests_today=0,  # TODO: Track test usage
            tests_this_month=0,
        )

    def _escape_json(self, text: str) -> str:
        """Escape text for JSON string."""
        return (
            text.replace("\\", "\\\\")
            .replace('"', '\\"')
            .replace("\n", "\\n")
            .replace("\r", "\\r")
            .replace("\t", "\\t")
        )
