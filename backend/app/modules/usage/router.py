"""
Usage Module - Router

Endpoints for token usage tracking and analytics.
"""

from datetime import date
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import TenantUser
from app.utils.logger import get_logger

from .schemas import (
    UsagePeriod,
    UsageSummaryResponse,
    UsageQuota,
    UsageChartResponse,
)
from .service import UsageService

logger = get_logger(__name__)
router = APIRouter()


def get_usage_service(db: AsyncSession = Depends(get_db)) -> UsageService:
    """Dependency to get usage service."""
    return UsageService(db)


@router.get("/summary", response_model=UsageSummaryResponse)
async def get_usage_summary(
    current_user: TenantUser,
    period: UsagePeriod = Query(UsagePeriod.MONTHLY, description="Aggregation period"),
    start_date: date = Query(None, description="Start date"),
    end_date: date = Query(None, description="End date"),
    service: UsageService = Depends(get_usage_service),
):
    """
    Get usage summary for current tenant.

    Includes totals and breakdowns by model and agent.
    """
    tenant_id = getattr(current_user, "tenant_id", None)
    if not tenant_id:
        raise HTTPException(status_code=400, detail="User not associated with a tenant")

    return await service.get_usage_summary(
        tenant_id=tenant_id,
        period=period,
        start_date=start_date,
        end_date=end_date,
    )


@router.get("/quota", response_model=UsageQuota)
async def get_usage_quota(
    current_user: TenantUser,
    service: UsageService = Depends(get_usage_service),
):
    """
    Get current usage quota status.

    Shows tokens used, remaining, and limit based on plan.
    """
    tenant_id = getattr(current_user, "tenant_id", None)
    if not tenant_id:
        raise HTTPException(status_code=400, detail="User not associated with a tenant")

    try:
        return await service.get_quota(tenant_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/chart", response_model=UsageChartResponse)
async def get_usage_chart(
    current_user: TenantUser,
    days: int = Query(30, ge=1, le=90, description="Number of days"),
    service: UsageService = Depends(get_usage_service),
):
    """
    Get daily usage data for charts.

    Returns data points for the specified number of days.
    """
    tenant_id = getattr(current_user, "tenant_id", None)
    if not tenant_id:
        raise HTTPException(status_code=400, detail="User not associated with a tenant")

    return await service.get_usage_chart(
        tenant_id=tenant_id,
        days=days,
    )


@router.get("/by-agent")
async def get_usage_by_agent(
    current_user: TenantUser,
    service: UsageService = Depends(get_usage_service),
):
    """Get token usage breakdown by agent."""
    tenant_id = getattr(current_user, "tenant_id", None)
    if not tenant_id:
        raise HTTPException(status_code=400, detail="User not associated with a tenant")

    summary = await service.get_usage_summary(
        tenant_id=tenant_id,
        period=UsagePeriod.MONTHLY,
    )

    return {"agents": list(summary.by_agent.values())}


@router.get("/by-model")
async def get_usage_by_model(
    current_user: TenantUser,
    service: UsageService = Depends(get_usage_service),
):
    """Get token usage breakdown by AI model."""
    tenant_id = getattr(current_user, "tenant_id", None)
    if not tenant_id:
        raise HTTPException(status_code=400, detail="User not associated with a tenant")

    summary = await service.get_usage_summary(
        tenant_id=tenant_id,
        period=UsagePeriod.MONTHLY,
    )

    return {"models": list(summary.by_model.values())}
