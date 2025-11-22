"""
Unified notification service for AIPanel.

Coordinates all notification channels:
- Email (SendGrid/SMTP)
- SMS (Twilio)
- Slack
- Push Notifications (OneSignal)
"""

from typing import Optional, List, Dict, Any
from enum import Enum
from dataclasses import dataclass

from app.integrations.slack_client import slack_client
from app.integrations.push_notifications import push_service
from app.integrations.sms_client import sms_client
from app.modules.email.service import email_service
from app.utils.logger import get_logger

logger = get_logger(__name__)


class NotificationChannel(str, Enum):
    EMAIL = "email"
    SMS = "sms"
    SLACK = "slack"
    PUSH = "push"


class NotificationType(str, Enum):
    # User notifications
    WELCOME = "welcome"
    PASSWORD_RESET = "password_reset"
    EMAIL_VERIFICATION = "email_verification"

    # Usage notifications
    USAGE_WARNING = "usage_warning"
    USAGE_CRITICAL = "usage_critical"
    QUOTA_EXCEEDED = "quota_exceeded"

    # Payment notifications
    PAYMENT_SUCCESS = "payment_success"
    PAYMENT_FAILED = "payment_failed"
    SUBSCRIPTION_EXPIRING = "subscription_expiring"
    SUBSCRIPTION_CANCELLED = "subscription_cancelled"
    SUBSCRIPTION_REACTIVATED = "subscription_reactivated"

    # Document notifications
    DOCUMENT_PROCESSED = "document_processed"
    DOCUMENT_FAILED = "document_failed"

    # Agent notifications
    AGENT_READY = "agent_ready"
    AGENT_ERROR = "agent_error"

    # System notifications
    SYSTEM_ALERT = "system_alert"
    SECURITY_ALERT = "security_alert"


@dataclass
class NotificationResult:
    """Result of sending a notification."""
    channel: NotificationChannel
    success: bool
    message_id: Optional[str] = None
    error: Optional[str] = None


