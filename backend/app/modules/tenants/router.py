"""
Tenants Module - Router

CRUD operations for tenant management (admin only).
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import AdminUser

from .schemas import CreateTenantRequest, UpdateTenantRequest, TenantResponse, TenantListResponse
from .service import TenantService

router = APIRouter()


def get_tenant_service(db: AsyncSession = Depends(get_db)) -> TenantService:
    return TenantService(db)


@router.get("/", response_model=TenantListResponse)
async def list_tenants(
    current_user: AdminUser,
    service: TenantService = Depends(get_tenant_service),
):
    """List all tenants (admin only)."""
    return await service.list_tenants()


@router.post("/", response_model=TenantResponse, status_code=status.HTTP_201_CREATED)
async def create_tenant(
    request: CreateTenantRequest,
    current_user: AdminUser,
    service: TenantService = Depends(get_tenant_service),
):
    """Create a new tenant with admin user."""
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
    """Update tenant."""
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
    """Delete (cancel) tenant."""
    deleted = await service.delete_tenant(tenant_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Tenant not found")
