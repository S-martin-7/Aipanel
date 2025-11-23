"""
Tenant Admin Service - Level 2 (Tenant Admin).

Tenant-specific administration for:
- User management within tenant
- Activity monitoring for the tenant
- Agent and document management
- Usage and billing visibility
"""

from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from sqlalchemy import select, func, and_, desc, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import (
    Tenant, TenantUser, TenantUserRole,
    Agent, Conversation, Message,
    Document, AIExecutionLog, ExecutionStatus,
)
from app.utils.logger import get_logger

logger = get_logger(__name__)


class TenantAdminService:
    """
    Tenant-level administration service.

    Provides user management and monitoring for a specific tenant.
    Accessible by OWNER and ADMIN roles within the tenant.
    """

    def __init__(self, db: AsyncSession, tenant_id: str):
        self.db = db
        self.tenant_id = tenant_id

    # ============================================================
    # Tenant Dashboard
    # ============================================================

    async def get_dashboard_summary(self) -> Dict[str, Any]:
        """Get tenant dashboard summary."""
        now = datetime.utcnow()
        today = now.replace(hour=0, minute=0, second=0, microsecond=0)
        month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        hour_ago = now - timedelta(hours=1)

        # Users
        users = await self.db.execute(
            select(
                func.count(TenantUser.id).label('total'),
                func.count(TenantUser.id).filter(TenantUser.is_active == True).label('active'),
                func.count(TenantUser.id).filter(TenantUser.last_login >= today).label('online_today'),
                func.count(TenantUser.id).filter(TenantUser.last_login >= hour_ago).label('online_now'),
            )
            .where(TenantUser.tenant_id == self.tenant_id)
        )
        user_stats = users.one()

        # Agents
        agents = await self.db.execute(
            select(
                func.count(Agent.id).label('total'),
                func.count(Agent.id).filter(Agent.status == 'ACTIVE').label('active'),
            )
            .where(Agent.tenant_id == self.tenant_id)
        )
        agent_stats = agents.one()

        # Documents
        docs = await self.db.execute(
            select(func.count(Document.id))
            .join(Agent)
            .where(Agent.tenant_id == self.tenant_id)
        )
        doc_count = docs.scalar() or 0

        # Activity
        activity = await self.db.execute(
            select(
                func.count(AIExecutionLog.id).label('requests_today'),
                func.sum(AIExecutionLog.total_tokens).label('tokens_today'),
                func.count(AIExecutionLog.id).filter(
                    AIExecutionLog.status != ExecutionStatus.SUCCESS.value
                ).label('errors_today'),
            )
            .where(
                AIExecutionLog.tenant_id == self.tenant_id,
                AIExecutionLog.created_at >= today
            )
        )
        activity_stats = activity.one()

        # Month usage
        month_usage = await self.db.execute(
            select(
                func.count(AIExecutionLog.id).label('requests'),
                func.sum(AIExecutionLog.total_tokens).label('tokens'),
            )
            .where(
                AIExecutionLog.tenant_id == self.tenant_id,
                AIExecutionLog.created_at >= month_start
            )
        )
        month_stats = month_usage.one()

        return {
            "users": {
                "total": user_stats.total or 0,
                "active": user_stats.active or 0,
                "online_today": user_stats.online_today or 0,
                "online_now": user_stats.online_now or 0,
            },
            "agents": {
                "total": agent_stats.total or 0,
                "active": agent_stats.active or 0,
            },
            "documents": {
                "total": doc_count,
            },
            "today": {
                "requests": activity_stats.requests_today or 0,
                "tokens": activity_stats.tokens_today or 0,
                "errors": activity_stats.errors_today or 0,
            },
            "this_month": {
                "requests": month_stats.requests or 0,
                "tokens": month_stats.tokens or 0,
            },
            "timestamp": now.isoformat(),
        }

    # ============================================================
    # User Management
    # ============================================================

    async def list_users(
        self,
        include_inactive: bool = False,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[List[Dict], int]:
        """List all users in tenant."""
        query = select(TenantUser).where(TenantUser.tenant_id == self.tenant_id)

        if not include_inactive:
            query = query.where(TenantUser.is_active == True)

        # Count
        count_query = select(func.count(TenantUser.id)).where(
            TenantUser.tenant_id == self.tenant_id
        )
        if not include_inactive:
            count_query = count_query.where(TenantUser.is_active == True)
        count_result = await self.db.execute(count_query)
        total = count_result.scalar() or 0

        # Get users with activity
        query = query.order_by(desc(TenantUser.last_login)).offset(offset).limit(limit)
        result = await self.db.execute(query)
        users = result.scalars().all()

        user_list = []
        for user in users:
            # Get user's activity
            activity = await self.db.execute(
                select(
                    func.count(Conversation.id).label('conversations'),
                    func.count(Message.id).label('messages'),
                )
                .join(Message, Message.conversation_id == Conversation.id)
                .where(Conversation.user_id == str(user.id))
            )
            user_activity = activity.one()

            user_list.append({
                "id": str(user.id),
                "email": user.email,
                "name": user.name,
                "role": user.role.value if hasattr(user.role, 'value') else user.role,
                "is_active": user.is_active,
                "last_login": user.last_login.isoformat() if user.last_login else None,
                "created_at": user.created_at.isoformat() if user.created_at else None,
                "conversations": user_activity.conversations or 0,
                "messages": user_activity.messages or 0,
            })

        return user_list, total

    async def get_user_detail(self, user_id: str) -> Optional[Dict]:
        """Get detailed user information."""
        result = await self.db.execute(
            select(TenantUser).where(
                TenantUser.id == user_id,
                TenantUser.tenant_id == self.tenant_id
            )
        )
        user = result.scalar_one_or_none()
        if not user:
            return None

        now = datetime.utcnow()
        month_start = now.replace(day=1)

        # Get user's conversations
        convs = await self.db.execute(
            select(Conversation)
            .where(Conversation.user_id == str(user.id))
            .order_by(desc(Conversation.created_at))
            .limit(10)
        )
        recent_conversations = [
            {
                "id": str(c.id),
                "agent_id": str(c.agent_id) if c.agent_id else None,
                "title": c.title,
                "created_at": c.created_at.isoformat() if c.created_at else None,
            }
            for c in convs.scalars().all()
        ]

        # Get user's activity stats
        activity = await self.db.execute(
            select(
                func.count(Conversation.id).label('total_conversations'),
                func.count(Conversation.id).filter(
                    Conversation.created_at >= month_start
                ).label('conversations_this_month'),
            )
            .where(Conversation.user_id == str(user.id))
        )
        activity_stats = activity.one()

        return {
            "id": str(user.id),
            "email": user.email,
            "name": user.name,
            "role": user.role.value if hasattr(user.role, 'value') else user.role,
            "is_active": user.is_active,
            "last_login": user.last_login.isoformat() if user.last_login else None,
            "created_at": user.created_at.isoformat() if user.created_at else None,
            "total_conversations": activity_stats.total_conversations or 0,
            "conversations_this_month": activity_stats.conversations_this_month or 0,
            "recent_conversations": recent_conversations,
        }

    async def update_user_status(
        self,
        user_id: str,
        is_active: bool,
    ) -> bool:
        """Activate or deactivate a user."""
        result = await self.db.execute(
            update(TenantUser)
            .where(
                TenantUser.id == user_id,
                TenantUser.tenant_id == self.tenant_id
            )
            .values(is_active=is_active)
        )
        await self.db.commit()
        return result.rowcount > 0

    async def update_user_role(
        self,
        user_id: str,
        role: str,
    ) -> bool:
        """Update user's role within tenant."""
        try:
            role_enum = TenantUserRole(role)
        except ValueError:
            return False

        result = await self.db.execute(
            update(TenantUser)
            .where(
                TenantUser.id == user_id,
                TenantUser.tenant_id == self.tenant_id
            )
            .values(role=role_enum)
        )
        await self.db.commit()
        return result.rowcount > 0

    # ============================================================
    # Activity Monitoring
    # ============================================================

    async def get_online_users(self, minutes: int = 30) -> List[Dict]:
        """Get users currently online."""
        since = datetime.utcnow() - timedelta(minutes=minutes)

        result = await self.db.execute(
            select(TenantUser)
            .where(
                TenantUser.tenant_id == self.tenant_id,
                TenantUser.last_login >= since
            )
            .order_by(desc(TenantUser.last_login))
        )

        return [
            {
                "id": str(u.id),
                "email": u.email,
                "name": u.name,
                "role": u.role.value if hasattr(u.role, 'value') else u.role,
                "last_login": u.last_login.isoformat() if u.last_login else None,
            }
            for u in result.scalars().all()
        ]

    async def get_activity_timeline(
        self,
        hours: int = 24,
    ) -> List[Dict]:
        """Get hourly activity breakdown."""
        since = datetime.utcnow() - timedelta(hours=hours)

        result = await self.db.execute(
            select(
                func.date_trunc('hour', AIExecutionLog.created_at).label('hour'),
                func.count(AIExecutionLog.id).label('requests'),
                func.sum(AIExecutionLog.total_tokens).label('tokens'),
                func.count(AIExecutionLog.id).filter(
                    AIExecutionLog.status != ExecutionStatus.SUCCESS.value
                ).label('errors'),
            )
            .where(
                AIExecutionLog.tenant_id == self.tenant_id,
                AIExecutionLog.created_at >= since
            )
            .group_by(func.date_trunc('hour', AIExecutionLog.created_at))
            .order_by(func.date_trunc('hour', AIExecutionLog.created_at))
        )

        return [
            {
                "hour": row.hour.isoformat() if row.hour else None,
                "requests": row.requests,
                "tokens": row.tokens or 0,
                "errors": row.errors or 0,
            }
            for row in result.all()
        ]

    async def get_agent_activity(self, days: int = 7) -> List[Dict]:
        """Get activity breakdown by agent."""
        since = datetime.utcnow() - timedelta(days=days)

        result = await self.db.execute(
            select(
                Agent.id,
                Agent.name,
                Agent.status,
                func.count(AIExecutionLog.id).label('requests'),
                func.sum(AIExecutionLog.total_tokens).label('tokens'),
                func.avg(AIExecutionLog.latency_ms).label('avg_latency'),
                func.count(AIExecutionLog.id).filter(
                    AIExecutionLog.status != ExecutionStatus.SUCCESS.value
                ).label('errors'),
            )
            .join(AIExecutionLog, AIExecutionLog.agent_id == Agent.id)
            .where(
                Agent.tenant_id == self.tenant_id,
                AIExecutionLog.created_at >= since
            )
            .group_by(Agent.id, Agent.name, Agent.status)
            .order_by(desc(func.count(AIExecutionLog.id)))
        )

        return [
            {
                "agent_id": str(row.id),
                "agent_name": row.name,
                "status": row.status.value if hasattr(row.status, 'value') else row.status,
                "requests": row.requests,
                "tokens": row.tokens or 0,
                "avg_latency_ms": round(row.avg_latency or 0, 2),
                "errors": row.errors or 0,
            }
            for row in result.all()
        ]

    # ============================================================
    # Errors and Logs
    # ============================================================

    async def get_recent_errors(
        self,
        hours: int = 24,
        limit: int = 50,
    ) -> List[Dict]:
        """Get recent errors for this tenant."""
        since = datetime.utcnow() - timedelta(hours=hours)

        result = await self.db.execute(
            select(AIExecutionLog)
            .where(
                AIExecutionLog.tenant_id == self.tenant_id,
                AIExecutionLog.created_at >= since,
                AIExecutionLog.status != ExecutionStatus.SUCCESS.value
            )
            .order_by(desc(AIExecutionLog.created_at))
            .limit(limit)
        )

        return [
            {
                "id": str(log.id),
                "agent_id": str(log.agent_id) if log.agent_id else None,
                "request_type": log.request_type,
                "status": log.status,
                "error_code": log.error_code,
                "error_message": log.error_message,
                "latency_ms": log.latency_ms,
                "created_at": log.created_at.isoformat() if log.created_at else None,
            }
            for log in result.scalars().all()
        ]

    async def get_usage_by_user(self, days: int = 30) -> List[Dict]:
        """Get token usage breakdown by user."""
        since = datetime.utcnow() - timedelta(days=days)

        # This requires joining through conversations to get user
        result = await self.db.execute(
            select(
                Conversation.user_id,
                func.count(AIExecutionLog.id).label('requests'),
                func.sum(AIExecutionLog.total_tokens).label('tokens'),
            )
            .join(Conversation, AIExecutionLog.conversation_id == Conversation.id)
            .where(
                AIExecutionLog.tenant_id == self.tenant_id,
                AIExecutionLog.created_at >= since
            )
            .group_by(Conversation.user_id)
            .order_by(desc(func.sum(AIExecutionLog.total_tokens)))
        )

        usage_list = []
        for row in result.all():
            # Get user info
            user = await self.db.execute(
                select(TenantUser).where(TenantUser.id == row.user_id)
            )
            user_data = user.scalar_one_or_none()

            usage_list.append({
                "user_id": str(row.user_id) if row.user_id else None,
                "user_name": user_data.name if user_data else "Unknown",
                "user_email": user_data.email if user_data else None,
                "requests": row.requests,
                "tokens": row.tokens or 0,
            })

        return usage_list
