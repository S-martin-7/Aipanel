"""
Base AI Provider Interface.

All AI providers must implement this interface for dynamic loading.
"""

from abc import ABC, abstractmethod
from typing import AsyncIterator, Optional, Any
from dataclasses import dataclass
from enum import Enum


class MessageRole(str, Enum):
    """Message roles in conversation."""
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"


@dataclass
class Message:
    """Chat message."""
    role: MessageRole
    content: str
    name: Optional[str] = None
    metadata: Optional[dict] = None


@dataclass
class TokenUsage:
    """Token usage from API response."""
    input_tokens: int = 0
    output_tokens: int = 0
    reasoning_tokens: int = 0
    cached_tokens: int = 0
    total_tokens: int = 0


@dataclass
class CompletionResponse:
    """Response from chat completion."""
    content: str
    model: str
    usage: TokenUsage
    finish_reason: Optional[str] = None
    thinking: Optional[str] = None  # For extended thinking
    metadata: Optional[dict] = None


class BaseAIProvider(ABC):
    """
    Abstract base class for AI providers.

    All providers (OpenAI, Anthropic, etc.) must implement this interface.
    """

    def __init__(self, config: dict):
        """
        Initialize provider with configuration.

        Args:
            config: Provider configuration (API keys, endpoints, etc.)
        """
        self.config = config
        self._validate_config()

    @abstractmethod
    def _validate_config(self) -> None:
        """Validate provider configuration."""
        pass

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Return provider name."""
        pass

    @abstractmethod
    async def chat_completion(
        self,
        messages: list[Message],
        model: str,
        temperature: float = 0.7,
        max_tokens: int = 2048,
        system_prompt: Optional[str] = None,
        **kwargs
    ) -> CompletionResponse:
        """
        Create a chat completion.

        Args:
            messages: List of conversation messages
            model: Model identifier
            temperature: Sampling temperature (0-2)
            max_tokens: Maximum tokens to generate
            system_prompt: Optional system prompt
            **kwargs: Additional provider-specific parameters

        Returns:
            CompletionResponse with content and usage
        """
        pass

    @abstractmethod
    async def stream_completion(
        self,
        messages: list[Message],
        model: str,
        temperature: float = 0.7,
        max_tokens: int = 2048,
        system_prompt: Optional[str] = None,
        **kwargs
    ) -> AsyncIterator[str]:
        """
        Stream a chat completion.

        Args:
            messages: List of conversation messages
            model: Model identifier
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate
            system_prompt: Optional system prompt
            **kwargs: Additional parameters

        Yields:
            Text chunks as they are generated
        """
        pass

    async def count_tokens(
        self,
        messages: list[Message],
        model: str
    ) -> int:
        """
        Count tokens for messages.

        Default implementation returns estimate.
        Override for accurate counting.
        """
        # Rough estimate: ~4 chars per token
        total_chars = sum(len(m.content) for m in messages)
        return total_chars // 4

    def supports_streaming(self) -> bool:
        """Check if provider supports streaming."""
        return True

    def supports_vision(self) -> bool:
        """Check if provider supports vision/images."""
        return False

    def supports_tools(self) -> bool:
        """Check if provider supports function calling/tools."""
        return False
