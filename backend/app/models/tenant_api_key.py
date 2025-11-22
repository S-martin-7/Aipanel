"""
Tenant API Keys model.

Stores encrypted API keys per tenant for each AI provider.
"""

from sqlalchemy import Column, String, Boolean, Enum, ForeignKey, Text, DateTime
from sqlalchemy.orm import relationship
from datetime import datetime

from .base import BaseModel
from .enums import AIProviderType


class TenantAPIKey(BaseModel):
    """
    API Keys for AI providers per tenant.

    Each tenant can configure their own API keys for OpenAI, Anthropic, etc.
    Keys are stored encrypted.
    """

    __tablename__ = "tenant_api_keys"

    tenant_id = Column(String(36), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)

    # Provider identification
    provider_type = Column(Enum(AIProviderType), nullable=False)
    provider_name = Column(String(50), nullable=False)  # "OpenAI", "Anthropic"

    # Encrypted API key (use Fernet or similar in production)
    api_key_encrypted = Column(Text, nullable=False)

    # Optional additional config
    organization_id = Column(String(100), nullable=True)  # For OpenAI org ID
    base_url = Column(String(500), nullable=True)  # For custom endpoints

    # Status
    is_active = Column(Boolean, default=True, nullable=False)
    is_valid = Column(Boolean, default=True, nullable=False)  # Set to False if key fails

    # Validation
    last_validated_at = Column(DateTime, nullable=True)
    last_error = Column(Text, nullable=True)

    # Relationships
    tenant = relationship("Tenant", back_populates="api_keys")

    # Unique constraint: one key per provider per tenant
    __table_args__ = (
        # Unique constraint handled by application logic for flexibility
        {"sqlite_autoincrement": True},
    )

    def __repr__(self):
        return f"<TenantAPIKey {self.provider_name} @ {self.tenant_id[:8]}>"
