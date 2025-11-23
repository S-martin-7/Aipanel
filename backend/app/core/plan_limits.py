"""
Plan Limits and Usage Guards.

Enforces plan-based limits on AI usage, API calls, and resources.
"""

from enum import Enum
from dataclasses import dataclass
from typing import Optional, Tuple
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Tenant
from app.utils.logger import get_logger

logger = get_logger(__name__)


class Plan(str, Enum):
    """Available subscription plans."""
    FREE = "free"
    STARTER = "starter"
    PROFESSIONAL = "professional"
    ENTERPRISE = "enterprise"


@dataclass
class PlanLimits:
    """Limits for a subscription plan."""
    tokens_per_month: int
    agents_limit: int
    documents_per_agent: int
    api_rate_limit_per_minute: int
    webhooks_limit: int
    can_use_premium_models: bool
    max_document_size_mb: int
    support_level: str


# Plan configurations
PLAN_LIMITS = {
    Plan.FREE: PlanLimits(
        tokens_per_month=10_000,
        agents_limit=1,
        documents_per_agent=5,
        api_rate_limit_per_minute=10,
        webhooks_limit=1,
        can_use_premium_models=False,
        max_document_size_mb=5,
        support_level="community",
    ),
    Plan.STARTER: PlanLimits(
        tokens_per_month=100_000,
        agents_limit=3,
        documents_per_agent=20,
        api_rate_limit_per_minute=30,
        webhooks_limit=5,
        can_use_premium_models=False,
        max_document_size_mb=10,
        support_level="email",
    ),
    Plan.PROFESSIONAL: PlanLimits(
        tokens_per_month=500_000,
        agents_limit=10,
        documents_per_agent=100,
        api_rate_limit_per_minute=100,
        webhooks_limit=20,
        can_use_premium_models=True,
        max_document_size_mb=50,
        support_level="priority",
    ),
    Plan.ENTERPRISE: PlanLimits(
        tokens_per_month=2_000_000,
        agents_limit=999,
        documents_per_agent=999,
        api_rate_limit_per_minute=500,
        webhooks_limit=100,
        can_use_premium_models=True,
        max_document_size_mb=100,
        support_level="dedicated",
    ),
}


@dataclass
class UsageStatus:
    """Current usage status for a tenant."""
    plan: Plan
    tokens_used: int
    tokens_limit: int
    tokens_remaining: int
    usage_percentage: float
    is_exceeded: bool
    is_near_limit: bool  # 80%+ usage
    reset_date: Optional[datetime] = None


class PlanLimitExceededError(Exception):
    """Raised when plan limits are exceeded."""
    def __init__(self, message: str, usage_status: UsageStatus):
        self.usage_status = usage_status
        super().__init__(message)


