"""
AI Agent models.

Defines AI agents and their configurations.
"""

from sqlalchemy import Column, String, Boolean, Enum, Integer, Text, ForeignKey, Float
from sqlalchemy.dialects.postgresql import JSONB, ARRAY
from sqlalchemy.orm import relationship

from .base import BaseModel
from .enums import AgentStatus, AgentMode


class Agent(BaseModel):
    """
    AI Agent configuration.

    Each agent has its own personality, model, and settings.
    """

    __tablename__ = "agents"

    tenant_id = Column(String(36), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)

    # Basic info
    name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    avatar_url = Column(String(500), nullable=True)

    # Status and mode
    status = Column(Enum(AgentStatus), default=AgentStatus.DRAFT, nullable=False)
    mode = Column(Enum(AgentMode), default=AgentMode.CHAT, nullable=False)

    # AI Configuration
    system_prompt = Column(Text, nullable=False)
    welcome_message = Column(Text, nullable=True)

    # Model settings (can be overridden by AI routes)
    default_model_id = Column(String(36), ForeignKey("ai_models.id"), nullable=True)
    temperature = Column(Float, default=0.7, nullable=False)
    max_tokens = Column(Integer, default=2048, nullable=False)
    top_p = Column(Float, default=1.0, nullable=False)

    # Features
    enable_memory = Column(Boolean, default=True, nullable=False)
    enable_documents = Column(Boolean, default=True, nullable=False)
    enable_web_search = Column(Boolean, default=False, nullable=False)

    # Restrictions
    allowed_topics = Column(ARRAY(String), nullable=True)
    blocked_topics = Column(ARRAY(String), nullable=True)

    # Stats
    total_interactions = Column(Integer, default=0, nullable=False)
    total_tokens_used = Column(Integer, default=0, nullable=False)

    # Metadata
    metadata = Column(JSONB, nullable=True)

    # Relationships
    tenant = relationship("Tenant", back_populates="agents")
    conversations = relationship("Conversation", back_populates="agent", cascade="all, delete-orphan")
    documents = relationship("Document", back_populates="agent")

    def __repr__(self):
        return f"<Agent {self.name}>"


class Conversation(BaseModel):
    """
    Chat conversation with an agent.

    Groups messages into a conversation thread.
    """

    __tablename__ = "conversations"

    agent_id = Column(String(36), ForeignKey("agents.id", ondelete="CASCADE"), nullable=False, index=True)
    tenant_user_id = Column(String(36), ForeignKey("tenant_users.id", ondelete="SET NULL"), nullable=True, index=True)

    # Metadata
    title = Column(String(200), nullable=True)
    summary = Column(Text, nullable=True)

    # Stats
    message_count = Column(Integer, default=0, nullable=False)
    total_tokens = Column(Integer, default=0, nullable=False)

    # Status
    is_archived = Column(Boolean, default=False, nullable=False)

    # Relationships
    agent = relationship("Agent", back_populates="conversations")
    messages = relationship("Message", back_populates="conversation", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Conversation {self.id[:8]}>"


class Message(BaseModel):
    """
    Individual message in a conversation.

    Stores both user and assistant messages.
    """

    __tablename__ = "messages"

    conversation_id = Column(String(36), ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False, index=True)

    # Message content
    role = Column(String(20), nullable=False)  # user, assistant, system
    content = Column(Text, nullable=False)

    # Token tracking
    input_tokens = Column(Integer, default=0, nullable=False)
    output_tokens = Column(Integer, default=0, nullable=False)

    # Model used
    model = Column(String(50), nullable=True)

    # Metadata (tool calls, sources, etc.)
    metadata = Column(JSONB, nullable=True)

    # Relationships
    conversation = relationship("Conversation", back_populates="messages")

    def __repr__(self):
        return f"<Message {self.role} {self.id[:8]}>"