class NotificationService:
    """
    Unified notification service.

    Sends notifications through multiple channels based on user preferences
    and notification type.
    """

    # Default channels for each notification type
    DEFAULT_CHANNELS = {
        NotificationType.WELCOME: [NotificationChannel.EMAIL],
        NotificationType.PASSWORD_RESET: [NotificationChannel.EMAIL],
        NotificationType.EMAIL_VERIFICATION: [NotificationChannel.EMAIL],
        NotificationType.USAGE_WARNING: [NotificationChannel.EMAIL, NotificationChannel.PUSH],
        NotificationType.USAGE_CRITICAL: [NotificationChannel.EMAIL, NotificationChannel.PUSH, NotificationChannel.SLACK],
        NotificationType.QUOTA_EXCEEDED: [NotificationChannel.EMAIL, NotificationChannel.PUSH, NotificationChannel.SLACK],
        NotificationType.PAYMENT_SUCCESS: [NotificationChannel.EMAIL, NotificationChannel.PUSH],
        NotificationType.PAYMENT_FAILED: [NotificationChannel.EMAIL, NotificationChannel.PUSH, NotificationChannel.SMS],
        NotificationType.SUBSCRIPTION_EXPIRING: [NotificationChannel.EMAIL, NotificationChannel.PUSH],
        NotificationType.SUBSCRIPTION_CANCELLED: [NotificationChannel.EMAIL],
        NotificationType.SUBSCRIPTION_REACTIVATED: [NotificationChannel.EMAIL, NotificationChannel.PUSH],
        NotificationType.DOCUMENT_PROCESSED: [NotificationChannel.PUSH],
        NotificationType.DOCUMENT_FAILED: [NotificationChannel.EMAIL, NotificationChannel.PUSH],
        NotificationType.AGENT_READY: [NotificationChannel.PUSH],
        NotificationType.AGENT_ERROR: [NotificationChannel.EMAIL, NotificationChannel.PUSH],
        NotificationType.SYSTEM_ALERT: [NotificationChannel.SLACK],
        NotificationType.SECURITY_ALERT: [NotificationChannel.EMAIL, NotificationChannel.SLACK],
    }

    async def send(
        self,
        notification_type: NotificationType,
        recipient_email: str,
        recipient_phone: str = None,
        recipient_user_id: str = None,
        tenant_name: str = None,
        data: Dict[str, Any] = None,
        channels: List[NotificationChannel] = None,
    ) -> List[NotificationResult]:
        """
        Send notification through appropriate channels.

        Args:
            notification_type: Type of notification
            recipient_email: Email address
            recipient_phone: Phone number (optional, for SMS)
            recipient_user_id: User ID (for push notifications)
            tenant_name: Tenant name for context
            data: Additional data for templates
            channels: Override default channels

        Returns:
            List of NotificationResult for each channel
        """
        results = []
        data = data or {}

        # Determine channels to use
        active_channels = channels or self.DEFAULT_CHANNELS.get(
            notification_type, [NotificationChannel.EMAIL]
        )

        for channel in active_channels:
            try:
                if channel == NotificationChannel.EMAIL:
                    result = await self._send_email(
                        notification_type, recipient_email, tenant_name, data
                    )
                elif channel == NotificationChannel.SMS and recipient_phone:
                    result = await self._send_sms(
                        notification_type, recipient_phone, tenant_name, data
                    )
                elif channel == NotificationChannel.PUSH and recipient_user_id:
                    result = await self._send_push(
                        notification_type, recipient_user_id, tenant_name, data
                    )
                elif channel == NotificationChannel.SLACK:
                    result = await self._send_slack(
                        notification_type, tenant_name, data
                    )
                else:
                    continue

                results.append(result)
            except Exception as e:
                logger.error(f"Notification error ({channel}): {e}")
                results.append(NotificationResult(
                    channel=channel,
                    success=False,
                    error=str(e),
                ))

        return results

    async def _send_email(
        self,
        notification_type: NotificationType,
        recipient_email: str,
        tenant_name: str,
        data: Dict[str, Any],
    ) -> NotificationResult:
        """Send email notification."""
        templates = {
            NotificationType.WELCOME: ("welcome", "Bienvenido a AIPanel"),
            NotificationType.PASSWORD_RESET: ("password_reset", "Restablecer Contrasena"),
            NotificationType.USAGE_WARNING: ("usage_alert", "Alerta de Uso"),
            NotificationType.USAGE_CRITICAL: ("usage_alert", "Uso Critico"),
            NotificationType.PAYMENT_SUCCESS: ("payment_receipt", "Comprobante de Pago"),
            NotificationType.PAYMENT_FAILED: ("subscription_status", "Pago Fallido"),
            NotificationType.SUBSCRIPTION_EXPIRING: ("subscription_status", "Suscripcion por Vencer"),
        }

        template, default_subject = templates.get(
            notification_type, ("base", "Notificacion de AIPanel")
        )

        result = await email_service.send_email(
            to=recipient_email,
            subject=data.get("subject", default_subject),
            template=template,
            context={
                "user_name": data.get("user_name", "Usuario"),
                "tenant_name": tenant_name,
                **data,
            },
        )

        return NotificationResult(
            channel=NotificationChannel.EMAIL,
            success=result.get("success", False),
            message_id=result.get("message_id"),
            error=result.get("error"),
        )

    async def _send_sms(
        self,
        notification_type: NotificationType,
        recipient_phone: str,
        tenant_name: str,
        data: Dict[str, Any],
    ) -> NotificationResult:
        """Send SMS notification."""
        messages = {
            NotificationType.PAYMENT_FAILED: "AIPanel: Tu pago fallo. Actualiza tu metodo de pago en {url}",
            NotificationType.USAGE_CRITICAL: "AIPanel: Has usado {percentage}% de tus tokens. Actualiza tu plan.",
            NotificationType.SECURITY_ALERT: "AIPanel: Alerta de seguridad en tu cuenta. Revisa tu email.",
        }

        message_template = messages.get(notification_type, "AIPanel: {message}")
        message = message_template.format(**data)

        result = await sms_client.send_sms(
            to=recipient_phone,
            message=message,
        )

        return NotificationResult(
            channel=NotificationChannel.SMS,
            success=result.get("error") is None,
            message_id=result.get("sid"),
            error=result.get("error"),
        )

    async def _send_push(
        self,
        notification_type: NotificationType,
        recipient_user_id: str,
        tenant_name: str,
        data: Dict[str, Any],
    ) -> NotificationResult:
        """Send push notification."""
        push_configs = {
            NotificationType.USAGE_WARNING: ("⚠️ Alerta de Uso", "Has usado {percentage}% de tus tokens", "/usage"),
            NotificationType.USAGE_CRITICAL: ("🚨 Uso Critico", "Has usado {percentage}% de tus tokens", "/usage"),
            NotificationType.PAYMENT_SUCCESS: ("💰 Pago Confirmado", "Pago de ${amount} procesado", "/billing"),
            NotificationType.PAYMENT_FAILED: ("❌ Pago Fallido", "No pudimos procesar tu pago", "/billing"),
            NotificationType.DOCUMENT_PROCESSED: ("📄 Documento Listo", "{document_name} fue procesado", "/documents"),
            NotificationType.AGENT_READY: ("🤖 Agente Listo", "{agent_name} esta listo", "/agents"),
        }

        config = push_configs.get(notification_type)
        if not config:
            return NotificationResult(
                channel=NotificationChannel.PUSH,
                success=False,
                error="Notification type not configured for push",
            )

        title, message_template, url = config
        message = message_template.format(**data)

        result = await push_service.send_to_user(
            user_id=recipient_user_id,
            title=title,
            message=message,
            data={"type": notification_type.value, **data},
            url=url,
        )

        return NotificationResult(
            channel=NotificationChannel.PUSH,
            success=result.get("success", False),
            message_id=result.get("notification_id"),
            error=result.get("error"),
        )

    async def _send_slack(
        self,
        notification_type: NotificationType,
        tenant_name: str,
        data: Dict[str, Any],
    ) -> NotificationResult:
        """Send Slack notification."""
        if notification_type == NotificationType.USAGE_CRITICAL:
            result = await slack_client.send_usage_alert(
                tenant_name=tenant_name or "Unknown",
                usage_percentage=data.get("percentage", 0),
                tokens_used=data.get("tokens_used", 0),
                tokens_limit=data.get("tokens_limit", 0),
            )
        elif notification_type in (NotificationType.PAYMENT_SUCCESS, NotificationType.PAYMENT_FAILED):
            result = await slack_client.send_payment_notification(
                tenant_name=tenant_name or "Unknown",
                amount=data.get("amount", 0),
                status="success" if notification_type == NotificationType.PAYMENT_SUCCESS else "failed",
                transaction_id=data.get("transaction_id"),
            )
        elif notification_type == NotificationType.SYSTEM_ALERT:
            result = await slack_client.send_error_alert(
                error_type=data.get("error_type", "Unknown"),
                error_message=data.get("error_message", "No message"),
                context=data.get("context"),
            )
        else:
            result = await slack_client.send_webhook(
                text=f"[{notification_type.value}] {tenant_name}: {data.get('message', 'Notification')}",
            )

        return NotificationResult(
            channel=NotificationChannel.SLACK,
            success=result.get("success", False),
            error=result.get("error"),
        )

    # Convenience methods for common notifications

    async def notify_usage_warning(
        self,
        email: str,
        user_id: str,
        tenant_name: str,
        percentage: int,
        tokens_used: int,
        tokens_limit: int,
    ) -> List[NotificationResult]:
        """Send usage warning notification."""
        notification_type = (
            NotificationType.USAGE_CRITICAL if percentage >= 90
            else NotificationType.USAGE_WARNING
        )

        return await self.send(
            notification_type=notification_type,
            recipient_email=email,
            recipient_user_id=user_id,
            tenant_name=tenant_name,
            data={
                "percentage": percentage,
                "tokens_used": tokens_used,
                "tokens_limit": tokens_limit,
                "tokens_remaining": tokens_limit - tokens_used,
            },
        )

    async def notify_payment(
        self,
        email: str,
        user_id: str,
        tenant_name: str,
        success: bool,
        amount: int,
        transaction_id: str = None,
    ) -> List[NotificationResult]:
        """Send payment notification."""
        return await self.send(
            notification_type=(
                NotificationType.PAYMENT_SUCCESS if success
                else NotificationType.PAYMENT_FAILED
            ),
            recipient_email=email,
            recipient_user_id=user_id,
            tenant_name=tenant_name,
            data={
                "amount": amount,
                "transaction_id": transaction_id,
            },
        )


# Global service instance
notification_service = NotificationService()
