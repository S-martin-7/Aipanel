"""
External API Keys for tenant integrations.

These keys allow external services (WhatsApp bots, voice assistants, etc.)
to authenticate and use the AIPanel API on behalf of a tenant.
"""

import secrets
import hashlib
from datetime import datetime
from typing import Optional, List

from sqlalchemy import Column, String, Boolean, Text, DateTime, ForeignKey, Integer
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import ARRAY

from .base import BaseModel


def generate_api_key() -> str:
    """Generate a secure API key with prefix."""
    # Format: aip_<32 random chars>
    return f"aip_{secrets.token_urlsafe(32)}"


def hash_api_key(api_key: str) -> str:
    """Hash an API key for storage."""
    return hashlib.sha256(api_key.encode()).hexdigest()


class ExternalAPIKey(BaseModel):
    """
    External API key for tenant integrations.

    These keys allow external services to access the API on behalf of a tenant.
    Keys are stored hashed, and only shown once upon creation.
    """

    __tablename__ = "external_api_keys"

    # Ownership
    tenant_id = Column(String(36), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)

    # Key identification
    name = Column(String(100), nullable=False)  # e.g., "WhatsApp Bot", "Voice Assistant"
    description = Column(Text, nullable=True)

    # Key storage (only hash is stored)
    key_hash = Column(String(64), nullable=False, unique=True, index=True)
    key_prefix = Column(String(12), nullable=False)  # First 12 chars for identification (aip_XXXX)

    # Permissions/Scopes
    scopes = Column(ARRAY(String), nullable=True, default=list)  # ['chat', 'agents', 'documents']

    # Optional: restrict to specific agent
    agent_id = Column(String(36), ForeignKey("agents.id", ondelete="SET NULL"), nullable=True)

    # Rate limiting (requests per minute, 0 = unlimited)
    rate_limit = Column(Integer, default=60, nullable=False)

    # Status
    is_active = Column(Boolean, default=True, nullable=False)

    # Usage tracking
    last_used_at = Column(DateTime, nullable=True)
    total_requests = Column(Integer, default=0, nullable=False)

    # Expiration (optional)
    expires_at = Column(DateTime, nullable=True)

    # IP restriction (optional, comma-separated)
    allowed_ips = Column(Text, nullable=True)

    # Relationships
    tenant = relationship("Tenant", backref="external_api_keys")
    agent = relationship("Agent", backref="api_keys")

    @property
    def is_expired(self) -> bool:
        """Check if key has expired."""
        if not self.expires_at:
            return False
        return datetime.utcnow() > self.expires_at

    @property
    def is_valid(self) -> bool:
        """Check if key is valid (active and not expired)."""
        return self.is_active and not self.is_expired

    def has_scope(self, scope: str) -> bool:
        """Check if key has a specific scope."""
        if not self.scopes:
            return True  # Empty scopes = all permissions
        return scope in self.scopes

    def check_ip(self, ip: str) -> bool:
        """Check if IP is allowed."""
        if not self.allowed_ips:
            return True  # No restrictions
        allowed = [x.strip() for x in self.allowed_ips.split(",")]
        return ip in allowed

    def record_usage(self):
        """Update usage tracking."""
        self.last_used_at = datetime.utcnow()
        self.total_requests += 1

    @classmethod
    def create_key(cls, tenant_id: str, name: str, **kwargs) -> tuple['ExternalAPIKey', str]:
        """
        Create a new API key.

        Returns:
            Tuple of (ExternalAPIKey instance, plain text key)
            The plain text key is only available at creation time.
        """
        plain_key = generate_api_key()
        key_hash = hash_api_key(plain_key)
        key_prefix = plain_key[:12]  # "aip_XXXXXXXX"

        instance = cls(
            tenant_id=tenant_id,
            name=name,
            key_hash=key_hash,
            key_prefix=key_prefix,
            **kwargs
        )

        return instance, plain_key

    @classmethod
    def verify_key(cls, plain_key: str, stored_hash: str) -> bool:
        """Verify a plain key against stored hash."""
        return hash_api_key(plain_key) == stored_hash

    def __repr__(self):
        return f"<ExternalAPIKey {self.name} ({self.key_prefix}...)>"


# Available scopes
API_KEY_SCOPES = [
    "chat",           # Use chat endpoints
    "chat:stream",    # Use streaming chat
    "agents:read",    # Read agent info
    "agents:write",   # Modify agents
    "documents:read", # Read documents
    "documents:write",# Upload documents
    "usage:read",     # View usage stats
]