class PlanLimitGuard:
    """
    Guards AI operations against plan limits.

    Use before any AI call to ensure tenant hasn't exceeded their plan.
    """

    def __init__(self, db: AsyncSession):
        self.db = db

    async def check_token_limit(
        self,
        tenant_id: str,
        estimated_tokens: int = 0,
    ) -> UsageStatus:
        """
        Check if tenant can make an AI request.

        Args:
            tenant_id: Tenant ID to check
            estimated_tokens: Estimated tokens for the request

        Returns:
            UsageStatus with current usage info

        Raises:
            PlanLimitExceededError: If tenant has exceeded their plan
        """
        # Get tenant
        result = await self.db.execute(
            select(Tenant).where(Tenant.id == tenant_id)
        )
        tenant = result.scalar_one_or_none()

        if not tenant:
            raise ValueError(f"Tenant not found: {tenant_id}")

        # Get plan and limits
        plan = Plan(getattr(tenant, 'plan', 'free') or 'free')
        limits = PLAN_LIMITS[plan]

        # Get current usage
        tokens_used = getattr(tenant, 'tokens_used_this_period', 0) or 0
        tokens_limit = limits.tokens_per_month
        tokens_remaining = max(0, tokens_limit - tokens_used)
        usage_percentage = (tokens_used / tokens_limit * 100) if tokens_limit > 0 else 0

        # Get reset date
        period_start = getattr(tenant, 'current_period_start', None)
        reset_date = None
        if period_start:
            from datetime import timedelta
            reset_date = (period_start + timedelta(days=32)).replace(day=1)

        status = UsageStatus(
            plan=plan,
            tokens_used=tokens_used,
            tokens_limit=tokens_limit,
            tokens_remaining=tokens_remaining,
            usage_percentage=round(usage_percentage, 2),
            is_exceeded=tokens_used >= tokens_limit,
            is_near_limit=usage_percentage >= 80,
            reset_date=reset_date,
        )

        # Check if exceeded
        if status.is_exceeded:
            logger.warning(
                f"Plan limit exceeded for tenant {tenant_id}: "
                f"{tokens_used}/{tokens_limit} tokens"
            )
            raise PlanLimitExceededError(
                f"Token limit exceeded. Used {tokens_used} of {tokens_limit} tokens. "
                f"Please upgrade your plan to continue.",
                status
            )

        # Check if request would exceed
        if estimated_tokens > 0 and (tokens_used + estimated_tokens) > tokens_limit:
            logger.warning(
                f"Request would exceed limit for tenant {tenant_id}: "
                f"{tokens_used} + {estimated_tokens} > {tokens_limit}"
            )
            raise PlanLimitExceededError(
                f"This request would exceed your token limit. "
                f"Remaining: {tokens_remaining} tokens.",
                status
            )

        return status

    async def check_agents_limit(self, tenant_id: str, current_count: int) -> bool:
        """Check if tenant can create more agents."""
        result = await self.db.execute(
            select(Tenant).where(Tenant.id == tenant_id)
        )
        tenant = result.scalar_one_or_none()

        if not tenant:
            return False

        plan = Plan(getattr(tenant, 'plan', 'free') or 'free')
        limits = PLAN_LIMITS[plan]

        return current_count < limits.agents_limit

    async def check_documents_limit(
        self,
        tenant_id: str,
        agent_id: str,
        current_count: int
    ) -> bool:
        """Check if agent can have more documents."""
        result = await self.db.execute(
            select(Tenant).where(Tenant.id == tenant_id)
        )
        tenant = result.scalar_one_or_none()

        if not tenant:
            return False

        plan = Plan(getattr(tenant, 'plan', 'free') or 'free')
        limits = PLAN_LIMITS[plan]

        return current_count < limits.documents_per_agent

    async def check_document_size(self, tenant_id: str, size_bytes: int) -> bool:
        """Check if document size is within plan limits."""
        result = await self.db.execute(
            select(Tenant).where(Tenant.id == tenant_id)
        )
        tenant = result.scalar_one_or_none()

        if not tenant:
            return False

        plan = Plan(getattr(tenant, 'plan', 'free') or 'free')
        limits = PLAN_LIMITS[plan]

        max_bytes = limits.max_document_size_mb * 1024 * 1024
        return size_bytes <= max_bytes

    async def can_use_model(self, tenant_id: str, model: str) -> bool:
        """Check if tenant can use a specific model."""
        result = await self.db.execute(
            select(Tenant).where(Tenant.id == tenant_id)
        )
        tenant = result.scalar_one_or_none()

        if not tenant:
            return False

        plan = Plan(getattr(tenant, 'plan', 'free') or 'free')
        limits = PLAN_LIMITS[plan]

        # Premium models (example list)
        premium_models = ["gpt-4", "gpt-4-turbo", "gpt-4o", "claude-3-opus", "o1"]

        model_lower = model.lower()
        is_premium = any(pm in model_lower for pm in premium_models)

        if is_premium and not limits.can_use_premium_models:
            return False

        return True

    async def get_rate_limit(self, tenant_id: str) -> int:
        """Get API rate limit for tenant's plan."""
        result = await self.db.execute(
            select(Tenant).where(Tenant.id == tenant_id)
        )
        tenant = result.scalar_one_or_none()

        if not tenant:
            return PLAN_LIMITS[Plan.FREE].api_rate_limit_per_minute

        plan = Plan(getattr(tenant, 'plan', 'free') or 'free')
        return PLAN_LIMITS[plan].api_rate_limit_per_minute

    def get_plan_limits(self, plan: Plan) -> PlanLimits:
        """Get limits for a specific plan."""
        return PLAN_LIMITS[plan]


def get_plan_limits_for_display() -> dict:
    """Get plan limits formatted for display/comparison."""
    return {
        plan.value: {
            "tokens_per_month": f"{limits.tokens_per_month:,}",
            "agents": limits.agents_limit if limits.agents_limit < 100 else "Unlimited",
            "documents_per_agent": limits.documents_per_agent if limits.documents_per_agent < 100 else "Unlimited",
            "rate_limit": f"{limits.api_rate_limit_per_minute}/min",
            "webhooks": limits.webhooks_limit,
            "premium_models": limits.can_use_premium_models,
            "max_document_size": f"{limits.max_document_size_mb} MB",
            "support": limits.support_level,
        }
        for plan, limits in PLAN_LIMITS.items()
    }
