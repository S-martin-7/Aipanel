"""
Billing and subscription tasks.
"""
from celery import shared_task
from datetime import datetime, timedelta
from app.utils.logger import get_logger

logger = get_logger(__name__)


@shared_task(name="app.tasks.billing_tasks.check_trial_expirations")
def check_trial_expirations():
    """Check for expiring trials and send reminders."""
    logger.info("Checking trial expirations")

    try:
        import asyncio
        from app.core.database import get_db_context
        from sqlalchemy import select, and_
        from app.models.tenant import Tenant
        from app.tasks.email_tasks import send_trial_reminder

        async def _check():
            async with get_db_context() as db:
                now = datetime.utcnow()

                # Check for trials ending in 7, 3, and 1 days
                for days in [7, 3, 1]:
                    target_date = now + timedelta(days=days)
                    target_start = target_date.replace(hour=0, minute=0, second=0)
                    target_end = target_date.replace(hour=23, minute=59, second=59)

                    result = await db.execute(
                        select(Tenant).where(
                            and_(
                                Tenant.trial_end >= target_start,
                                Tenant.trial_end <= target_end,
                                Tenant.is_paid == False
                            )
                        )
                    )
                    tenants = result.scalars().all()

                    for tenant in tenants:
                        send_trial_reminder.delay(tenant.id, days)
                        logger.info(f"Trial reminder queued for tenant {tenant.id} ({days} days)")

        asyncio.run(_check())
        logger.info("Trial expiration check completed")

    except Exception as e:
        logger.error(f"Error checking trial expirations: {e}")
        raise


@shared_task(name="app.tasks.billing_tasks.generate_monthly_invoices")
def generate_monthly_invoices():
    """Generate invoices for all active subscriptions."""
    logger.info("Generating monthly invoices")

    try:
        import asyncio
        from app.core.database import get_db_context
        from app.modules.billing.service import billing_service

        async def _generate():
            async with get_db_context() as db:
                await billing_service.generate_monthly_invoices(db)

        asyncio.run(_generate())
        logger.info("Monthly invoice generation completed")

    except Exception as e:
        logger.error(f"Error generating monthly invoices: {e}")
        raise


@shared_task(name="app.tasks.billing_tasks.process_subscription_renewal")
def process_subscription_renewal(subscription_id: str):
    """Process a subscription renewal."""
    logger.info(f"Processing renewal for subscription {subscription_id}")

    try:
        import asyncio
        from app.core.database import get_db_context
        from app.modules.billing.service import billing_service

        async def _renew():
            async with get_db_context() as db:
                await billing_service.renew_subscription(db, subscription_id)

        asyncio.run(_renew())
        logger.info(f"Subscription {subscription_id} renewed")

    except Exception as e:
        logger.error(f"Error renewing subscription {subscription_id}: {e}")
        raise


@shared_task(name="app.tasks.billing_tasks.suspend_expired_trials")
def suspend_expired_trials():
    """Suspend tenants with expired trials that haven't paid."""
    logger.info("Checking for expired trials to suspend")

    try:
        import asyncio
        from app.core.database import get_db_context
        from sqlalchemy import select, and_
        from app.models.tenant import Tenant
        from app.models.enums import TenantStatus

        async def _suspend():
            async with get_db_context() as db:
                now = datetime.utcnow()

                result = await db.execute(
                    select(Tenant).where(
                        and_(
                            Tenant.trial_end < now,
                            Tenant.is_paid == False,
                            Tenant.status == TenantStatus.ACTIVE,
                            Tenant.suspend_on_trial_end == True
                        )
                    )
                )
                tenants = result.scalars().all()

                for tenant in tenants:
                    tenant.status = TenantStatus.SUSPENDED
                    tenant.suspended_at = now
                    tenant.suspension_reason = "Trial expired"
                    logger.info(f"Suspended tenant {tenant.id} - trial expired")

                await db.commit()

        asyncio.run(_suspend())

    except Exception as e:
        logger.error(f"Error suspending expired trials: {e}")
        raise


@shared_task(name="app.tasks.billing_tasks.send_invoice_reminder")
def send_invoice_reminder(invoice_id: str):
    """Send reminder for unpaid invoice."""
    logger.info(f"Sending invoice reminder for {invoice_id}")

    try:
        import asyncio
        from app.core.database import get_db_context
        from sqlalchemy import select
        from app.models.usage import Invoice
        from app.models.tenant import Tenant
        from app.tasks.email_tasks import send_email

        async def _send():
            async with get_db_context() as db:
                result = await db.execute(
                    select(Invoice).where(Invoice.id == invoice_id)
                )
                invoice = result.scalar_one_or_none()
                if not invoice:
                    return

                tenant_result = await db.execute(
                    select(Tenant).where(Tenant.id == invoice.tenant_id)
                )
                tenant = tenant_result.scalar_one_or_none()
                if not tenant:
                    return

                send_email.delay(
                    to_email=tenant.email,
                    email_type="invoice_reminder",
                    variables={
                        "tenant_name": tenant.name,
                        "invoice_number": invoice.invoice_number,
                        "amount": invoice.total,
                        "due_date": invoice.due_date.isoformat() if invoice.due_date else None,
                        "invoice_url": f"https://app.aipanel.cl/billing/invoices/{invoice.id}"
                    },
                    tenant_id=invoice.tenant_id
                )

        asyncio.run(_send())

    except Exception as e:
        logger.error(f"Error sending invoice reminder: {e}")
        raise
