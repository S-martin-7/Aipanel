"""
Tenants Module - Service
"""

from typing import Optional
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Tenant, User, TenantUser
from app.models.enums import TenantStatus, UserRole
from app.core.security import get_password_hash
from app.utils.logger import get_logger

from .schemas import CreateTenantRequest, UpdateTenantRequest, TenantResponse, TenantListResponse

logger = get_logger(__name__)


class TenantService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_tenant(self, request: CreateTenantRequest) -> TenantResponse:
        """Create tenant with admin user."""
        # Create tenant
        tenant = Tenant(
            name=request.name,
            plan="free",
            status=TenantStatus.ACTIVE,
            tokens_used_this_period=0,
            current_period_start=datetime.utcnow(),
        )
        self.db.add(tenant)
        await self.db.flush()

        # Create admin user
        user = User(
            email=request.admin_email,
            name=request.admin_name,
            password_hash=get_password_hash(request.admin_password),
            role=UserRole.TENANT_ADMIN,
            is_active=True,
        )
        self.db.add(user)
        await self.db.flush()

        # Link user to tenant
        tenant_user = TenantUser(
            tenant_id=tenant.id,
            user_id=user.id,
            role="admin",
        )
        self.db.add(tenant_user)
        await self.db.commit()

        logger.info(f"Tenant created: {tenant.id}")
        return self._to_response(tenant)

    async def get_tenant(self, tenant_id: str) -> Optional[TenantResponse]:
        result = await self.db.execute(select(Tenant).where(Tenant.id == tenant_id))
        tenant = result.scalar_one_or_none()
        return self._to_response(tenant) if tenant else None

    async def list_tenants(self) -> TenantListResponse:
        result = await self.db.execute(select(Tenant).order_by(Tenant.created_at.desc()))
        tenants = result.scalars().all()
        return TenantListResponse(
            tenants=[self._to_response(t) for t in tenants],
            total=len(tenants),
        )

    async def update_tenant(self, tenant_id: str, request: UpdateTenantRequest) -> Optional[TenantResponse]:
        result = await self.db.execute(select(Tenant).where(Tenant.id == tenant_id))
        tenant = result.scalar_one_or_none()
        if not tenant:
            return None

        update_data = request.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            if hasattr(tenant, field):
                setattr(tenant, field, value)

        tenant.updated_at = datetime.utcnow()
        await self.db.commit()
        return self._to_response(tenant)

    async def delete_tenant(self, tenant_id: str) -> bool:
        result = await self.db.execute(select(Tenant).where(Tenant.id == tenant_id))
        tenant = result.scalar_one_or_none()
        if not tenant:
            return False

        tenant.status = TenantStatus.CANCELLED
        await self.db.commit()
        return True

    def _to_response(self, tenant: Tenant) -> TenantResponse:
        return TenantResponse(
            id=tenant.id,
            name=tenant.name,
            plan=tenant.plan or "free",
            status=tenant.status,
            tokens_used_this_period=tenant.tokens_used_this_period or 0,
            current_period_start=tenant.current_period_start,
            created_at=tenant.created_at,
            updated_at=tenant.updated_at,
        )
