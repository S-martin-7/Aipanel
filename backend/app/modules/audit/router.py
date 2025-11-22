"""
Audit router for querying audit logs.
"""
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import TenantUserAuth, get_current_admin
from app.modules.audit.service import audit_service
from app.modules.audit.schemas import (
    AuditLogResponse, AuditLogListResponse, AuditLogFilters,
    AuditStats, AuditActionsResponse
)


router = APIRouter()


# ============ Tenant Audit Logs ============

@router.get("/actions", response_model=AuditActionsResponse)
async def list_available_actions(
    current_user: TenantUserAuth
):
    """List all available audit action types."""
    actions = audit_service.get_available_actions()
    return AuditActionsResponse(actions=actions)


@router.get("", response_model=AuditLogListResponse)
async def list_audit_logs(
    current_user: TenantUserAuth,
    db: AsyncSession = Depends(get_db),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    action: Optional[str] = None,
    resource_type: Optional[str] = None,
    resource_id: Optional[str] = None,
    user_id: Optional[str] = None,
    status_filter: Optional[str] = Query(None, alias="status")
):
    """List audit logs for the current tenant."""
    # Only admin/owner can view audit logs
    if current_user["role"] not in ["admin", "owner"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can view audit logs"
        )

    filters = AuditLogFilters(
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        user_id=user_id,
        status=status_filter
    )

    logs, total = await audit_service.get_logs(
        db,
        tenant_id=current_user["tenant_id"],
        filters=filters,
        page=page,
        page_size=page_size
    )

    total_pages = (total + page_size - 1) // page_size

    return AuditLogListResponse(
        logs=[AuditLogResponse.model_validate(log) for log in logs],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages
    )


@router.get("/stats", response_model=AuditStats)
async def get_audit_stats(
    current_user: TenantUserAuth,
    db: AsyncSession = Depends(get_db),
    days: int = Query(30, ge=1, le=365)
):
    """Get audit log statistics for the tenant."""
    if current_user["role"] not in ["admin", "owner"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can view audit statistics"
        )

    stats = await audit_service.get_stats(
        db, tenant_id=current_user["tenant_id"], days=days
    )

    return AuditStats(
        total_logs=stats["total_logs"],
        logs_today=stats["logs_today"],
        logs_this_week=stats["logs_this_week"],
        logs_this_month=stats["logs_this_month"],
        by_action=stats["by_action"],
        by_resource_type=stats["by_resource_type"],
        by_status=stats["by_status"],
        by_user=stats["by_user"],
        recent_failures=[AuditLogResponse.model_validate(f) for f in stats["recent_failures"]]
    )


@router.get("/resource/{resource_type}/{resource_id}")
async def get_resource_history(
    resource_type: str,
    resource_id: str,
    current_user: TenantUserAuth,
    db: AsyncSession = Depends(get_db)
):
    """Get audit history for a specific resource."""
    logs = await audit_service.get_resource_history(
        db,
        resource_type=resource_type,
        resource_id=resource_id,
        tenant_id=current_user["tenant_id"]
    )
    return {
        "logs": [AuditLogResponse.model_validate(log) for log in logs],
        "resource_type": resource_type,
        "resource_id": resource_id
    }


@router.get("/user/{user_id}")
async def get_user_activity(
    user_id: str,
    current_user: TenantUserAuth,
    db: AsyncSession = Depends(get_db),
    days: int = Query(30, ge=1, le=365)
):
    """Get audit logs for a specific user."""
    if current_user["role"] not in ["admin", "owner"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can view user activity"
        )

    logs = await audit_service.get_user_activity(
        db,
        user_id=user_id,
        tenant_id=current_user["tenant_id"],
        days=days
    )
    return {
        "logs": [AuditLogResponse.model_validate(log) for log in logs],
        "user_id": user_id,
        "days": days
    }


@router.get("/{log_id}", response_model=AuditLogResponse)
async def get_audit_log(
    log_id: str,
    current_user: TenantUserAuth,
    db: AsyncSession = Depends(get_db)
):
    """Get a single audit log by ID."""
    if current_user["role"] not in ["admin", "owner"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can view audit logs"
        )

    log = await audit_service.get_log_by_id(
        db, log_id, tenant_id=current_user["tenant_id"]
    )
    if not log:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Audit log not found"
        )

    return AuditLogResponse.model_validate(log)


# ============ Admin Platform Audit Logs ============

@router.get("/admin/all", response_model=AuditLogListResponse)
async def list_all_audit_logs(
    current_admin = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    tenant_id: Optional[str] = None,
    action: Optional[str] = None,
    resource_type: Optional[str] = None,
    status_filter: Optional[str] = Query(None, alias="status")
):
    """List all audit logs (super admin only)."""
    filters = AuditLogFilters(
        action=action,
        resource_type=resource_type,
        status=status_filter
    )

    logs, total = await audit_service.get_logs(
        db,
        tenant_id=tenant_id,  # Can filter by specific tenant or see all
        filters=filters,
        page=page,
        page_size=page_size
    )

    total_pages = (total + page_size - 1) // page_size

    return AuditLogListResponse(
        logs=[AuditLogResponse.model_validate(log) for log in logs],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages
    )


@router.get("/admin/stats", response_model=AuditStats)
async def get_platform_audit_stats(
    current_admin = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
    days: int = Query(30, ge=1, le=365)
):
    """Get platform-wide audit statistics (super admin only)."""
    stats = await audit_service.get_stats(db, tenant_id=None, days=days)

    return AuditStats(
        total_logs=stats["total_logs"],
        logs_today=stats["logs_today"],
        logs_this_week=stats["logs_this_week"],
        logs_this_month=stats["logs_this_month"],
        by_action=stats["by_action"],
        by_resource_type=stats["by_resource_type"],
        by_status=stats["by_status"],
        by_user=stats["by_user"],
        recent_failures=[AuditLogResponse.model_validate(f) for f in stats["recent_failures"]]
    )
