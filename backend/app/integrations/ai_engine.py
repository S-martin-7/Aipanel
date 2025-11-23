"""
AI Engine - Dynamic Provider Loading and Routing.

Handles dynamic loading of AI providers and model routing based on configuration.
Supports tenant-specific API keys with fallback to global config.
Records usage for billing and analytics.
"""

import importlib
import base64
from typing import Optional, Type

from cryptography.fernet import Fernet
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import AIProvider, AIModel, AIRoute, AIParamProfile, TenantAPIKey, AIProviderType
from app.core.config import settings
from app.utils.logger import get_logger
from .base_provider import BaseAIProvider, Message, CompletionResponse

logger = get_logger(__name__)


# Mapping from provider names to AIProviderType enum
PROVIDER_NAME_TO_TYPE = {
    "OpenAI": AIProviderType.OPENAI,
    "Anthropic": AIProviderType.ANTHROPIC,
    "Google": AIProviderType.GOOGLE,
}


class AIEngine:
    """
    AI Engine for dynamic provider management.

    Responsibilities:
    - Load providers dynamically from database config
    - Route requests to appropriate model/provider
    - Apply parameter profiles
    - Handle fallbacks
    - Support tenant-specific API keys
    """

    def __init__(self, db: AsyncSession):
        """
        Initialize AI Engine.

        Args:
            db: Database session for loading configurations
        """
        self.db = db
        self._provider_cache: dict[str, BaseAIProvider] = {}
        self._init_cipher()

    def _init_cipher(self) -> None:
        """Initialize encryption cipher for decrypting tenant API keys."""
        key_bytes = settings.SECRET_KEY.encode()[:32].ljust(32, b'0')
        self._cipher = Fernet(base64.urlsafe_b64encode(key_bytes))

    def _decrypt_key(self, encrypted_key: str) -> str:
        """Decrypt an API key."""
        return self._cipher.decrypt(encrypted_key.encode()).decode()

    async def _get_tenant_api_key(
        self,
        tenant_id: str,
        provider_type: AIProviderType
    ) -> Optional[dict]:
        """
        Get decrypted API key for a tenant and provider.

        Args:
            tenant_id: Tenant ID
            provider_type: Provider type enum

        Returns:
            Dict with api_key and config, or None if not found
        """
        result = await self.db.execute(
            select(TenantAPIKey).where(
                TenantAPIKey.tenant_id == tenant_id,
                TenantAPIKey.provider_type == provider_type,
                TenantAPIKey.is_active == True
            )
        )
        key = result.scalar_one_or_none()

        if not key:
            return None

        try:
            api_key = self._decrypt_key(key.api_key_encrypted)
            return {
                "api_key": api_key,
                "organization_id": key.organization_id,
                "base_url": key.base_url,
            }
        except Exception as e:
            logger.error(f"Failed to decrypt API key for tenant {tenant_id}: {e}")
            return None

    async def get_provider(
        self,
        provider_id: str,
        tenant_id: Optional[str] = None
    ) -> BaseAIProvider:
        """
        Get or create provider instance.

        If tenant_id is provided, tries to use tenant-specific API key.
        Falls back to global config if tenant key not available.

        Args:
            provider_id: Provider ID from database
            tenant_id: Optional tenant ID for tenant-specific keys

        Returns:
            BaseAIProvider instance
        """
        # Cache key includes tenant_id to separate instances
        cache_key = f"{provider_id}:{tenant_id or 'global'}"

        if cache_key in self._provider_cache:
            return self._provider_cache[cache_key]

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

        # Try to get tenant-specific API key
        config = None
        if tenant_id:
            provider_type = PROVIDER_NAME_TO_TYPE.get(provider_config.name)
            if provider_type:
                tenant_key = await self._get_tenant_api_key(tenant_id, provider_type)
                if tenant_key:
                    config = {
                        "api_key": tenant_key["api_key"],
                        "organization_id": tenant_key.get("organization_id"),
                        "base_url": tenant_key.get("base_url"),
                    }
                    logger.info(f"Using tenant-specific API key for {provider_config.name}")

        # Fall back to global config if no tenant key
        if not config:
            config = provider_config.config_json or {}
            # Also check environment variables as fallback
            if not config.get("api_key"):
                if provider_config.name == "OpenAI" and settings.OPENAI_API_KEY:
                    config["api_key"] = settings.OPENAI_API_KEY
                elif provider_config.name == "Anthropic" and settings.ANTHROPIC_API_KEY:
                    config["api_key"] = settings.ANTHROPIC_API_KEY

            logger.info(f"Using global config for {provider_config.name}")

        if not config.get("api_key"):
            raise ValueError(f"No API key configured for provider: {provider_config.name}")

        # Create instance with config
        provider_instance = provider_class(config)

        # Cache for reuse
        self._provider_cache[cache_key] = provider_instance

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
            tenant_id: Optional tenant for routing and API key lookup
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

        # Get provider with tenant-specific key if available
        provider = await self.get_provider(model.provider_id, tenant_id)

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
        response = await provider.chat_completion(**params)

        # Record usage for billing (if tenant_id provided)
        if tenant_id and response.usage:
            await self._record_usage(
                tenant_id=tenant_id,
                agent_id=agent_id,
                model_name=model.name,
                usage=response.usage,
            )

        return response

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

        # Get provider with tenant-specific key if available
        provider = await self.get_provider(model.provider_id, tenant_id)

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

    def clear_cache(self, tenant_id: Optional[str] = None) -> None:
        """
        Clear provider cache.

        Args:
            tenant_id: If provided, only clear cache for this tenant.
                       If None, clear all cache.
        """
        if tenant_id:
            keys_to_remove = [k for k in self._provider_cache if k.endswith(f":{tenant_id}")]
            for key in keys_to_remove:
                del self._provider_cache[key]
            logger.info(f"Provider cache cleared for tenant {tenant_id}")
        else:
            self._provider_cache.clear()
            logger.info("Provider cache cleared")

    async def _record_usage(
        self,
        tenant_id: str,
        agent_id: Optional[str],
        model_name: str,
        usage: dict,
    ) -> None:
        """
        Record token usage for billing and analytics.

        Args:
            tenant_id: Tenant ID
            agent_id: Agent ID (optional)
            model_name: Model name used
            usage: Usage dict with token counts
        """
        try:
            # Import here to avoid circular imports
            from app.modules.usage.service import UsageService

            usage_service = UsageService(self.db)
            await usage_service.record_usage(
                tenant_id=tenant_id,
                agent_id=agent_id or "system",
                model=model_name,
                prompt_tokens=usage.get("prompt_tokens", 0),
                completion_tokens=usage.get("completion_tokens", 0),
            )
            logger.info(
                f"Usage recorded: {usage.get('total_tokens', 0)} tokens for model={model_name}",
                extra={
                    "tenant_id": tenant_id,
                    "agent_id": agent_id,
                    "model": model_name,
                    "tokens": usage.get("total_tokens", 0),
                }
            )
        except Exception as e:
            # Don't fail the request if usage tracking fails
            logger.error(f"Failed to record usage: {e}")


# Factory function for dependency injection
def get_ai_engine(db: AsyncSession) -> AIEngine:
    """Create AI Engine instance."""
    return AIEngine(db)
