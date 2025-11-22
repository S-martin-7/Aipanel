"""
Tenants Module - Service

Complete tenant and tenant user management.
"""

import secrets
import hashlib
from typing import Optional, List
from datetime import datetime

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import Tenant, TenantUser, Agent, Document, TenantAPIKey, Payment
from app.models.enums import TenantStatus, TenantUserRole, TenantPlan, AIProviderType
from app.core.security import get_password_hash
from app.utils.logger import get_logger

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

logger = get_logger(__name__)


class TenantService:
    """Service for tenant and tenant user management."""

    def __init__(self, db: AsyncSession):
        self.db = db

    # ============================================================
    # Tenant CRUD
    # ============================================================

    async def create_tenant(self, request: CreateTenantRequest) -> TenantResponse:
        """Create tenant with owner user."""
        # Generate slug if not provided
        slug = request.slug or self._generate_slug(request.name)

        # Check slug uniqueness
        existing = await self.db.execute(
            select(Tenant).where(Tenant.slug == slug)
        )
        if existing.scalar_one_or_none():
            slug = f"{slug}-{secrets.token_hex(4)}"

        # Create tenant
        tenant = Tenant(
            name=request.name,
            slug=slug,
            email=request.admin_email,
            plan=TenantPlan[request.plan.upper()] if hasattr(request, 'plan') else TenantPlan.FREE,
            status=TenantStatus.ACTIVE,
            monthly_token_limit=self._get_plan_limits(request.plan.value)["tokens"],
            max_agents=self._get_plan_limits(request.plan.value)["agents"],
            max_documents=self._get_plan_limits(request.plan.value)["documents"],
            current_month_usage=0,
        )
        self.db.add(tenant)
        await self.db.flush()

        # Create owner user
        tenant_user = TenantUser(
            tenant_id=tenant.id,
            email=request.admin_email,
            name=request.admin_name,
            password_hash=get_password_hash(request.admin_password),
            role=TenantUserRole.OWNER,
            is_active=True,
        )
        self.db.add(tenant_user)
        await self.db.commit()

        logger.info(f"Tenant created: {tenant.id} ({tenant.name})")
        return await self._to_response(tenant)

    async def get_tenant(self, tenant_id: str) -> Optional[TenantResponse]:
        """Get tenant by ID."""
        result = await self.db.execute(select(Tenant).where(Tenant.id == tenant_id))
        tenant = result.scalar_one_or_none()
        return await self._to_response(tenant) if tenant else None

    async def list_tenants(
        self,
        status: Optional[str] = None,
        plan: Optional[str] = None,
        search: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> TenantListResponse:
        """List tenants with filters."""
        query = select(Tenant)

        if status:
            query = query.where(Tenant.status == TenantStatus(status))
        if plan:
            query = query.where(Tenant.plan == TenantPlan(plan))
        if search:
            query = query.where(
                Tenant.name.ilike(f"%{search}%") |
                Tenant.email.ilike(f"%{search}%") |
                Tenant.slug.ilike(f"%{search}%")
            )

        # Count total
        count_result = await self.db.execute(
            select(func.count(Tenant.id)).select_from(query.subquery())
        )
        total = count_result.scalar() or 0

        # Get paginated results
        query = query.order_by(Tenant.created_at.desc()).offset(offset).limit(limit)
        result = await self.db.execute(query)
        tenants = result.scalars().all()

        responses = [await self._to_response(t) for t in tenants]
        return TenantListResponse(tenants=responses, total=total)

    async def update_tenant(
        self,
        tenant_id: str,
        request: UpdateTenantRequest
    ) -> Optional[TenantResponse]:
        """Update tenant details."""
        result = await self.db.execute(select(Tenant).where(Tenant.id == tenant_id))
        tenant = result.scalar_one_or_none()
        if not tenant:
            return None

        update_data = request.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            if hasattr(tenant, field) and value is not None:
                if field == 'plan':
                    setattr(tenant, field, TenantPlan(value))
                else:
                    setattr(tenant, field, value)

        tenant.updated_at = datetime.utcnow()
        await self.db.commit()

        logger.info(f"Tenant updated: {tenant_id}")
        return await self._to_response(tenant)

    async def delete_tenant(self, tenant_id: str) -> bool:
        """Soft delete (cancel) tenant."""
        result = await self.db.execute(select(Tenant).where(Tenant.id == tenant_id))
        tenant = result.scalar_one_or_none()
        if not tenant:
            return False

        tenant.status = TenantStatus.CANCELLED
        tenant.updated_at = datetime.utcnow()
        await self.db.commit()

        logger.info(f"Tenant cancelled: {tenant_id}")
        return True

    # ============================================================
    # Tenant Status Management
    # ============================================================

    async def suspend_tenant(
        self,
        tenant_id: str,
        request: SuspendTenantRequest
    ) -> Optional[TenantResponse]:
        """Suspend a tenant account."""
        result = await self.db.execute(select(Tenant).where(Tenant.id == tenant_id))
        tenant = result.scalar_one_or_none()
        if not tenant:
            return None

        tenant.status = TenantStatus.SUSPENDED
        tenant.updated_at = datetime.utcnow()
        # Store suspension reason in metadata or separate field
        await self.db.commit()

        logger.warning(f"Tenant suspended: {tenant_id}, reason: {request.reason}")

        # TODO: Send notification to users if request.notify_users

        return await self._to_response(tenant)

    async def activate_tenant(self, tenant_id: str) -> Optional[TenantResponse]:
        """Activate/reactivate a tenant account."""
        result = await self.db.execute(select(Tenant).where(Tenant.id == tenant_id))
        tenant = result.scalar_one_or_none()
        if not tenant:
            return None

        if tenant.status == TenantStatus.CANCELLED:
            raise ValueError("Cannot activate a cancelled tenant")

        tenant.status = TenantStatus.ACTIVE
        tenant.updated_at = datetime.utcnow()
        await self.db.commit()

        logger.info(f"Tenant activated: {tenant_id}")
        return await self._to_response(tenant)

    async def get_account_overview(self, tenant_id: str) -> Optional[TenantAccountOverview]:
        """Get complete account overview for a tenant."""
        result = await self.db.execute(select(Tenant).where(Tenant.id == tenant_id))
        tenant = result.scalar_one_or_none()
        if not tenant:
            return None

        # Count resources
        agent_count = await self.db.execute(
            select(func.count(Agent.id)).where(Agent.tenant_id == tenant_id)
        )
        doc_count = await self.db.execute(
            select(func.count(Document.id)).where(Document.tenant_id == tenant_id)
        )
        user_count = await self.db.execute(
            select(func.count(TenantUser.id)).where(TenantUser.tenant_id == tenant_id)
        )

        # Check API keys
        api_keys = await self.db.execute(
            select(TenantAPIKey).where(
                TenantAPIKey.tenant_id == tenant_id,
                TenantAPIKey.is_active == True
            )
        )
        keys = api_keys.scalars().all()
        has_openai = any(k.provider_type == AIProviderType.OPENAI for k in keys)
        has_anthropic = any(k.provider_type == AIProviderType.ANTHROPIC for k in keys)

        # Get last payment
        last_payment = await self.db.execute(
            select(Payment)
            .where(Payment.tenant_id == tenant_id)
            .order_by(Payment.created_at.desc())
            .limit(1)
        )
        payment = last_payment.scalar_one_or_none()

        usage_pct = (tenant.current_month_usage / tenant.monthly_token_limit * 100) if tenant.monthly_token_limit > 0 else 0

        return TenantAccountOverview(
            id=tenant.id,
            name=tenant.name,
            slug=tenant.slug,
            status=tenant.status,
            plan=tenant.plan.value if tenant.plan else "free",
            monthly_token_limit=tenant.monthly_token_limit,
            current_month_usage=tenant.current_month_usage,
            usage_percentage=round(usage_pct, 2),
            max_agents=tenant.max_agents,
            current_agents=agent_count.scalar() or 0,
            max_documents=tenant.max_documents,
            current_documents=doc_count.scalar() or 0,
            max_users=self._get_plan_limits(tenant.plan.value if tenant.plan else "free")["users"],
            current_users=user_count.scalar() or 0,
            has_payment_method=payment is not None,
            last_payment_date=payment.created_at if payment else None,
            api_keys_configured=len(keys),
            has_openai=has_openai,
            has_anthropic=has_anthropic,
            created_at=tenant.created_at,
        )

    # ============================================================
    # API Key Rotation
    # ============================================================

    async def rotate_api_key(self, tenant_id: str) -> Optional[RotateAPIKeyResponse]:
        """Generate a new API key for tenant."""
        result = await self.db.execute(select(Tenant).where(Tenant.id == tenant_id))
        tenant = result.scalar_one_or_none()
        if not tenant:
            return None

        # Generate new key
        new_key = f"aip_{secrets.token_urlsafe(32)}"
        key_hash = hashlib.sha256(new_key.encode()).hexdigest()

        tenant.api_key_hash = key_hash
        tenant.updated_at = datetime.utcnow()
        await self.db.commit()

        logger.info(f"API key rotated for tenant: {tenant_id}")

        return RotateAPIKeyResponse(api_key=new_key)

    # ============================================================
    # Tenant Users CRUD
    # ============================================================

    async def create_tenant_user(
        self,
        tenant_id: str,
        request: CreateTenantUserRequest
    ) -> TenantUserResponse:
        """Create a user within a tenant."""
        # Check tenant exists
        tenant = await self.db.execute(select(Tenant).where(Tenant.id == tenant_id))
        if not tenant.scalar_one_or_none():
            raise ValueError("Tenant not found")

        # Check email uniqueness within tenant
        existing = await self.db.execute(
            select(TenantUser).where(
                TenantUser.tenant_id == tenant_id,
                TenantUser.email == request.email
            )
        )
        if existing.scalar_one_or_none():
            raise ValueError("Email already exists in this tenant")

        user = TenantUser(
            tenant_id=tenant_id,
            email=request.email,
            name=request.name,
            password_hash=get_password_hash(request.password),
            role=TenantUserRole(request.role.value),
            phone=request.phone,
            is_active=True,
        )
        self.db.add(user)
        await self.db.commit()
        await self.db.refresh(user)

        logger.info(f"Tenant user created: {user.id} in tenant {tenant_id}")
        return self._user_to_response(user)

    async def get_tenant_user(
        self,
        tenant_id: str,
        user_id: str
    ) -> Optional[TenantUserResponse]:
        """Get a tenant user by ID."""
        result = await self.db.execute(
            select(TenantUser).where(
                TenantUser.id == user_id,
                TenantUser.tenant_id == tenant_id
            )
        )
        user = result.scalar_one_or_none()
        return self._user_to_response(user) if user else None

    async def list_tenant_users(
        self,
        tenant_id: str,
        include_inactive: bool = False
    ) -> TenantUserListResponse:
        """List all users in a tenant."""
        query = select(TenantUser).where(TenantUser.tenant_id == tenant_id)

        if not include_inactive:
            query = query.where(TenantUser.is_active == True)

        query = query.order_by(TenantUser.created_at.desc())

        result = await self.db.execute(query)
        users = result.scalars().all()

        return TenantUserListResponse(
            users=[self._user_to_response(u) for u in users],
            total=len(users)
        )

    async def update_tenant_user(
        self,
        tenant_id: str,
        user_id: str,
        request: UpdateTenantUserRequest
    ) -> Optional[TenantUserResponse]:
        """Update a tenant user."""
        result = await self.db.execute(
            select(TenantUser).where(
                TenantUser.id == user_id,
                TenantUser.tenant_id == tenant_id
            )
        )
        user = result.scalar_one_or_none()
        if not user:
            return None

        update_data = request.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            if hasattr(user, field) and value is not None:
                if field == 'role':
                    setattr(user, field, TenantUserRole(value))
                else:
                    setattr(user, field, value)

        user.updated_at = datetime.utcnow()
        await self.db.commit()

        logger.info(f"Tenant user updated: {user_id}")
        return self._user_to_response(user)

    async def delete_tenant_user(self, tenant_id: str, user_id: str) -> bool:
        """Deactivate a tenant user (soft delete)."""
        result = await self.db.execute(
            select(TenantUser).where(
                TenantUser.id == user_id,
                TenantUser.tenant_id == tenant_id
            )
        )
        user = result.scalar_one_or_none()
        if not user:
            return False

        # Don't delete owners
        if user.role == TenantUserRole.OWNER:
            raise ValueError("Cannot delete tenant owner")

        user.is_active = False
        user.updated_at = datetime.utcnow()
        await self.db.commit()

        logger.info(f"Tenant user deactivated: {user_id}")
        return True

    # ============================================================
    # Helper Methods
    # ============================================================

    def _generate_slug(self, name: str) -> str:
        """Generate URL-friendly slug from name."""
        import re
        slug = name.lower()
        slug = re.sub(r'[^a-z0-9\s-]', '', slug)
        slug = re.sub(r'[\s_]+', '-', slug)
        slug = re.sub(r'-+', '-', slug)
        return slug.strip('-')[:50]

    def _get_plan_limits(self, plan: str) -> dict:
        """Get resource limits for a plan."""
        limits = {
            "free": {"tokens": 100000, "agents": 3, "documents": 50, "users": 2},
            "starter": {"tokens": 500000, "agents": 10, "documents": 200, "users": 5},
            "professional": {"tokens": 2000000, "agents": 50, "documents": 1000, "users": 20},
            "enterprise": {"tokens": 10000000, "agents": 200, "documents": 5000, "users": 100},
        }
        return limits.get(plan, limits["free"])

    async def _to_response(self, tenant: Tenant) -> TenantResponse:
        """Convert tenant model to response."""
        # Count users and agents
        user_count = await self.db.execute(
            select(func.count(TenantUser.id)).where(TenantUser.tenant_id == tenant.id)
        )
        agent_count = await self.db.execute(
            select(func.count(Agent.id)).where(Agent.tenant_id == tenant.id)
        )

        return TenantResponse(
            id=tenant.id,
            name=tenant.name,
            slug=tenant.slug,
            plan=tenant.plan.value if tenant.plan else "free",
            status=tenant.status,
            monthly_token_limit=tenant.monthly_token_limit,
            current_month_usage=tenant.current_month_usage,
            max_agents=tenant.max_agents,
            max_documents=tenant.max_documents,
            logo_url=tenant.logo_url,
            primary_color=tenant.primary_color,
            user_count=user_count.scalar() or 0,
            agent_count=agent_count.scalar() or 0,
            created_at=tenant.created_at,
            updated_at=tenant.updated_at,
        )

    def _user_to_response(self, user: TenantUser) -> TenantUserResponse:
        """Convert tenant user model to response."""
        return TenantUserResponse(
            id=user.id,
            tenant_id=user.tenant_id,
            email=user.email,
            name=user.name,
            role=user.role,
            is_active=user.is_active,
            phone=user.phone,
            avatar_url=user.avatar_url,
            created_at=user.created_at,
            updated_at=user.updated_at,
        )
