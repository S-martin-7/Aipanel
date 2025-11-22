"""
Base model with common fields.

All models inherit from this base to get common functionality.
"""

from datetime import datetime
from sqlalchemy import Column, DateTime, String
from sqlalchemy.sql import func
import uuid

from app.core.database import Base


def generate_uuid() -> str:
    """Generate a new UUID string."""
    return str(uuid.uuid4())


class TimestampMixin:
    """Mixin that adds created_at and updated_at timestamps."""

    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False
    )


class BaseModel(Base, TimestampMixin):
    """
    Abstract base model with UUID primary key and timestamps.

    All models should inherit from this class.
    """

    __abstract__ = True

    id = Column(
        String(36),
        primary_key=True,
        default=generate_uuid,
        nullable=False
    )
