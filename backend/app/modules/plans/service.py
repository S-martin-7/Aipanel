"""
Plans Module - Service.

Business logic for plan management.
"""

from typing import Optional, List
from datetime import datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Plan, Tenant, DEFAULT_PLANS
from app.models.enums import TenantStatus
from app.utils.logger import get_logger

from .schemas import (
    CreatePlanRequest,
    UpdatePlanRequest,
    PlanResponse,
    PlanListResponse,
    PublicPlanResponse,
    AssignPlanRequest,
)

logger = get_logger(__name__)


class PlanService:
    """Service for plan management."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def seed_default_plans(self) -> int:
        """Seed default plans if they don't exist."""
        created = 0
        for plan_data in DEFAULT_PLANS:
            existing = await self.db.execute(
                select(Plan).where(Plan.code == plan_data["code"])
            )
            if not existing.scalar_one_or_none():
                plan = Plan(**plan_data)
                self.db.add(plan)
                created += 1

        if created > 0:
            await self.db.commit()
            logger.info(f"Seeded {created} default plans")

        return created

    async def get_plan(self, plan_code: str) -> Optional[PlanResponse]:
        """Get plan by code."""
        result = await self.db.execute(
            select(Plan).where(Plan.code == plan_code)
        )
        plan = result.scalar_one_or_none()
        return self._to_response(plan) if plan else None

    async def get_plan_by_id(self, plan_id: str) -> Optional[PlanResponse]:
        """Get plan by ID."""
        result = await self.db.execute(
            select(Plan).where(Plan.id == plan_id)
        )
        plan = result.scalar_one_or_none()
        return self._to_response(plan) if plan else None

    async def list_plans(
        self,
        include_inactive: bool = False,
        public_only: bool = False,
    ) -> PlanListResponse:
        """List all plans."""
        query = select(Plan)

        if not include_inactive:
            query = query.where(Plan.is_active == True)

        if public_only:
            query = query.where(Plan.is_public == True)

        query = query.order_by(Plan.display_order.asc())

        result = await self.db.execute(query)
        plans = result.scalars().all()

        return PlanListResponse(
            plans=[self._to_response(p) for p in plans],
            total=len(plans)
        )

    async def list_public_plans(self) -> List[PublicPlanResponse]:
        """List public plans for pricing page."""
        result = await self.db.execute(
            select(Plan)
            .where(Plan.is_active == True, Plan.is_public == True)
            .order_by(Plan.display_order.asc())
        )
        plans = result.scalars().all()

        return [
            PublicPlanResponse(
                code=p.code,
                name=p.name,
                description=p.description,
                price_monthly=p.price_monthly,
                price_yearly=p.price_yearly,
                currency=p.currency,
                is_trial=p.is_trial,
                trial_days=p.trial_days,
                max_tokens_monthly=p.max_tokens_monthly,
                max_agents=p.max_agents,
                max_documents=p.max_documents,
                max_users=p.max_users,
                features=p.features,
                badge_text=p.badge_text,
                badge_color=p.badge_color,
            )
            for p in plans
        ]

    async def create_plan(self, request: CreatePlanRequest) -> PlanResponse:
        """Create a new plan."""
        # Check code uniqueness
        existing = await self.db.execute(
            select(Plan).where(Plan.code == request.code)
        )
        if existing.scalar_one_or_none():
            raise ValueError(f"Plan with code '{request.code}' already exists")

        plan = Plan(
            code=request.code,
            name=request.name,
            description=request.description,
            plan_type=request.plan_type,
            price_monthly=request.price_monthly,
            price_yearly=request.price_yearly,
            requires_payment=request.requires_payment,
            is_trial=request.is_trial,
            trial_days=request.trial_days,
            max_tokens_monthly=request.max_tokens_monthly,
            max_agents=request.max_agents,
            max_documents=request.max_documents,
            max_users=request.max_users,
            max_storage_mb=request.max_storage_mb,
            features=request.features,
            is_public=request.is_public,
            display_order=request.display_order,
            badge_text=request.badge_text,
            badge_color=request.badge_color,
        )

        self.db.add(plan)
        await self.db.commit()
        await self.db.refresh(plan)

        logger.info(f"Plan created: {plan.code}")
        return self._to_response(plan)

    async def update_plan(
        self,
        plan_code: str,
        request: UpdatePlanRequest
    ) -> Optional[PlanResponse]:
        """Update a plan."""
        result = await self.db.execute(
            select(Plan).where(Plan.code == plan_code)
        )
        plan = result.scalar_one_or_none()
        if not plan:
            return None

        update_data = request.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            if hasattr(plan, field) and value is not None:
                setattr(plan, field, value)

        plan.updated_at = datetime.utcnow()
        await self.db.commit()

        logger.info(f"Plan updated: {plan_code}")
        return self._to_response(plan)

    async def delete_plan(self, plan_code: str) -> bool:
        """Deactivate a plan (soft delete)."""
        # Don't delete default plans
        if plan_code in ["demo", "starter", "professional", "enterprise"]:
            raise ValueError("Cannot delete default plans")

        result = await self.db.execute(
            select(Plan).where(Plan.code == plan_code)
        )
        plan = result.scalar_one_or_none()
        if not plan:
            return False

        plan.is_active = False
        plan.updated_at = datetime.utcnow()
        await self.db.commit()

        logger.info(f"Plan deactivated: {plan_code}")
        return True

    async def assign_plan_to_tenant(
        self,
        tenant_id: str,
        request: AssignPlanRequest
    ) -> Tenant:
        """Assign a plan to a tenant."""
        # Get plan
        plan_result = await self.db.execute(
            select(Plan).where(Plan.code == request.plan_code, Plan.is_active == True)
        )
        plan = plan_result.scalar_one_or_none()
        if not plan:
            raise ValueError(f"Plan '{request.plan_code}' not found or inactive")

        # Get tenant
        tenant_result = await self.db.execute(
            select(Tenant).where(Tenant.id == tenant_id)
        )
        tenant = tenant_result.scalar_one_or_none()
        if not tenant:
            raise ValueError("Tenant not found")

        # Update tenant with plan
        tenant.plan_code = plan.code
        tenant.monthly_token_limit = plan.max_tokens_monthly
        tenant.max_agents = plan.max_agents
        tenant.max_documents = plan.max_documents
        tenant.max_users = plan.max_users

        # Set payment requirement
        if request.payment_required is not None:
            tenant.payment_required = request.payment_required
        else:
            tenant.payment_required = plan.requires_payment

        # Handle trial
        if plan.is_trial and request.start_trial:
            tenant.trial_start = datetime.utcnow()
            tenant.trial_end = datetime.utcnow() + timedelta(days=plan.trial_days)
            tenant.is_paid = False
        elif not plan.requires_payment:
            # No payment required plans (internal, etc.)
            tenant.is_paid = True
            tenant.trial_start = None
            tenant.trial_end = None

        # Activate tenant if suspended due to expired trial
        if tenant.status == TenantStatus.SUSPENDED and tenant.is_paid:
            tenant.status = TenantStatus.ACTIVE
            tenant.suspended_at = None
            tenant.suspension_reason = None

        tenant.updated_at = datetime.utcnow()
        await self.db.commit()

        logger.info(f"Plan '{plan.code}' assigned to tenant {tenant_id}")
        return tenant

    def _to_response(self, plan: Plan) -> PlanResponse:
        """Convert plan model to response."""
        return PlanResponse(
            id=plan.id,
            code=plan.code,
            name=plan.name,
            description=plan.description,
            plan_type=plan.plan_type,
            price_monthly=plan.price_monthly,
            price_yearly=plan.price_yearly,
            currency=plan.currency,
            requires_payment=plan.requires_payment,
            is_trial=plan.is_trial,
            trial_days=plan.trial_days,
            max_tokens_monthly=plan.max_tokens_monthly,
            max_agents=plan.max_agents,
            max_documents=plan.max_documents,
            max_users=plan.max_users,
            max_storage_mb=plan.max_storage_mb,
            features=plan.features,
            is_active=plan.is_active,
            is_public=plan.is_public,
            display_order=plan.display_order,
            badge_text=plan.badge_text,
            badge_color=plan.badge_color,
            created_at=plan.created_at,
            updated_at=plan.updated_at,
        )
