"""
OpenAI Provider Client.

Implements BaseAIProvider for OpenAI API (GPT-4, GPT-4o, etc.).
"""

from typing import AsyncIterator, Optional
import openai
from openai import AsyncOpenAI

from app.utils.logger import get_logger
from .base_provider import (
    BaseAIProvider,
    Message,
    MessageRole,
    CompletionResponse,
    TokenUsage
)

logger = get_logger(__name__)


class OpenAIProvider(BaseAIProvider):
    """
    OpenAI API provider.

    Supports GPT-4, GPT-4o, GPT-4o-mini, and O-series models.
    """

    @property
    def provider_name(self) -> str:
        return "OpenAI"

    def _validate_config(self) -> None:
        """Validate OpenAI configuration."""
        if not self.config.get("api_key"):
            raise ValueError("OpenAI API key is required")

        self.client = AsyncOpenAI(
            api_key=self.config["api_key"],
            organization=self.config.get("organization_id")
        )

    def _convert_messages(
        self,
        messages: list[Message],
        system_prompt: Optional[str] = None
    ) -> list[dict]:
        """Convert internal messages to OpenAI format."""
        openai_messages = []

        if system_prompt:
            openai_messages.append({
                "role": "system",
                "content": system_prompt
            })

        for msg in messages:
            openai_messages.append({
                "role": msg.role.value,
                "content": msg.content
            })

        return openai_messages

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
        Create chat completion with OpenAI.

        Supports:
        - Standard chat models (gpt-4o, gpt-4o-mini)
        - O-series reasoning models (o1, o1-mini)
        - JSON mode
        - Tool/function calling
        """
        logger.info(f"OpenAI completion: model={model}")

        openai_messages = self._convert_messages(messages, system_prompt)

        # Build request parameters
        params = {
            "model": model,
            "messages": openai_messages,
            "max_tokens": max_tokens,
        }

        # O-series models don't support temperature
        if not model.startswith("o1"):
            params["temperature"] = temperature

        # Add optional parameters
        if kwargs.get("json_mode"):
            params["response_format"] = {"type": "json_object"}

        if kwargs.get("tools"):
            params["tools"] = kwargs["tools"]

        try:
            response = await self.client.chat.completions.create(**params)

            # Extract usage
            usage = TokenUsage(
                input_tokens=response.usage.prompt_tokens,
                output_tokens=response.usage.completion_tokens,
                total_tokens=response.usage.total_tokens
            )

            # Handle reasoning tokens for O-series
            if hasattr(response.usage, "completion_tokens_details"):
                details = response.usage.completion_tokens_details
                if hasattr(details, "reasoning_tokens"):
                    usage.reasoning_tokens = details.reasoning_tokens

            return CompletionResponse(
                content=response.choices[0].message.content or "",
                model=response.model,
                usage=usage,
                finish_reason=response.choices[0].finish_reason,
                metadata={
                    "id": response.id,
                    "created": response.created
                }
            )

        except openai.APIError as e:
            logger.error(f"OpenAI API error: {e}")
            raise

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
        Stream chat completion from OpenAI.

        Yields text chunks as they are generated.
        """
        logger.info(f"OpenAI streaming: model={model}")

        openai_messages = self._convert_messages(messages, system_prompt)

        params = {
            "model": model,
            "messages": openai_messages,
            "max_tokens": max_tokens,
            "stream": True
        }

        if not model.startswith("o1"):
            params["temperature"] = temperature

        try:
            stream = await self.client.chat.completions.create(**params)

            async for chunk in stream:
                if chunk.choices and chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content

        except openai.APIError as e:
            logger.error(f"OpenAI streaming error: {e}")
            raise

    def supports_vision(self) -> bool:
        """OpenAI supports vision with GPT-4V models."""
        return True

    def supports_tools(self) -> bool:
        """OpenAI supports function calling."""
        return True


# Alias for dynamic loading
OpenAIProviderClient = OpenAIProvider
