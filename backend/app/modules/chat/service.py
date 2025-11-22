"""
Chat Module - Service

Business logic for chat interactions.
"""

import uuid
from typing import Optional, AsyncIterator
from datetime import datetime

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import Agent, Conversation, Message, User
from app.models.enums import MessageRole, ConversationStatus
from app.integrations import AIEngine, Message as AIMessage
from app.utils.logger import get_logger

from .schemas import (
    ChatCompletionRequest,
    ChatCompletionResponse,
    ChatMessage,
    UsageInfo,
    ConversationResponse,
    ConversationListItem,
)

logger = get_logger(__name__)


class ChatService:
    """
    Chat service for managing conversations and completions.

    Handles:
    - Creating and managing conversations
    - Sending messages to AI providers
    - Streaming responses
    - Token tracking
    """

    def __init__(self, db: AsyncSession):
        """Initialize with database session."""
        self.db = db
        self.ai_engine = AIEngine(db)

    async def create_completion(
        self,
        request: ChatCompletionRequest,
        user: User,
        tenant_id: str,
    ) -> ChatCompletionResponse:
        """
        Create a chat completion.

        Args:
            request: Completion request with message
            user: Current user
            tenant_id: Tenant ID for routing

        Returns:
            ChatCompletionResponse with AI response
        """
        # Get or create conversation
        conversation = await self._get_or_create_conversation(
            conversation_id=request.conversation_id,
            agent_id=request.agent_id,
            user_id=user.id,
            tenant_id=tenant_id,
        )

        # Validate agent belongs to tenant
        agent = await self._get_agent(request.agent_id, tenant_id)
        if not agent:
            raise ValueError("Agent not found or not accessible")

        # Save user message
        user_message = await self._save_message(
            conversation_id=conversation.id,
            role=MessageRole.USER,
            content=request.message,
        )

        # Build message history
        messages = await self._build_message_history(conversation.id, agent)

        # Call AI provider
        response = await self.ai_engine.chat_completion(
            messages=messages,
            tenant_id=tenant_id,
            agent_id=request.agent_id,
            temperature=request.temperature,
            max_tokens=request.max_tokens,
        )

        # Save assistant response
        assistant_message = await self._save_message(
            conversation_id=conversation.id,
            role=MessageRole.ASSISTANT,
            content=response.content,
            tokens_used=response.usage.get("total_tokens") if response.usage else None,
        )

        # Update conversation
        conversation.updated_at = datetime.utcnow()
        if not conversation.title and len(request.message) > 0:
            conversation.title = request.message[:50] + ("..." if len(request.message) > 50 else "")

        await self.db.commit()

        logger.info(f"Completion created for conversation {conversation.id}")

        return ChatCompletionResponse(
            id=str(uuid.uuid4()),
            conversation_id=conversation.id,
            message=ChatMessage(
                id=assistant_message.id,
                conversation_id=conversation.id,
                role="assistant",
                content=response.content,
                tokens_used=response.usage.get("total_tokens") if response.usage else None,
                created_at=assistant_message.created_at,
            ),
            usage=UsageInfo(
                prompt_tokens=response.usage.get("prompt_tokens", 0) if response.usage else 0,
                completion_tokens=response.usage.get("completion_tokens", 0) if response.usage else 0,
                total_tokens=response.usage.get("total_tokens", 0) if response.usage else 0,
            ),
            model=response.model or "unknown",
            finish_reason=response.finish_reason,
        )

    async def stream_completion(
        self,
        request: ChatCompletionRequest,
        user: User,
        tenant_id: str,
    ) -> AsyncIterator[str]:
        """
        Stream a chat completion.

        Yields SSE-formatted chunks.
        """
        # Get or create conversation
        conversation = await self._get_or_create_conversation(
            conversation_id=request.conversation_id,
            agent_id=request.agent_id,
            user_id=user.id,
            tenant_id=tenant_id,
        )

        # Validate agent
        agent = await self._get_agent(request.agent_id, tenant_id)
        if not agent:
            yield f"data: {{\"error\": \"Agent not found\"}}\n\n"
            return

        # Save user message
        await self._save_message(
            conversation_id=conversation.id,
            role=MessageRole.USER,
            content=request.message,
        )

        # Build message history
        messages = await self._build_message_history(conversation.id, agent)

        # Stream from AI provider
        full_response = ""
        chunk_id = str(uuid.uuid4())

        try:
            async for chunk in self.ai_engine.stream_completion(
                messages=messages,
                tenant_id=tenant_id,
                agent_id=request.agent_id,
                temperature=request.temperature,
                max_tokens=request.max_tokens,
            ):
                full_response += chunk
                yield f"data: {{\"id\": \"{chunk_id}\", \"conversation_id\": \"{conversation.id}\", \"delta\": \"{self._escape_json(chunk)}\"}}\n\n"

            # Save complete response
            await self._save_message(
                conversation_id=conversation.id,
                role=MessageRole.ASSISTANT,
                content=full_response,
            )

            # Update conversation
            conversation.updated_at = datetime.utcnow()
            if not conversation.title:
                conversation.title = request.message[:50] + ("..." if len(request.message) > 50 else "")

            await self.db.commit()

            # Send done signal
            yield f"data: {{\"id\": \"{chunk_id}\", \"conversation_id\": \"{conversation.id}\", \"delta\": \"\", \"finish_reason\": \"stop\"}}\n\n"
            yield "data: [DONE]\n\n"

        except Exception as e:
            logger.error(f"Stream error: {e}")
            yield f"data: {{\"error\": \"{self._escape_json(str(e))}\"}}\n\n"

    async def get_conversation(
        self,
        conversation_id: str,
        user_id: str,
    ) -> Optional[ConversationResponse]:
        """Get a conversation with its messages."""
        result = await self.db.execute(
            select(Conversation)
            .options(selectinload(Conversation.messages))
            .where(
                Conversation.id == conversation_id,
                Conversation.user_id == user_id,
            )
        )
        conversation = result.scalar_one_or_none()

        if not conversation:
            return None

        return ConversationResponse(
            id=conversation.id,
            agent_id=conversation.agent_id,
            title=conversation.title,
            messages=[
                ChatMessage(
                    id=msg.id,
                    conversation_id=conversation.id,
                    role=msg.role.value,
                    content=msg.content,
                    tokens_used=msg.tokens_used,
                    created_at=msg.created_at,
                )
                for msg in sorted(conversation.messages, key=lambda m: m.created_at)
            ],
            created_at=conversation.created_at,
            updated_at=conversation.updated_at,
        )

    async def list_conversations(
        self,
        user_id: str,
        agent_id: Optional[str] = None,
        limit: int = 20,
        offset: int = 0,
    ) -> list[ConversationListItem]:
        """List conversations for a user."""
        query = select(Conversation).where(Conversation.user_id == user_id)

        if agent_id:
            query = query.where(Conversation.agent_id == agent_id)

        query = query.order_by(Conversation.updated_at.desc()).offset(offset).limit(limit)

        result = await self.db.execute(query)
        conversations = result.scalars().all()

        items = []
        for conv in conversations:
            # Get message count
            count_result = await self.db.execute(
                select(func.count(Message.id)).where(Message.conversation_id == conv.id)
            )
            message_count = count_result.scalar() or 0

            items.append(ConversationListItem(
                id=conv.id,
                agent_id=conv.agent_id,
                title=conv.title,
                message_count=message_count,
                last_message_at=conv.updated_at,
                created_at=conv.created_at,
            ))

        return items

    async def delete_conversation(
        self,
        conversation_id: str,
        user_id: str,
    ) -> bool:
        """Delete a conversation."""
        result = await self.db.execute(
            select(Conversation).where(
                Conversation.id == conversation_id,
                Conversation.user_id == user_id,
            )
        )
        conversation = result.scalar_one_or_none()

        if not conversation:
            return False

        conversation.status = ConversationStatus.ARCHIVED
        await self.db.commit()
        return True

    # Private helper methods

    async def _get_or_create_conversation(
        self,
        conversation_id: Optional[str],
        agent_id: str,
        user_id: str,
        tenant_id: str,
    ) -> Conversation:
        """Get existing conversation or create new one."""
        if conversation_id:
            result = await self.db.execute(
                select(Conversation).where(
                    Conversation.id == conversation_id,
                    Conversation.user_id == user_id,
                )
            )
            conversation = result.scalar_one_or_none()
            if conversation:
                return conversation

        # Create new conversation
        conversation = Conversation(
            agent_id=agent_id,
            user_id=user_id,
            tenant_id=tenant_id,
            status=ConversationStatus.ACTIVE,
        )
        self.db.add(conversation)
        await self.db.flush()

        logger.info(f"Created new conversation: {conversation.id}")
        return conversation

    async def _get_agent(self, agent_id: str, tenant_id: str) -> Optional[Agent]:
        """Get agent by ID and tenant."""
        result = await self.db.execute(
            select(Agent).where(
                Agent.id == agent_id,
                Agent.tenant_id == tenant_id,
            )
        )
        return result.scalar_one_or_none()

    async def _save_message(
        self,
        conversation_id: str,
        role: MessageRole,
        content: str,
        tokens_used: Optional[int] = None,
    ) -> Message:
        """Save a message to the database."""
        message = Message(
            conversation_id=conversation_id,
            role=role,
            content=content,
            tokens_used=tokens_used,
        )
        self.db.add(message)
        await self.db.flush()
        return message

    async def _build_message_history(
        self,
        conversation_id: str,
        agent: Agent,
    ) -> list[AIMessage]:
        """Build message history for AI request."""
        messages: list[AIMessage] = []

        # Add system prompt from agent
        if agent.system_prompt:
            messages.append(AIMessage(role="system", content=agent.system_prompt))

        # Get conversation messages
        result = await self.db.execute(
            select(Message)
            .where(Message.conversation_id == conversation_id)
            .order_by(Message.created_at)
        )
        db_messages = result.scalars().all()

        for msg in db_messages:
            messages.append(AIMessage(role=msg.role.value, content=msg.content))

        return messages

    def _escape_json(self, text: str) -> str:
        """Escape text for JSON string."""
        return (
            text.replace("\\", "\\\\")
            .replace('"', '\\"')
            .replace("\n", "\\n")
            .replace("\r", "\\r")
            .replace("\t", "\\t")
        )
