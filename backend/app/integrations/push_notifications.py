"""
Push notifications integration for AIPanel.

Supports multiple push notification providers:
- OneSignal (primary)
- Firebase Cloud Messaging (FCM)
"""

from typing import Optional, List, Dict, Any
from enum import Enum
import httpx

from app.core.config import settings
from app.utils.logger import get_logger

logger = get_logger(__name__)


class NotificationPriority(str, Enum):
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"


class PushProvider:
    """Base class for push notification providers."""

    async def send_notification(
        self,
        title: str,
        message: str,
        user_ids: List[str] = None,
        segments: List[str] = None,
        data: Dict[str, Any] = None,
    ) -> dict:
        raise NotImplementedError


class OneSignalClient(PushProvider):
    """
    OneSignal push notification client.
    """

    def __init__(
        self,
        app_id: str = None,
        api_key: str = None,
    ):
        self.app_id = app_id or getattr(settings, 'ONESIGNAL_APP_ID', None)
        self.api_key = api_key or getattr(settings, 'ONESIGNAL_API_KEY', None)
        self.api_base = "https://onesignal.com/api/v1"

    async def send_notification(
        self,
        title: str,
        message: str,
        user_ids: List[str] = None,
        segments: List[str] = None,
        data: Dict[str, Any] = None,
        url: str = None,
        priority: NotificationPriority = NotificationPriority.NORMAL,
        ttl: int = 86400,  # 24 hours
        collapse_id: str = None,
        buttons: List[Dict] = None,
        image_url: str = None,
    ) -> dict:
        """
        Send push notification via OneSignal.

        Args:
            title: Notification title
            message: Notification body
            user_ids: List of external user IDs (tenant user IDs)
            segments: List of OneSignal segments (e.g., ["All", "Active Users"])
            data: Additional data payload
            url: URL to open when notification is clicked
            priority: Notification priority
            ttl: Time to live in seconds
            collapse_id: Collapse key for grouping notifications
            buttons: Action buttons
            image_url: Big picture image URL

        Returns:
            Response dict
        """
        if not self.app_id or not self.api_key:
            logger.warning("OneSignal not configured")
            return {"success": False, "error": "OneSignal not configured"}

        # Build notification payload
        payload = {
            "app_id": self.app_id,
            "headings": {"en": title, "es": title},
            "contents": {"en": message, "es": message},
            "priority": 10 if priority == NotificationPriority.HIGH else 5,
            "ttl": ttl,
        }

        # Target users
        if user_ids:
            payload["include_external_user_ids"] = user_ids
        elif segments:
            payload["included_segments"] = segments
        else:
            # Default to all subscribed users
            payload["included_segments"] = ["Subscribed Users"]

        # Optional fields
        if data:
            payload["data"] = data
        if url:
            payload["url"] = url
        if collapse_id:
            payload["collapse_id"] = collapse_id
        if buttons:
            payload["buttons"] = buttons
        if image_url:
            payload["big_picture"] = image_url
            payload["ios_attachments"] = {"image": image_url}

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.api_base}/notifications",
                    headers={
                        "Authorization": f"Basic {self.api_key}",
                        "Content-Type": "application/json",
                    },
                    json=payload,
                    timeout=10.0,
                )

                data = response.json()

                if response.status_code == 200:
                    return {
                        "success": True,
                        "notification_id": data.get("id"),
                        "recipients": data.get("recipients"),
                        "external_id": data.get("external_id"),
                    }
                else:
                    return {
                        "success": False,
                        "error": data.get("errors", response.text),
                    }
        except Exception as e:
            logger.error(f"OneSignal error: {e}")
            return {"success": False, "error": str(e)}

    async def cancel_notification(self, notification_id: str) -> dict:
        """Cancel a scheduled notification."""
        if not self.app_id or not self.api_key:
            return {"success": False, "error": "OneSignal not configured"}

        try:
            async with httpx.AsyncClient() as client:
                response = await client.delete(
                    f"{self.api_base}/notifications/{notification_id}",
                    params={"app_id": self.app_id},
                    headers={"Authorization": f"Basic {self.api_key}"},
                    timeout=10.0,
                )

                if response.status_code == 200:
                    return {"success": True}
                else:
                    return {"success": False, "error": response.text}
        except Exception as e:
            logger.error(f"OneSignal cancel error: {e}")
            return {"success": False, "error": str(e)}


