"""
Tenants Module - Router

Complete CRUD and management operations for tenants and tenant users.
"""

from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import AdminUser, get_current_tenant_id

from .schemas import (
    CreateTenantRequest,
    UpdateTenantRequest,
    SuspendTenantRequest,
    TenantResponse,
    TenantListResponse,
    TenantAccountOverview,
    CreateTenantUserRequest,
    UpdateTenantUserRequest,
    TenantUserResponse,
    TenantUserListResponse,
    RotateAPIKeyResponse,
)
from .service import TenantService

router = APIRouter()


def get_tenant_service(db: AsyncSession = Depends(get_db)) -> TenantService:
    return TenantService(db)


# ============================================================
# Tenant CRUD (Admin Only)
# ============================================================

@router.get("/", response_model=TenantListResponse)
async def list_tenants(
    current_user: AdminUser,
    service: TenantService = Depends(get_tenant_service),
    status: Optional[str] = Query(None, description="Filter by status"),
    plan: Optional[str] = Query(None, description="Filter by plan"),
    search: Optional[str] = Query(None, description="Search by name/email/slug"),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
):
    """
    List all tenants with optional filters.

    Admin only endpoint.
    """
    return await service.list_tenants(
        status=status,
        plan=plan,
        search=search,
        limit=limit,
        offset=offset
    )


@router.post("/", response_model=TenantResponse, status_code=status.HTTP_201_CREATED)
async def create_tenant(
    request: CreateTenantRequest,
    current_user: AdminUser,
    service: TenantService = Depends(get_tenant_service),
):
    """
    Create a new tenant with owner user.

    Admin only endpoint.
    """
    return await service.create_tenant(request)


@router.get("/{tenant_id}", response_model=TenantResponse)
async def get_tenant(
    tenant_id: str,
    current_user: AdminUser,
    service: TenantService = Depends(get_tenant_service),
):
    """Get tenant by ID."""
    tenant = await service.get_tenant(tenant_id)
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")
    return tenant


@router.patch("/{tenant_id}", response_model=TenantResponse)
async def update_tenant(
    tenant_id: str,
    request: UpdateTenantRequest,
    current_user: AdminUser,
    service: TenantService = Depends(get_tenant_service),
):
    """Update tenant details."""
    tenant = await service.update_tenant(tenant_id, request)
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")
    return tenant


@router.delete("/{tenant_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_tenant(
    tenant_id: str,
    current_user: AdminUser,
    service: TenantService = Depends(get_tenant_service),
):
    """Cancel (soft delete) tenant."""
    deleted = await service.delete_tenant(tenant_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Tenant not found")


# ============================================================
# Tenant Status Management (Admin Only)
# ============================================================

@router.post("/{tenant_id}/suspend", response_model=TenantResponse)
async def suspend_tenant(
    tenant_id: str,
    request: SuspendTenantRequest,
    current_user: AdminUser,
    service: TenantService = Depends(get_tenant_service),
):
    """
    Suspend a tenant account.

    Suspended tenants cannot access the platform.
    """
    tenant = await service.suspend_tenant(tenant_id, request)
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")
    return tenant


@router.post("/{tenant_id}/activate", response_model=TenantResponse)
async def activate_tenant(
    tenant_id: str,
    current_user: AdminUser,
    service: TenantService = Depends(get_tenant_service),
):
    """
    Activate or reactivate a tenant account.

    Cannot activate cancelled tenants.
    """
    try:
        tenant = await service.activate_tenant(tenant_id)
        if not tenant:
            raise HTTPException(status_code=404, detail="Tenant not found")
        return tenant
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{tenant_id}/overview", response_model=TenantAccountOverview)
async def get_tenant_overview(
    tenant_id: str,
    current_user: AdminUser,
    service: TenantService = Depends(get_tenant_service),
):
    """
    Get complete account overview for a tenant.

    Includes usage, resources, billing status, and API keys info.
    """
    overview = await service.get_account_overview(tenant_id)
    if not overview:
        raise HTTPException(status_code=404, detail="Tenant not found")
    return overview


# ============================================================
# API Key Management (Admin Only)
# ============================================================

@router.post("/{tenant_id}/api-key/rotate", response_model=RotateAPIKeyResponse)
async def rotate_api_key(
    tenant_id: str,
    current_user: AdminUser,
    service: TenantService = Depends(get_tenant_service),
):
    """
    Generate a new API key for tenant.

    The old key is immediately invalidated.
    Save the new key securely - it won't be shown again.
    """
    result = await service.rotate_api_key(tenant_id)
    if not result:
        raise HTTPException(status_code=404, detail="Tenant not found")
    return result


# ============================================================
# Tenant Users CRUD (Admin Only)
# ============================================================

@router.get("/{tenant_id}/users", response_model=TenantUserListResponse)
async def list_tenant_users(
    tenant_id: str,
    current_user: AdminUser,
    service: TenantService = Depends(get_tenant_service),
    include_inactive: bool = Query(False, description="Include inactive users"),
):
    """List all users in a tenant."""
    return await service.list_tenant_users(tenant_id, include_inactive)


@router.post("/{tenant_id}/users", response_model=TenantUserResponse, status_code=status.HTTP_201_CREATED)
async def create_tenant_user(
    tenant_id: str,
    request: CreateTenantUserRequest,
    current_user: AdminUser,
    service: TenantService = Depends(get_tenant_service),
):
    """Create a new user within a tenant."""
    try:
        return await service.create_tenant_user(tenant_id, request)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{tenant_id}/users/{user_id}", response_model=TenantUserResponse)
async def get_tenant_user(
    tenant_id: str,
    user_id: str,
    current_user: AdminUser,
    service: TenantService = Depends(get_tenant_service),
):
    """Get a specific user in a tenant."""
    user = await service.get_tenant_user(tenant_id, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


@router.patch("/{tenant_id}/users/{user_id}", response_model=TenantUserResponse)
async def update_tenant_user(
    tenant_id: str,
    user_id: str,
    request: UpdateTenantUserRequest,
    current_user: AdminUser,
    service: TenantService = Depends(get_tenant_service),
):
    """Update a user in a tenant."""
    user = await service.update_tenant_user(tenant_id, user_id, request)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


@router.delete("/{tenant_id}/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_tenant_user(
    tenant_id: str,
    user_id: str,
    current_user: AdminUser,
    service: TenantService = Depends(get_tenant_service),
):
    """Deactivate (soft delete) a user in a tenant."""
    try:
        deleted = await service.delete_tenant_user(tenant_id, user_id)
        if not deleted:
            raise HTTPException(status_code=404, detail="User not found")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
