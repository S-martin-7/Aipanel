"""
Webhook delivery tasks.
"""
from celery import shared_task
from typing import Dict, Any, Optional
from datetime import datetime
from app.utils.logger import get_logger

logger = get_logger(__name__)


@shared_task(name="app.tasks.webhook_tasks.deliver_webhook")
def deliver_webhook(delivery_id: str):
    """Deliver a webhook."""
    logger.info(f"Delivering webhook {delivery_id}")

    try:
        import asyncio
        from app.core.database import get_db_context
        from app.modules.webhooks.service import webhook_service

        async def _deliver():
            async with get_db_context() as db:
                await webhook_service._deliver_webhook(db, delivery_id)

        asyncio.run(_deliver())

    except Exception as e:
        logger.error(f"Error delivering webhook {delivery_id}: {e}")
        raise


@shared_task(name="app.tasks.webhook_tasks.retry_failed_deliveries")
def retry_failed_deliveries():
    """Retry failed webhook deliveries that are due for retry."""
    logger.info("Retrying failed webhook deliveries")

    try:
        import asyncio
        from app.core.database import get_db_context
        from sqlalchemy import select, and_
        from app.models.webhook import WebhookDelivery, DeliveryStatus

        async def _retry():
            async with get_db_context() as db:
                now = datetime.utcnow()

                result = await db.execute(
                    select(WebhookDelivery).where(
                        and_(
                            WebhookDelivery.status == DeliveryStatus.RETRYING.value,
                            WebhookDelivery.next_retry_at <= now
                        )
                    ).limit(100)
                )
                deliveries = result.scalars().all()

                for delivery in deliveries:
                    deliver_webhook.delay(delivery.id)
                    logger.info(f"Queued retry for delivery {delivery.id}")

        asyncio.run(_retry())

    except Exception as e:
        logger.error(f"Error retrying webhooks: {e}")
        raise


@shared_task(name="app.tasks.webhook_tasks.trigger_event")
def trigger_event(
    tenant_id: str,
    event_type: str,
    data: Dict[str, Any],
    agent_id: Optional[str] = None
):
    """Trigger a webhook event for all matching webhooks."""
    logger.info(f"Triggering {event_type} for tenant {tenant_id}")

    try:
        import asyncio
        from app.core.database import get_db_context
        from app.modules.webhooks.service import webhook_service
        from app.models.webhook import WebhookEvent

        async def _trigger():
            async with get_db_context() as db:
                delivery_ids = await webhook_service.trigger_event(
                    db,
                    tenant_id=tenant_id,
                    event_type=WebhookEvent(event_type),
                    data=data,
                    agent_id=agent_id
                )
                logger.info(f"Created {len(delivery_ids)} webhook deliveries")

        asyncio.run(_trigger())

    except Exception as e:
        logger.error(f"Error triggering webhook event: {e}")
        raise


@shared_task(name="app.tasks.webhook_tasks.cleanup_old_deliveries")
def cleanup_old_deliveries():
    """Clean up old webhook delivery records."""
    logger.info("Cleaning up old webhook deliveries")

    try:
        import asyncio
        from datetime import timedelta
        from app.core.database import get_db_context
        from sqlalchemy import delete
        from app.models.webhook import WebhookDelivery

        async def _cleanup():
            async with get_db_context() as db:
                cutoff = datetime.utcnow() - timedelta(days=30)
                await db.execute(
                    delete(WebhookDelivery).where(
                        WebhookDelivery.created_at < cutoff
                    )
                )
                await db.commit()

        asyncio.run(_cleanup())
        logger.info("Webhook delivery cleanup completed")

    except Exception as e:
        logger.error(f"Error cleaning up webhook deliveries: {e}")
        raise
