"""
Dynamic Provider Loader.

Handles dynamic loading and caching of AI provider plugins
using importlib for runtime class loading.
"""

import importlib
import asyncio
from typing import Dict, Optional, Type, Any
from datetime import datetime, timedelta
from dataclasses import dataclass, field

from app.integrations.providers.base import AIProviderBase, ProviderHealth
from app.utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class CachedProvider:
    """Cached provider instance with metadata."""
    instance: AIProviderBase
    provider_id: str
    provider_code: str
    loaded_at: datetime
    last_health_check: Optional[datetime] = None
    health_status: Optional[ProviderHealth] = None
    error_count: int = 0


@dataclass
class ProviderConfig:
    """Configuration for loading a provider."""
    provider_id: str
    code: str
    name: str
    provider_class: str  # Full path: app.integrations.providers.openai_provider.OpenAIProvider
    api_key: str
    base_url: Optional[str] = None
    organization_id: Optional[str] = None
    default_headers: Dict[str, str] = field(default_factory=dict)
    timeout_ms: int = 30000
    max_retries: int = 2
    is_active: bool = True
    priority: int = 100


class ProviderLoadError(Exception):
    """Error loading a provider."""
    pass


class ProviderLoader:
    """
    Dynamic provider loader with caching and health tracking.

    Features:
    - Dynamic class loading via importlib
    - Instance caching with TTL
    - Health check tracking
    - Circuit breaker support
    - Thread-safe operations
    """

    def __init__(
        self,
        cache_ttl_seconds: int = 300,
        health_check_interval: int = 60,
        max_error_count: int = 5,
    ):
        self.cache_ttl = timedelta(seconds=cache_ttl_seconds)
        self.health_check_interval = timedelta(seconds=health_check_interval)
        self.max_error_count = max_error_count

        self._cache: Dict[str, CachedProvider] = {}
        self._class_cache: Dict[str, Type[AIProviderBase]] = {}
        self._lock = asyncio.Lock()
        self._config_version = 0

    async def load_provider(
        self,
        config: ProviderConfig,
        force_reload: bool = False,
    ) -> AIProviderBase:
        """
        Load and cache a provider instance.

        Args:
            config: Provider configuration
            force_reload: Force reload even if cached

        Returns:
            Initialized provider instance
        """
        cache_key = self._get_cache_key(config)

        async with self._lock:
            # Check cache
            if not force_reload and cache_key in self._cache:
                cached = self._cache[cache_key]

                # Check if cache is still valid
                if datetime.utcnow() - cached.loaded_at < self.cache_ttl:
                    # Check circuit breaker
                    if cached.error_count >= self.max_error_count:
                        logger.warning(
                            f"Provider {config.code} circuit breaker open "
                            f"(errors: {cached.error_count})"
                        )
                        raise ProviderLoadError(
                            f"Provider {config.code} is unhealthy (circuit breaker open)"
                        )
                    return cached.instance

            # Load provider class
            provider_class = self._load_class(config.provider_class)

            # Create instance
            try:
                instance = provider_class(
                    api_key=config.api_key,
                    base_url=config.base_url,
                    organization_id=config.organization_id,
                    default_headers=config.default_headers,
                    timeout=config.timeout_ms,
                    max_retries=config.max_retries,
                )

                # Initialize
                await instance.initialize()

                # Cache
                self._cache[cache_key] = CachedProvider(
                    instance=instance,
                    provider_id=config.provider_id,
                    provider_code=config.code,
                    loaded_at=datetime.utcnow(),
                )

                logger.info(f"Loaded provider: {config.code} ({config.provider_class})")
                return instance

            except Exception as e:
                logger.error(f"Error loading provider {config.code}: {e}")
                raise ProviderLoadError(f"Failed to load provider {config.code}: {e}")

    def _load_class(self, class_path: str) -> Type[AIProviderBase]:
        """
        Dynamically load a provider class.

        Args:
            class_path: Full module path (e.g., 'app.integrations.providers.openai_provider.OpenAIProvider')

        Returns:
            Provider class type
        """
        if class_path in self._class_cache:
            return self._class_cache[class_path]

        try:
            # Split module and class name
            module_path, class_name = class_path.rsplit(".", 1)

            # Import module
            module = importlib.import_module(module_path)

            # Get class
            provider_class = getattr(module, class_name)

            # Validate it's a proper provider
            if not issubclass(provider_class, AIProviderBase):
                raise ProviderLoadError(
                    f"Class {class_path} is not a subclass of AIProviderBase"
                )

            # Cache class
            self._class_cache[class_path] = provider_class

            return provider_class

        except ImportError as e:
            raise ProviderLoadError(f"Cannot import module for {class_path}: {e}")
        except AttributeError as e:
            raise ProviderLoadError(f"Class not found in module {class_path}: {e}")

    async def get_provider(self, provider_code: str) -> Optional[AIProviderBase]:
        """Get a cached provider by code."""
        for cached in self._cache.values():
            if cached.provider_code == provider_code:
                return cached.instance
        return None

    async def health_check(self, provider_code: str) -> Optional[ProviderHealth]:
        """
        Run health check on a provider.

        Updates cached health status and error count.
        """
        for cache_key, cached in self._cache.items():
            if cached.provider_code == provider_code:
                # Check if we need to run health check
                if (
                    cached.last_health_check
                    and datetime.utcnow() - cached.last_health_check < self.health_check_interval
                ):
                    return cached.health_status

                try:
                    health = await cached.instance.health_check()
                    cached.health_status = health
                    cached.last_health_check = datetime.utcnow()

                    if health.is_healthy:
                        cached.error_count = 0
                    else:
                        cached.error_count += 1

                    return health

                except Exception as e:
                    cached.error_count += 1
                    return ProviderHealth(
                        is_healthy=False,
                        error=str(e),
                        last_check=datetime.utcnow(),
                    )

        return None

    async def record_error(self, provider_code: str) -> None:
        """Record an error for circuit breaker."""
        for cached in self._cache.values():
            if cached.provider_code == provider_code:
                cached.error_count += 1
                break

    async def record_success(self, provider_code: str) -> None:
        """Record a success, reset error count."""
        for cached in self._cache.values():
            if cached.provider_code == provider_code:
                cached.error_count = max(0, cached.error_count - 1)
                break

    async def invalidate(self, provider_code: Optional[str] = None) -> int:
        """
        Invalidate cached providers.

        Args:
            provider_code: Specific provider to invalidate, or None for all

        Returns:
            Number of providers invalidated
        """
        async with self._lock:
            if provider_code:
                # Invalidate specific provider
                to_remove = [
                    key for key, cached in self._cache.items()
                    if cached.provider_code == provider_code
                ]
            else:
                # Invalidate all
                to_remove = list(self._cache.keys())

            for key in to_remove:
                cached = self._cache.pop(key)
                try:
                    await cached.instance.close()
                except Exception as e:
                    logger.warning(f"Error closing provider {cached.provider_code}: {e}")

            self._config_version += 1
            logger.info(f"Invalidated {len(to_remove)} provider(s)")
            return len(to_remove)

    async def close_all(self) -> None:
        """Close all cached providers."""
        await self.invalidate()

    def _get_cache_key(self, config: ProviderConfig) -> str:
        """Generate cache key for provider config."""
        return f"{config.code}:{config.provider_id}"

    def get_stats(self) -> Dict[str, Any]:
        """Get loader statistics."""
        return {
            "cached_providers": len(self._cache),
            "cached_classes": len(self._class_cache),
            "config_version": self._config_version,
            "providers": [
                {
                    "code": cached.provider_code,
                    "loaded_at": cached.loaded_at.isoformat(),
                    "error_count": cached.error_count,
                    "is_healthy": cached.health_status.is_healthy if cached.health_status else None,
                }
                for cached in self._cache.values()
            ],
        }


# Global instance
provider_loader = ProviderLoader()
