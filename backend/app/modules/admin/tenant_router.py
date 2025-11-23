"""
Tenant Admin Router - Level 2 (Tenant Admin).

REST endpoints for tenant-level administration.
Requires OWNER or ADMIN role within the tenant.
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_user, CurrentUser
from app.models import TenantUserRole
from app.utils.logger import get_logger

from .tenant_service import TenantAdminService

logger = get_logger(__name__)

router = APIRouter()


def get_tenant_service(
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = None,
) -> TenantAdminService:
    """Get TenantAdminService with tenant context."""
    tenant_id = current_user.get("tenant_id") if current_user else None
    if not tenant_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Tenant context required"
        )
    return TenantAdminService(db, tenant_id)


async def require_tenant_admin(current_user: CurrentUser) -> CurrentUser:
    """Require OWNER or ADMIN role within tenant."""
    role = current_user.get("tenant_role")
    if role not in [TenantUserRole.OWNER.value, TenantUserRole.ADMIN.value, "OWNER", "ADMIN"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Tenant admin access required"
        )
    return current_user


# ============================================================
# Dashboard
# ============================================================

@router.get("/dashboard")
async def get_dashboard(
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    """
    Get tenant dashboard summary.

    Shows users, agents, documents, and activity stats.
    """
    await require_tenant_admin(current_user)
    tenant_id = current_user.get("tenant_id")

    service = TenantAdminService(db, tenant_id)
    return await service.get_dashboard_summary()


# ============================================================
# User Management
# ============================================================

@router.get("/users")
async def list_users(
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
    include_inactive: bool = Query(False, description="Include inactive users"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
):
    """
    List all users in the tenant.

    Returns user list with activity metrics.
    """
    await require_tenant_admin(current_user)
    tenant_id = current_user.get("tenant_id")

    service = TenantAdminService(db, tenant_id)
    users, total = await service.list_users(
        include_inactive=include_inactive,
        limit=limit,
        offset=offset
    )

    return {
        "users": users,
        "total": total,
        "limit": limit,
        "offset": offset,
    }


@router.get("/users/online")
async def get_online_users(
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
    minutes: int = Query(30, ge=5, le=1440),
):
    """
    Get currently online users.

    Shows users active within the specified time window.
    """
    await require_tenant_admin(current_user)
    tenant_id = current_user.get("tenant_id")

    service = TenantAdminService(db, tenant_id)
    return await service.get_online_users(minutes=minutes)


@router.get("/users/{user_id}")
async def get_user_detail(
    user_id: str,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    """
    Get detailed user information.

    Includes activity stats and recent conversations.
    """
    await require_tenant_admin(current_user)
    tenant_id = current_user.get("tenant_id")

    service = TenantAdminService(db, tenant_id)
    user = await service.get_user_detail(user_id)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    return user


@router.patch("/users/{user_id}/status")
async def update_user_status(
    user_id: str,
    is_active: bool,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    """
    Activate or deactivate a user.
    """
    await require_tenant_admin(current_user)
    tenant_id = current_user.get("tenant_id")

    service = TenantAdminService(db, tenant_id)
    success = await service.update_user_status(user_id, is_active)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    action = "activated" if is_active else "deactivated"
    logger.info(f"User {user_id} {action} by {current_user.get('email')}")

    return {"message": f"User {action} successfully"}


@router.patch("/users/{user_id}/role")
async def update_user_role(
    user_id: str,
    role: str,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    """
    Update user's role within tenant.

    Valid roles: OWNER, ADMIN, MEMBER, VIEWER
    """
    await require_tenant_admin(current_user)
    tenant_id = current_user.get("tenant_id")

    # Only OWNER can promote to OWNER/ADMIN
    current_role = current_user.get("tenant_role")
    if role in ["OWNER", "ADMIN"] and current_role != "OWNER":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only owners can assign admin roles"
        )

    service = TenantAdminService(db, tenant_id)
    success = await service.update_user_role(user_id, role)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to update role. Check if user exists and role is valid."
        )

    logger.info(f"User {user_id} role changed to {role} by {current_user.get('email')}")

    return {"message": f"User role updated to {role}"}


# ============================================================
# Activity Monitoring
# ============================================================

@router.get("/activity/timeline")
async def get_activity_timeline(
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
    hours: int = Query(24, ge=1, le=168),
):
    """
    Get hourly activity breakdown.

    Shows requests, tokens, and errors per hour.
    """
    await require_tenant_admin(current_user)
    tenant_id = current_user.get("tenant_id")

    service = TenantAdminService(db, tenant_id)
    return await service.get_activity_timeline(hours=hours)


@router.get("/activity/agents")
async def get_agent_activity(
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
    days: int = Query(7, ge=1, le=90),
):
    """
    Get activity breakdown by agent.

    Shows usage stats per agent.
    """
    await require_tenant_admin(current_user)
    tenant_id = current_user.get("tenant_id")

    service = TenantAdminService(db, tenant_id)
    return await service.get_agent_activity(days=days)


# ============================================================
# Usage & Billing
# ============================================================

@router.get("/usage/by-user")
async def get_usage_by_user(
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
    days: int = Query(30, ge=1, le=90),
):
    """
    Get token usage breakdown by user.
    """
    await require_tenant_admin(current_user)
    tenant_id = current_user.get("tenant_id")

    service = TenantAdminService(db, tenant_id)
    return await service.get_usage_by_user(days=days)


# ============================================================
# Errors
# ============================================================

@router.get("/errors")
async def get_recent_errors(
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
    hours: int = Query(24, ge=1, le=168),
    limit: int = Query(50, ge=1, le=200),
):
    """
    Get recent errors for this tenant.
    """
    await require_tenant_admin(current_user)
    tenant_id = current_user.get("tenant_id")

    service = TenantAdminService(db, tenant_id)
    return await service.get_recent_errors(hours=hours, limit=limit)