class PushNotificationService:
    """
    High-level push notification service.
    """

    def __init__(self):
        self.onesignal = OneSignalClient()

    async def send_to_user(
        self,
        user_id: str,
        title: str,
        message: str,
        data: Dict[str, Any] = None,
        url: str = None,
    ) -> dict:
        """Send push notification to a specific user."""
        return await self.onesignal.send_notification(
            title=title,
            message=message,
            user_ids=[user_id],
            data=data,
            url=url,
        )

    async def send_to_users(
        self,
        user_ids: List[str],
        title: str,
        message: str,
        data: Dict[str, Any] = None,
    ) -> dict:
        """Send push notification to multiple users."""
        return await self.onesignal.send_notification(
            title=title,
            message=message,
            user_ids=user_ids,
            data=data,
        )

    async def send_to_tenant(
        self,
        tenant_id: str,
        title: str,
        message: str,
        data: Dict[str, Any] = None,
    ) -> dict:
        """
        Send push notification to all users of a tenant.

        Uses a tenant-specific segment.
        """
        return await self.onesignal.send_notification(
            title=title,
            message=message,
            segments=[f"tenant_{tenant_id}"],
            data=data,
        )

    async def broadcast(
        self,
        title: str,
        message: str,
        data: Dict[str, Any] = None,
    ) -> dict:
        """Broadcast notification to all users."""
        return await self.onesignal.send_notification(
            title=title,
            message=message,
            segments=["All"],
            data=data,
        )

    # Pre-built notification templates

    async def send_usage_alert(
        self,
        user_id: str,
        usage_percentage: int,
        tokens_remaining: int,
    ) -> dict:
        """Send usage alert push notification."""
        emoji = "⚠️" if usage_percentage < 90 else "🚨"
        title = f"{emoji} Alerta de Uso"
        message = f"Has usado {usage_percentage}% de tus tokens. Te quedan {tokens_remaining:,} tokens."

        return await self.send_to_user(
            user_id=user_id,
            title=title,
            message=message,
            data={
                "type": "usage_alert",
                "usage_percentage": usage_percentage,
            },
            url="/usage",
        )

    async def send_payment_success(
        self,
        user_id: str,
        amount: int,
        plan_name: str,
    ) -> dict:
        """Send payment success notification."""
        return await self.send_to_user(
            user_id=user_id,
            title="💰 Pago Confirmado",
            message=f"Tu pago de ${amount:,} CLP fue procesado. Plan: {plan_name}",
            data={
                "type": "payment_success",
                "amount": amount,
            },
            url="/billing",
        )

    async def send_payment_failed(
        self,
        user_id: str,
        reason: str = None,
    ) -> dict:
        """Send payment failed notification."""
        message = "No pudimos procesar tu pago."
        if reason:
            message += f" Razon: {reason}"

        return await self.send_to_user(
            user_id=user_id,
            title="❌ Pago Fallido",
            message=message,
            data={"type": "payment_failed"},
            url="/billing/payment-method",
        )

    async def send_agent_ready(
        self,
        user_id: str,
        agent_name: str,
    ) -> dict:
        """Send notification when agent is ready."""
        return await self.send_to_user(
            user_id=user_id,
            title="🤖 Agente Listo",
            message=f"Tu agente '{agent_name}' esta listo para usar.",
            data={
                "type": "agent_ready",
                "agent_name": agent_name,
            },
            url="/agents",
        )

    async def send_document_processed(
        self,
        user_id: str,
        document_name: str,
        chunks_created: int,
    ) -> dict:
        """Send notification when document processing is complete."""
        return await self.send_to_user(
            user_id=user_id,
            title="📄 Documento Procesado",
            message=f"'{document_name}' fue procesado exitosamente ({chunks_created} fragmentos).",
            data={
                "type": "document_processed",
                "document_name": document_name,
            },
            url="/documents",
        )

    async def send_subscription_expiring(
        self,
        user_id: str,
        days_remaining: int,
    ) -> dict:
        """Send subscription expiring soon notification."""
        return await self.send_to_user(
            user_id=user_id,
            title="⏰ Suscripcion por Vencer",
            message=f"Tu suscripcion vence en {days_remaining} dias. Renueva para no perder acceso.",
            data={
                "type": "subscription_expiring",
                "days_remaining": days_remaining,
            },
            url="/billing",
        )


# Global service instance
push_service = PushNotificationService()
