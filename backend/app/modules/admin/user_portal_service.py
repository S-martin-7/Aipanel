"""
User Portal Service - Level 3 (End User).

User-facing portal for:
- Viewing own conversations and messages
- Personal usage statistics
- Available agents and documents
- Account activity
"""

from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from sqlalchemy import select, func, and_, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import (
    TenantUser, Agent, Conversation, Message,
    Document, AIExecutionLog, ExecutionStatus,
)
from app.utils.logger import get_logger

logger = get_logger(__name__)


class UserPortalService:
    """
    End user portal service.

    Provides personal dashboard and activity for authenticated users.
    All queries are scoped to the user's tenant and own data.
    """

    def __init__(self, db: AsyncSession, user_id: str, tenant_id: str):
        self.db = db
        self.user_id = user_id
        self.tenant_id = tenant_id

    # ============================================================
    # User Dashboard
    # ============================================================

    async def get_dashboard(self) -> Dict[str, Any]:
        """Get user's personal dashboard."""
        now = datetime.utcnow()
        today = now.replace(hour=0, minute=0, second=0, microsecond=0)
        month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

        # Conversation stats
        conv_stats = await self.db.execute(
            select(
                func.count(Conversation.id).label('total'),
                func.count(Conversation.id).filter(
                    Conversation.created_at >= today
                ).label('today'),
                func.count(Conversation.id).filter(
                    Conversation.created_at >= month_start
                ).label('this_month'),
            )
            .where(Conversation.user_id == self.user_id)
        )
        conv = conv_stats.one()

        # Message stats
        msg_stats = await self.db.execute(
            select(func.count(Message.id))
            .join(Conversation)
            .where(Conversation.user_id == self.user_id)
        )
        total_messages = msg_stats.scalar() or 0

        # Available agents
        agents = await self.db.execute(
            select(func.count(Agent.id))
            .where(
                Agent.tenant_id == self.tenant_id,
                Agent.status == 'ACTIVE'
            )
        )
        available_agents = agents.scalar() or 0

        # Recent activity
        recent_conv = await self.db.execute(
            select(Conversation)
            .where(Conversation.user_id == self.user_id)
            .order_by(desc(Conversation.updated_at))
            .limit(5)
        )
        recent_conversations = [
            {
                "id": str(c.id),
                "title": c.title,
                "agent_id": str(c.agent_id) if c.agent_id else None,
                "updated_at": c.updated_at.isoformat() if c.updated_at else None,
            }
            for c in recent_conv.scalars().all()
        ]

        return {
            "conversations": {
                "total": conv.total or 0,
                "today": conv.today or 0,
                "this_month": conv.this_month or 0,
            },
            "messages": {
                "total": total_messages,
            },
            "available_agents": available_agents,
            "recent_conversations": recent_conversations,
            "timestamp": now.isoformat(),
        }

    # ============================================================
    # Conversations
    # ============================================================

    async def list_conversations(
        self,
        agent_id: Optional[str] = None,
        limit: int = 20,
        offset: int = 0,
    ) -> tuple[List[Dict], int]:
        """List user's conversations."""
        query = select(Conversation).where(Conversation.user_id == self.user_id)

        if agent_id:
            query = query.where(Conversation.agent_id == agent_id)

        # Count
        count_query = select(func.count(Conversation.id)).where(
            Conversation.user_id == self.user_id
        )
        if agent_id:
            count_query = count_query.where(Conversation.agent_id == agent_id)

        count_result = await self.db.execute(count_query)
        total = count_result.scalar() or 0

        # Get conversations
        query = query.order_by(desc(Conversation.updated_at)).offset(offset).limit(limit)
        result = await self.db.execute(query)
        conversations = result.scalars().all()

        conv_list = []
        for conv in conversations:
            # Get message count
            msg_count = await self.db.execute(
                select(func.count(Message.id))
                .where(Message.conversation_id == conv.id)
            )

            conv_list.append({
                "id": str(conv.id),
                "title": conv.title,
                "agent_id": str(conv.agent_id) if conv.agent_id else None,
                "status": conv.status.value if hasattr(conv.status, 'value') else conv.status,
                "message_count": msg_count.scalar() or 0,
                "created_at": conv.created_at.isoformat() if conv.created_at else None,
                "updated_at": conv.updated_at.isoformat() if conv.updated_at else None,
            })

        return conv_list, total

    async def get_conversation(self, conversation_id: str) -> Optional[Dict]:
        """Get a specific conversation with messages."""
        result = await self.db.execute(
            select(Conversation).where(
                Conversation.id == conversation_id,
                Conversation.user_id == self.user_id
            )
        )
        conv = result.scalar_one_or_none()

        if not conv:
            return None

        # Get messages
        messages_result = await self.db.execute(
            select(Message)
            .where(Message.conversation_id == conv.id)
            .order_by(Message.created_at)
        )
        messages = [
            {
                "id": str(m.id),
                "role": m.role.value if hasattr(m.role, 'value') else m.role,
                "content": m.content,
                "created_at": m.created_at.isoformat() if m.created_at else None,
            }
            for m in messages_result.scalars().all()
        ]

        return {
            "id": str(conv.id),
            "title": conv.title,
            "agent_id": str(conv.agent_id) if conv.agent_id else None,
            "status": conv.status.value if hasattr(conv.status, 'value') else conv.status,
            "messages": messages,
            "created_at": conv.created_at.isoformat() if conv.created_at else None,
            "updated_at": conv.updated_at.isoformat() if conv.updated_at else None,
        }

    # ============================================================
    # Available Agents
    # ============================================================

    async def list_available_agents(self) -> List[Dict]:
        """List agents available to the user."""
        result = await self.db.execute(
            select(Agent)
            .where(
                Agent.tenant_id == self.tenant_id,
                Agent.status == 'ACTIVE'
            )
            .order_by(Agent.name)
        )

        return [
            {
                "id": str(agent.id),
                "name": agent.name,
                "description": agent.description,
                "mode": agent.mode.value if hasattr(agent.mode, 'value') else agent.mode,
            }
            for agent in result.scalars().all()
        ]

    async def get_agent_info(self, agent_id: str) -> Optional[Dict]:
        """Get public info about an agent."""
        result = await self.db.execute(
            select(Agent).where(
                Agent.id == agent_id,
                Agent.tenant_id == self.tenant_id,
                Agent.status == 'ACTIVE'
            )
        )
        agent = result.scalar_one_or_none()

        if not agent:
            return None

        # Get document count
        doc_count = await self.db.execute(
            select(func.count(Document.id))
            .where(Document.agent_id == agent.id)
        )

        return {
            "id": str(agent.id),
            "name": agent.name,
            "description": agent.description,
            "mode": agent.mode.value if hasattr(agent.mode, 'value') else agent.mode,
            "documents_count": doc_count.scalar() or 0,
        }

    # ============================================================
    # Personal Usage
    # ============================================================

    async def get_usage_summary(self, days: int = 30) -> Dict[str, Any]:
        """Get user's personal usage summary."""
        since = datetime.utcnow() - timedelta(days=days)

        # Get usage from AI execution logs via conversations
        result = await self.db.execute(
            select(
                func.count(AIExecutionLog.id).label('requests'),
                func.sum(AIExecutionLog.total_tokens).label('tokens'),
                func.count(AIExecutionLog.id).filter(
                    AIExecutionLog.status != ExecutionStatus.SUCCESS.value
                ).label('errors'),
            )
            .join(Conversation, AIExecutionLog.conversation_id == Conversation.id)
            .where(
                Conversation.user_id == self.user_id,
                AIExecutionLog.created_at >= since
            )
        )
        stats = result.one()

        # Usage by agent
        by_agent = await self.db.execute(
            select(
                Agent.id,
                Agent.name,
                func.count(AIExecutionLog.id).label('requests'),
                func.sum(AIExecutionLog.total_tokens).label('tokens'),
            )
            .join(Conversation, AIExecutionLog.conversation_id == Conversation.id)
            .join(Agent, AIExecutionLog.agent_id == Agent.id)
            .where(
                Conversation.user_id == self.user_id,
                AIExecutionLog.created_at >= since
            )
            .group_by(Agent.id, Agent.name)
            .order_by(desc(func.sum(AIExecutionLog.total_tokens)))
        )

        usage_by_agent = [
            {
                "agent_id": str(row.id),
                "agent_name": row.name,
                "requests": row.requests,
                "tokens": row.tokens or 0,
            }
            for row in by_agent.all()
        ]

        return {
            "period_days": days,
            "total_requests": stats.requests or 0,
            "total_tokens": stats.tokens or 0,
            "total_errors": stats.errors or 0,
            "usage_by_agent": usage_by_agent,
        }

    async def get_activity_history(
        self,
        days: int = 7,
    ) -> List[Dict]:
        """Get user's daily activity history."""
        since = datetime.utcnow() - timedelta(days=days)

        result = await self.db.execute(
            select(
                func.date_trunc('day', Conversation.created_at).label('date'),
                func.count(Conversation.id).label('conversations'),
            )
            .where(
                Conversation.user_id == self.user_id,
                Conversation.created_at >= since
            )
            .group_by(func.date_trunc('day', Conversation.created_at))
            .order_by(func.date_trunc('day', Conversation.created_at))
        )

        return [
            {
                "date": row.date.isoformat() if row.date else None,
                "conversations": row.conversations,
            }
            for row in result.all()
        ]

    # ============================================================
    # Account Info
    # ============================================================

    async def get_account_info(self) -> Optional[Dict]:
        """Get user's account information."""
        result = await self.db.execute(
            select(TenantUser).where(TenantUser.id == self.user_id)
        )
        user = result.scalar_one_or_none()

        if not user:
            return None

        return {
            "id": str(user.id),
            "email": user.email,
            "name": user.name,
            "role": user.role.value if hasattr(user.role, 'value') else user.role,
            "created_at": user.created_at.isoformat() if user.created_at else None,
            "last_login": user.last_login.isoformat() if user.last_login else None,
        }
