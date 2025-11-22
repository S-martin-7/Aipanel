"""
Email sending tasks.
"""
from celery import shared_task
from typing import Dict, Any, List, Optional
from app.utils.logger import get_logger

logger = get_logger(__name__)


@shared_task(name="app.tasks.email_tasks.send_email")
def send_email(
    to_email: str,
    email_type: str,
    variables: Dict[str, Any],
    tenant_id: Optional[str] = None,
    to_name: Optional[str] = None
):
    """Send a single email."""
    logger.info(f"Sending {email_type} email to {to_email}")

    try:
        import asyncio
        from app.core.database import get_db_context
        from app.modules.email.service import email_service
        from app.modules.email.schemas import SendEmailRequest
        from app.models.email import EmailType

        async def _send():
            async with get_db_context() as db:
                request = SendEmailRequest(
                    to_email=to_email,
                    to_name=to_name,
                    email_type=EmailType(email_type),
                    variables=variables
                )
                await email_service.send_email(db, request, tenant_id)

        asyncio.run(_send())
        logger.info(f"Email sent to {to_email}")

    except Exception as e:
        logger.error(f"Error sending email to {to_email}: {e}")
        raise


@shared_task(name="app.tasks.email_tasks.send_bulk_emails")
def send_bulk_emails(
    email_type: str,
    recipients: List[Dict[str, Any]],
    tenant_id: Optional[str] = None
):
    """Send emails to multiple recipients."""
    logger.info(f"Sending {email_type} to {len(recipients)} recipients")

    for recipient in recipients:
        try:
            send_email.delay(
                to_email=recipient["email"],
                email_type=email_type,
                variables=recipient.get("variables", {}),
                tenant_id=tenant_id,
                to_name=recipient.get("name")
            )
        except Exception as e:
            logger.error(f"Error queueing email for {recipient['email']}: {e}")


@shared_task(name="app.tasks.email_tasks.send_trial_reminder")
def send_trial_reminder(tenant_id: str, days_remaining: int):
    """Send trial expiration reminder."""
    logger.info(f"Sending trial reminder to tenant {tenant_id} ({days_remaining} days)")

    try:
        import asyncio
        from app.core.database import get_db_context
        from sqlalchemy import select
        from app.models.tenant import Tenant, TenantUser
        from app.models.enums import TenantUserRole

        async def _send():
            async with get_db_context() as db:
                # Get tenant
                result = await db.execute(
                    select(Tenant).where(Tenant.id == tenant_id)
                )
                tenant = result.scalar_one_or_none()
                if not tenant:
                    return

                # Get admin users
                users_result = await db.execute(
                    select(TenantUser).where(
                        TenantUser.tenant_id == tenant_id,
                        TenantUser.role.in_([TenantUserRole.OWNER, TenantUserRole.ADMIN])
                    )
                )
                users = users_result.scalars().all()

                for user in users:
                    send_email.delay(
                        to_email=user.email,
                        email_type="trial_ending",
                        variables={
                            "user_name": user.name,
                            "tenant_name": tenant.name,
                            "days_remaining": days_remaining,
                            "upgrade_url": f"https://app.aipanel.cl/billing"
                        },
                        tenant_id=tenant_id,
                        to_name=user.name
                    )

        asyncio.run(_send())

    except Exception as e:
        logger.error(f"Error sending trial reminder: {e}")
        raise


@shared_task(name="app.tasks.email_tasks.send_usage_alert")
def send_usage_alert(tenant_id: str, usage_percent: int, limit: int):
    """Send usage threshold alert."""
    logger.info(f"Sending usage alert to tenant {tenant_id} ({usage_percent}%)")

    email_type = "usage_warning" if usage_percent < 100 else "usage_limit_reached"

    try:
        import asyncio
        from app.core.database import get_db_context
        from sqlalchemy import select
        from app.models.tenant import Tenant, TenantUser
        from app.models.enums import TenantUserRole

        async def _send():
            async with get_db_context() as db:
                result = await db.execute(
                    select(Tenant).where(Tenant.id == tenant_id)
                )
                tenant = result.scalar_one_or_none()
                if not tenant:
                    return

                users_result = await db.execute(
                    select(TenantUser).where(
                        TenantUser.tenant_id == tenant_id,
                        TenantUser.role.in_([TenantUserRole.OWNER, TenantUserRole.ADMIN])
                    )
                )
                users = users_result.scalars().all()

                for user in users:
                    send_email.delay(
                        to_email=user.email,
                        email_type=email_type,
                        variables={
                            "user_name": user.name,
                            "tenant_name": tenant.name,
                            "usage_percent": usage_percent,
                            "limit": limit,
                            "upgrade_url": f"https://app.aipanel.cl/billing"
                        },
                        tenant_id=tenant_id
                    )

        asyncio.run(_send())

    except Exception as e:
        logger.error(f"Error sending usage alert: {e}")
        raise
