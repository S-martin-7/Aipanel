"""
Widget Module - Service.

Business logic for embeddable chat widget.
"""

import uuid
import secrets
from datetime import datetime
from typing import Optional, AsyncIterator

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Agent, Tenant, Conversation, Message, MessageRole, ConversationStatus
from app.integrations import AIEngine, Message as AIMessage
from app.core.config import settings
from app.core.plan_limits import PlanLimitGuard, PlanLimitExceededError
from app.utils.logger import get_logger

from .schemas import (
    WidgetConfig,
    UpdateWidgetConfigRequest,
    WidgetEmbedCode,
    WidgetChatRequest,
    WidgetChatResponse,
    WidgetChatMessage,
    AgentPublicInfo,
)

logger = get_logger(__name__)


class WidgetService:
    """Service for widget operations."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.ai_engine = AIEngine(db)
        self.plan_guard = PlanLimitGuard(db)

    # ============================================================
    # Widget Configuration
    # ============================================================

    async def get_widget_config(self, agent_id: str, tenant_id: str) -> Optional[WidgetConfig]:
        """Get widget configuration for an agent."""
        agent = await self._get_agent(agent_id, tenant_id)
        if not agent:
            return None

        # Widget config stored in agent.metadata
        metadata = agent.metadata or {}
        widget_data = metadata.get("widget_config", {})

        return WidgetConfig(**widget_data)

    async def update_widget_config(
        self,
        agent_id: str,
        tenant_id: str,
        request: UpdateWidgetConfigRequest
    ) -> Optional[WidgetConfig]:
        """Update widget configuration."""
        result = await self.db.execute(
            select(Agent).where(
                Agent.id == agent_id,
                Agent.tenant_id == tenant_id
            )
        )
        agent = result.scalar_one_or_none()
        if not agent:
            return None

        # Update metadata
        metadata = agent.metadata or {}
        widget_config = metadata.get("widget_config", {})

        # Apply updates
        update_data = request.model_dump(exclude_unset=True)
        widget_config.update(update_data)

        metadata["widget_config"] = widget_config
        agent.metadata = metadata
        agent.updated_at = datetime.utcnow()

        await self.db.commit()
        await self.db.refresh(agent)

        return WidgetConfig(**widget_config)

    # ============================================================
    # Embed Code
    # ============================================================

    async def get_embed_code(self, agent_id: str, tenant_id: str) -> Optional[WidgetEmbedCode]:
        """Generate embed code for an agent."""
        agent = await self._get_agent(agent_id, tenant_id)
        if not agent:
            return None

        # Get or create public key for agent
        metadata = agent.metadata or {}
        public_key = metadata.get("widget_public_key")

        if not public_key:
            public_key = f"pk_{secrets.token_urlsafe(24)}"
            metadata["widget_public_key"] = public_key

            # Update agent
            result = await self.db.execute(
                select(Agent).where(Agent.id == agent_id)
            )
            agent_obj = result.scalar_one()
            agent_obj.metadata = metadata
            await self.db.commit()

        # Generate URLs
        base_url = settings.FRONTEND_URL or "https://widget.aipanel.cl"
        script_url = f"{base_url}/widget.js"

        # Embed code (script tag)
        embed_code = f'''<script>
  window.AIPanelWidget = {{
    agentId: "{agent_id}",
    publicKey: "{public_key}"
  }};
</script>
<script src="{script_url}" async></script>'''

        # Iframe code (alternative)
        iframe_url = f"{base_url}/widget/{agent_id}?key={public_key}"
        iframe_code = f'''<iframe
  src="{iframe_url}"
  style="position: fixed; bottom: 20px; right: 20px; width: 380px; height: 600px; border: none; border-radius: 16px; box-shadow: 0 4px 24px rgba(0,0,0,0.15);"
  allow="microphone"
></iframe>'''

        return WidgetEmbedCode(
            agent_id=agent_id,
            public_key=public_key,
            script_url=script_url,
            embed_code=embed_code,
            iframe_code=iframe_code,
        )

    # ============================================================
    # Public Chat (no auth required, uses public key)
    # ============================================================

    async def get_agent_public_info(self, agent_id: str, public_key: str) -> Optional[AgentPublicInfo]:
        """Get public agent info for widget."""
        agent = await self._get_agent_by_public_key(agent_id, public_key)
        if not agent:
            return None

        return AgentPublicInfo(
            id=agent.id,
            name=agent.name,
            description=agent.description,
            avatar_url=agent.avatar_url,
            welcome_message=agent.welcome_message,
            is_online=agent.status.value == "ACTIVE" if hasattr(agent.status, 'value') else agent.status == "ACTIVE",
        )

    async def widget_chat(
        self,
        agent_id: str,
        public_key: str,
        request: WidgetChatRequest
    ) -> Optional[WidgetChatResponse]:
        """Handle chat message from widget."""
        # Validate agent and public key
        agent = await self._get_agent_by_public_key(agent_id, public_key)
        if not agent:
            return None

        # Check plan limits for tenant
        try:
            await self.plan_guard.check_token_limit(str(agent.tenant_id))
        except PlanLimitExceededError:
            raise ValueError("Service temporarily unavailable. Please try again later.")

        # Get or create session/conversation
        session_id = request.session_id
        conversation = None

        if session_id:
            result = await self.db.execute(
                select(Conversation).where(
                    Conversation.id == session_id,
                    Conversation.agent_id == agent_id
                )
            )
            conversation = result.scalar_one_or_none()

        if not conversation:
            session_id = str(uuid.uuid4())
            conversation = Conversation(
                id=session_id,
                agent_id=agent_id,
                tenant_id=agent.tenant_id,
                status=ConversationStatus.ACTIVE,
                title=f"Widget: {request.visitor_email or 'Visitante'}",
            )
            self.db.add(conversation)
            await self.db.flush()

        # Save user message
        user_message = Message(
            conversation_id=conversation.id,
            role=MessageRole.USER,
            content=request.message,
        )
        self.db.add(user_message)
        await self.db.flush()

        # Build message history
        messages = await self._build_widget_history(conversation.id, agent)

        # Call AI
        try:
            response = await self.ai_engine.chat_completion(
                messages=messages,
                tenant_id=agent.tenant_id,
                agent_id=agent_id,
            )
        except Exception as e:
            logger.error(f"Widget chat error: {e}")
            raise ValueError(f"Chat failed: {str(e)}")

        # Save assistant message
        assistant_message = Message(
            conversation_id=conversation.id,
            role=MessageRole.ASSISTANT,
            content=response.content,
            tokens_used=response.usage.get("total_tokens") if response.usage else None,
        )
        self.db.add(assistant_message)

        conversation.updated_at = datetime.utcnow()
        await self.db.commit()

        return WidgetChatResponse(
            session_id=session_id,
            message=WidgetChatMessage(
                role="assistant",
                content=response.content,
                timestamp=datetime.utcnow(),
            ),
            agent_name=agent.name,
            agent_avatar=agent.avatar_url,
        )

    async def stream_widget_chat(
        self,
        agent_id: str,
        public_key: str,
        request: WidgetChatRequest
    ) -> AsyncIterator[str]:
        """Stream chat response for widget."""
        agent = await self._get_agent_by_public_key(agent_id, public_key)
        if not agent:
            yield f"data: {{\"error\": \"Agent not found\"}}\n\n"
            return

        # Check plan limits for tenant
        try:
            await self.plan_guard.check_token_limit(str(agent.tenant_id))
        except PlanLimitExceededError:
            yield f"data: {{\"error\": \"Service temporarily unavailable\"}}\n\n"
            return

        # Get or create session
        session_id = request.session_id or str(uuid.uuid4())

        result = await self.db.execute(
            select(Conversation).where(
                Conversation.id == session_id,
                Conversation.agent_id == agent_id
            )
        )
        conversation = result.scalar_one_or_none()

        if not conversation:
            conversation = Conversation(
                id=session_id,
                agent_id=agent_id,
                tenant_id=agent.tenant_id,
                status=ConversationStatus.ACTIVE,
            )
            self.db.add(conversation)
            await self.db.flush()

        # Save user message
        user_message = Message(
            conversation_id=conversation.id,
            role=MessageRole.USER,
            content=request.message,
        )
        self.db.add(user_message)
        await self.db.flush()

        # Build history
        messages = await self._build_widget_history(conversation.id, agent)

        # Stream response
        full_response = ""
        chunk_id = str(uuid.uuid4())

        yield f"data: {{\"session_id\": \"{session_id}\"}}\n\n"

        try:
            async for chunk in self.ai_engine.stream_completion(
                messages=messages,
                tenant_id=agent.tenant_id,
                agent_id=agent_id,
            ):
                full_response += chunk
                yield f"data: {{\"delta\": \"{self._escape_json(chunk)}\"}}\n\n"

            # Save assistant message
            assistant_message = Message(
                conversation_id=conversation.id,
                role=MessageRole.ASSISTANT,
                content=full_response,
            )
            self.db.add(assistant_message)
            conversation.updated_at = datetime.utcnow()
            await self.db.commit()

            yield f"data: {{\"finish_reason\": \"stop\"}}\n\n"
            yield "data: [DONE]\n\n"

        except Exception as e:
            logger.error(f"Widget stream error: {e}")
            yield f"data: {{\"error\": \"{self._escape_json(str(e))}\"}}\n\n"

    # ============================================================
    # Helper Methods
    # ============================================================

    async def _get_agent(self, agent_id: str, tenant_id: str) -> Optional[Agent]:
        """Get agent by ID and tenant."""
        result = await self.db.execute(
            select(Agent).where(
                Agent.id == agent_id,
                Agent.tenant_id == tenant_id
            )
        )
        return result.scalar_one_or_none()

    async def _get_agent_by_public_key(self, agent_id: str, public_key: str) -> Optional[Agent]:
        """Get agent by ID and validate public key."""
        result = await self.db.execute(
            select(Agent).where(Agent.id == agent_id)
        )
        agent = result.scalar_one_or_none()

        if not agent:
            return None

        # Verify public key
        metadata = agent.metadata or {}
        stored_key = metadata.get("widget_public_key")

        if stored_key != public_key:
            return None

        return agent

    async def _build_widget_history(
        self,
        conversation_id: str,
        agent: Agent
    ) -> list[AIMessage]:
        """Build message history for widget chat."""
        messages: list[AIMessage] = []

        # System prompt
        if agent.system_prompt:
            messages.append(AIMessage(role="system", content=agent.system_prompt))

        # Get conversation messages (last 20)
        result = await self.db.execute(
            select(Message)
            .where(Message.conversation_id == conversation_id)
            .order_by(Message.created_at.desc())
            .limit(20)
        )
        db_messages = list(reversed(result.scalars().all()))

        for msg in db_messages:
            role = msg.role.value if hasattr(msg.role, 'value') else str(msg.role)
            messages.append(AIMessage(role=role, content=msg.content))

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
