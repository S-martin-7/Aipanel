"""
AI Engine - Dynamic Provider Loading and Routing.

Handles dynamic loading of AI providers and model routing based on configuration.
"""

import importlib
from typing import Optional, Type
from functools import lru_cache

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import AIProvider, AIModel, AIRoute, AIParamProfile
from app.utils.logger import get_logger
from .base_provider import BaseAIProvider, Message, CompletionResponse

logger = get_logger(__name__)


class AIEngine:
    """
    AI Engine for dynamic provider management.

    Responsibilities:
    - Load providers dynamically from database config
    - Route requests to appropriate model/provider
    - Apply parameter profiles
    - Handle fallbacks
    """

    def __init__(self, db: AsyncSession):
        """
        Initialize AI Engine.

        Args:
            db: Database session for loading configurations
        """
        self.db = db
        self._provider_cache: dict[str, BaseAIProvider] = {}

    async def get_provider(self, provider_id: str) -> BaseAIProvider:
        """
        Get or create provider instance.

        Providers are cached for reuse.

        Args:
            provider_id: Provider ID from database

        Returns:
            BaseAIProvider instance
        """
        if provider_id in self._provider_cache:
            return self._provider_cache[provider_id]

        # Load provider config from database
        result = await self.db.execute(
            select(AIProvider).where(
                AIProvider.id == provider_id,
                AIProvider.is_active == True
            )
        )
        provider_config = result.scalar_one_or_none()

        if not provider_config:
            raise ValueError(f"Provider not found or inactive: {provider_id}")

        # Dynamically load provider class
        provider_class = self._load_provider_class(
            provider_config.handler_module,
            provider_config.handler_class
        )

        # Create instance with config
        config = provider_config.config_json or {}
        provider_instance = provider_class(config)

        # Cache for reuse
        self._provider_cache[provider_id] = provider_instance

        logger.info(f"Loaded provider: {provider_config.name}")
        return provider_instance

    def _load_provider_class(
        self,
        module_path: str,
        class_name: str
    ) -> Type[BaseAIProvider]:
        """
        Dynamically load provider class.

        Args:
            module_path: Full module path (e.g., "app.integrations.openai_client")
            class_name: Class name (e.g., "OpenAIProvider")

        Returns:
            Provider class
        """
        try:
            module = importlib.import_module(module_path)
            provider_class = getattr(module, class_name)

            if not issubclass(provider_class, BaseAIProvider):
                # For backwards compatibility, wrap legacy clients
                logger.warning(f"{class_name} doesn't inherit BaseAIProvider")

            return provider_class
        except (ImportError, AttributeError) as e:
            logger.error(f"Failed to load provider {module_path}.{class_name}: {e}")
            raise ValueError(f"Invalid provider configuration: {e}")

    async def resolve_route(
        self,
        tenant_id: Optional[str] = None,
        agent_id: Optional[str] = None,
        mode: str = "CHAT"
    ) -> tuple[AIModel, Optional[AIParamProfile]]:
        """
        Resolve the best route for given context.

        Routes are matched by specificity:
        1. Agent-specific route
        2. Tenant-specific route
        3. Global route

        Args:
            tenant_id: Optional tenant ID
            agent_id: Optional agent ID
            mode: Interaction mode (CHAT, REALTIME)

        Returns:
            Tuple of (AIModel, optional AIParamProfile)
        """
        # Build query for matching routes
        query = select(AIRoute).where(
            AIRoute.mode == mode,
            AIRoute.is_active == True
        )

        # Add scope filters
        if agent_id:
            query = query.where(
                (AIRoute.agent_id == agent_id) |
                (AIRoute.agent_id == None)
            )
        if tenant_id:
            query = query.where(
                (AIRoute.tenant_id == tenant_id) |
                (AIRoute.tenant_id == None)
            )

        # Order by priority (higher = more specific)
        query = query.order_by(AIRoute.priority.desc())

        result = await self.db.execute(query)
        routes = result.scalars().all()

        if not routes:
            raise ValueError(f"No active route found for mode={mode}")

        # Get best matching route
        best_route = routes[0]

        # Load model
        model_result = await self.db.execute(
            select(AIModel).where(AIModel.id == best_route.model_id)
        )
        model = model_result.scalar_one_or_none()

        if not model:
            raise ValueError(f"Model not found: {best_route.model_id}")

        # Load param profile if specified
        param_profile = None
        if best_route.param_profile_id:
            profile_result = await self.db.execute(
                select(AIParamProfile).where(
                    AIParamProfile.id == best_route.param_profile_id
                )
            )
            param_profile = profile_result.scalar_one_or_none()

        logger.info(f"Resolved route: model={model.name}, profile={param_profile.name if param_profile else 'default'}")
        return model, param_profile

    async def chat_completion(
        self,
        messages: list[Message],
        tenant_id: Optional[str] = None,
        agent_id: Optional[str] = None,
        mode: str = "CHAT",
        **kwargs
    ) -> CompletionResponse:
        """
        Execute chat completion using resolved route.

        Args:
            messages: Conversation messages
            tenant_id: Optional tenant for routing
            agent_id: Optional agent for routing
            mode: Interaction mode
            **kwargs: Additional parameters (can override route settings)

        Returns:
            CompletionResponse with content and usage
        """
        # Resolve route
        model, param_profile = await self.resolve_route(
            tenant_id=tenant_id,
            agent_id=agent_id,
            mode=mode
        )

        # Get provider
        provider = await self.get_provider(model.provider_id)

        # Build parameters from profile
        params = {
            "messages": messages,
            "model": model.name,
            "max_tokens": kwargs.get("max_tokens", model.max_tokens or 2048)
        }

        if param_profile:
            if param_profile.temperature is not None:
                params["temperature"] = param_profile.temperature
            if param_profile.max_tokens is not None:
                params["max_tokens"] = param_profile.max_tokens
            if param_profile.top_p is not None:
                params["top_p"] = param_profile.top_p

        # Override with kwargs
        params.update({k: v for k, v in kwargs.items() if v is not None})

        # Execute completion
        return await provider.chat_completion(**params)

    async def stream_completion(
        self,
        messages: list[Message],
        tenant_id: Optional[str] = None,
        agent_id: Optional[str] = None,
        mode: str = "CHAT",
        **kwargs
    ):
        """
        Stream chat completion using resolved route.

        Yields text chunks as they are generated.
        """
        model, param_profile = await self.resolve_route(
            tenant_id=tenant_id,
            agent_id=agent_id,
            mode=mode
        )

        provider = await self.get_provider(model.provider_id)

        params = {
            "messages": messages,
            "model": model.name,
            "max_tokens": kwargs.get("max_tokens", model.max_tokens or 2048)
        }

        if param_profile:
            if param_profile.temperature is not None:
                params["temperature"] = param_profile.temperature

        params.update({k: v for k, v in kwargs.items() if v is not None})

        async for chunk in provider.stream_completion(**params):
            yield chunk

    def clear_cache(self) -> None:
        """Clear provider cache (useful after config changes)."""
        self._provider_cache.clear()
        logger.info("Provider cache cleared")


# Factory function for dependency injection
def get_ai_engine(db: AsyncSession) -> AIEngine:
    """Create AI Engine instance."""
    return AIEngine(db)
