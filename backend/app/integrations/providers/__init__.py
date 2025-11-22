"""
AI Provider Plugins.

Contains implementations of AIProviderBase for various AI providers.
"""

from app.integrations.providers.base import (
    AIProviderBase,
    Message,
    GenerationParams,
    GenerationResult,
    StreamChunk,
    EmbeddingResult,
    TokenUsage,
    ProviderHealth,
    ModelCapability,
    ToolDefinition,
)

from app.integrations.providers.openai_provider import OpenAIProvider

__all__ = [
    # Base classes
    "AIProviderBase",
    "Message",
    "GenerationParams",
    "GenerationResult",
    "StreamChunk",
    "EmbeddingResult",
    "TokenUsage",
    "ProviderHealth",
    "ModelCapability",
    "ToolDefinition",
    # Providers
    "OpenAIProvider",
]
