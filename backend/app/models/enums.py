"""
Enumerations for database models.

Defines all enum types used across models.
"""

import enum


class UserRole(str, enum.Enum):
    """Roles for admin users (level 1)."""
    SUPER_ADMIN = "SUPER_ADMIN"
    ADMIN = "ADMIN"
    VIEWER = "VIEWER"


class TenantUserRole(str, enum.Enum):
    """Roles for tenant users (level 2)."""
    OWNER = "OWNER"
    ADMIN = "ADMIN"
    MEMBER = "MEMBER"
    VIEWER = "VIEWER"


class TenantStatus(str, enum.Enum):
    """Tenant account status."""
    ACTIVE = "ACTIVE"
    SUSPENDED = "SUSPENDED"
    PENDING = "PENDING"
    CANCELLED = "CANCELLED"


class TenantPlan(str, enum.Enum):
    """Subscription plans for tenants."""
    FREE = "FREE"
    STARTER = "STARTER"
    PROFESSIONAL = "PROFESSIONAL"
    ENTERPRISE = "ENTERPRISE"


class AgentStatus(str, enum.Enum):
    """AI Agent status."""
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"
    DRAFT = "DRAFT"


class AgentMode(str, enum.Enum):
    """AI Agent interaction mode."""
    CHAT = "CHAT"
    REALTIME = "REALTIME"
    ASSISTANT = "ASSISTANT"


class AIModelStatus(str, enum.Enum):
    """Status of AI models in the system."""
    EXPERIMENTAL = "EXPERIMENTAL"
    STABLE = "STABLE"
    DEPRECATED = "DEPRECATED"


class DocumentStatus(str, enum.Enum):
    """Document processing status."""
    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class AlertLevel(str, enum.Enum):
    """Usage alert severity levels."""
    INFO = "INFO"
    WARNING = "WARNING"
    CRITICAL = "CRITICAL"


class PaymentStatus(str, enum.Enum):
    """Payment transaction status."""
    PENDING = "PENDING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    REFUNDED = "REFUNDED"
