"""
Plan Model - Configurable subscription plans.

Supports trial periods, custom plans, and payment requirements.
"""

from sqlalchemy import Column, String, Integer, Boolean, Numeric, Text, DateTime, Enum
from sqlalchemy.dialects.postgresql import JSONB

from .base import BaseModel


class PlanType(str):
    """Plan type identifiers."""
    DEMO = "demo"
    STARTER = "starter"
    PROFESSIONAL = "professional"
    ENTERPRISE = "enterprise"
    CUSTOM = "custom"


class Plan(BaseModel):
    """
    Subscription plan configuration.

    Plans define resource limits, pricing, and trial settings.
    """

    __tablename__ = "plans"

    # Identification
    code = Column(String(50), unique=True, nullable=False)  # "demo", "starter", etc.
    name = Column(String(100), nullable=False)  # "Plan Demo", "Plan Starter"
    description = Column(Text, nullable=True)

    # Type
    plan_type = Column(String(20), nullable=False, default="starter")  # demo, starter, professional, enterprise, custom

    # Pricing (CLP)
    price_monthly = Column(Integer, default=0, nullable=False)  # 0 = free/demo
    price_yearly = Column(Integer, default=0, nullable=False)
    currency = Column(String(3), default="CLP", nullable=False)

    # Payment requirement
    requires_payment = Column(Boolean, default=True, nullable=False)  # False for demo, internal plans

    # Trial settings
    is_trial = Column(Boolean, default=False, nullable=False)
    trial_days = Column(Integer, default=0, nullable=False)  # 60 for demo

    # Resource limits
    max_tokens_monthly = Column(Integer, default=100000, nullable=False)
    max_agents = Column(Integer, default=1, nullable=False)
    max_documents = Column(Integer, default=20, nullable=False)
    max_users = Column(Integer, default=2, nullable=False)
    max_storage_mb = Column(Integer, default=100, nullable=False)

    # Features
    features = Column(JSONB, nullable=True)  # {"streaming": true, "rag": true, "realtime": false}

    # Status
    is_active = Column(Boolean, default=True, nullable=False)
    is_public = Column(Boolean, default=True, nullable=False)  # False = only admin can assign

    # Display
    display_order = Column(Integer, default=0, nullable=False)
    badge_text = Column(String(50), nullable=True)  # "Popular", "Recomendado"
    badge_color = Column(String(7), nullable=True)  # "#FF5733"

    def __repr__(self):
        return f"<Plan {self.code} ({self.name})>"


# Default plans configuration
DEFAULT_PLANS = [
    {
        "code": "demo",
        "name": "Plan Demo",
        "description": "Prueba gratuita por 60 días. Ideal para evaluar la plataforma.",
        "plan_type": "demo",
        "price_monthly": 0,
        "price_yearly": 0,
        "requires_payment": False,
        "is_trial": True,
        "trial_days": 60,
        "max_tokens_monthly": 50000,
        "max_agents": 1,
        "max_documents": 20,
        "max_users": 2,
        "max_storage_mb": 50,
        "features": {"streaming": True, "rag": True, "realtime": False, "priority_support": False},
        "is_public": True,
        "display_order": 0,
        "badge_text": "Gratis 60 días",
        "badge_color": "#10B981",
    },
    {
        "code": "starter",
        "name": "Plan Starter",
        "description": "Para equipos pequeños que comienzan con IA.",
        "plan_type": "starter",
        "price_monthly": 19990,  # CLP
        "price_yearly": 199900,
        "requires_payment": True,
        "is_trial": False,
        "trial_days": 0,
        "max_tokens_monthly": 500000,
        "max_agents": 5,
        "max_documents": 100,
        "max_users": 5,
        "max_storage_mb": 500,
        "features": {"streaming": True, "rag": True, "realtime": False, "priority_support": False},
        "is_public": True,
        "display_order": 1,
    },
    {
        "code": "professional",
        "name": "Plan Profesional",
        "description": "Para empresas que necesitan más capacidad y funciones.",
        "plan_type": "professional",
        "price_monthly": 49990,
        "price_yearly": 499900,
        "requires_payment": True,
        "is_trial": False,
        "trial_days": 0,
        "max_tokens_monthly": 2000000,
        "max_agents": 20,
        "max_documents": 500,
        "max_users": 20,
        "max_storage_mb": 2000,
        "features": {"streaming": True, "rag": True, "realtime": True, "priority_support": True},
        "is_public": True,
        "display_order": 2,
        "badge_text": "Popular",
        "badge_color": "#3B82F6",
    },
    {
        "code": "enterprise",
        "name": "Plan Enterprise",
        "description": "Solución completa para grandes organizaciones.",
        "plan_type": "enterprise",
        "price_monthly": 149990,
        "price_yearly": 1499900,
        "requires_payment": True,
        "is_trial": False,
        "trial_days": 0,
        "max_tokens_monthly": 10000000,
        "max_agents": 100,
        "max_documents": 2000,
        "max_users": 100,
        "max_storage_mb": 10000,
        "features": {"streaming": True, "rag": True, "realtime": True, "priority_support": True, "dedicated_support": True, "custom_integrations": True},
        "is_public": True,
        "display_order": 3,
    },
    {
        "code": "internal",
        "name": "Plan Interno",
        "description": "Plan sin costo para uso interno y testing.",
        "plan_type": "custom",
        "price_monthly": 0,
        "price_yearly": 0,
        "requires_payment": False,
        "is_trial": False,
        "trial_days": 0,
        "max_tokens_monthly": 10000000,
        "max_agents": 100,
        "max_documents": 2000,
        "max_users": 50,
        "max_storage_mb": 10000,
        "features": {"streaming": True, "rag": True, "realtime": True, "priority_support": True},
        "is_public": False,  # Only admin can assign
        "display_order": 99,
    },
]
