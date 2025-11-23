"""
Base Service for Multi-Tenant Operations.

Provides automatic tenant isolation for all database queries.
All services that handle tenant-specific data should inherit from this.
"""

from typing import TypeVar, Generic, Optional, List, Type, Any
from uuid import UUID

from sqlalchemy import select, update, delete, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import DeclarativeBase

from app.utils.logger import get_logger

logger = get_logger(__name__)

T = TypeVar("T", bound=DeclarativeBase)


class TenantIsolationError(Exception):
    """Raised when a tenant isolation violation is detected."""
    pass


class TenantScopedService(Generic[T]):
    """
    Base service class that enforces tenant isolation.

    All queries are automatically scoped to the current tenant.
    This prevents accidental data leakage between tenants.

    Usage:
        class AgentService(TenantScopedService[Agent]):
            def __init__(self, db: AsyncSession, tenant_id: UUID):
                super().__init__(db, tenant_id, Agent)

            async def get_agent(self, agent_id: UUID) -> Optional[Agent]:
                return await self.get_by_id(agent_id)
    """

    def __init__(
        self,
        db: AsyncSession,
        tenant_id: UUID,
        model: Type[T],
    ):
        self.db = db
        self.tenant_id = tenant_id
        self.model = model
        self._validate_model()

    def _validate_model(self) -> None:
        """Validate that the model has a tenant_id column."""
        if not hasattr(self.model, "tenant_id"):
            raise TenantIsolationError(
                f"Model {self.model.__name__} does not have a tenant_id column. "
                "Cannot use TenantScopedService with this model."
            )

    def scope_query(self, query):
        """
        Add tenant isolation filter to a query.

        Always use this method when building custom queries.

        Args:
            query: SQLAlchemy select/update/delete query

        Returns:
            Query with tenant filter applied
        """
        return query.where(self.model.tenant_id == self.tenant_id)

    def _base_query(self):
        """Get base select query with tenant filter."""
        return select(self.model).where(self.model.tenant_id == self.tenant_id)

    async def get_by_id(self, id: UUID) -> Optional[T]:
        """
        Get a single record by ID within tenant scope.

        Args:
            id: Record UUID

        Returns:
            Record if found and belongs to tenant, None otherwise
        """
        query = self._base_query().where(self.model.id == id)
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def get_all(
        self,
        limit: int = 100,
        offset: int = 0,
        order_by: Optional[Any] = None,
    ) -> List[T]:
        """
        Get all records for the tenant with pagination.

        Args:
            limit: Maximum records to return
            offset: Number of records to skip
            order_by: Column to order by

        Returns:
            List of records
        """
        query = self._base_query()

        if order_by is not None:
            query = query.order_by(order_by)

        query = query.limit(limit).offset(offset)
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def count(self) -> int:
        """Count total records for tenant."""
        from sqlalchemy import func
        query = select(func.count()).select_from(self.model).where(
            self.model.tenant_id == self.tenant_id
        )
        result = await self.db.execute(query)
        return result.scalar() or 0

    async def exists(self, id: UUID) -> bool:
        """Check if a record exists within tenant scope."""
        from sqlalchemy import func
        query = select(func.count()).select_from(self.model).where(
            and_(
                self.model.tenant_id == self.tenant_id,
                self.model.id == id,
            )
        )
        result = await self.db.execute(query)
        return (result.scalar() or 0) > 0

    async def create(self, **kwargs) -> T:
        """
        Create a new record with automatic tenant assignment.

        The tenant_id is automatically set - do not pass it in kwargs.

        Args:
            **kwargs: Model field values

        Returns:
            Created record
        """
        # Force tenant_id to current tenant
        kwargs["tenant_id"] = self.tenant_id

        instance = self.model(**kwargs)
        self.db.add(instance)
        await self.db.commit()
        await self.db.refresh(instance)

        logger.info(
            f"Created {self.model.__name__}",
            extra={
                "tenant_id": str(self.tenant_id),
                "record_id": str(instance.id),
            }
        )

        return instance

    async def update_by_id(self, id: UUID, **kwargs) -> Optional[T]:
        """
        Update a record by ID within tenant scope.

        Args:
            id: Record UUID
            **kwargs: Fields to update

        Returns:
            Updated record if found, None otherwise
        """
        # Prevent changing tenant_id
        kwargs.pop("tenant_id", None)

        # First verify the record exists and belongs to tenant
        existing = await self.get_by_id(id)
        if not existing:
            return None

        # Update
        for key, value in kwargs.items():
            if hasattr(existing, key):
                setattr(existing, key, value)

        await self.db.commit()
        await self.db.refresh(existing)

        logger.info(
            f"Updated {self.model.__name__}",
            extra={
                "tenant_id": str(self.tenant_id),
                "record_id": str(id),
                "fields": list(kwargs.keys()),
            }
        )

        return existing

    async def delete_by_id(self, id: UUID) -> bool:
        """
        Delete a record by ID within tenant scope.

        Args:
            id: Record UUID

        Returns:
            True if deleted, False if not found
        """
        # Verify exists and belongs to tenant
        existing = await self.get_by_id(id)
        if not existing:
            return False

        await self.db.delete(existing)
        await self.db.commit()

        logger.info(
            f"Deleted {self.model.__name__}",
            extra={
                "tenant_id": str(self.tenant_id),
                "record_id": str(id),
            }
        )

        return True

    async def bulk_delete(self, ids: List[UUID]) -> int:
        """
        Delete multiple records within tenant scope.

        Args:
            ids: List of record UUIDs

        Returns:
            Number of records deleted
        """
        query = delete(self.model).where(
            and_(
                self.model.tenant_id == self.tenant_id,
                self.model.id.in_(ids),
            )
        )
        result = await self.db.execute(query)
        await self.db.commit()

        count = result.rowcount
        logger.info(
            f"Bulk deleted {self.model.__name__}",
            extra={
                "tenant_id": str(self.tenant_id),
                "count": count,
            }
        )

        return count

    def filter(self, *conditions):
        """
        Create a filtered query with tenant scope.

        Args:
            *conditions: SQLAlchemy filter conditions

        Returns:
            Scoped query with additional filters

        Example:
            query = service.filter(Agent.is_active == True)
            result = await db.execute(query)
        """
        query = self._base_query()
        for condition in conditions:
            query = query.where(condition)
        return query


class ReadOnlyTenantService(TenantScopedService[T]):
    """
    Read-only version of TenantScopedService.

    Use this for services that should never modify data.
    Create, update, and delete methods raise NotImplementedError.
    """

    async def create(self, **kwargs) -> T:
        raise NotImplementedError("This service is read-only")

    async def update_by_id(self, id: UUID, **kwargs) -> Optional[T]:
        raise NotImplementedError("This service is read-only")

    async def delete_by_id(self, id: UUID) -> bool:
        raise NotImplementedError("This service is read-only")

    async def bulk_delete(self, ids: List[UUID]) -> int:
        raise NotImplementedError("This service is read-only")
