"""
Anthropic/Claude API Client with Extended Thinking support.

This module handles the integration with Claude API, including proper
handling of thinking blocks to avoid the error:
"thinking or redacted_thinking blocks in the latest assistant message cannot be modified"

The key insight is that when using Extended Thinking:
1. Assistant responses contain 'thinking' or 'redacted_thinking' content blocks
2. These blocks MUST be preserved exactly as-is when sent back in conversation history
3. You cannot modify, add, or remove thinking blocks from historical messages
"""

from typing import AsyncIterator, Optional
import anthropic
from anthropic import AsyncAnthropic
from tenacity import retry, stop_after_attempt, wait_exponential
import logging

logger = logging.getLogger(__name__)


class AnthropicClient:
    """
    Async client for Anthropic/Claude API with Extended Thinking support.

    Handles:
    - Chat completions with streaming
    - Extended Thinking mode
    - Proper thinking block filtering for conversation history
    - Retry logic with exponential backoff
    """

    def __init__(self, api_key: str):
        """
        Initialize the Anthropic client.

        Args:
            api_key: Anthropic API key
        """
        self.client = AsyncAnthropic(api_key=api_key)
        self.sync_client = anthropic.Anthropic(api_key=api_key)

    @staticmethod
    def filter_thinking_blocks(messages: list[dict]) -> list[dict]:
        """
        Filter thinking/redacted_thinking blocks from message history.

        IMPORTANT: This MUST be called before sending conversation history
        back to the API to avoid the error:
        "thinking or redacted_thinking blocks in the latest assistant message cannot be modified"

        The API requires that thinking blocks remain unchanged, but for subsequent
        requests, we should filter them out from the history to avoid issues.

        Args:
            messages: List of message dictionaries with 'role' and 'content'

        Returns:
            List of messages with thinking blocks removed from assistant messages
        """
        filtered_messages = []

        for message in messages:
            if message.get("role") == "assistant":
                content = message.get("content", [])

                # If content is a string, keep it as-is
                if isinstance(content, str):
                    filtered_messages.append(message)
                    continue

                # If content is a list, filter out thinking blocks
                if isinstance(content, list):
                    filtered_content = [
                        block for block in content
                        if not (
                            isinstance(block, dict) and
                            block.get("type") in ("thinking", "redacted_thinking")
                        )
                    ]

                    # Only include message if there's remaining content
                    if filtered_content:
                        filtered_messages.append({
                            **message,
                            "content": filtered_content
                        })
                    elif not filtered_content:
                        # If all content was thinking blocks, add empty text
                        filtered_messages.append({
                            **message,
                            "content": [{"type": "text", "text": ""}]
                        })
            else:
                # Keep user/system messages unchanged
                filtered_messages.append(message)

        return filtered_messages

    @staticmethod
    def extract_text_from_response(response) -> str:
        """
        Extract text content from an Anthropic response, ignoring thinking blocks.

        Args:
            response: Anthropic API response object

        Returns:
            Concatenated text content from the response
        """
        text_parts = []

        for block in response.content:
            if hasattr(block, 'type'):
                if block.type == "text":
                    text_parts.append(block.text)
                elif block.type in ("thinking", "redacted_thinking"):
                    # Skip thinking blocks in final output
                    continue

        return "".join(text_parts)

    @staticmethod
    def extract_thinking_from_response(response) -> Optional[str]:
        """
        Extract thinking content from an Anthropic response.

        Useful for debugging or logging the model's reasoning process.

        Args:
            response: Anthropic API response object

        Returns:
            Thinking content if present, None otherwise
        """
        for block in response.content:
            if hasattr(block, 'type') and block.type == "thinking":
                return block.thinking
        return None

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10)
    )
    async def chat_completion(
        self,
        model: str = "claude-sonnet-4-5-20250929",
        messages: list[dict] = None,
        system: str = None,
        temperature: float = 1.0,
        max_tokens: int = 8096,
        extended_thinking: bool = False,
        thinking_budget: int = 10000,
        stream: bool = False
    ):
        """
        Create a chat completion with Claude.

        Args:
            model: Claude model to use (default: claude-sonnet-4-5-20250929)
            messages: List of message dicts with 'role' and 'content'
            system: System prompt
            temperature: Sampling temperature (ignored if extended_thinking=True)
            max_tokens: Maximum tokens to generate
            extended_thinking: Enable Extended Thinking mode
            thinking_budget: Max tokens for thinking when extended_thinking=True
            stream: Whether to stream the response

        Returns:
            Anthropic API response or async iterator for streaming

        Note:
            When extended_thinking=True, temperature must be 1.0 (API requirement)
        """
        messages = messages or []

        # CRITICAL: Filter thinking blocks from historical messages
        filtered_messages = self.filter_thinking_blocks(messages)

        # Build request parameters
        params = {
            "model": model,
            "max_tokens": max_tokens,
            "messages": filtered_messages,
        }

        if system:
            params["system"] = system

        # Configure Extended Thinking if enabled
        if extended_thinking:
            params["thinking"] = {
                "type": "enabled",
                "budget_tokens": thinking_budget
            }
            # Temperature must be 1.0 for extended thinking
            params["temperature"] = 1.0
        else:
            params["temperature"] = temperature

        if stream:
            return await self._stream_completion(**params)
        else:
            response = await self.client.messages.create(**params)
            return response

    async def _stream_completion(self, **params) -> AsyncIterator[str]:
        """
        Stream a chat completion response.

        Yields:
            Text chunks from the response (thinking blocks are not yielded)
        """
        async with self.client.messages.stream(**params) as stream:
            async for event in stream:
                if hasattr(event, 'type'):
                    if event.type == "content_block_delta":
                        delta = event.delta
                        if hasattr(delta, 'type'):
                            if delta.type == "text_delta":
                                yield delta.text
                            elif delta.type == "thinking_delta":
                                # Optionally log thinking, but don't yield
                                logger.debug(f"Thinking: {delta.thinking}")

    def chat_completion_sync(
        self,
        model: str = "claude-sonnet-4-5-20250929",
        messages: list[dict] = None,
        system: str = None,
        temperature: float = 1.0,
        max_tokens: int = 8096,
        extended_thinking: bool = False,
        thinking_budget: int = 10000
    ):
        """
        Synchronous version of chat_completion.

        Use this when you need to call from a non-async context.
        """
        messages = messages or []

        # CRITICAL: Filter thinking blocks from historical messages
        filtered_messages = self.filter_thinking_blocks(messages)

        params = {
            "model": model,
            "max_tokens": max_tokens,
            "messages": filtered_messages,
        }

        if system:
            params["system"] = system

        if extended_thinking:
            params["thinking"] = {
                "type": "enabled",
                "budget_tokens": thinking_budget
            }
            params["temperature"] = 1.0
        else:
            params["temperature"] = temperature

        response = self.sync_client.messages.create(**params)
        return response

    async def count_tokens(self, messages: list[dict], system: str = None) -> int:
        """
        Count tokens for a list of messages.

        Args:
            messages: List of message dicts
            system: Optional system prompt

        Returns:
            Token count
        """
        # Filter thinking blocks for accurate counting
        filtered_messages = self.filter_thinking_blocks(messages)

        response = await self.client.messages.count_tokens(
            model="claude-sonnet-4-5-20250929",
            messages=filtered_messages,
            system=system or ""
        )

        return response.input_tokens


# Example usage
if __name__ == "__main__":
    import asyncio
    import os

    async def example():
        client = AnthropicClient(api_key=os.getenv("ANTHROPIC_API_KEY"))

        # Simple completion
        response = await client.chat_completion(
            messages=[{"role": "user", "content": "Hello!"}],
            max_tokens=100
        )

        print("Response:", client.extract_text_from_response(response))

        # With Extended Thinking
        response = await client.chat_completion(
            messages=[{"role": "user", "content": "What is 15 * 23?"}],
            extended_thinking=True,
            thinking_budget=5000,
            max_tokens=1000
        )

        print("Response:", client.extract_text_from_response(response))
        print("Thinking:", client.extract_thinking_from_response(response))

        # Continuing conversation (demonstrates thinking block filtering)
        conversation = [
            {"role": "user", "content": "What is 15 * 23?"},
            {
                "role": "assistant",
                "content": response.content  # This contains thinking blocks
            },
            {"role": "user", "content": "Now multiply that by 2"}
        ]

        # The filter_thinking_blocks method is called automatically
        response2 = await client.chat_completion(
            messages=conversation,
            extended_thinking=True,
            max_tokens=1000
        )

        print("Follow-up response:", client.extract_text_from_response(response2))

    asyncio.run(example())
