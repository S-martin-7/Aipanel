"""
Email service for sending notifications.
"""
import secrets
import smtplib
import re
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from sqlalchemy import select, func, and_, or_, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.email import (
    EmailTemplate, EmailLog, EmailPreference,
    EmailType, EmailStatus
)
from app.modules.email.schemas import (
    EmailTemplateCreate, EmailTemplateUpdate,
    SendEmailRequest, EmailPreferenceUpdate, EmailTypeInfo
)


class EmailService:
    """Service for email operations."""

    # Email type descriptions
    EMAIL_TYPE_INFO = {
        EmailType.WELCOME: ("Auth", "Welcome email for new users", ["user_name", "tenant_name", "login_url"]),
        EmailType.EMAIL_VERIFICATION: ("Auth", "Email verification link", ["user_name", "verification_url", "expires_in"]),
        EmailType.PASSWORD_RESET: ("Auth", "Password reset link", ["user_name", "reset_url", "expires_in"]),
        EmailType.PASSWORD_CHANGED: ("Auth", "Password change confirmation", ["user_name", "changed_at", "ip_address"]),
        EmailType.USER_INVITED: ("Users", "Invitation to join tenant", ["inviter_name", "tenant_name", "invite_url", "role"]),
        EmailType.USER_REMOVED: ("Users", "Removed from tenant notification", ["user_name", "tenant_name"]),
        EmailType.ROLE_CHANGED: ("Users", "Role change notification", ["user_name", "old_role", "new_role", "tenant_name"]),
        EmailType.TRIAL_STARTED: ("Billing", "Trial period started", ["user_name", "tenant_name", "trial_days", "trial_end_date"]),
        EmailType.TRIAL_ENDING: ("Billing", "Trial ending reminder", ["user_name", "tenant_name", "days_remaining", "upgrade_url"]),
        EmailType.TRIAL_EXPIRED: ("Billing", "Trial has expired", ["user_name", "tenant_name", "upgrade_url"]),
        EmailType.SUBSCRIPTION_CREATED: ("Billing", "New subscription confirmation", ["user_name", "plan_name", "amount", "next_billing"]),
        EmailType.SUBSCRIPTION_RENEWED: ("Billing", "Subscription renewed", ["user_name", "plan_name", "amount", "next_billing"]),
        EmailType.SUBSCRIPTION_CANCELLED: ("Billing", "Subscription cancelled", ["user_name", "plan_name", "end_date"]),
        EmailType.PAYMENT_RECEIVED: ("Billing", "Payment confirmation", ["user_name", "amount", "invoice_number", "receipt_url"]),
        EmailType.PAYMENT_FAILED: ("Billing", "Payment failed notification", ["user_name", "amount", "retry_url", "reason"]),
        EmailType.INVOICE_CREATED: ("Billing", "New invoice generated", ["user_name", "invoice_number", "amount", "due_date", "invoice_url"]),
        EmailType.USAGE_WARNING: ("Usage", "Usage limit warning (80%)", ["user_name", "tenant_name", "usage_percent", "limit", "upgrade_url"]),
        EmailType.USAGE_LIMIT_REACHED: ("Usage", "Usage limit reached", ["user_name", "tenant_name", "limit", "upgrade_url"]),
        EmailType.SECURITY_ALERT: ("Security", "Security alert notification", ["user_name", "alert_type", "details", "action_url"]),
        EmailType.API_KEY_CREATED: ("Security", "New API key created", ["user_name", "key_name", "created_at", "ip_address"]),
        EmailType.WEBHOOK_FAILING: ("System", "Webhook delivery failures", ["user_name", "webhook_name", "failure_count", "last_error"]),
        EmailType.CUSTOM: ("Custom", "Custom email", []),
    }

    # Default templates
    DEFAULT_TEMPLATES = {
        EmailType.WELCOME: {
            "subject": "¡Bienvenido a {{tenant_name}}!",
            "body_html": """
            <h1>¡Hola {{user_name}}!</h1>
            <p>Te damos la bienvenida a <strong>{{tenant_name}}</strong>.</p>
            <p>Ya puedes comenzar a usar nuestros agentes de IA para potenciar tu negocio.</p>
            <p><a href="{{login_url}}" style="background-color: #4CAF50; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px;">Iniciar sesión</a></p>
            <p>¿Necesitas ayuda? Responde a este correo y te asistiremos.</p>
            """
        },
        EmailType.PASSWORD_RESET: {
            "subject": "Restablecer tu contraseña",
            "body_html": """
            <h1>Hola {{user_name}}</h1>
            <p>Recibimos una solicitud para restablecer tu contraseña.</p>
            <p><a href="{{reset_url}}" style="background-color: #2196F3; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px;">Restablecer contraseña</a></p>
            <p>Este enlace expira en {{expires_in}}.</p>
            <p>Si no solicitaste esto, ignora este correo.</p>
            """
        },
        EmailType.TRIAL_ENDING: {
            "subject": "Tu período de prueba termina en {{days_remaining}} días",
            "body_html": """
            <h1>Hola {{user_name}}</h1>
            <p>Tu período de prueba en <strong>{{tenant_name}}</strong> termina en <strong>{{days_remaining}} días</strong>.</p>
            <p>Para seguir disfrutando de todas las funcionalidades, actualiza tu plan:</p>
            <p><a href="{{upgrade_url}}" style="background-color: #FF9800; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px;">Ver planes</a></p>
            """
        },
        EmailType.INVOICE_CREATED: {
            "subject": "Nueva factura #{{invoice_number}}",
            "body_html": """
            <h1>Hola {{user_name}}</h1>
            <p>Se ha generado una nueva factura:</p>
            <ul>
                <li><strong>Número:</strong> {{invoice_number}}</li>
                <li><strong>Monto:</strong> {{amount}}</li>
                <li><strong>Vencimiento:</strong> {{due_date}}</li>
            </ul>
            <p><a href="{{invoice_url}}" style="background-color: #4CAF50; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px;">Ver factura</a></p>
            """
        },
        EmailType.USAGE_WARNING: {
            "subject": "⚠️ Has usado el {{usage_percent}}% de tu límite",
            "body_html": """
            <h1>Hola {{user_name}}</h1>
            <p>Tu cuenta <strong>{{tenant_name}}</strong> ha usado el <strong>{{usage_percent}}%</strong> del límite de tokens.</p>
            <p>Límite actual: {{limit}} tokens</p>
            <p>Para evitar interrupciones, considera actualizar tu plan:</p>
            <p><a href="{{upgrade_url}}" style="background-color: #FF9800; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px;">Aumentar límite</a></p>
            """
        },
    }

    async def create_template(
        self,
        db: AsyncSession,
        data: EmailTemplateCreate,
        tenant_id: Optional[str] = None
    ) -> EmailTemplate:
        """Create an email template."""
        template = EmailTemplate(
            tenant_id=tenant_id,
            email_type=data.email_type.value,
            name=data.name,
            description=data.description,
            subject=data.subject,
            body_html=data.body_html,
            body_text=data.body_text,
            header_image_url=data.header_image_url,
            footer_text=data.footer_text,
            primary_color=data.primary_color,
            available_variables=data.available_variables,
            is_active=data.is_active
        )
        db.add(template)
        await db.commit()
        await db.refresh(template)
        return template

    async def get_template(
        self,
        db: AsyncSession,
        template_id: str,
        tenant_id: Optional[str] = None
    ) -> Optional[EmailTemplate]:
        """Get a template by ID."""
        query = select(EmailTemplate).where(EmailTemplate.id == template_id)
        if tenant_id:
            query = query.where(
                or_(EmailTemplate.tenant_id == tenant_id, EmailTemplate.tenant_id == None)
            )
        result = await db.execute(query)
        return result.scalar_one_or_none()

    async def get_template_for_type(
        self,
        db: AsyncSession,
        email_type: EmailType,
        tenant_id: Optional[str] = None
    ) -> Optional[EmailTemplate]:
        """Get the best template for an email type (tenant-specific or default)."""
        # Try tenant-specific first
        if tenant_id:
            result = await db.execute(
                select(EmailTemplate).where(
                    and_(
                        EmailTemplate.email_type == email_type.value,
                        EmailTemplate.tenant_id == tenant_id,
                        EmailTemplate.is_active == True
                    )
                )
            )
            template = result.scalar_one_or_none()
            if template:
                return template

        # Fall back to system default
        result = await db.execute(
            select(EmailTemplate).where(
                and_(
                    EmailTemplate.email_type == email_type.value,
                    EmailTemplate.tenant_id == None,
                    EmailTemplate.is_default == True,
                    EmailTemplate.is_active == True
                )
            )
        )
        return result.scalar_one_or_none()

    async def list_templates(
        self,
        db: AsyncSession,
        tenant_id: Optional[str] = None,
        email_type: Optional[str] = None
    ) -> tuple[List[EmailTemplate], int]:
        """List email templates."""
        query = select(EmailTemplate)

        if tenant_id:
            # Show tenant-specific and system defaults
            query = query.where(
                or_(EmailTemplate.tenant_id == tenant_id, EmailTemplate.tenant_id == None)
            )
        else:
            # Admin: show all
            pass

        if email_type:
            query = query.where(EmailTemplate.email_type == email_type)

        count_result = await db.execute(
            select(func.count(EmailTemplate.id)).where(
                or_(EmailTemplate.tenant_id == tenant_id, EmailTemplate.tenant_id == None) if tenant_id else True
            )
        )
        total = count_result.scalar() or 0

        result = await db.execute(query.order_by(EmailTemplate.email_type, EmailTemplate.created_at))
        templates = list(result.scalars().all())

        return templates, total

    async def update_template(
        self,
        db: AsyncSession,
        template: EmailTemplate,
        data: EmailTemplateUpdate
    ) -> EmailTemplate:
        """Update an email template."""
        update_data = data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(template, field, value)
        await db.commit()
        await db.refresh(template)
        return template

    async def delete_template(self, db: AsyncSession, template: EmailTemplate) -> None:
        """Delete an email template."""
        await db.delete(template)
        await db.commit()

    def render_template(
        self,
        subject: str,
        body_html: str,
        body_text: Optional[str],
        variables: Dict[str, Any]
    ) -> tuple[str, str, Optional[str]]:
        """Render template with variables."""
        rendered_subject = subject
        rendered_html = body_html
        rendered_text = body_text

        for key, value in variables.items():
            placeholder = f"{{{{{key}}}}}"
            rendered_subject = rendered_subject.replace(placeholder, str(value))
            rendered_html = rendered_html.replace(placeholder, str(value))
            if rendered_text:
                rendered_text = rendered_text.replace(placeholder, str(value))

        return rendered_subject, rendered_html, rendered_text

    async def send_email(
        self,
        db: AsyncSession,
        data: SendEmailRequest,
        tenant_id: Optional[str] = None
    ) -> EmailLog:
        """Send an email."""
        # Get template
        template = None
        if data.template_id:
            template = await self.get_template(db, data.template_id, tenant_id)
        else:
            template = await self.get_template_for_type(db, data.email_type, tenant_id)

        # Use default template if none found
        if template:
            subject = data.subject_override or template.subject
            body_html = template.body_html
            body_text = template.body_text
        else:
            # Use hardcoded default
            default = self.DEFAULT_TEMPLATES.get(data.email_type, {})
            subject = data.subject_override or default.get("subject", f"Notification: {data.email_type.value}")
            body_html = default.get("body_html", "<p>{{content}}</p>")
            body_text = None

        # Render with variables
        variables = data.variables or {}
        rendered_subject, rendered_html, rendered_text = self.render_template(
            subject, body_html, body_text, variables
        )

        # Create email log
        email_log = EmailLog(
            tenant_id=tenant_id,
            to_email=data.to_email,
            to_name=data.to_name,
            cc_emails=data.cc_emails,
            bcc_emails=data.bcc_emails,
            email_type=data.email_type.value,
            template_id=template.id if template else None,
            subject=rendered_subject,
            body_html=rendered_html,
            variables=variables,
            status=EmailStatus.PENDING.value
        )
        db.add(email_log)
        await db.commit()
        await db.refresh(email_log)

        # Send via configured provider
        try:
            await self._send_smtp(email_log, rendered_text)
            email_log.status = EmailStatus.SENT.value
            email_log.sent_at = datetime.utcnow()
        except Exception as e:
            email_log.status = EmailStatus.FAILED.value
            email_log.error_message = str(e)
            email_log.attempts += 1
            email_log.last_attempt_at = datetime.utcnow()

        await db.commit()
        await db.refresh(email_log)
        return email_log

    async def _send_smtp(self, email_log: EmailLog, body_text: Optional[str] = None) -> None:
        """Send email via SMTP."""
        # Get SMTP settings from config
        smtp_host = getattr(settings, 'SMTP_HOST', None)
        smtp_port = getattr(settings, 'SMTP_PORT', 587)
        smtp_user = getattr(settings, 'SMTP_USER', None)
        smtp_password = getattr(settings, 'SMTP_PASSWORD', None)
        smtp_from = getattr(settings, 'SMTP_FROM', None)

        if not all([smtp_host, smtp_user, smtp_password, smtp_from]):
            # Skip if SMTP not configured (development mode)
            email_log.provider = "mock"
            return

        # Create message
        msg = MIMEMultipart('alternative')
        msg['Subject'] = email_log.subject
        msg['From'] = smtp_from
        msg['To'] = email_log.to_email

        if email_log.cc_emails:
            msg['Cc'] = ', '.join(email_log.cc_emails)

        # Add text and HTML parts
        if body_text:
            msg.attach(MIMEText(body_text, 'plain'))
        msg.attach(MIMEText(email_log.body_html, 'html'))

        # Send
        with smtplib.SMTP(smtp_host, smtp_port) as server:
            server.starttls()
            server.login(smtp_user, smtp_password)

            recipients = [email_log.to_email]
            if email_log.cc_emails:
                recipients.extend(email_log.cc_emails)
            if email_log.bcc_emails:
                recipients.extend(email_log.bcc_emails)

            server.sendmail(smtp_from, recipients, msg.as_string())

        email_log.provider = "smtp"

    async def get_email_logs(
        self,
        db: AsyncSession,
        tenant_id: Optional[str] = None,
        email_type: Optional[str] = None,
        status: Optional[str] = None,
        to_email: Optional[str] = None,
        page: int = 1,
        page_size: int = 50
    ) -> tuple[List[EmailLog], int]:
        """Get email logs."""
        query = select(EmailLog)
        count_query = select(func.count(EmailLog.id))

        if tenant_id:
            query = query.where(EmailLog.tenant_id == tenant_id)
            count_query = count_query.where(EmailLog.tenant_id == tenant_id)

        if email_type:
            query = query.where(EmailLog.email_type == email_type)
            count_query = count_query.where(EmailLog.email_type == email_type)

        if status:
            query = query.where(EmailLog.status == status)
            count_query = count_query.where(EmailLog.status == status)

        if to_email:
            query = query.where(EmailLog.to_email.ilike(f"%{to_email}%"))
            count_query = count_query.where(EmailLog.to_email.ilike(f"%{to_email}%"))

        total = (await db.execute(count_query)).scalar() or 0

        offset = (page - 1) * page_size
        result = await db.execute(
            query.order_by(desc(EmailLog.created_at)).offset(offset).limit(page_size)
        )
        logs = list(result.scalars().all())

        return logs, total

    async def get_email_stats(
        self,
        db: AsyncSession,
        tenant_id: Optional[str] = None,
        days: int = 30
    ) -> Dict[str, Any]:
        """Get email statistics."""
        start_date = datetime.utcnow() - timedelta(days=days)
        base_filter = and_(
            EmailLog.created_at >= start_date,
            EmailLog.tenant_id == tenant_id if tenant_id else True
        )

        # Counts by status
        status_result = await db.execute(
            select(EmailLog.status, func.count(EmailLog.id))
            .where(base_filter)
            .group_by(EmailLog.status)
        )
        by_status = dict(status_result.all())

        # Counts by type
        type_result = await db.execute(
            select(EmailLog.email_type, func.count(EmailLog.id))
            .where(base_filter)
            .group_by(EmailLog.email_type)
        )
        by_type = dict(type_result.all())

        # Calculate rates
        total_sent = sum(by_status.values())
        delivered = by_status.get(EmailStatus.DELIVERED.value, 0) + by_status.get(EmailStatus.SENT.value, 0)
        failed = by_status.get(EmailStatus.FAILED.value, 0)
        bounced = by_status.get(EmailStatus.BOUNCED.value, 0)

        # Open/click tracking
        opened = await db.execute(
            select(func.count(EmailLog.id))
            .where(and_(base_filter, EmailLog.opened_at != None))
        )
        clicked = await db.execute(
            select(func.count(EmailLog.id))
            .where(and_(base_filter, EmailLog.clicked_at != None))
        )

        opened_count = opened.scalar() or 0
        clicked_count = clicked.scalar() or 0

        # Recent failures
        failures_result = await db.execute(
            select(EmailLog)
            .where(and_(base_filter, EmailLog.status == EmailStatus.FAILED.value))
            .order_by(desc(EmailLog.created_at))
            .limit(10)
        )
        recent_failures = list(failures_result.scalars().all())

        return {
            "total_sent": total_sent,
            "total_delivered": delivered,
            "total_failed": failed,
            "total_bounced": bounced,
            "delivery_rate": round(delivered / total_sent * 100, 2) if total_sent > 0 else 0,
            "open_rate": round(opened_count / delivered * 100, 2) if delivered > 0 else 0,
            "click_rate": round(clicked_count / delivered * 100, 2) if delivered > 0 else 0,
            "by_type": by_type,
            "by_status": by_status,
            "recent_failures": recent_failures
        }

    async def get_or_create_preferences(
        self,
        db: AsyncSession,
        email: str,
        tenant_id: Optional[str] = None,
        user_id: Optional[str] = None
    ) -> EmailPreference:
        """Get or create email preferences."""
        query = select(EmailPreference).where(EmailPreference.email == email)
        if tenant_id:
            query = query.where(EmailPreference.tenant_id == tenant_id)

        result = await db.execute(query)
        pref = result.scalar_one_or_none()

        if not pref:
            pref = EmailPreference(
                tenant_id=tenant_id,
                user_id=user_id,
                email=email,
                unsubscribe_token=secrets.token_urlsafe(32)
            )
            db.add(pref)
            await db.commit()
            await db.refresh(pref)

        return pref

    async def update_preferences(
        self,
        db: AsyncSession,
        pref: EmailPreference,
        data: EmailPreferenceUpdate
    ) -> EmailPreference:
        """Update email preferences."""
        update_data = data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(pref, field, value)
        await db.commit()
        await db.refresh(pref)
        return pref

    async def unsubscribe_by_token(
        self,
        db: AsyncSession,
        token: str
    ) -> Optional[EmailPreference]:
        """Unsubscribe using token."""
        result = await db.execute(
            select(EmailPreference).where(EmailPreference.unsubscribe_token == token)
        )
        pref = result.scalar_one_or_none()
        if pref:
            pref.unsubscribed_all = True
            await db.commit()
            await db.refresh(pref)
        return pref

    def get_available_types(self) -> List[EmailTypeInfo]:
        """Get list of available email types."""
        types = []
        for email_type in EmailType:
            category, description, variables = self.EMAIL_TYPE_INFO.get(
                email_type, ("Other", str(email_type), [])
            )
            types.append(EmailTypeInfo(
                email_type=email_type.value,
                category=category,
                description=description,
                default_variables=variables
            ))
        return types


# Singleton
email_service = EmailService()


# Convenience functions
async def send_notification(
    db: AsyncSession,
    to_email: str,
    email_type: EmailType,
    variables: Dict[str, Any],
    tenant_id: Optional[str] = None,
    to_name: Optional[str] = None
) -> EmailLog:
    """Convenience function to send a notification email."""
    request = SendEmailRequest(
        to_email=to_email,
        to_name=to_name,
        email_type=email_type,
        variables=variables
    )
    return await email_service.send_email(db, request, tenant_id)
