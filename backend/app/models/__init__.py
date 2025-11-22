"""
Database models for AIPanel.

Exports all SQLAlchemy models for easy importing.
"""

from .base import BaseModel, TimestampMixin, generate_uuid
from .enums import (
    UserRole,
    TenantUserRole,
    TenantStatus,
    TenantPlan,
    AgentStatus,
    AgentMode,
    AIModelStatus,
    DocumentStatus,
    AlertLevel,
    PaymentStatus,
    MessageRole,
    ConversationStatus,
    AIProviderType,
)
from .user import User, RefreshToken
from .tenant import Tenant, TenantUser
from .agent import Agent, Conversation, Message
from .ai_provider import AIProvider, AIModel, AIParamProfile, AIRoute, FeatureFlag
from .document import Document, DocumentChunk, ChunkSummary, DocumentSummary
from .usage import TokenUsage, UsageSummary, UsageThreshold, UsageAlert, Payment
from .tenant_api_key import TenantAPIKey
from .plan import Plan, DEFAULT_PLANS
from .external_api_key import ExternalAPIKey, API_KEY_SCOPES, generate_api_key, hash_api_key

__all__ = [
    # Base
    "BaseModel",
    "TimestampMixin",
    "generate_uuid",
    # Enums
    "UserRole",
    "TenantUserRole",
    "TenantStatus",
    "TenantPlan",
    "AgentStatus",
    "AgentMode",
    "AIModelStatus",
    "DocumentStatus",
    "AlertLevel",
    "PaymentStatus",
    "MessageRole",
    "ConversationStatus",
    "AIProviderType",
    # User models
    "User",
    "RefreshToken",
    # Tenant models
    "Tenant",
    "TenantUser",
    "TenantAPIKey",
    # Agent models
    "Agent",
    "Conversation",
    "Message",
    # AI Provider models
    "AIProvider",
    "AIModel",
    "AIParamProfile",
    "AIRoute",
    "FeatureFlag",
    # Document models
    "Document",
    "DocumentChunk",
    "ChunkSummary",
    "DocumentSummary",
    # Usage models
    "TokenUsage",
    "UsageSummary",
    "UsageThreshold",
    "UsageAlert",
    "Payment",
    # Plan models
    "Plan",
    "DEFAULT_PLANS",
    # External API Key models
    "ExternalAPIKey",
    "API_KEY_SCOPES",
    "generate_api_key",
    "hash_api_key",
]
