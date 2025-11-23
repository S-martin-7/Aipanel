"""
Platform Admin Router - Level 1 (Super Admin).

Endpoints for platform-wide administration.
Only accessible by SUPER_ADMIN users.
"""

from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import AdminUser
from app.utils.logger import get_logger

from .platform_service import PlatformAdminService

logger = get_logger(__name__)
router = APIRouter()


def get_platform_service(db: AsyncSession = Depends(get_db)) -> PlatformAdminService:
    """Dependency to get platform service."""
    return PlatformAdminService(db)


def require_super_admin(current_user: AdminUser):
    """Verify user is SUPER_ADMIN."""
    if current_user.get("role") != "SUPER_ADMIN":
        raise HTTPException(
            status_code=403,
            detail="Super admin access required"
        )
    return current_user


# ============================================================
# Platform Health & Overview
# ============================================================

@router.get("/health")
async def get_platform_health(
    current_user: AdminUser = Depends(require_super_admin),
    service: PlatformAdminService = Depends(get_platform_service),
):
    """
    Get platform health status.

    Returns current health status, error rates, and active metrics.
    """
    return await service.get_platform_health()


@router.get("/overview")
async def get_platform_overview(
    current_user: AdminUser = Depends(require_super_admin),
    service: PlatformAdminService = Depends(get_platform_service),
):
    """
    Get platform overview statistics.

    Returns counts for tenants, users, agents, conversations, tokens.
    """
    return await service.get_platform_overview()


# ============================================================
# Tenant Management
# ============================================================

@router.get("/tenants")
async def list_tenants(
    current_user: AdminUser = Depends(require_super_admin),
    status: Optional[str] = Query(None, description="Filter by status"),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    service: PlatformAdminService = Depends(get_platform_service),
):
    """
    List all tenants with activity metrics.

    Includes user count, agent count, recent activity, token usage.
    """
    offset = (page - 1) * page_size
    tenants, total = await service.list_tenants(
        status=status,
        limit=page_size,
        offset=offset,
    )

    return {
        "tenants": tenants,
        "total": total,
        "page": page,
        "page_size": page_size,
    }


@router.get("/tenants/{tenant_id}")
async def get_tenant_detail(
    tenant_id: str,
    current_user: AdminUser = Depends(require_super_admin),
    service: PlatformAdminService = Depends(get_platform_service),
):
    """
    Get detailed tenant information.

    Includes users, agents, and usage statistics.
    """
    tenant = await service.get_tenant_detail(tenant_id)
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")
    return tenant


# ============================================================
# Active Users Monitoring
# ============================================================

@router.get("/users/active")
async def get_active_users(
    current_user: AdminUser = Depends(require_super_admin),
    hours: int = Query(1, ge=1, le=24),
    tenant_id: Optional[str] = Query(None, description="Filter by tenant"),
    service: PlatformAdminService = Depends(get_platform_service),
):
    """
    Get currently active users across platform.

    Shows users who have logged in within the specified time window.
    """
    users = await service.get_active_users(hours=hours, tenant_id=tenant_id)
    return {
        "users": users,
        "count": len(users),
        "period_hours": hours,
    }


# ============================================================
# Error Monitoring
# ============================================================

@router.get("/errors")
async def get_recent_errors(
    current_user: AdminUser = Depends(require_super_admin),
    hours: int = Query(24, ge=1, le=168),
    tenant_id: Optional[str] = Query(None),
    limit: int = Query(100, ge=1, le=500),
    service: PlatformAdminService = Depends(get_platform_service),
):
    """
    Get recent errors across platform.

    Returns error logs for debugging and monitoring.
    """
    errors = await service.get_recent_errors(
        hours=hours,
        tenant_id=tenant_id,
        limit=limit,
    )
    return {
        "errors": errors,
        "count": len(errors),
        "period_hours": hours,
    }


@router.get("/errors/summary")
async def get_error_summary(
    current_user: AdminUser = Depends(require_super_admin),
    hours: int = Query(24, ge=1, le=168),
    service: PlatformAdminService = Depends(get_platform_service),
):
    """
    Get error summary and breakdown.

    Groups errors by code and by tenant.
    """
    return await service.get_error_summary(hours=hours)


# ============================================================
# Activity Monitoring
# ============================================================

@router.get("/activity/feed")
async def get_activity_feed(
    current_user: AdminUser = Depends(require_super_admin),
    hours: int = Query(1, ge=1, le=24),
    limit: int = Query(50, ge=1, le=200),
    service: PlatformAdminService = Depends(get_platform_service),
):
    """
    Get real-time activity feed across platform.

    Shows recent AI requests with tenant, status, tokens, latency.
    """
    activity = await service.get_activity_feed(hours=hours, limit=limit)
    return {
        "activity": activity,
        "count": len(activity),
        "period_hours": hours,
    }


@router.get("/activity/ranking")
async def get_tenant_ranking(
    current_user: AdminUser = Depends(require_super_admin),
    days: int = Query(7, ge=1, le=30),
    limit: int = Query(20, ge=1, le=50),
    service: PlatformAdminService = Depends(get_platform_service),
):
    """
    Get tenants ranked by activity.

    Shows top tenants by request count, tokens, and error rate.
    """
    ranking = await service.get_tenant_activity_ranking(days=days, limit=limit)
    return {
        "ranking": ranking,
        "period_days": days,
    }
