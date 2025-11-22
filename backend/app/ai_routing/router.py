"""
AI Routing Layer.

Provides dynamic routing of AI requests based on configured routes,
with automatic fallback, circuit breaking, and load balancing.
"""

import time
import asyncio
from typing import List, Optional, Dict, Any, AsyncIterator
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.integrations.providers.base import (
    AIProviderBase,
    Message,
    GenerationParams,
    GenerationResult,
    StreamChunk,
    EmbeddingResult,
    TokenUsage,
    ToolDefinition,
)
from app.ai_config.provider_loader import provider_loader, ProviderConfig, ProviderLoadError
from app.utils.logger import get_logger
from app.core.request_context import get_contextual_logger

logger = get_contextual_logger(__name__)


class RouteType(str, Enum):
    """Types of AI routes."""
    CHAT = "chat"
    COMPLETION = "completion"
    EMBEDDING = "embedding"
    REALTIME = "realtime"


@dataclass
class ResolvedRoute:
    """A resolved route with all necessary info for execution."""
    route_id: str
    route_code: str
    provider_code: str
    provider_class: str
    model_code: str
    model_id: str
    params: GenerationParams
    timeout_ms: int
    retry_count: int
    fallback_models: List[Dict[str, str]]  # [{"model_id": ..., "model_code": ..., "provider_code": ...}]
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class RoutingContext:
    """Context for route resolution."""
    tenant_id: str
    agent_id: Optional[str] = None
    route_type: RouteType = RouteType.CHAT
    conditions: Dict[str, Any] = field(default_factory=dict)
    required_capabilities: List[str] = field(default_factory=list)


@dataclass
class ExecutionResult:
    """Result from AI execution including routing metadata."""
    result: GenerationResult
    route_used: ResolvedRoute
    fallback_used: bool = False
    fallback_model: Optional[str] = None
    retry_count: int = 0
    total_latency_ms: int = 0


class RouteNotFoundError(Exception):
    """No matching route found."""
    pass


class AllRoutesFailedError(Exception):
    """All routes (including fallbacks) failed."""
    def __init__(self, errors: List[str]):
        self.errors = errors
        super().__init__(f"All routes failed: {'; '.join(errors)}")


