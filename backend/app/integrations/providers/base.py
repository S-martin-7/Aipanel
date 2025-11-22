"""
Base AI Provider Interface.

All AI providers must implement this interface to be compatible
with AIPanel's dynamic provider system.
"""

from abc import ABC, abstractmethod
from typing import AsyncIterator, Optional, List, Dict, Any, Union
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime


class ModelCapability(str, Enum):
    """Capabilities a model can support."""
    CHAT = "chat"
    COMPLETION = "completion"
    EMBEDDING = "embedding"
    VISION = "vision"
    FUNCTIONS = "functions"
    JSON_MODE = "json_mode"
    STREAMING = "streaming"
    REALTIME = "realtime"


@dataclass
class Message:
    """Chat message."""
    role: str  # system, user, assistant, tool
    content: Union[str, List[Dict[str, Any]]]  # Text or multimodal content
    name: Optional[str] = None
    tool_call_id: Optional[str] = None
    tool_calls: Optional[List[Dict]] = None


@dataclass
class ToolDefinition:
    """Tool/function definition for AI."""
    name: str
    description: str
    parameters: Dict[str, Any]  # JSON Schema


@dataclass
class GenerationParams:
    """Parameters for text generation."""
    temperature: float = 0.7
    top_p: float = 1.0
    top_k: Optional[int] = None
    max_tokens: int = 2048
    stop_sequences: List[str] = field(default_factory=list)
    frequency_penalty: float = 0.0
    presence_penalty: float = 0.0
    response_format: Optional[str] = None  # "text" or "json_object"
    seed: Optional[int] = None
    tools: Optional[List[ToolDefinition]] = None
    tool_choice: Optional[str] = None  # "auto", "none", or specific tool


@dataclass
class TokenUsage:
    """Token usage statistics."""
    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0
    cached_tokens: int = 0


@dataclass
class GenerationResult:
    """Result from a generation request."""
    content: str
    finish_reason: str  # stop, length, tool_calls, content_filter
    usage: TokenUsage
    tool_calls: Optional[List[Dict]] = None
    model: Optional[str] = None
    provider: Optional[str] = None
    latency_ms: Optional[int] = None
    raw_response: Optional[Dict] = None


@dataclass
class StreamChunk:
    """Chunk from streaming response."""
    content: str
    finish_reason: Optional[str] = None
    tool_calls: Optional[List[Dict]] = None
    usage: Optional[TokenUsage] = None
    is_final: bool = False


@dataclass
class EmbeddingResult:
    """Result from embedding request."""
    embeddings: List[List[float]]
    usage: TokenUsage
    model: str
    dimensions: int


@dataclass
class ProviderHealth:
    """Health status of a provider."""
    is_healthy: bool
    latency_ms: Optional[int] = None
    error: Optional[str] = None
    last_check: Optional[datetime] = None
    details: Dict[str, Any] = field(default_factory=dict)


class AIProviderBase(ABC):
    """
    Abstract base class for AI providers.

    All providers (OpenAI, Anthropic, Google, etc.) must implement
    this interface to work with AIPanel's dynamic routing system.
    """

    def __init__(
        self,
        api_key: str,
        base_url: Optional[str] = None,
        organization_id: Optional[str] = None,
        default_headers: Optional[Dict[str, str]] = None,
        timeout: int = 30000,
        max_retries: int = 2,
    ):
        self.api_key = api_key
        self.base_url = base_url
        self.organization_id = organization_id
        self.default_headers = default_headers or {}
        self.timeout = timeout
        self.max_retries = max_retries
        self._client = None

    @property
    @abstractmethod
    def provider_code(self) -> str:
        """Unique provider identifier (e.g., 'OPENAI', 'ANTHROPIC')."""
        pass

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Human-readable provider name."""
        pass

    @abstractmethod
    async def initialize(self) -> None:
        """Initialize the provider client."""
        pass

    @abstractmethod
    async def close(self) -> None:
        """Close and cleanup the provider client."""
        pass

    @abstractmethod
    async def generate(
        self,
        messages: List[Message],
        model: str,
        params: GenerationParams,
    ) -> GenerationResult:
        """
        Generate a completion (non-streaming).

        Args:
            messages: List of chat messages
            model: Model identifier (e.g., 'gpt-4o')
            params: Generation parameters

        Returns:
            GenerationResult with content and usage
        """
        pass

    @abstractmethod
    async def generate_stream(
        self,
        messages: List[Message],
        model: str,
        params: GenerationParams,
    ) -> AsyncIterator[StreamChunk]:
        """
        Generate a streaming completion.

        Args:
            messages: List of chat messages
            model: Model identifier
            params: Generation parameters

        Yields:
            StreamChunk with incremental content
        """
        pass

    @abstractmethod
    async def embed(
        self,
        texts: List[str],
        model: str,
    ) -> EmbeddingResult:
        """
        Generate embeddings for texts.

        Args:
            texts: List of texts to embed
            model: Embedding model identifier

        Returns:
            EmbeddingResult with vectors
        """
        pass

    async def realtime_connect(
        self,
        model: str,
        params: GenerationParams,
    ) -> Any:
        """
        Establish realtime/websocket connection.

        Override in providers that support realtime mode.
        """
        raise NotImplementedError(
            f"Provider {self.provider_code} does not support realtime mode"
        )

    @abstractmethod
    async def health_check(self) -> ProviderHealth:
        """
        Check provider health and availability.

        Returns:
            ProviderHealth with status information
        """
        pass

    @abstractmethod
    def supports_capability(self, capability: ModelCapability, model: str) -> bool:
        """
        Check if a model supports a specific capability.

        Args:
            capability: The capability to check
            model: Model identifier

        Returns:
            True if the model supports the capability
        """
        pass

    def validate_params(self, params: GenerationParams, model: str) -> GenerationParams:
        """
        Validate and adjust parameters for the specific provider/model.

        Override to apply provider-specific constraints.
        """
        return params

    def format_messages(self, messages: List[Message]) -> Any:
        """
        Format messages for the specific provider API.

        Override if provider requires different message format.
        """
        return [
            {"role": m.role, "content": m.content}
            for m in messages
        ]

    def calculate_cost(
        self,
        usage: TokenUsage,
        model: str,
        input_price_per_1k: float,
        output_price_per_1k: float,
    ) -> float:
        """Calculate cost in USD for the request."""
        input_cost = (usage.input_tokens / 1000) * input_price_per_1k
        output_cost = (usage.output_tokens / 1000) * output_price_per_1k
        return input_cost + output_cost
