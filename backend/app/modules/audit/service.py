"""
Audit service for logging and querying audit events.
"""
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from sqlalchemy import select, func, and_, or_, desc
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import Request

from app.models.audit_log import AuditLog, AuditAction
from app.modules.audit.schemas import AuditLogFilters, AuditActionInfo


class AuditService:
    """Service for audit log operations."""

    # Action descriptions
    ACTION_INFO = {
        AuditAction.LOGIN: ("Authentication", "User logged in"),
        AuditAction.LOGOUT: ("Authentication", "User logged out"),
        AuditAction.LOGIN_FAILED: ("Authentication", "Failed login attempt"),
        AuditAction.PASSWORD_CHANGED: ("Authentication", "User changed password"),
        AuditAction.PASSWORD_RESET: ("Authentication", "Password was reset"),
        AuditAction.API_KEY_CREATED: ("Authentication", "API key created"),
        AuditAction.API_KEY_REVOKED: ("Authentication", "API key revoked"),
        AuditAction.USER_CREATED: ("Users", "User account created"),
        AuditAction.USER_UPDATED: ("Users", "User account updated"),
        AuditAction.USER_DELETED: ("Users", "User account deleted"),
        AuditAction.USER_INVITED: ("Users", "User invited to tenant"),
        AuditAction.USER_ROLE_CHANGED: ("Users", "User role changed"),
        AuditAction.AGENT_CREATED: ("Agents", "Agent created"),
        AuditAction.AGENT_UPDATED: ("Agents", "Agent configuration updated"),
        AuditAction.AGENT_DELETED: ("Agents", "Agent deleted"),
        AuditAction.AGENT_ACTIVATED: ("Agents", "Agent activated"),
        AuditAction.AGENT_DEACTIVATED: ("Agents", "Agent deactivated"),
        AuditAction.DOCUMENT_UPLOADED: ("Documents", "Document uploaded"),
        AuditAction.DOCUMENT_PROCESSED: ("Documents", "Document processing completed"),
        AuditAction.DOCUMENT_DELETED: ("Documents", "Document deleted"),
        AuditAction.CONVERSATION_STARTED: ("Conversations", "New conversation started"),
        AuditAction.CONVERSATION_DELETED: ("Conversations", "Conversation deleted"),
        AuditAction.CONVERSATION_EXPORTED: ("Conversations", "Conversation exported"),
        AuditAction.SETTINGS_UPDATED: ("Settings", "Settings updated"),
        AuditAction.WEBHOOK_CREATED: ("Webhooks", "Webhook created"),
        AuditAction.WEBHOOK_UPDATED: ("Webhooks", "Webhook updated"),
        AuditAction.WEBHOOK_DELETED: ("Webhooks", "Webhook deleted"),
        AuditAction.SUBSCRIPTION_CREATED: ("Billing", "Subscription created"),
        AuditAction.SUBSCRIPTION_UPDATED: ("Billing", "Subscription updated"),
        AuditAction.SUBSCRIPTION_CANCELLED: ("Billing", "Subscription cancelled"),
        AuditAction.PAYMENT_RECEIVED: ("Billing", "Payment received"),
        AuditAction.PAYMENT_FAILED: ("Billing", "Payment failed"),
        AuditAction.TENANT_CREATED: ("Admin", "Tenant created"),
        AuditAction.TENANT_UPDATED: ("Admin", "Tenant updated"),
        AuditAction.TENANT_SUSPENDED: ("Admin", "Tenant suspended"),
        AuditAction.TENANT_ACTIVATED: ("Admin", "Tenant activated"),
        AuditAction.PLAN_CHANGED: ("Admin", "Plan changed"),
    }

    async def log(
        self,
        db: AsyncSession,
        action: AuditAction,
        tenant_id: Optional[str] = None,
        user_id: Optional[str] = None,
        user_email: Optional[str] = None,
        user_type: Optional[str] = None,
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
        resource_name: Optional[str] = None,
        description: Optional[str] = None,
        old_values: Optional[Dict[str, Any]] = None,
        new_values: Optional[Dict[str, Any]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        request: Optional[Request] = None,
        status: str = "success",
        error_message: Optional[str] = None
    ) -> AuditLog:
        """Create an audit log entry."""
        # Extract request info
        ip_address = None
        user_agent = None
        request_id = None

        if request:
            # Get real IP (handle proxies)
            forwarded = request.headers.get("X-Forwarded-For")
            if forwarded:
                ip_address = forwarded.split(",")[0].strip()
            else:
                ip_address = request.client.host if request.client else None

            user_agent = request.headers.get("User-Agent", "")[:500]
            request_id = request.headers.get("X-Request-ID")

        # Generate description if not provided
        if not description:
            _, desc = self.ACTION_INFO.get(action, ("Other", str(action)))
            description = desc

        log_entry = AuditLog(
            tenant_id=tenant_id,
            user_id=user_id,
            user_email=user_email,
            user_type=user_type,
            action=action.value,
            resource_type=resource_type,
            resource_id=resource_id,
            resource_name=resource_name,
            description=description,
            old_values=old_values,
            new_values=new_values,
            metadata=metadata,
            ip_address=ip_address,
            user_agent=user_agent,
            request_id=request_id,
            status=status,
            error_message=error_message
        )

        db.add(log_entry)
        await db.commit()
        await db.refresh(log_entry)
        return log_entry

    async def get_logs(
        self,
        db: AsyncSession,
        tenant_id: Optional[str] = None,
        filters: Optional[AuditLogFilters] = None,
        page: int = 1,
        page_size: int = 50
    ) -> tuple[List[AuditLog], int]:
        """Get audit logs with filters."""
        query = select(AuditLog)
        count_query = select(func.count(AuditLog.id))

        # Base filter by tenant
        if tenant_id:
            query = query.where(AuditLog.tenant_id == tenant_id)
            count_query = count_query.where(AuditLog.tenant_id == tenant_id)

        # Apply filters
        if filters:
            if filters.action:
                query = query.where(AuditLog.action == filters.action)
                count_query = count_query.where(AuditLog.action == filters.action)

            if filters.resource_type:
                query = query.where(AuditLog.resource_type == filters.resource_type)
                count_query = count_query.where(AuditLog.resource_type == filters.resource_type)

            if filters.resource_id:
                query = query.where(AuditLog.resource_id == filters.resource_id)
                count_query = count_query.where(AuditLog.resource_id == filters.resource_id)

            if filters.user_id:
                query = query.where(AuditLog.user_id == filters.user_id)
                count_query = count_query.where(AuditLog.user_id == filters.user_id)

            if filters.user_email:
                query = query.where(AuditLog.user_email.ilike(f"%{filters.user_email}%"))
                count_query = count_query.where(AuditLog.user_email.ilike(f"%{filters.user_email}%"))

            if filters.status:
                query = query.where(AuditLog.status == filters.status)
                count_query = count_query.where(AuditLog.status == filters.status)

            if filters.start_date:
                query = query.where(AuditLog.created_at >= filters.start_date)
                count_query = count_query.where(AuditLog.created_at >= filters.start_date)

            if filters.end_date:
                query = query.where(AuditLog.created_at <= filters.end_date)
                count_query = count_query.where(AuditLog.created_at <= filters.end_date)

            if filters.ip_address:
                query = query.where(AuditLog.ip_address == filters.ip_address)
                count_query = count_query.where(AuditLog.ip_address == filters.ip_address)

        # Get total count
        count_result = await db.execute(count_query)
        total = count_result.scalar() or 0

        # Get paginated results
        offset = (page - 1) * page_size
        result = await db.execute(
            query.order_by(desc(AuditLog.created_at))
            .offset(offset)
            .limit(page_size)
        )
        logs = list(result.scalars().all())

        return logs, total

    async def get_log_by_id(
        self,
        db: AsyncSession,
        log_id: str,
        tenant_id: Optional[str] = None
    ) -> Optional[AuditLog]:
        """Get a single audit log by ID."""
        query = select(AuditLog).where(AuditLog.id == log_id)
        if tenant_id:
            query = query.where(AuditLog.tenant_id == tenant_id)

        result = await db.execute(query)
        return result.scalar_one_or_none()

    async def get_stats(
        self,
        db: AsyncSession,
        tenant_id: Optional[str] = None,
        days: int = 30
    ) -> Dict[str, Any]:
        """Get audit log statistics."""
        now = datetime.utcnow()
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        week_start = today_start - timedelta(days=today_start.weekday())
        month_start = today_start.replace(day=1)
        period_start = now - timedelta(days=days)

        base_filter = AuditLog.tenant_id == tenant_id if tenant_id else True

        # Total counts
        counts = await db.execute(
            select(
                func.count(AuditLog.id).label('total'),
                func.sum(func.cast(AuditLog.created_at >= today_start, Integer)).label('today'),
                func.sum(func.cast(AuditLog.created_at >= week_start, Integer)).label('week'),
                func.sum(func.cast(AuditLog.created_at >= month_start, Integer)).label('month')
            ).where(base_filter)
        )
        count_data = counts.first()

        # By action
        by_action_result = await db.execute(
            select(AuditLog.action, func.count(AuditLog.id))
            .where(and_(base_filter, AuditLog.created_at >= period_start))
            .group_by(AuditLog.action)
            .order_by(desc(func.count(AuditLog.id)))
            .limit(20)
        )
        by_action = dict(by_action_result.all())

        # By resource type
        by_resource_result = await db.execute(
            select(AuditLog.resource_type, func.count(AuditLog.id))
            .where(and_(base_filter, AuditLog.created_at >= period_start, AuditLog.resource_type != None))
            .group_by(AuditLog.resource_type)
        )
        by_resource = dict(by_resource_result.all())

        # By status
        by_status_result = await db.execute(
            select(AuditLog.status, func.count(AuditLog.id))
            .where(and_(base_filter, AuditLog.created_at >= period_start))
            .group_by(AuditLog.status)
        )
        by_status = dict(by_status_result.all())

        # By user (top 10)
        by_user_result = await db.execute(
            select(
                AuditLog.user_id,
                AuditLog.user_email,
                func.count(AuditLog.id).label('count')
            )
            .where(and_(base_filter, AuditLog.created_at >= period_start, AuditLog.user_id != None))
            .group_by(AuditLog.user_id, AuditLog.user_email)
            .order_by(desc(func.count(AuditLog.id)))
            .limit(10)
        )
        by_user = [
            {"user_id": r.user_id, "user_email": r.user_email, "count": r.count}
            for r in by_user_result.all()
        ]

        # Recent failures
        failures_result = await db.execute(
            select(AuditLog)
            .where(and_(base_filter, AuditLog.status == "failed"))
            .order_by(desc(AuditLog.created_at))
            .limit(10)
        )
        recent_failures = list(failures_result.scalars().all())

        return {
            "total_logs": count_data.total or 0,
            "logs_today": count_data.today or 0,
            "logs_this_week": count_data.week or 0,
            "logs_this_month": count_data.month or 0,
            "by_action": by_action,
            "by_resource_type": by_resource,
            "by_status": by_status,
            "by_user": by_user,
            "recent_failures": recent_failures
        }

    def get_available_actions(self) -> List[AuditActionInfo]:
        """Get list of available audit actions."""
        actions = []
        for action in AuditAction:
            category, description = self.ACTION_INFO.get(action, ("Other", str(action)))
            actions.append(AuditActionInfo(
                action=action.value,
                category=category,
                description=description
            ))
        return actions

    async def get_resource_history(
        self,
        db: AsyncSession,
        resource_type: str,
        resource_id: str,
        tenant_id: Optional[str] = None
    ) -> List[AuditLog]:
        """Get audit history for a specific resource."""
        query = select(AuditLog).where(
            and_(
                AuditLog.resource_type == resource_type,
                AuditLog.resource_id == resource_id
            )
        )

        if tenant_id:
            query = query.where(AuditLog.tenant_id == tenant_id)

        result = await db.execute(
            query.order_by(desc(AuditLog.created_at)).limit(100)
        )
        return list(result.scalars().all())

    async def get_user_activity(
        self,
        db: AsyncSession,
        user_id: str,
        tenant_id: Optional[str] = None,
        days: int = 30
    ) -> List[AuditLog]:
        """Get audit logs for a specific user."""
        start_date = datetime.utcnow() - timedelta(days=days)

        query = select(AuditLog).where(
            and_(
                AuditLog.user_id == user_id,
                AuditLog.created_at >= start_date
            )
        )

        if tenant_id:
            query = query.where(AuditLog.tenant_id == tenant_id)

        result = await db.execute(
            query.order_by(desc(AuditLog.created_at)).limit(500)
        )
        return list(result.scalars().all())


# Singleton
audit_service = AuditService()


# Convenience function for logging from anywhere in the app
async def log_audit(
    db: AsyncSession,
    action: AuditAction,
    tenant_id: Optional[str] = None,
    user_id: Optional[str] = None,
    user_email: Optional[str] = None,
    user_type: Optional[str] = None,
    resource_type: Optional[str] = None,
    resource_id: Optional[str] = None,
    resource_name: Optional[str] = None,
    description: Optional[str] = None,
    old_values: Optional[Dict[str, Any]] = None,
    new_values: Optional[Dict[str, Any]] = None,
    metadata: Optional[Dict[str, Any]] = None,
    request: Optional[Request] = None,
    status: str = "success",
    error_message: Optional[str] = None
) -> AuditLog:
    """Convenience function to log audit events."""
    return await audit_service.log(
        db=db,
        action=action,
        tenant_id=tenant_id,
        user_id=user_id,
        user_email=user_email,
        user_type=user_type,
        resource_type=resource_type,
        resource_id=resource_id,
        resource_name=resource_name,
        description=description,
        old_values=old_values,
        new_values=new_values,
        metadata=metadata,
        request=request,
        status=status,
        error_message=error_message
    )
