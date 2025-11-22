"""
User models for admin authentication (Level 1).

Admin users manage servers and tenants.
"""

from sqlalchemy import Column, String, Boolean, Enum, Text
from sqlalchemy.orm import relationship

from .base import BaseModel
from .enums import UserRole


class User(BaseModel):
    """
    Admin user model (Level 1).

    These users manage the platform: servers, tenants, global settings.
    """

    __tablename__ = "users"

    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    name = Column(String(100), nullable=False)
    role = Column(Enum(UserRole), default=UserRole.ADMIN, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)

    # Optional fields
    phone = Column(String(20), nullable=True)
    avatar_url = Column(String(500), nullable=True)

    # Relationships
    refresh_tokens = relationship(
        "RefreshToken",
        back_populates="user",
        cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f"<User {self.email}>"


class RefreshToken(BaseModel):
    """
    Refresh token storage for JWT rotation.

    Stores active refresh tokens to allow invalidation on logout.
    """

    __tablename__ = "refresh_tokens"

    user_id = Column(String(36), nullable=False, index=True)
    token_hash = Column(String(255), nullable=False, unique=True)
    expires_at = Column(String(50), nullable=False)
    is_revoked = Column(Boolean, default=False, nullable=False)

    # Device info for security
    device_info = Column(Text, nullable=True)
    ip_address = Column(String(45), nullable=True)

    # Relationships
    user = relationship("User", back_populates="refresh_tokens", foreign_keys=[user_id])

    def __repr__(self):
        return f"<RefreshToken user={self.user_id}>"
