"""
AI Provider models for dynamic provider management.

Allows configuring AI providers and models without code changes.
"""

from sqlalchemy import Column, String, Boolean, Enum, Integer, Float, ForeignKey, Text
from sqlalchemy.dialects.postgresql import JSONB, ARRAY
from sqlalchemy.orm import relationship

from .base import BaseModel
from .enums import AIModelStatus


class AIProvider(BaseModel):
    """
    AI Provider configuration (OpenAI, Anthropic, etc.).

    Providers are loaded dynamically at runtime.
    """

    __tablename__ = "ai_providers"

    name = Column(String(50), nullable=False, unique=True)  # "OpenAI", "Anthropic"
    display_name = Column(String(100), nullable=True)

    # Dynamic loading
    handler_module = Column(String(200), nullable=False)  # "app.integrations.openai_client"
    handler_class = Column(String(100), nullable=False)   # "OpenAIProviderClient"

    # Configuration (encrypted in production)
    config_json = Column(JSONB, nullable=True)  # API keys, endpoints, etc.

    # Status
    is_active = Column(Boolean, default=True, nullable=False)
    allowed_in_prod = Column(Boolean, default=False, nullable=False)

    # Rate limits
    requests_per_minute = Column(Integer, nullable=True)
    tokens_per_minute = Column(Integer, nullable=True)

    # Relationships
    models = relationship("AIModel", back_populates="provider", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<AIProvider {self.name}>"


class AIModel(BaseModel):
    """
    AI Model configuration.

    Defines available models and their capabilities.
    """

    __tablename__ = "ai_models"

    provider_id = Column(String(36), ForeignKey("ai_providers.id", ondelete="CASCADE"), nullable=False, index=True)

    # Model identification
    name = Column(String(100), nullable=False)  # "gpt-4o-mini", "claude-sonnet-4-5"
    display_name = Column(String(100), nullable=True)
    description = Column(Text, nullable=True)

    # Capabilities
    capabilities = Column(ARRAY(String), nullable=True)  # ['chat', 'vision', 'streaming', 'tools']
    status = Column(Enum(AIModelStatus), default=AIModelStatus.EXPERIMENTAL, nullable=False)

    # Pricing (per 1K tokens)
    pricing_input = Column(Float, nullable=True)   # Cost per 1K input tokens
    pricing_output = Column(Float, nullable=True)  # Cost per 1K output tokens
    pricing_cached = Column(Float, nullable=True)  # Cost per 1K cached tokens

    # Limits
    max_tokens = Column(Integer, nullable=True)
    context_window = Column(Integer, nullable=True)

    # Features
    supports_streaming = Column(Boolean, default=True, nullable=False)
    supports_vision = Column(Boolean, default=False, nullable=False)
    supports_tools = Column(Boolean, default=False, nullable=False)
    supports_json_mode = Column(Boolean, default=False, nullable=False)

    # Relationships
    provider = relationship("AIProvider", back_populates="models")

    def __repr__(self):
        return f"<AIModel {self.name}>"


class AIParamProfile(BaseModel):
    """
    Reusable parameter profiles for AI calls.

    Predefined configurations like "creative", "precise", "balanced".
    """

    __tablename__ = "ai_param_profiles"

    name = Column(String(50), nullable=False, unique=True)  # "creative", "precise"
    description = Column(Text, nullable=True)

    # Parameters
    temperature = Column(Float, nullable=True)
    max_tokens = Column(Integer, nullable=True)
    top_p = Column(Float, nullable=True)
    frequency_penalty = Column(Float, nullable=True)
    presence_penalty = Column(Float, nullable=True)

    # System prompt additions
    system_prompt_suffix = Column(Text, nullable=True)

    # Status
    is_active = Column(Boolean, default=True, nullable=False)

    def __repr__(self):
        return f"<AIParamProfile {self.name}>"


class AIRoute(BaseModel):
    """
    Routing rules for AI model selection.

    Determines which model to use based on context.
    """

    __tablename__ = "ai_routes"

    name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)

    # Scope (NULL = global)
    tenant_id = Column(String(36), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=True, index=True)
    agent_id = Column(String(36), ForeignKey("agents.id", ondelete="CASCADE"), nullable=True, index=True)

    # Mode filter
    mode = Column(String(20), default="CHAT", nullable=False)  # CHAT, REALTIME

    # Target model
    model_id = Column(String(36), ForeignKey("ai_models.id", ondelete="CASCADE"), nullable=False)
    param_profile_id = Column(String(36), ForeignKey("ai_param_profiles.id"), nullable=True)

    # Priority (higher = more specific)
    priority = Column(Integer, default=0, nullable=False)

    # Conditions (JSON for complex rules)
    condition_json = Column(JSONB, nullable=True)

    # Fallback
    fallback_route_id = Column(String(36), ForeignKey("ai_routes.id"), nullable=True)

    # Status
    is_active = Column(Boolean, default=True, nullable=False)

    def __repr__(self):
        return f"<AIRoute {self.name}>"


class FeatureFlag(BaseModel):
    """
    Feature flags for gradual rollouts.

    Control features at global, tenant, or user level.
    """

    __tablename__ = "feature_flags"

    name = Column(String(100), nullable=False, unique=True)  # "enable_realtime", "enable_vision"
    description = Column(Text, nullable=True)

    # Scope
    scope = Column(String(20), default="GLOBAL", nullable=False)  # GLOBAL, TENANT, USER

    # Status
    is_enabled = Column(Boolean, default=False, nullable=False)

    # Configuration
    config_json = Column(JSONB, nullable=True)

    # Percentage rollout (0-100)
    rollout_percentage = Column(Integer, default=100, nullable=False)

    def __repr__(self):
        return f"<FeatureFlag {self.name}>"
