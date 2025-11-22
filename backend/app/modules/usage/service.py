"""
Usage Module - Service

Business logic for usage tracking and analytics.
"""

from typing import Optional
from datetime import datetime, date, timedelta

from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import TokenUsage, UsageSummary, Tenant, Agent
from app.utils.logger import get_logger

from .schemas import (
    UsagePeriod,
    TokenUsageRecord,
    UsageSummaryResponse,
    ModelUsage,
    AgentUsage,
    UsageQuota,
    DailyUsagePoint,
    UsageChartResponse,
)

logger = get_logger(__name__)

# Cost per 1K tokens (approximate, varies by model)
MODEL_COSTS = {
    "gpt-4o": {"input": 0.005, "output": 0.015},
    "gpt-4o-mini": {"input": 0.00015, "output": 0.0006},
    "o1": {"input": 0.015, "output": 0.06},
    "claude-sonnet-4-5-20250929": {"input": 0.003, "output": 0.015},
    "claude-3-5-haiku-20241022": {"input": 0.001, "output": 0.005},
    "default": {"input": 0.002, "output": 0.008},
}


class UsageService:
    """
    Usage service for tracking token consumption.

    Features:
    - Record token usage per request
    - Calculate costs
    - Generate usage summaries
    - Check quotas and alerts
    """

    def __init__(self, db: AsyncSession):
        """Initialize with database session."""
        self.db = db

    async def record_usage(
        self,
        tenant_id: str,
        agent_id: str,
        model: str,
        prompt_tokens: int,
        completion_tokens: int,
    ) -> TokenUsageRecord:
        """
        Record token usage for a request.

        Args:
            tenant_id: Tenant ID
            agent_id: Agent ID
            model: Model used
            prompt_tokens: Input tokens
            completion_tokens: Output tokens

        Returns:
            TokenUsageRecord
        """
        total_tokens = prompt_tokens + completion_tokens
        cost = self._calculate_cost(model, prompt_tokens, completion_tokens)

        usage = TokenUsage(
            tenant_id=tenant_id,
            agent_id=agent_id,
            model=model,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=total_tokens,
            cost_usd=cost,
        )
        self.db.add(usage)

        # Update tenant's period usage
        await self._update_tenant_usage(tenant_id, total_tokens)

        await self.db.commit()
        await self.db.refresh(usage)

        return TokenUsageRecord(
            id=usage.id,
            tenant_id=tenant_id,
            agent_id=agent_id,
            model=model,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=total_tokens,
            cost_usd=cost,
            created_at=usage.created_at,
        )

    async def get_usage_summary(
        self,
        tenant_id: str,
        period: UsagePeriod = UsagePeriod.MONTHLY,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
    ) -> UsageSummaryResponse:
        """
        Get usage summary for a period.

        Args:
            tenant_id: Tenant ID
            period: Aggregation period
            start_date: Start date (defaults to period start)
            end_date: End date (defaults to today)

        Returns:
            UsageSummaryResponse
        """
        # Calculate date range
        today = date.today()
        if not end_date:
            end_date = today

        if not start_date:
            if period == UsagePeriod.DAILY:
                start_date = today
            elif period == UsagePeriod.WEEKLY:
                start_date = today - timedelta(days=7)
            else:  # MONTHLY
                start_date = today.replace(day=1)

        start_dt = datetime.combine(start_date, datetime.min.time())
        end_dt = datetime.combine(end_date, datetime.max.time())

        # Query usage
        result = await self.db.execute(
            select(
                func.count(TokenUsage.id).label("total_requests"),
                func.sum(TokenUsage.total_tokens).label("total_tokens"),
                func.sum(TokenUsage.prompt_tokens).label("prompt_tokens"),
                func.sum(TokenUsage.completion_tokens).label("completion_tokens"),
                func.sum(TokenUsage.cost_usd).label("total_cost"),
            ).where(
                and_(
                    TokenUsage.tenant_id == tenant_id,
                    TokenUsage.created_at >= start_dt,
                    TokenUsage.created_at <= end_dt,
                )
            )
        )
        row = result.one()

        # Get by model breakdown
        model_result = await self.db.execute(
            select(
                TokenUsage.model,
                func.count(TokenUsage.id).label("requests"),
                func.sum(TokenUsage.total_tokens).label("total_tokens"),
                func.sum(TokenUsage.cost_usd).label("cost"),
            )
            .where(
                and_(
                    TokenUsage.tenant_id == tenant_id,
                    TokenUsage.created_at >= start_dt,
                    TokenUsage.created_at <= end_dt,
                )
            )
            .group_by(TokenUsage.model)
        )
        by_model = {
            r.model: ModelUsage(
                model=r.model,
                requests=r.requests,
                total_tokens=r.total_tokens or 0,
                cost_usd=float(r.cost or 0),
            )
            for r in model_result
        }

        # Get by agent breakdown
        agent_result = await self.db.execute(
            select(
                TokenUsage.agent_id,
                Agent.name,
                func.count(TokenUsage.id).label("requests"),
                func.sum(TokenUsage.total_tokens).label("total_tokens"),
            )
            .join(Agent, Agent.id == TokenUsage.agent_id, isouter=True)
            .where(
                and_(
                    TokenUsage.tenant_id == tenant_id,
                    TokenUsage.created_at >= start_dt,
                    TokenUsage.created_at <= end_dt,
                )
            )
            .group_by(TokenUsage.agent_id, Agent.name)
        )
        by_agent = {
            r.agent_id: AgentUsage(
                agent_id=r.agent_id,
                agent_name=r.name or "Unknown",
                requests=r.requests,
                total_tokens=r.total_tokens or 0,
            )
            for r in agent_result
            if r.agent_id
        }

        return UsageSummaryResponse(
            tenant_id=tenant_id,
            period=period,
            start_date=start_date,
            end_date=end_date,
            total_requests=row.total_requests or 0,
            total_tokens=row.total_tokens or 0,
            prompt_tokens=row.prompt_tokens or 0,
            completion_tokens=row.completion_tokens or 0,
            estimated_cost_usd=float(row.total_cost or 0),
            by_model=by_model,
            by_agent=by_agent,
        )

    async def get_quota(
        self,
        tenant_id: str,
    ) -> UsageQuota:
        """Get current usage quota status."""
        # Get tenant
        result = await self.db.execute(
            select(Tenant).where(Tenant.id == tenant_id)
        )
        tenant = result.scalar_one_or_none()

        if not tenant:
            raise ValueError("Tenant not found")

        # Get plan limits
        plan = getattr(tenant, 'plan', 'free') or 'free'
        plan_limits = {
            'free': 10000,
            'starter': 100000,
            'professional': 500000,
            'enterprise': 2000000,
        }
        tokens_limit = plan_limits.get(plan, 10000)

        # Get current usage
        tokens_used = getattr(tenant, 'tokens_used_this_period', 0) or 0
        tokens_remaining = max(0, tokens_limit - tokens_used)
        usage_percentage = (tokens_used / tokens_limit * 100) if tokens_limit > 0 else 0

        # Reset date (first of next month)
        period_start = getattr(tenant, 'current_period_start', None) or datetime.utcnow().replace(day=1)
        reset_date = (period_start + timedelta(days=32)).replace(day=1).date()

        return UsageQuota(
            tenant_id=tenant_id,
            plan=plan,
            tokens_limit=tokens_limit,
            tokens_used=tokens_used,
            tokens_remaining=tokens_remaining,
            usage_percentage=round(usage_percentage, 2),
            reset_date=reset_date,
            is_exceeded=tokens_used >= tokens_limit,
        )

    async def get_usage_chart(
        self,
        tenant_id: str,
        days: int = 30,
    ) -> UsageChartResponse:
        """
        Get daily usage data for charts.

        Args:
            tenant_id: Tenant ID
            days: Number of days to include

        Returns:
            UsageChartResponse with daily data points
        """
        end_date = date.today()
        start_date = end_date - timedelta(days=days)
        start_dt = datetime.combine(start_date, datetime.min.time())

        # Query daily aggregates
        result = await self.db.execute(
            select(
                func.date(TokenUsage.created_at).label("date"),
                func.sum(TokenUsage.total_tokens).label("tokens"),
                func.count(TokenUsage.id).label("requests"),
                func.sum(TokenUsage.cost_usd).label("cost"),
            )
            .where(
                and_(
                    TokenUsage.tenant_id == tenant_id,
                    TokenUsage.created_at >= start_dt,
                )
            )
            .group_by(func.date(TokenUsage.created_at))
            .order_by(func.date(TokenUsage.created_at))
        )
        rows = result.all()

        # Build data points (fill missing days with zeros)
        data_by_date = {r.date: r for r in rows}
        data_points = []
        total_tokens = 0
        total_requests = 0
        total_cost = 0.0

        current = start_date
        while current <= end_date:
            if current in data_by_date:
                r = data_by_date[current]
                tokens = r.tokens or 0
                requests = r.requests or 0
                cost = float(r.cost or 0)
            else:
                tokens = 0
                requests = 0
                cost = 0.0

            data_points.append(DailyUsagePoint(
                date=current,
                tokens=tokens,
                requests=requests,
                cost_usd=cost,
            ))

            total_tokens += tokens
            total_requests += requests
            total_cost += cost
            current += timedelta(days=1)

        return UsageChartResponse(
            tenant_id=tenant_id,
            period=UsagePeriod.DAILY,
            data_points=data_points,
            total_tokens=total_tokens,
            total_requests=total_requests,
            total_cost_usd=round(total_cost, 4),
        )

    def _calculate_cost(
        self,
        model: str,
        prompt_tokens: int,
        completion_tokens: int,
    ) -> float:
        """Calculate cost in USD for token usage."""
        costs = MODEL_COSTS.get(model, MODEL_COSTS["default"])
        input_cost = (prompt_tokens / 1000) * costs["input"]
        output_cost = (completion_tokens / 1000) * costs["output"]
        return round(input_cost + output_cost, 6)

    async def _update_tenant_usage(
        self,
        tenant_id: str,
        tokens: int,
    ) -> None:
        """Update tenant's period token usage."""
        result = await self.db.execute(
            select(Tenant).where(Tenant.id == tenant_id)
        )
        tenant = result.scalar_one_or_none()

        if tenant:
            current_usage = getattr(tenant, 'tokens_used_this_period', 0) or 0
            tenant.tokens_used_this_period = current_usage + tokens
            await self.db.flush()
