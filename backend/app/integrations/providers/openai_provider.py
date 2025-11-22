"""
OpenAI Provider Implementation.

Implements AIProviderBase for OpenAI's API including GPT-4, GPT-3.5,
and embedding models.
"""

import time
from typing import AsyncIterator, Optional, List, Dict, Any
from datetime import datetime

from openai import AsyncOpenAI
import httpx

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
from app.utils.logger import get_logger

logger = get_logger(__name__)


class OpenAIProvider(AIProviderBase):
    """OpenAI API provider implementation."""

    # Model capabilities mapping
    MODEL_CAPABILITIES: Dict[str, List[ModelCapability]] = {
        "gpt-4o": [
            ModelCapability.CHAT,
            ModelCapability.STREAMING,
            ModelCapability.FUNCTIONS,
            ModelCapability.VISION,
            ModelCapability.JSON_MODE,
        ],
        "gpt-4o-mini": [
            ModelCapability.CHAT,
            ModelCapability.STREAMING,
            ModelCapability.FUNCTIONS,
            ModelCapability.VISION,
            ModelCapability.JSON_MODE,
        ],
        "gpt-4-turbo": [
            ModelCapability.CHAT,
            ModelCapability.STREAMING,
            ModelCapability.FUNCTIONS,
            ModelCapability.VISION,
            ModelCapability.JSON_MODE,
        ],
        "gpt-3.5-turbo": [
            ModelCapability.CHAT,
            ModelCapability.STREAMING,
            ModelCapability.FUNCTIONS,
            ModelCapability.JSON_MODE,
        ],
        "text-embedding-3-small": [ModelCapability.EMBEDDING],
        "text-embedding-3-large": [ModelCapability.EMBEDDING],
        "gpt-4o-realtime-preview": [
            ModelCapability.CHAT,
            ModelCapability.STREAMING,
            ModelCapability.REALTIME,
        ],
    }

    @property
    def provider_code(self) -> str:
        return "OPENAI"

    @property
    def provider_name(self) -> str:
        return "OpenAI"

    async def initialize(self) -> None:
        """Initialize OpenAI client."""
        self._client = AsyncOpenAI(
            api_key=self.api_key,
            organization=self.organization_id,
            base_url=self.base_url,
            timeout=httpx.Timeout(self.timeout / 1000),
            max_retries=self.max_retries,
            default_headers=self.default_headers,
        )
        logger.info(f"OpenAI provider initialized")

    async def close(self) -> None:
        """Close OpenAI client."""
        if self._client:
            await self._client.close()
            self._client = None

    async def generate(
        self,
        messages: List[Message],
        model: str,
        params: GenerationParams,
    ) -> GenerationResult:
        """Generate a non-streaming completion."""
        start_time = time.time()

        # Format messages
        formatted_messages = self._format_messages_openai(messages)

        # Build request kwargs
        kwargs = self._build_request_kwargs(model, params, formatted_messages)

        try:
            response = await self._client.chat.completions.create(**kwargs)

            latency_ms = int((time.time() - start_time) * 1000)
            choice = response.choices[0]

            # Extract tool calls if present
            tool_calls = None
            if choice.message.tool_calls:
                tool_calls = [
                    {
                        "id": tc.id,
                        "type": tc.type,
                        "function": {
                            "name": tc.function.name,
                            "arguments": tc.function.arguments,
                        },
                    }
                    for tc in choice.message.tool_calls
                ]

            return GenerationResult(
                content=choice.message.content or "",
                finish_reason=choice.finish_reason,
                usage=TokenUsage(
                    input_tokens=response.usage.prompt_tokens,
                    output_tokens=response.usage.completion_tokens,
                    total_tokens=response.usage.total_tokens,
                ),
                tool_calls=tool_calls,
                model=response.model,
                provider=self.provider_code,
                latency_ms=latency_ms,
                raw_response=response.model_dump(),
            )
        except Exception as e:
            logger.error(f"OpenAI generation error: {e}")
            raise

    async def generate_stream(
        self,
        messages: List[Message],
        model: str,
        params: GenerationParams,
    ) -> AsyncIterator[StreamChunk]:
        """Generate a streaming completion."""
        # Format messages
        formatted_messages = self._format_messages_openai(messages)

        # Build request kwargs
        kwargs = self._build_request_kwargs(model, params, formatted_messages)
        kwargs["stream"] = True
        kwargs["stream_options"] = {"include_usage": True}

        try:
            stream = await self._client.chat.completions.create(**kwargs)

            tool_calls_buffer: Dict[int, Dict] = {}
            final_usage = None

            async for chunk in stream:
                if not chunk.choices:
                    # Usage chunk at the end
                    if chunk.usage:
                        final_usage = TokenUsage(
                            input_tokens=chunk.usage.prompt_tokens,
                            output_tokens=chunk.usage.completion_tokens,
                            total_tokens=chunk.usage.total_tokens,
                        )
                    continue

                choice = chunk.choices[0]
                delta = choice.delta

                # Handle tool calls
                if delta.tool_calls:
                    for tc in delta.tool_calls:
                        if tc.index not in tool_calls_buffer:
                            tool_calls_buffer[tc.index] = {
                                "id": tc.id or "",
                                "type": "function",
                                "function": {"name": "", "arguments": ""},
                            }
                        if tc.function:
                            if tc.function.name:
                                tool_calls_buffer[tc.index]["function"]["name"] = tc.function.name
                            if tc.function.arguments:
                                tool_calls_buffer[tc.index]["function"]["arguments"] += tc.function.arguments

                # Build chunk
                stream_chunk = StreamChunk(
                    content=delta.content or "",
                    finish_reason=choice.finish_reason,
                    tool_calls=list(tool_calls_buffer.values()) if tool_calls_buffer and choice.finish_reason else None,
                    is_final=choice.finish_reason is not None,
                )

                if choice.finish_reason and final_usage:
                    stream_chunk.usage = final_usage

                yield stream_chunk

        except Exception as e:
            logger.error(f"OpenAI streaming error: {e}")
            raise

    async def embed(
        self,
        texts: List[str],
        model: str,
    ) -> EmbeddingResult:
        """Generate embeddings."""
        try:
            response = await self._client.embeddings.create(
                model=model,
                input=texts,
            )

            embeddings = [item.embedding for item in response.data]
            dimensions = len(embeddings[0]) if embeddings else 0

            return EmbeddingResult(
                embeddings=embeddings,
                usage=TokenUsage(
                    input_tokens=response.usage.prompt_tokens,
                    output_tokens=0,
                    total_tokens=response.usage.total_tokens,
                ),
                model=response.model,
                dimensions=dimensions,
            )
        except Exception as e:
            logger.error(f"OpenAI embedding error: {e}")
            raise

    async def health_check(self) -> ProviderHealth:
        """Check OpenAI API health."""
        start_time = time.time()
        try:
            # Simple models list call to verify connectivity
            await self._client.models.list()
            latency_ms = int((time.time() - start_time) * 1000)

            return ProviderHealth(
                is_healthy=True,
                latency_ms=latency_ms,
                last_check=datetime.utcnow(),
            )
        except Exception as e:
            return ProviderHealth(
                is_healthy=False,
                error=str(e),
                last_check=datetime.utcnow(),
            )

    def supports_capability(self, capability: ModelCapability, model: str) -> bool:
        """Check if model supports capability."""
        # Check exact match first
        if model in self.MODEL_CAPABILITIES:
            return capability in self.MODEL_CAPABILITIES[model]

        # Check prefix match for versioned models
        for known_model, caps in self.MODEL_CAPABILITIES.items():
            if model.startswith(known_model):
                return capability in caps

        # Default: assume basic chat capability
        return capability in [ModelCapability.CHAT, ModelCapability.STREAMING]

    def _format_messages_openai(self, messages: List[Message]) -> List[Dict]:
        """Format messages for OpenAI API."""
        formatted = []
        for msg in messages:
            formatted_msg: Dict[str, Any] = {
                "role": msg.role,
                "content": msg.content,
            }
            if msg.name:
                formatted_msg["name"] = msg.name
            if msg.tool_call_id:
                formatted_msg["tool_call_id"] = msg.tool_call_id
            if msg.tool_calls:
                formatted_msg["tool_calls"] = msg.tool_calls

            formatted.append(formatted_msg)

        return formatted

    def _build_request_kwargs(
        self,
        model: str,
        params: GenerationParams,
        messages: List[Dict],
    ) -> Dict[str, Any]:
        """Build kwargs for OpenAI API request."""
        kwargs: Dict[str, Any] = {
            "model": model,
            "messages": messages,
            "temperature": params.temperature,
            "max_tokens": params.max_tokens,
        }

        if params.top_p is not None:
            kwargs["top_p"] = params.top_p
        if params.frequency_penalty:
            kwargs["frequency_penalty"] = params.frequency_penalty
        if params.presence_penalty:
            kwargs["presence_penalty"] = params.presence_penalty
        if params.stop_sequences:
            kwargs["stop"] = params.stop_sequences
        if params.seed is not None:
            kwargs["seed"] = params.seed

        # Response format
        if params.response_format == "json_object":
            kwargs["response_format"] = {"type": "json_object"}

        # Tools/Functions
        if params.tools:
            kwargs["tools"] = [
                {
                    "type": "function",
                    "function": {
                        "name": tool.name,
                        "description": tool.description,
                        "parameters": tool.parameters,
                    },
                }
                for tool in params.tools
            ]
            if params.tool_choice:
                kwargs["tool_choice"] = params.tool_choice

        return kwargs
