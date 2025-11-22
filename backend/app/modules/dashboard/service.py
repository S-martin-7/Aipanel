"""
Dashboard service for analytics and statistics.
"""
from datetime import datetime, timedelta, date
from typing import Optional, List, Dict, Any
from sqlalchemy import select, func, and_, or_, cast, Date
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.agent import Agent
from app.models.document import Document
from app.models.conversation import Conversation, Message
from app.models.usage import UsageRecord, Subscription
from app.models.tenant import Tenant, TenantUser
from app.modules.dashboard.schemas import (
    OverviewStats, TimeSeriesPoint, ConversationsTimeSeries,
    MessagesTimeSeries, TokensTimeSeries, AgentStats,
    UsageByModel, UsageBreakdown, TopAgent, TopDocument,
    RealtimeStats, PeriodComparison, PlatformStats
)


class DashboardService:
    """Service for dashboard analytics."""

    async def get_overview_stats(
        self,
        db: AsyncSession,
        tenant_id: str
    ) -> OverviewStats:
        """Get main dashboard overview statistics."""
        now = datetime.utcnow()
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        week_start = today_start - timedelta(days=today_start.weekday())
        month_start = today_start.replace(day=1)
        prev_month_start = (month_start - timedelta(days=1)).replace(day=1)

        # Conversations
        conv_stats = await db.execute(
            select(
                func.count(Conversation.id).label('total'),
                func.sum(func.cast(Conversation.created_at >= today_start, Integer)).label('today'),
                func.sum(func.cast(Conversation.created_at >= week_start, Integer)).label('week'),
                func.sum(func.cast(Conversation.created_at >= month_start, Integer)).label('month'),
                func.sum(func.cast(
                    and_(
                        Conversation.created_at >= prev_month_start,
                        Conversation.created_at < month_start
                    ), Integer
                )).label('prev_month')
            ).where(Conversation.tenant_id == tenant_id)
        )
        conv = conv_stats.first()

        # Messages
        msg_stats = await db.execute(
            select(
                func.count(Message.id).label('total'),
                func.sum(func.cast(Message.created_at >= today_start, Integer)).label('today')
            )
            .join(Conversation)
            .where(Conversation.tenant_id == tenant_id)
        )
        msg = msg_stats.first()

        # Average messages per conversation
        avg_msgs = (msg.total / conv.total) if conv.total > 0 else 0

        # Agents
        agent_stats = await db.execute(
            select(
                func.count(Agent.id).label('total'),
                func.sum(func.cast(Agent.is_active == True, Integer)).label('active')
            ).where(Agent.tenant_id == tenant_id)
        )
        agents = agent_stats.first()

        # Documents
        doc_stats = await db.execute(
            select(
                func.count(Document.id).label('total'),
                func.coalesce(func.sum(Document.chunk_count), 0).label('chunks')
            )
            .join(Agent)
            .where(Agent.tenant_id == tenant_id)
        )
        docs = doc_stats.first()

        # Users
        user_stats = await db.execute(
            select(
                func.count(TenantUser.id).label('total'),
                func.sum(func.cast(TenantUser.last_login >= today_start, Integer)).label('active_today')
            ).where(TenantUser.tenant_id == tenant_id)
        )
        users = user_stats.first()

        # Token usage
        usage_stats = await db.execute(
            select(
                func.coalesce(func.sum(UsageRecord.total_tokens), 0).label('total'),
                func.coalesce(func.sum(
                    func.cast(UsageRecord.created_at >= month_start, Integer) * UsageRecord.total_tokens
                ), 0).label('this_month'),
                func.coalesce(func.sum(
                    func.cast(UsageRecord.created_at >= month_start, Integer) * UsageRecord.cost
                ), 0).label('cost_month')
            ).where(UsageRecord.tenant_id == tenant_id)
        )
        usage = usage_stats.first()

        # Calculate change percent
        current_month = conv.month or 0
        prev_month = conv.prev_month or 0
        change_percent = 0.0
        if prev_month > 0:
            change_percent = round((current_month - prev_month) / prev_month * 100, 2)

        return OverviewStats(
            total_conversations=conv.total or 0,
            conversations_today=conv.today or 0,
            conversations_this_week=conv.week or 0,
            conversations_this_month=current_month,
            conversations_change_percent=change_percent,
            total_messages=msg.total or 0,
            messages_today=msg.today or 0,
            avg_messages_per_conversation=round(avg_msgs, 2),
            total_agents=agents.total or 0,
            active_agents=agents.active or 0,
            total_documents=docs.total or 0,
            total_document_chunks=docs.chunks or 0,
            total_users=users.total or 0,
            active_users_today=users.active_today or 0,
            total_tokens_used=usage.total or 0,
            tokens_this_month=usage.this_month or 0,
            estimated_cost_this_month=float(usage.cost_month or 0),
            currency="CLP"
        )

    async def get_conversations_time_series(
        self,
        db: AsyncSession,
        tenant_id: str,
        days: int = 30
    ) -> ConversationsTimeSeries:
        """Get conversations over time."""
        end_date = datetime.utcnow().date()
        start_date = end_date - timedelta(days=days)

        result = await db.execute(
            select(
                cast(Conversation.created_at, Date).label('date'),
                func.count(Conversation.id).label('count')
            )
            .where(
                and_(
                    Conversation.tenant_id == tenant_id,
                    Conversation.created_at >= start_date
                )
            )
            .group_by(cast(Conversation.created_at, Date))
            .order_by(cast(Conversation.created_at, Date))
        )
        data = result.all()

        # Fill in missing dates
        date_map = {row.date: row.count for row in data}
        points = []
        current = start_date
        total = 0

        while current <= end_date:
            value = date_map.get(current, 0)
            points.append(TimeSeriesPoint(date=current, value=value))
            total += value
            current += timedelta(days=1)

        return ConversationsTimeSeries(
            period="day",
            conversations=points,
            total=total,
            average_per_day=round(total / days, 2)
        )

    async def get_messages_time_series(
        self,
        db: AsyncSession,
        tenant_id: str,
        days: int = 30
    ) -> MessagesTimeSeries:
        """Get messages over time."""
        end_date = datetime.utcnow().date()
        start_date = end_date - timedelta(days=days)

        result = await db.execute(
            select(
                cast(Message.created_at, Date).label('date'),
                func.count(Message.id).label('count')
            )
            .join(Conversation)
            .where(
                and_(
                    Conversation.tenant_id == tenant_id,
                    Message.created_at >= start_date
                )
            )
            .group_by(cast(Message.created_at, Date))
            .order_by(cast(Message.created_at, Date))
        )
        data = result.all()

        date_map = {row.date: row.count for row in data}
        points = []
        current = start_date
        total = 0

        while current <= end_date:
            value = date_map.get(current, 0)
            points.append(TimeSeriesPoint(date=current, value=value))
            total += value
            current += timedelta(days=1)

        return MessagesTimeSeries(
            period="day",
            messages=points,
            total=total,
            average_per_day=round(total / days, 2)
        )

    async def get_tokens_time_series(
        self,
        db: AsyncSession,
        tenant_id: str,
        days: int = 30
    ) -> TokensTimeSeries:
        """Get token usage over time."""
        end_date = datetime.utcnow().date()
        start_date = end_date - timedelta(days=days)

        result = await db.execute(
            select(
                cast(UsageRecord.created_at, Date).label('date'),
                func.sum(UsageRecord.total_tokens).label('tokens'),
                func.sum(UsageRecord.cost).label('cost')
            )
            .where(
                and_(
                    UsageRecord.tenant_id == tenant_id,
                    UsageRecord.created_at >= start_date
                )
            )
            .group_by(cast(UsageRecord.created_at, Date))
            .order_by(cast(UsageRecord.created_at, Date))
        )
        data = result.all()

        date_map = {row.date: (row.tokens or 0, row.cost or 0) for row in data}
        points = []
        current = start_date
        total_tokens = 0
        total_cost = 0.0

        while current <= end_date:
            tokens, cost = date_map.get(current, (0, 0))
            points.append(TimeSeriesPoint(date=current, value=tokens))
            total_tokens += tokens
            total_cost += float(cost)
            current += timedelta(days=1)

        return TokensTimeSeries(
            period="day",
            tokens=points,
            total=total_tokens,
            cost=round(total_cost, 2),
            currency="CLP"
        )

    async def get_agent_stats(
        self,
        db: AsyncSession,
        tenant_id: str,
        days: int = 30
    ) -> List[AgentStats]:
        """Get statistics for each agent."""
        start_date = datetime.utcnow() - timedelta(days=days)

        result = await db.execute(
            select(
                Agent.id,
                Agent.name,
                func.count(Conversation.id.distinct()).label('conversations'),
                func.count(Message.id).label('messages'),
                func.coalesce(func.sum(UsageRecord.total_tokens), 0).label('tokens'),
                func.coalesce(func.sum(UsageRecord.cost), 0).label('cost')
            )
            .outerjoin(Conversation, Conversation.agent_id == Agent.id)
            .outerjoin(Message, Message.conversation_id == Conversation.id)
            .outerjoin(UsageRecord, UsageRecord.agent_id == Agent.id)
            .where(
                and_(
                    Agent.tenant_id == tenant_id,
                    or_(
                        Conversation.created_at >= start_date,
                        Conversation.id == None
                    )
                )
            )
            .group_by(Agent.id, Agent.name)
        )
        data = result.all()

        return [
            AgentStats(
                agent_id=row.id,
                agent_name=row.name,
                total_conversations=row.conversations or 0,
                total_messages=row.messages or 0,
                avg_response_time_ms=None,  # TODO: Track response times
                total_tokens=row.tokens or 0,
                total_cost=float(row.cost or 0),
                satisfaction_score=None
            )
            for row in data
        ]

    async def get_usage_breakdown(
        self,
        db: AsyncSession,
        tenant_id: str,
        days: int = 30
    ) -> UsageBreakdown:
        """Get detailed usage breakdown."""
        start_date = datetime.utcnow() - timedelta(days=days)

        # By model
        by_model_result = await db.execute(
            select(
                UsageRecord.model,
                UsageRecord.provider,
                func.sum(UsageRecord.input_tokens).label('input'),
                func.sum(UsageRecord.output_tokens).label('output'),
                func.sum(UsageRecord.total_tokens).label('total'),
                func.sum(UsageRecord.cost).label('cost')
            )
            .where(
                and_(
                    UsageRecord.tenant_id == tenant_id,
                    UsageRecord.created_at >= start_date
                )
            )
            .group_by(UsageRecord.model, UsageRecord.provider)
        )
        by_model_data = by_model_result.all()

        # Calculate totals
        total_input = sum(r.input or 0 for r in by_model_data)
        total_output = sum(r.output or 0 for r in by_model_data)
        total_tokens = sum(r.total or 0 for r in by_model_data)
        total_cost = sum(float(r.cost or 0) for r in by_model_data)

        by_model = [
            UsageByModel(
                model=row.model,
                provider=row.provider or "unknown",
                input_tokens=row.input or 0,
                output_tokens=row.output or 0,
                total_tokens=row.total or 0,
                cost=float(row.cost or 0),
                percentage=round((row.total or 0) / total_tokens * 100, 2) if total_tokens > 0 else 0
            )
            for row in by_model_data
        ]

        # By agent
        by_agent_result = await db.execute(
            select(
                Agent.id,
                Agent.name,
                func.sum(UsageRecord.total_tokens).label('tokens'),
                func.sum(UsageRecord.cost).label('cost')
            )
            .join(Agent, UsageRecord.agent_id == Agent.id)
            .where(
                and_(
                    UsageRecord.tenant_id == tenant_id,
                    UsageRecord.created_at >= start_date
                )
            )
            .group_by(Agent.id, Agent.name)
        )
        by_agent_data = by_agent_result.all()

        by_agent = [
            {
                "agent_id": row.id,
                "agent_name": row.name,
                "tokens": row.tokens or 0,
                "cost": float(row.cost or 0),
                "percentage": round((row.tokens or 0) / total_tokens * 100, 2) if total_tokens > 0 else 0
            }
            for row in by_agent_data
        ]

        return UsageBreakdown(
            by_model=by_model,
            by_agent=by_agent,
            total_input_tokens=total_input,
            total_output_tokens=total_output,
            total_tokens=total_tokens,
            total_cost=round(total_cost, 2),
            currency="CLP"
        )

    async def get_top_items(
        self,
        db: AsyncSession,
        tenant_id: str,
        limit: int = 5
    ) -> Dict[str, Any]:
        """Get top performing items."""
        # Top agents by conversations
        top_conv_result = await db.execute(
            select(
                Agent.id,
                Agent.name,
                func.count(Conversation.id).label('count')
            )
            .join(Conversation, Conversation.agent_id == Agent.id)
            .where(Agent.tenant_id == tenant_id)
            .group_by(Agent.id, Agent.name)
            .order_by(func.count(Conversation.id).desc())
            .limit(limit)
        )
        top_by_conv = [
            TopAgent(
                agent_id=r.id,
                agent_name=r.name,
                metric_value=r.count,
                metric_name="conversations"
            )
            for r in top_conv_result.all()
        ]

        # Top agents by messages
        top_msg_result = await db.execute(
            select(
                Agent.id,
                Agent.name,
                func.count(Message.id).label('count')
            )
            .join(Conversation, Conversation.agent_id == Agent.id)
            .join(Message, Message.conversation_id == Conversation.id)
            .where(Agent.tenant_id == tenant_id)
            .group_by(Agent.id, Agent.name)
            .order_by(func.count(Message.id).desc())
            .limit(limit)
        )
        top_by_msg = [
            TopAgent(
                agent_id=r.id,
                agent_name=r.name,
                metric_value=r.count,
                metric_name="messages"
            )
            for r in top_msg_result.all()
        ]

        # Top documents by query count
        top_docs_result = await db.execute(
            select(
                Document.id,
                Document.original_filename,
                Document.query_count,
                Agent.id.label('agent_id'),
                Agent.name.label('agent_name')
            )
            .join(Agent, Document.agent_id == Agent.id)
            .where(Agent.tenant_id == tenant_id)
            .order_by(Document.query_count.desc())
            .limit(limit)
        )
        top_docs = [
            TopDocument(
                document_id=r.id,
                document_name=r.original_filename,
                query_count=r.query_count or 0,
                agent_id=r.agent_id,
                agent_name=r.agent_name
            )
            for r in top_docs_result.all()
        ]

        return {
            "top_agents_by_conversations": top_by_conv,
            "top_agents_by_messages": top_by_msg,
            "top_documents_by_queries": top_docs
        }

    async def get_realtime_stats(
        self,
        db: AsyncSession,
        tenant_id: str
    ) -> RealtimeStats:
        """Get real-time activity statistics."""
        now = datetime.utcnow()
        hour_ago = now - timedelta(hours=1)
        five_min_ago = now - timedelta(minutes=5)

        # Active conversations (last hour)
        active_conv = await db.execute(
            select(func.count(Conversation.id.distinct()))
            .join(Message)
            .where(
                and_(
                    Conversation.tenant_id == tenant_id,
                    Message.created_at >= hour_ago
                )
            )
        )
        active_conversations = active_conv.scalar() or 0

        # Messages last hour and 5 min
        msg_stats = await db.execute(
            select(
                func.sum(func.cast(Message.created_at >= hour_ago, Integer)).label('hour'),
                func.sum(func.cast(Message.created_at >= five_min_ago, Integer)).label('five_min')
            )
            .join(Conversation)
            .where(Conversation.tenant_id == tenant_id)
        )
        msgs = msg_stats.first()

        # Active users (logged in last hour)
        active_users = await db.execute(
            select(func.count(TenantUser.id))
            .where(
                and_(
                    TenantUser.tenant_id == tenant_id,
                    TenantUser.last_login >= hour_ago
                )
            )
        )
        active_user_count = active_users.scalar() or 0

        return RealtimeStats(
            active_conversations=active_conversations,
            messages_last_hour=msgs.hour or 0,
            messages_last_5_min=msgs.five_min or 0,
            active_users=active_user_count,
            avg_response_time_ms=0.0,  # TODO: Track response times
            error_rate_percent=0.0  # TODO: Track errors
        )

    async def get_period_comparison(
        self,
        db: AsyncSession,
        tenant_id: str,
        period: str = "month"
    ) -> Dict[str, Any]:
        """Compare current period with previous period."""
        now = datetime.utcnow()

        if period == "week":
            current_start = now - timedelta(days=now.weekday())
            period_length = timedelta(days=7)
        elif period == "month":
            current_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            period_length = timedelta(days=30)
        else:  # day
            current_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
            period_length = timedelta(days=1)

        current_end = now
        previous_start = current_start - period_length
        previous_end = current_start

        # Get metrics for both periods
        async def get_period_metrics(start: datetime, end: datetime):
            conv = await db.execute(
                select(func.count(Conversation.id))
                .where(
                    and_(
                        Conversation.tenant_id == tenant_id,
                        Conversation.created_at >= start,
                        Conversation.created_at < end
                    )
                )
            )
            msg = await db.execute(
                select(func.count(Message.id))
                .join(Conversation)
                .where(
                    and_(
                        Conversation.tenant_id == tenant_id,
                        Message.created_at >= start,
                        Message.created_at < end
                    )
                )
            )
            tokens = await db.execute(
                select(func.coalesce(func.sum(UsageRecord.total_tokens), 0))
                .where(
                    and_(
                        UsageRecord.tenant_id == tenant_id,
                        UsageRecord.created_at >= start,
                        UsageRecord.created_at < end
                    )
                )
            )
            return {
                "conversations": conv.scalar() or 0,
                "messages": msg.scalar() or 0,
                "tokens": tokens.scalar() or 0
            }

        current = await get_period_metrics(current_start, current_end)
        previous = await get_period_metrics(previous_start, previous_end)

        comparisons = []
        for metric in ["conversations", "messages", "tokens"]:
            curr_val = current[metric]
            prev_val = previous[metric]
            change = curr_val - prev_val
            change_pct = (change / prev_val * 100) if prev_val > 0 else 0

            trend = "stable"
            if change_pct > 5:
                trend = "up"
            elif change_pct < -5:
                trend = "down"

            comparisons.append(PeriodComparison(
                metric=metric,
                current_value=curr_val,
                previous_value=prev_val,
                change_value=change,
                change_percent=round(change_pct, 2),
                trend=trend
            ))

        return {
            "period": period,
            "current_start": current_start.date(),
            "current_end": current_end.date(),
            "previous_start": previous_start.date(),
            "previous_end": previous_end.date(),
            "comparisons": comparisons
        }

    # ============ Admin Platform Stats ============

    async def get_platform_stats(self, db: AsyncSession) -> PlatformStats:
        """Get platform-wide statistics (super admin only)."""
        now = datetime.utcnow()
        month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        prev_month_start = (month_start - timedelta(days=1)).replace(day=1)

        # Tenant counts
        tenant_stats = await db.execute(
            select(
                func.count(Tenant.id).label('total'),
                func.sum(func.cast(Tenant.is_active == True, Integer)).label('active')
            )
        )
        tenants = tenant_stats.first()

        # User count
        user_count = await db.execute(select(func.count(TenantUser.id)))
        total_users = user_count.scalar() or 0

        # Agent count
        agent_count = await db.execute(select(func.count(Agent.id)))
        total_agents = agent_count.scalar() or 0

        # Conversation and message counts
        conv_count = await db.execute(select(func.count(Conversation.id)))
        msg_count = await db.execute(
            select(func.count(Message.id))
        )

        # Document count
        doc_count = await db.execute(select(func.count(Document.id)))

        # Token count
        token_count = await db.execute(
            select(func.coalesce(func.sum(UsageRecord.total_tokens), 0))
        )

        # Revenue (from paid invoices)
        # revenue_result = await db.execute(
        #     select(func.coalesce(func.sum(Invoice.total), 0))
        #     .where(Invoice.status == "paid")
        # )
        # total_revenue = revenue_result.scalar() or 0

        # MRR from active subscriptions
        mrr_result = await db.execute(
            select(func.coalesce(func.sum(Subscription.total_amount), 0))
            .where(Subscription.status == "ACTIVE")
        )
        mrr = float(mrr_result.scalar() or 0)

        # Tenants by plan
        by_plan_result = await db.execute(
            select(
                Subscription.plan_code,
                func.count(Subscription.id)
            )
            .where(Subscription.status == "ACTIVE")
            .group_by(Subscription.plan_code)
        )
        tenants_by_plan = dict(by_plan_result.all())

        # Growth rate (tenants this month vs last month)
        current_month_tenants = await db.execute(
            select(func.count(Tenant.id))
            .where(Tenant.created_at >= month_start)
        )
        prev_month_tenants = await db.execute(
            select(func.count(Tenant.id))
            .where(
                and_(
                    Tenant.created_at >= prev_month_start,
                    Tenant.created_at < month_start
                )
            )
        )
        curr_count = current_month_tenants.scalar() or 0
        prev_count = prev_month_tenants.scalar() or 0
        growth_rate = ((curr_count - prev_count) / prev_count * 100) if prev_count > 0 else 0

        return PlatformStats(
            total_tenants=tenants.total or 0,
            active_tenants=tenants.active or 0,
            total_users=total_users,
            total_agents=total_agents,
            total_conversations=conv_count.scalar() or 0,
            total_messages=msg_count.scalar() or 0,
            total_documents=doc_count.scalar() or 0,
            total_tokens=token_count.scalar() or 0,
            total_revenue=0,  # TODO: Calculate from invoices
            mrr=mrr,
            arr=mrr * 12,
            currency="CLP",
            tenants_by_plan=tenants_by_plan,
            growth_rate_percent=round(growth_rate, 2)
        )


# Singleton
dashboard_service = DashboardService()