class AIRouter:
    """
    Dynamic AI request router.

    Features:
    - Route resolution based on conditions
    - Automatic fallback on failure
    - Circuit breaker integration
    - Retry with exponential backoff
    - Usage logging and metrics
    """

    def __init__(self, db: AsyncSession, usage_service=None):
        self.db = db
        self._usage_service = usage_service
        self._route_cache: Dict[str, List[ResolvedRoute]] = {}
        self._cache_ttl = timedelta(seconds=60)
        self._cache_timestamps: Dict[str, datetime] = {}

    async def resolve_route(
        self,
        context: RoutingContext,
    ) -> ResolvedRoute:
        """
        Resolve the best route for the given context.

        Args:
            context: Routing context with tenant, agent, conditions

        Returns:
            ResolvedRoute ready for execution
        """
        # Check cache
        cache_key = self._get_cache_key(context)
        if cache_key in self._route_cache:
            if datetime.utcnow() - self._cache_timestamps.get(cache_key, datetime.min) < self._cache_ttl:
                routes = self._route_cache[cache_key]
                if routes:
                    return routes[0]

        # Query database for matching routes
        routes = await self._query_routes(context)

        if not routes:
            raise RouteNotFoundError(
                f"No route found for tenant={context.tenant_id}, "
                f"type={context.route_type}, conditions={context.conditions}"
            )

        # Cache routes
        self._route_cache[cache_key] = routes
        self._cache_timestamps[cache_key] = datetime.utcnow()

        return routes[0]

    async def execute(
        self,
        messages: List[Message],
        context: RoutingContext,
        params_override: Optional[GenerationParams] = None,
        tools: Optional[List[ToolDefinition]] = None,
    ) -> ExecutionResult:
        """
        Execute an AI request with automatic routing and fallback.

        Args:
            messages: Chat messages
            context: Routing context
            params_override: Override route params
            tools: Tool definitions for function calling

        Returns:
            ExecutionResult with response and routing metadata
        """
        start_time = time.time()
        errors: List[str] = []

        # Resolve route
        route = await self.resolve_route(context)

        # Merge params
        params = self._merge_params(route.params, params_override, tools)

        # Try primary model
        try:
            result = await self._execute_with_retries(
                route=route,
                messages=messages,
                params=params,
                provider_code=route.provider_code,
                model_code=route.model_code,
            )

            await provider_loader.record_success(route.provider_code)

            # Record usage metrics
            await self._record_usage(
                context=context,
                model=route.model_code,
                result=result,
            )

            return ExecutionResult(
                result=result,
                route_used=route,
                fallback_used=False,
                retry_count=0,
                total_latency_ms=int((time.time() - start_time) * 1000),
            )

        except Exception as e:
            errors.append(f"{route.provider_code}/{route.model_code}: {str(e)}")
            logger.warning(f"Primary model failed: {e}")
            await provider_loader.record_error(route.provider_code)

        # Try fallbacks
        for i, fallback in enumerate(route.fallback_models):
            try:
                result = await self._execute_with_retries(
                    route=route,
                    messages=messages,
                    params=params,
                    provider_code=fallback["provider_code"],
                    model_code=fallback["model_code"],
                )

                await provider_loader.record_success(fallback["provider_code"])

                # Record usage metrics for fallback
                await self._record_usage(
                    context=context,
                    model=fallback["model_code"],
                    result=result,
                )

                return ExecutionResult(
                    result=result,
                    route_used=route,
                    fallback_used=True,
                    fallback_model=fallback["model_code"],
                    retry_count=i + 1,
                    total_latency_ms=int((time.time() - start_time) * 1000),
                )

            except Exception as e:
                errors.append(f"{fallback['provider_code']}/{fallback['model_code']}: {str(e)}")
                logger.warning(f"Fallback {i+1} failed: {e}")
                await provider_loader.record_error(fallback["provider_code"])

        raise AllRoutesFailedError(errors)

    async def execute_stream(
        self,
        messages: List[Message],
        context: RoutingContext,
        params_override: Optional[GenerationParams] = None,
        tools: Optional[List[ToolDefinition]] = None,
    ) -> AsyncIterator[StreamChunk]:
        """
        Execute a streaming AI request with routing.

        Yields chunks from the first successful provider.
        """
        errors: List[str] = []

        route = await self.resolve_route(context)
        params = self._merge_params(route.params, params_override, tools)

        # Try primary model
        try:
            provider = await self._get_provider(route.provider_code)
            async for chunk in provider.generate_stream(
                messages=messages,
                model=route.model_code,
                params=params,
            ):
                yield chunk

            await provider_loader.record_success(route.provider_code)
            return

        except Exception as e:
            errors.append(f"{route.provider_code}/{route.model_code}: {str(e)}")
            logger.warning(f"Primary streaming failed: {e}")
            await provider_loader.record_error(route.provider_code)

        # Try fallbacks
        for fallback in route.fallback_models:
            try:
                provider = await self._get_provider(fallback["provider_code"])
                async for chunk in provider.generate_stream(
                    messages=messages,
                    model=fallback["model_code"],
                    params=params,
                ):
                    yield chunk

                await provider_loader.record_success(fallback["provider_code"])
                return

            except Exception as e:
                errors.append(f"{fallback['provider_code']}/{fallback['model_code']}: {str(e)}")
                await provider_loader.record_error(fallback["provider_code"])

        raise AllRoutesFailedError(errors)

    async def embed(
        self,
        texts: List[str],
        context: RoutingContext,
    ) -> EmbeddingResult:
        """Execute embedding request with routing."""
        context.route_type = RouteType.EMBEDDING
        route = await self.resolve_route(context)

        provider = await self._get_provider(route.provider_code)
        return await provider.embed(texts=texts, model=route.model_code)

    async def _execute_with_retries(
        self,
        route: ResolvedRoute,
        messages: List[Message],
        params: GenerationParams,
        provider_code: str,
        model_code: str,
    ) -> GenerationResult:
        """Execute with retry logic."""
        last_error: Optional[Exception] = None

        for attempt in range(route.retry_count + 1):
            try:
                provider = await self._get_provider(provider_code)
                return await asyncio.wait_for(
                    provider.generate(
                        messages=messages,
                        model=model_code,
                        params=params,
                    ),
                    timeout=route.timeout_ms / 1000,
                )

            except asyncio.TimeoutError:
                last_error = TimeoutError(f"Request timed out after {route.timeout_ms}ms")
                logger.warning(f"Timeout on attempt {attempt + 1}")

            except Exception as e:
                last_error = e
                logger.warning(f"Error on attempt {attempt + 1}: {e}")

            # Exponential backoff
            if attempt < route.retry_count:
                await asyncio.sleep(0.5 * (2 ** attempt))

        raise last_error or Exception("Unknown error")

    async def _get_provider(self, provider_code: str) -> AIProviderBase:
        """Get or load a provider."""
        # Get provider config from DB
        config = await self._get_provider_config(provider_code)
        return await provider_loader.load_provider(config)

    async def _get_provider_config(self, provider_code: str) -> ProviderConfig:
        """Get provider configuration from database."""
        # Query provider
        result = await self.db.execute(
            select("*").select_from("ai_providers").where(
                and_(
                    "code" == provider_code,
                    "is_active" == True,
                )
            )
        )
        row = result.fetchone()

        if not row:
            raise ProviderLoadError(f"Provider {provider_code} not found or inactive")

        # Get API key from tenant settings or global
        api_key = await self._get_api_key(provider_code)

        return ProviderConfig(
            provider_id=str(row.id),
            code=row.code,
            name=row.name,
            provider_class=row.provider_class,
            api_key=api_key,
            base_url=row.base_url,
            default_headers=row.default_headers or {},
            timeout_ms=30000,
            max_retries=2,
            is_active=row.is_active,
            priority=row.priority,
        )

    async def _get_api_key(self, provider_code: str) -> str:
        """Get API key for provider (placeholder - implement based on your key storage)."""
        # TODO: Query from tenant_api_keys or global settings
        from app.core.config import settings

        if provider_code == "OPENAI":
            return settings.OPENAI_API_KEY or ""
        elif provider_code == "ANTHROPIC":
            return settings.ANTHROPIC_API_KEY or ""
        return ""

    async def _query_routes(self, context: RoutingContext) -> List[ResolvedRoute]:
        """Query matching routes from database."""
        # This is a simplified version - full implementation would use proper SQLAlchemy
        sql = """
            SELECT
                r.id as route_id,
                r.code as route_code,
                r.primary_model_id,
                r.fallback_model_ids,
                r.param_profile_id,
                r.timeout_ms,
                r.retry_count,
                r.conditions,
                r.metadata,
                m.code as model_code,
                m.id as model_id,
                p.code as provider_code,
                p.provider_class,
                pp.temperature,
                pp.top_p,
                pp.max_tokens,
                pp.frequency_penalty,
                pp.presence_penalty,
                pp.stop_sequences,
                pp.response_format
            FROM ai_routes r
            JOIN ai_models m ON m.id = r.primary_model_id
            JOIN ai_providers p ON p.id = m.provider_id
            LEFT JOIN ai_param_profiles pp ON pp.id = r.param_profile_id
            WHERE r.is_active = true
                AND r.route_type = :route_type
                AND (r.tenant_id IS NULL OR r.tenant_id = :tenant_id)
                AND (r.valid_from IS NULL OR r.valid_from <= NOW())
                AND (r.valid_until IS NULL OR r.valid_until >= NOW())
            ORDER BY
                CASE WHEN r.tenant_id IS NOT NULL THEN 0 ELSE 1 END,
                r.priority ASC
            LIMIT 10
        """

        from sqlalchemy import text
        result = await self.db.execute(
            text(sql),
            {
                "route_type": context.route_type.value,
                "tenant_id": context.tenant_id,
            }
        )
        rows = result.fetchall()

        routes = []
        for row in rows:
            # Build params from profile
            params = GenerationParams(
                temperature=float(row.temperature or 0.7),
                top_p=float(row.top_p or 1.0),
                max_tokens=row.max_tokens or 2048,
                frequency_penalty=float(row.frequency_penalty or 0),
                presence_penalty=float(row.presence_penalty or 0),
                stop_sequences=row.stop_sequences or [],
                response_format=row.response_format,
            )

            # Build fallback list
            fallbacks = []
            if row.fallback_model_ids:
                # Query fallback models (simplified)
                for model_id in row.fallback_model_ids:
                    fallbacks.append({
                        "model_id": str(model_id),
                        "model_code": "",  # Would query from DB
                        "provider_code": "",
                    })

            routes.append(ResolvedRoute(
                route_id=str(row.route_id),
                route_code=row.route_code,
                provider_code=row.provider_code,
                provider_class=row.provider_class,
                model_code=row.model_code,
                model_id=str(row.model_id),
                params=params,
                timeout_ms=row.timeout_ms or 30000,
                retry_count=row.retry_count or 2,
                fallback_models=fallbacks,
                metadata=row.metadata or {},
            ))

        return routes

    def _merge_params(
        self,
        route_params: GenerationParams,
        override: Optional[GenerationParams],
        tools: Optional[List[ToolDefinition]],
    ) -> GenerationParams:
        """Merge route params with overrides."""
        if not override and not tools:
            return route_params

        return GenerationParams(
            temperature=override.temperature if override else route_params.temperature,
            top_p=override.top_p if override else route_params.top_p,
            top_k=override.top_k if override else route_params.top_k,
            max_tokens=override.max_tokens if override else route_params.max_tokens,
            stop_sequences=override.stop_sequences if override else route_params.stop_sequences,
            frequency_penalty=override.frequency_penalty if override else route_params.frequency_penalty,
            presence_penalty=override.presence_penalty if override else route_params.presence_penalty,
            response_format=override.response_format if override else route_params.response_format,
            seed=override.seed if override else route_params.seed,
            tools=tools,
            tool_choice=override.tool_choice if override else None,
        )

    def _get_cache_key(self, context: RoutingContext) -> str:
        """Generate cache key for route lookup."""
        return f"{context.tenant_id}:{context.route_type}:{context.agent_id or 'default'}"

    async def _record_usage(
        self,
        context: RoutingContext,
        model: str,
        result: GenerationResult,
    ) -> None:
        """
        Record token usage for billing and analytics.

        Args:
            context: Routing context with tenant/agent info
            model: Model code used
            result: Generation result with token usage
        """
        if not self._usage_service or not result.usage:
            return

        try:
            await self._usage_service.record_usage(
                tenant_id=context.tenant_id,
                agent_id=context.agent_id or "default",
                model=model,
                prompt_tokens=result.usage.prompt_tokens,
                completion_tokens=result.usage.completion_tokens,
            )
            logger.info(
                f"Recorded usage: {result.usage.total_tokens} tokens for {model}",
                extra={
                    "tenant_id": context.tenant_id,
                    "agent_id": context.agent_id,
                    "model": model,
                    "tokens": result.usage.total_tokens,
                }
            )
        except Exception as e:
            # Don't fail the request if usage tracking fails
            logger.error(f"Failed to record usage: {e}", extra={"error": str(e)})

    async def invalidate_cache(self, tenant_id: Optional[str] = None) -> None:
        """Invalidate route cache."""
        if tenant_id:
            keys_to_remove = [k for k in self._route_cache if k.startswith(tenant_id)]
        else:
            keys_to_remove = list(self._route_cache.keys())

        for key in keys_to_remove:
            self._route_cache.pop(key, None)
            self._cache_timestamps.pop(key, None)

        logger.info(f"Invalidated {len(keys_to_remove)} route cache entries")
