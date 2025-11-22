"""
Plans Module - Router.

API endpoints for plan management.
"""

from typing import List
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import AdminUser

from .service import PlanService
from .schemas import (
    CreatePlanRequest,
    UpdatePlanRequest,
    PlanResponse,
    PlanListResponse,
    PublicPlanResponse,
    AssignPlanRequest,
)

router = APIRouter()


def get_plan_service(db: AsyncSession = Depends(get_db)) -> PlanService:
    return PlanService(db)


# ============================================================
# Public Endpoints (No auth required)
# ============================================================

@router.get("/public", response_model=List[PublicPlanResponse])
async def list_public_plans(
    service: PlanService = Depends(get_plan_service),
):
    """
    List public plans for pricing page.

    No authentication required.
    """
    return await service.list_public_plans()


# ============================================================
# Admin Endpoints
# ============================================================

@router.get("/", response_model=PlanListResponse)
async def list_plans(
    current_user: AdminUser,
    service: PlanService = Depends(get_plan_service),
    include_inactive: bool = Query(False, description="Include inactive plans"),
    public_only: bool = Query(False, description="Show only public plans"),
):
    """
    List all plans.

    Admin only endpoint.
    """
    return await service.list_plans(
        include_inactive=include_inactive,
        public_only=public_only
    )


@router.post("/", response_model=PlanResponse, status_code=status.HTTP_201_CREATED)
async def create_plan(
    request: CreatePlanRequest,
    current_user: AdminUser,
    service: PlanService = Depends(get_plan_service),
):
    """
    Create a new plan.

    Admin only endpoint.
    """
    try:
        return await service.create_plan(request)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{plan_code}", response_model=PlanResponse)
async def get_plan(
    plan_code: str,
    current_user: AdminUser,
    service: PlanService = Depends(get_plan_service),
):
    """Get plan by code."""
    plan = await service.get_plan(plan_code)
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")
    return plan


@router.patch("/{plan_code}", response_model=PlanResponse)
async def update_plan(
    plan_code: str,
    request: UpdatePlanRequest,
    current_user: AdminUser,
    service: PlanService = Depends(get_plan_service),
):
    """Update a plan."""
    plan = await service.update_plan(plan_code, request)
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")
    return plan


@router.delete("/{plan_code}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_plan(
    plan_code: str,
    current_user: AdminUser,
    service: PlanService = Depends(get_plan_service),
):
    """Deactivate a plan (soft delete)."""
    try:
        deleted = await service.delete_plan(plan_code)
        if not deleted:
            raise HTTPException(status_code=404, detail="Plan not found")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/seed", response_model=dict)
async def seed_default_plans(
    current_user: AdminUser,
    service: PlanService = Depends(get_plan_service),
):
    """
    Seed default plans into database.

    Useful for initial setup.
    """
    created = await service.seed_default_plans()
    return {"message": f"Created {created} default plans"}


# ============================================================
# Tenant Plan Assignment
# ============================================================

@router.post("/assign/{tenant_id}", response_model=dict)
async def assign_plan_to_tenant(
    tenant_id: str,
    request: AssignPlanRequest,
    current_user: AdminUser,
    service: PlanService = Depends(get_plan_service),
):
    """
    Assign a plan to a tenant.

    This will update the tenant's limits and trial settings.
    """
    try:
        tenant = await service.assign_plan_to_tenant(tenant_id, request)
        return {
            "message": f"Plan '{request.plan_code}' assigned to tenant",
            "tenant_id": tenant.id,
            "plan_code": tenant.plan_code,
            "trial_end": tenant.trial_end.isoformat() if tenant.trial_end else None,
            "payment_required": tenant.payment_required,
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
