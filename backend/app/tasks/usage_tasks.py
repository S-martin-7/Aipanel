"""
Usage tracking and aggregation tasks.
"""
from celery import shared_task
from datetime import datetime, timedelta
from app.utils.logger import get_logger

logger = get_logger(__name__)


@shared_task(name="app.tasks.usage_tasks.aggregate_daily_usage")
def aggregate_daily_usage():
    """Aggregate daily usage for all tenants."""
    logger.info("Aggregating daily usage")

    try:
        import asyncio
        from app.core.database import get_db_context
        from sqlalchemy import select, func
        from app.models.usage import UsageRecord
        from app.models.tenant import Tenant

        async def _aggregate():
            async with get_db_context() as db:
                yesterday = datetime.utcnow().date() - timedelta(days=1)
                yesterday_start = datetime.combine(yesterday, datetime.min.time())
                yesterday_end = datetime.combine(yesterday, datetime.max.time())

                # Get all tenants
                tenants_result = await db.execute(select(Tenant.id))
                tenant_ids = [t[0] for t in tenants_result.all()]

                for tenant_id in tenant_ids:
                    # Aggregate usage
                    result = await db.execute(
                        select(
                            func.sum(UsageRecord.total_tokens).label('total_tokens'),
                            func.sum(UsageRecord.cost).label('total_cost'),
                            func.count(UsageRecord.id).label('request_count')
                        ).where(
                            UsageRecord.tenant_id == tenant_id,
                            UsageRecord.created_at >= yesterday_start,
                            UsageRecord.created_at <= yesterday_end
                        )
                    )
                    stats = result.first()

                    if stats and stats.total_tokens:
                        logger.info(
                            f"Tenant {tenant_id}: {stats.total_tokens} tokens, "
                            f"{stats.request_count} requests, ${stats.total_cost}"
                        )

        asyncio.run(_aggregate())
        logger.info("Daily usage aggregation completed")

    except Exception as e:
        logger.error(f"Error aggregating daily usage: {e}")
        raise


@shared_task(name="app.tasks.usage_tasks.check_all_thresholds")
def check_all_thresholds():
    """Check usage thresholds for all tenants."""
    logger.info("Checking usage thresholds")

    try:
        import asyncio
        from app.core.database import get_db_context
        from sqlalchemy import select
        from app.models.tenant import Tenant
        from app.models.enums import TenantStatus
        from app.tasks.email_tasks import send_usage_alert

        async def _check():
            async with get_db_context() as db:
                result = await db.execute(
                    select(Tenant).where(Tenant.status == TenantStatus.ACTIVE)
                )
                tenants = result.scalars().all()

                for tenant in tenants:
                    if tenant.monthly_token_limit > 0:
                        usage_percent = int(
                            (tenant.current_month_usage / tenant.monthly_token_limit) * 100
                        )

                        # Alert at 80%, 90%, and 100%
                        if usage_percent >= 100:
                            send_usage_alert.delay(
                                tenant.id, 100, tenant.monthly_token_limit
                            )
                        elif usage_percent >= 90:
                            send_usage_alert.delay(
                                tenant.id, 90, tenant.monthly_token_limit
                            )
                        elif usage_percent >= 80:
                            send_usage_alert.delay(
                                tenant.id, 80, tenant.monthly_token_limit
                            )

        asyncio.run(_check())

    except Exception as e:
        logger.error(f"Error checking thresholds: {e}")
        raise


@shared_task(name="app.tasks.usage_tasks.reset_monthly_usage")
def reset_monthly_usage():
    """Reset monthly usage counters for all tenants."""
    logger.info("Resetting monthly usage counters")

    try:
        import asyncio
        from app.core.database import get_db_context
        from sqlalchemy import update
        from app.models.tenant import Tenant

        async def _reset():
            async with get_db_context() as db:
                await db.execute(
                    update(Tenant).values(current_month_usage=0)
                )
                await db.commit()

        asyncio.run(_reset())
        logger.info("Monthly usage reset completed")

    except Exception as e:
        logger.error(f"Error resetting monthly usage: {e}")
        raise


@shared_task(name="app.tasks.usage_tasks.cleanup_old_data")
def cleanup_old_data():
    """Clean up old usage records and logs."""
    logger.info("Cleaning up old data")

    try:
        import asyncio
        from app.core.database import get_db_context
        from sqlalchemy import delete
        from app.models.usage import UsageRecord
        from app.models.audit_log import AuditLog

        async def _cleanup():
            async with get_db_context() as db:
                # Keep usage records for 90 days
                cutoff_usage = datetime.utcnow() - timedelta(days=90)
                await db.execute(
                    delete(UsageRecord).where(UsageRecord.created_at < cutoff_usage)
                )

                # Keep audit logs for 365 days
                cutoff_audit = datetime.utcnow() - timedelta(days=365)
                await db.execute(
                    delete(AuditLog).where(AuditLog.created_at < cutoff_audit)
                )

                await db.commit()

        asyncio.run(_cleanup())
        logger.info("Old data cleanup completed")

    except Exception as e:
        logger.error(f"Error cleaning up old data: {e}")
        raise


@shared_task(name="app.tasks.usage_tasks.update_tenant_usage")
def update_tenant_usage(tenant_id: str, tokens: int, cost: float):
    """Update tenant's current month usage."""
    logger.info(f"Updating usage for tenant {tenant_id}: +{tokens} tokens")

    try:
        import asyncio
        from app.core.database import get_db_context
        from sqlalchemy import select
        from app.models.tenant import Tenant

        async def _update():
            async with get_db_context() as db:
                result = await db.execute(
                    select(Tenant).where(Tenant.id == tenant_id)
                )
                tenant = result.scalar_one_or_none()
                if tenant:
                    tenant.current_month_usage += tokens
                    await db.commit()

        asyncio.run(_update())

    except Exception as e:
        logger.error(f"Error updating tenant usage: {e}")
        raise
