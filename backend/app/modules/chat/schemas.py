"""
Chat Module - Schemas

Pydantic schemas for chat interactions.
"""

from pydantic import BaseModel, Field
from typing import Optional, Literal
from datetime import datetime


class MessageContent(BaseModel):
    """Content of a message."""
    role: Literal["user", "assistant", "system"] = "user"
    content: str = Field(..., min_length=1, max_length=100000)


class ChatCompletionRequest(BaseModel):
    """Request for chat completion."""
    agent_id: str = Field(..., description="Agent ID to use")
    conversation_id: Optional[str] = Field(None, description="Existing conversation ID")
    message: str = Field(..., min_length=1, max_length=50000)

    # Optional parameters
    temperature: Optional[float] = Field(None, ge=0.0, le=2.0)
    max_tokens: Optional[int] = Field(None, ge=1, le=32000)
    stream: bool = Field(False, description="Enable streaming response")


class ChatMessage(BaseModel):
    """A single chat message."""
    id: str
    conversation_id: str
    role: Literal["user", "assistant", "system"]
    content: str
    tokens_used: Optional[int] = None
    created_at: datetime

    class Config:
        from_attributes = True


class ChatCompletionResponse(BaseModel):
    """Response from chat completion."""
    id: str
    conversation_id: str
    message: ChatMessage
    usage: "UsageInfo"
    model: str
    finish_reason: Optional[str] = None


class UsageInfo(BaseModel):
    """Token usage information."""
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int


class ConversationResponse(BaseModel):
    """A conversation with its messages."""
    id: str
    agent_id: str
    title: Optional[str] = None
    messages: list[ChatMessage] = []
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ConversationListItem(BaseModel):
    """Summary of a conversation for listing."""
    id: str
    agent_id: str
    title: Optional[str] = None
    message_count: int = 0
    last_message_at: Optional[datetime] = None
    created_at: datetime

    class Config:
        from_attributes = True


class StreamChunk(BaseModel):
    """A chunk of streamed response."""
    id: str
    conversation_id: str
    delta: str
    finish_reason: Optional[str] = None


# Update forward references
ChatCompletionResponse.model_rebuild()
