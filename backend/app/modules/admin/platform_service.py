"""
Platform Admin Service - Level 1 (Super Admin).

Server/platform-wide administration for:
- Multi-server deployments
- White-label installations
- Global monitoring and control
"""

from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from sqlalchemy import select, func, and_, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import (
    Tenant, TenantUser, TenantStatus,
    Agent, Conversation, Message,
    AIExecutionLog, ExecutionStatus,
)
from app.utils.logger import get_logger

logger = get_logger(__name__)


class PlatformAdminService:
    """
    Platform-level administration service.

    Provides monitoring and control across all tenants.
    Only accessible by SUPER_ADMIN users.
    """

    def __init__(self, db: AsyncSession):
        self.db = db

    # ============================================================
    # Platform Overview
    # ============================================================

    async def get_platform_health(self) -> Dict[str, Any]:
        """Get overall platform health status."""
        now = datetime.utcnow()
        hour_ago = now - timedelta(hours=1)

        # Error rate in last hour
        total_executions = await self.db.execute(
            select(func.count(AIExecutionLog.id))
            .where(AIExecutionLog.created_at >= hour_ago)
        )
        error_executions = await self.db.execute(
            select(func.count(AIExecutionLog.id))
            .where(
                AIExecutionLog.created_at >= hour_ago,
                AIExecutionLog.status != ExecutionStatus.SUCCESS.value
            )
        )
        total = total_executions.scalar() or 0
        errors = error_executions.scalar() or 0
        error_rate = (errors / total * 100) if total > 0 else 0

        # Avg latency
        latency = await self.db.execute(
            select(func.avg(AIExecutionLog.latency_ms))
            .where(
                AIExecutionLog.created_at >= hour_ago,
                AIExecutionLog.status == ExecutionStatus.SUCCESS.value
            )
        )
        avg_latency = latency.scalar() or 0

        # Active tenants (with activity in last hour)
        active_tenants = await self.db.execute(
            select(func.count(AIExecutionLog.tenant_id.distinct()))
            .where(AIExecutionLog.created_at >= hour_ago)
        )

        # Determine health status
        status = "healthy"
        if error_rate > 10:
            status = "degraded"
        if error_rate > 25:
            status = "critical"

        return {
            "status": status,
            "uptime_percent": 99.9,  # TODO: Track actual uptime
            "error_rate_percent": round(error_rate, 2),
            "avg_latency_ms": round(avg_latency, 2),
            "active_tenants": active_tenants.scalar() or 0,
            "requests_last_hour": total,
            "errors_last_hour": errors,
            "last_checked": now.isoformat(),
        }

    async def get_platform_overview(self) -> Dict[str, Any]:
        """Get platform-wide statistics."""
        now = datetime.utcnow()
        today = now.replace(hour=0, minute=0, second=0, microsecond=0)
        month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

        # Tenant stats
        tenant_result = await self.db.execute(
            select(
                func.count(Tenant.id).label('total'),
                func.count(Tenant.id).filter(Tenant.status == TenantStatus.ACTIVE).label('active'),
                func.count(Tenant.id).filter(Tenant.created_at >= month_start).label('new_this_month'),
            )
        )
        tenants = tenant_result.one()

        # User stats
        user_result = await self.db.execute(
            select(
                func.count(TenantUser.id).label('total'),
                func.count(TenantUser.id).filter(TenantUser.last_login >= today).label('active_today'),
            )
        )
        users = user_result.one()

        # Agent stats
        agent_result = await self.db.execute(
            select(func.count(Agent.id))
        )
        total_agents = agent_result.scalar() or 0

        # Conversation/Message stats
        conv_result = await self.db.execute(
            select(
                func.count(Conversation.id).label('total'),
                func.count(Conversation.id).filter(Conversation.created_at >= today).label('today'),
            )
        )
        convs = conv_result.one()

        msg_result = await self.db.execute(
            select(func.count(Message.id))
        )
        total_messages = msg_result.scalar() or 0

        # Token usage
        token_result = await self.db.execute(
            select(
                func.sum(AIExecutionLog.total_tokens).label('total'),
                func.sum(AIExecutionLog.total_tokens).filter(
                    AIExecutionLog.created_at >= month_start
                ).label('this_month'),
            )
        )
        tokens = token_result.one()

        return {
            "tenants": {
                "total": tenants.total or 0,
                "active": tenants.active or 0,
                "new_this_month": tenants.new_this_month or 0,
            },
            "users": {
                "total": users.total or 0,
                "active_today": users.active_today or 0,
            },
            "agents": {
                "total": total_agents,
            },
            "conversations": {
                "total": convs.total or 0,
                "today": convs.today or 0,
            },
            "messages": {
                "total": total_messages,
            },
            "tokens": {
                "total": tokens.total or 0,
                "this_month": tokens.this_month or 0,
            },
            "timestamp": now.isoformat(),
        }

    # ============================================================
    # Tenant Management
    # ============================================================

    async def list_tenants(
        self,
        status: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[List[Dict], int]:
        """List all tenants with activity metrics."""
        now = datetime.utcnow()
        week_ago = now - timedelta(days=7)

        query = select(Tenant)
        if status:
            query = query.where(Tenant.status == TenantStatus(status))

        # Get total count
        count_query = select(func.count(Tenant.id))
        if status:
            count_query = count_query.where(Tenant.status == TenantStatus(status))
        count_result = await self.db.execute(count_query)
        total = count_result.scalar() or 0

        # Get paginated results
        query = query.order_by(desc(Tenant.created_at)).offset(offset).limit(limit)
        result = await self.db.execute(query)
        tenants = result.scalars().all()

        tenant_list = []
        for tenant in tenants:
            # Get user count
            user_count = await self.db.execute(
                select(func.count(TenantUser.id))
                .where(TenantUser.tenant_id == tenant.id)
            )

            # Get agent count
            agent_count = await self.db.execute(
                select(func.count(Agent.id))
                .where(Agent.tenant_id == tenant.id)
            )

            # Get recent activity
            activity = await self.db.execute(
                select(func.count(AIExecutionLog.id))
                .where(
                    AIExecutionLog.tenant_id == tenant.id,
                    AIExecutionLog.created_at >= week_ago
                )
            )

            # Get token usage this month
            tokens = await self.db.execute(
                select(func.sum(AIExecutionLog.total_tokens))
                .where(
                    AIExecutionLog.tenant_id == tenant.id,
                    AIExecutionLog.created_at >= now.replace(day=1)
                )
            )

            tenant_list.append({
                "id": str(tenant.id),
                "name": tenant.name,
                "slug": tenant.slug,
                "status": tenant.status.value if hasattr(tenant.status, 'value') else tenant.status,
                "plan": getattr(tenant, 'plan', 'free'),
                "user_count": user_count.scalar() or 0,
                "agent_count": agent_count.scalar() or 0,
                "requests_last_week": activity.scalar() or 0,
                "tokens_this_month": tokens.scalar() or 0,
                "created_at": tenant.created_at.isoformat() if tenant.created_at else None,
            })

        return tenant_list, total

    async def get_tenant_detail(self, tenant_id: str) -> Optional[Dict]:
        """Get detailed tenant information."""
        result = await self.db.execute(
            select(Tenant).where(Tenant.id == tenant_id)
        )
        tenant = result.scalar_one_or_none()
        if not tenant:
            return None

        now = datetime.utcnow()
        month_start = now.replace(day=1)

        # Users
        users = await self.db.execute(
            select(TenantUser)
            .where(TenantUser.tenant_id == tenant_id)
            .order_by(desc(TenantUser.last_login))
        )
        user_list = [
            {
                "id": str(u.id),
                "email": u.email,
                "name": u.name,
                "role": u.role.value if hasattr(u.role, 'value') else u.role,
                "is_active": u.is_active,
                "last_login": u.last_login.isoformat() if u.last_login else None,
            }
            for u in users.scalars().all()
        ]

        # Agents
        agents = await self.db.execute(
            select(Agent).where(Agent.tenant_id == tenant_id)
        )
        agent_list = [
            {
                "id": str(a.id),
                "name": a.name,
                "status": a.status.value if hasattr(a.status, 'value') else a.status,
            }
            for a in agents.scalars().all()
        ]

        # Usage stats
        usage = await self.db.execute(
            select(
                func.count(AIExecutionLog.id).label('requests'),
                func.sum(AIExecutionLog.total_tokens).label('tokens'),
                func.count(AIExecutionLog.id).filter(
                    AIExecutionLog.status != ExecutionStatus.SUCCESS.value
                ).label('errors'),
            )
            .where(
                AIExecutionLog.tenant_id == tenant_id,
                AIExecutionLog.created_at >= month_start
            )
        )
        usage_stats = usage.one()

        return {
            "id": str(tenant.id),
            "name": tenant.name,
            "slug": tenant.slug,
            "status": tenant.status.value if hasattr(tenant.status, 'value') else tenant.status,
            "plan": getattr(tenant, 'plan', 'free'),
            "created_at": tenant.created_at.isoformat() if tenant.created_at else None,
            "users": user_list,
            "agents": agent_list,
            "usage_this_month": {
                "requests": usage_stats.requests or 0,
                "tokens": usage_stats.tokens or 0,
                "errors": usage_stats.errors or 0,
            },
        }

    # ============================================================
    # Active Users Monitoring
    # ============================================================

    async def get_active_users(
        self,
        hours: int = 1,
        tenant_id: Optional[str] = None,
    ) -> List[Dict]:
        """Get currently active users across platform or specific tenant."""
        since = datetime.utcnow() - timedelta(hours=hours)

        query = select(TenantUser).where(TenantUser.last_login >= since)
        if tenant_id:
            query = query.where(TenantUser.tenant_id == tenant_id)

        query = query.order_by(desc(TenantUser.last_login))
        result = await self.db.execute(query)

        return [
            {
                "id": str(u.id),
                "email": u.email,
                "name": u.name,
                "tenant_id": str(u.tenant_id),
                "role": u.role.value if hasattr(u.role, 'value') else u.role,
                "last_login": u.last_login.isoformat() if u.last_login else None,
                "is_active": u.is_active,
            }
            for u in result.scalars().all()
        ]

    # ============================================================
    # Error and Log Monitoring
    # ============================================================

    async def get_recent_errors(
        self,
        hours: int = 24,
        tenant_id: Optional[str] = None,
        limit: int = 100,
    ) -> List[Dict]:
        """Get recent errors across platform."""
        since = datetime.utcnow() - timedelta(hours=hours)

        query = select(AIExecutionLog).where(
            AIExecutionLog.created_at >= since,
            AIExecutionLog.status != ExecutionStatus.SUCCESS.value
        )
        if tenant_id:
            query = query.where(AIExecutionLog.tenant_id == tenant_id)

        query = query.order_by(desc(AIExecutionLog.created_at)).limit(limit)
        result = await self.db.execute(query)

        return [
            {
                "id": str(log.id),
                "tenant_id": str(log.tenant_id) if log.tenant_id else None,
                "agent_id": str(log.agent_id) if log.agent_id else None,
                "status": log.status,
                "error_code": log.error_code,
                "error_message": log.error_message,
                "latency_ms": log.latency_ms,
                "created_at": log.created_at.isoformat() if log.created_at else None,
            }
            for log in result.scalars().all()
        ]

    async def get_error_summary(
        self,
        hours: int = 24,
    ) -> Dict[str, Any]:
        """Get error summary/breakdown."""
        since = datetime.utcnow() - timedelta(hours=hours)

        # By error code
        by_code = await self.db.execute(
            select(
                AIExecutionLog.error_code,
                func.count(AIExecutionLog.id)
            )
            .where(
                AIExecutionLog.created_at >= since,
                AIExecutionLog.status != ExecutionStatus.SUCCESS.value
            )
            .group_by(AIExecutionLog.error_code)
            .order_by(desc(func.count(AIExecutionLog.id)))
        )

        # By tenant
        by_tenant = await self.db.execute(
            select(
                AIExecutionLog.tenant_id,
                Tenant.name,
                func.count(AIExecutionLog.id)
            )
            .join(Tenant, AIExecutionLog.tenant_id == Tenant.id)
            .where(
                AIExecutionLog.created_at >= since,
                AIExecutionLog.status != ExecutionStatus.SUCCESS.value
            )
            .group_by(AIExecutionLog.tenant_id, Tenant.name)
            .order_by(desc(func.count(AIExecutionLog.id)))
            .limit(10)
        )

        return {
            "period_hours": hours,
            "by_error_code": {
                (row[0] or "unknown"): row[1]
                for row in by_code.all()
            },
            "by_tenant": [
                {
                    "tenant_id": str(row[0]),
                    "tenant_name": row[1],
                    "error_count": row[2],
                }
                for row in by_tenant.all()
            ],
        }

    # ============================================================
    # Activity Monitoring
    # ============================================================

    async def get_activity_feed(
        self,
        hours: int = 1,
        limit: int = 50,
    ) -> List[Dict]:
        """Get recent activity across platform."""
        since = datetime.utcnow() - timedelta(hours=hours)

        result = await self.db.execute(
            select(AIExecutionLog, Tenant.name.label('tenant_name'))
            .join(Tenant, AIExecutionLog.tenant_id == Tenant.id)
            .where(AIExecutionLog.created_at >= since)
            .order_by(desc(AIExecutionLog.created_at))
            .limit(limit)
        )

        return [
            {
                "id": str(row.AIExecutionLog.id),
                "tenant_id": str(row.AIExecutionLog.tenant_id),
                "tenant_name": row.tenant_name,
                "agent_id": str(row.AIExecutionLog.agent_id) if row.AIExecutionLog.agent_id else None,
                "request_type": row.AIExecutionLog.request_type,
                "status": row.AIExecutionLog.status,
                "tokens": row.AIExecutionLog.total_tokens,
                "latency_ms": row.AIExecutionLog.latency_ms,
                "created_at": row.AIExecutionLog.created_at.isoformat(),
            }
            for row in result.all()
        ]

    async def get_tenant_activity_ranking(
        self,
        days: int = 7,
        limit: int = 20,
    ) -> List[Dict]:
        """Get tenants ranked by activity."""
        since = datetime.utcnow() - timedelta(days=days)

        result = await self.db.execute(
            select(
                AIExecutionLog.tenant_id,
                Tenant.name,
                func.count(AIExecutionLog.id).label('requests'),
                func.sum(AIExecutionLog.total_tokens).label('tokens'),
                func.count(AIExecutionLog.id).filter(
                    AIExecutionLog.status != ExecutionStatus.SUCCESS.value
                ).label('errors'),
            )
            .join(Tenant, AIExecutionLog.tenant_id == Tenant.id)
            .where(AIExecutionLog.created_at >= since)
            .group_by(AIExecutionLog.tenant_id, Tenant.name)
            .order_by(desc(func.count(AIExecutionLog.id)))
            .limit(limit)
        )

        return [
            {
                "tenant_id": str(row.tenant_id),
                "tenant_name": row.name,
                "requests": row.requests,
                "tokens": row.tokens or 0,
                "errors": row.errors or 0,
                "error_rate": round((row.errors / row.requests * 100) if row.requests > 0 else 0, 2),
            }
            for row in result.all()
        ]
