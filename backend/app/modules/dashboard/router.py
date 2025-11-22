"""
Dashboard router for analytics and statistics.
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import TenantUserAuth, get_current_admin
from app.modules.dashboard.service import dashboard_service
from app.modules.dashboard.schemas import (
    OverviewStats, ConversationsTimeSeries, MessagesTimeSeries,
    TokensTimeSeries, AgentStatsResponse, UsageBreakdown,
    TopItemsResponse, RealtimeStats, ComparisonResponse, PlatformStats
)


router = APIRouter()


# ============ Tenant Dashboard ============

@router.get("/overview", response_model=OverviewStats)
async def get_overview(
    current_user: TenantUserAuth,
    db: AsyncSession = Depends(get_db)
):
    """Get main dashboard overview statistics."""
    return await dashboard_service.get_overview_stats(
        db, current_user["tenant_id"]
    )


@router.get("/conversations/timeline", response_model=ConversationsTimeSeries)
async def get_conversations_timeline(
    current_user: TenantUserAuth,
    db: AsyncSession = Depends(get_db),
    days: int = Query(30, ge=1, le=365)
):
    """Get conversations over time."""
    return await dashboard_service.get_conversations_time_series(
        db, current_user["tenant_id"], days
    )


@router.get("/messages/timeline", response_model=MessagesTimeSeries)
async def get_messages_timeline(
    current_user: TenantUserAuth,
    db: AsyncSession = Depends(get_db),
    days: int = Query(30, ge=1, le=365)
):
    """Get messages over time."""
    return await dashboard_service.get_messages_time_series(
        db, current_user["tenant_id"], days
    )


@router.get("/tokens/timeline", response_model=TokensTimeSeries)
async def get_tokens_timeline(
    current_user: TenantUserAuth,
    db: AsyncSession = Depends(get_db),
    days: int = Query(30, ge=1, le=365)
):
    """Get token usage over time."""
    return await dashboard_service.get_tokens_time_series(
        db, current_user["tenant_id"], days
    )


@router.get("/agents/stats", response_model=AgentStatsResponse)
async def get_agents_stats(
    current_user: TenantUserAuth,
    db: AsyncSession = Depends(get_db),
    days: int = Query(30, ge=1, le=365)
):
    """Get statistics for each agent."""
    from datetime import datetime, timedelta

    stats = await dashboard_service.get_agent_stats(
        db, current_user["tenant_id"], days
    )
    return AgentStatsResponse(
        agents=stats,
        period_start=datetime.utcnow() - timedelta(days=days),
        period_end=datetime.utcnow()
    )


@router.get("/usage/breakdown", response_model=UsageBreakdown)
async def get_usage_breakdown(
    current_user: TenantUserAuth,
    db: AsyncSession = Depends(get_db),
    days: int = Query(30, ge=1, le=365)
):
    """Get detailed usage breakdown by model and agent."""
    return await dashboard_service.get_usage_breakdown(
        db, current_user["tenant_id"], days
    )


@router.get("/top", response_model=TopItemsResponse)
async def get_top_items(
    current_user: TenantUserAuth,
    db: AsyncSession = Depends(get_db),
    limit: int = Query(5, ge=1, le=20)
):
    """Get top performing items (agents, documents)."""
    result = await dashboard_service.get_top_items(
        db, current_user["tenant_id"], limit
    )
    return TopItemsResponse(**result)


@router.get("/realtime", response_model=RealtimeStats)
async def get_realtime_stats(
    current_user: TenantUserAuth,
    db: AsyncSession = Depends(get_db)
):
    """Get real-time activity statistics."""
    return await dashboard_service.get_realtime_stats(
        db, current_user["tenant_id"]
    )


@router.get("/comparison", response_model=ComparisonResponse)
async def get_period_comparison(
    current_user: TenantUserAuth,
    db: AsyncSession = Depends(get_db),
    period: str = Query("month", regex="^(day|week|month)$")
):
    """Compare current period with previous period."""
    result = await dashboard_service.get_period_comparison(
        db, current_user["tenant_id"], period
    )
    return ComparisonResponse(**result)


# ============ Admin Platform Stats ============

@router.get("/admin/platform", response_model=PlatformStats)
async def get_platform_stats(
    current_admin = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db)
):
    """Get platform-wide statistics (super admin only)."""
    return await dashboard_service.get_platform_stats(db)
