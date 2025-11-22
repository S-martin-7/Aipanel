"""
Slack integration for AIPanel notifications.

Sends notifications to Slack channels via webhooks and Bot API.
"""

from typing import Optional, List, Dict, Any
import httpx

from app.core.config import settings
from app.utils.logger import get_logger

logger = get_logger(__name__)


class SlackClient:
    """
    Slack notification client.

    Supports both webhook-based and Bot API notifications.
    """

    def __init__(
        self,
        webhook_url: str = None,
        bot_token: str = None,
    ):
        self.webhook_url = webhook_url or getattr(settings, 'SLACK_WEBHOOK_URL', None)
        self.bot_token = bot_token or getattr(settings, 'SLACK_BOT_TOKEN', None)
        self.api_base = "https://slack.com/api"

    async def send_webhook(
        self,
        text: str,
        blocks: List[Dict] = None,
        attachments: List[Dict] = None,
        channel: str = None,
    ) -> dict:
        """
        Send message via Slack webhook.

        Args:
            text: Fallback text for notifications
            blocks: Slack Block Kit blocks
            attachments: Legacy attachments
            channel: Override channel (if webhook supports it)

        Returns:
            Response dict
        """
        if not self.webhook_url:
            logger.warning("Slack webhook URL not configured")
            return {"success": False, "error": "Webhook URL not configured"}

        payload = {"text": text}

        if blocks:
            payload["blocks"] = blocks
        if attachments:
            payload["attachments"] = attachments
        if channel:
            payload["channel"] = channel

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    self.webhook_url,
                    json=payload,
                    timeout=10.0,
                )

                if response.status_code == 200:
                    return {"success": True}
                else:
                    return {
                        "success": False,
                        "error": response.text,
                        "status_code": response.status_code,
                    }
        except Exception as e:
            logger.error(f"Slack webhook error: {e}")
            return {"success": False, "error": str(e)}

    async def send_message(
        self,
        channel: str,
        text: str,
        blocks: List[Dict] = None,
        thread_ts: str = None,
    ) -> dict:
        """
        Send message via Slack Bot API.

        Args:
            channel: Channel ID or name
            text: Message text
            blocks: Slack Block Kit blocks
            thread_ts: Thread timestamp for replies

        Returns:
            Response dict with message details
        """
        if not self.bot_token:
            logger.warning("Slack bot token not configured")
            return {"success": False, "error": "Bot token not configured"}

        payload = {
            "channel": channel,
            "text": text,
        }

        if blocks:
            payload["blocks"] = blocks
        if thread_ts:
            payload["thread_ts"] = thread_ts

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.api_base}/chat.postMessage",
                    headers={"Authorization": f"Bearer {self.bot_token}"},
                    json=payload,
                    timeout=10.0,
                )

                data = response.json()

                if data.get("ok"):
                    return {
                        "success": True,
                        "channel": data.get("channel"),
                        "ts": data.get("ts"),
                        "message": data.get("message"),
                    }
                else:
                    return {
                        "success": False,
                        "error": data.get("error"),
                    }
        except Exception as e:
            logger.error(f"Slack API error: {e}")
            return {"success": False, "error": str(e)}

    # Pre-built notification templates

    async def send_usage_alert(
        self,
        tenant_name: str,
        usage_percentage: int,
        tokens_used: int,
        tokens_limit: int,
        channel: str = None,
    ) -> dict:
        """Send usage alert notification."""
        emoji = "⚠️" if usage_percentage < 90 else "🚨"
        color = "#FFA500" if usage_percentage < 90 else "#FF0000"

        blocks = [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": f"{emoji} Alerta de Uso - {tenant_name}",
                    "emoji": True,
                }
            },
            {
                "type": "section",
                "fields": [
                    {
                        "type": "mrkdwn",
                        "text": f"*Uso actual:*\n{usage_percentage}%"
                    },
                    {
                        "type": "mrkdwn",
                        "text": f"*Tokens usados:*\n{tokens_used:,} / {tokens_limit:,}"
                    }
                ]
            },
            {
                "type": "context",
                "elements": [
                    {
                        "type": "mrkdwn",
                        "text": f"Tenant: {tenant_name}"
                    }
                ]
            }
        ]

        text = f"{emoji} Alerta: {tenant_name} ha usado {usage_percentage}% de sus tokens"

        if channel:
            return await self.send_message(channel, text, blocks)
        else:
            return await self.send_webhook(text, blocks)

    async def send_payment_notification(
        self,
        tenant_name: str,
        amount: int,
        currency: str = "CLP",
        status: str = "success",
        transaction_id: str = None,
        channel: str = None,
    ) -> dict:
        """Send payment notification."""
        emoji = "💰" if status == "success" else "❌"
        color = "#28A745" if status == "success" else "#DC3545"
        status_text = "Exitoso" if status == "success" else "Fallido"

        blocks = [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": f"{emoji} Pago {status_text}",
                    "emoji": True,
                }
            },
            {
                "type": "section",
                "fields": [
                    {
                        "type": "mrkdwn",
                        "text": f"*Tenant:*\n{tenant_name}"
                    },
                    {
                        "type": "mrkdwn",
                        "text": f"*Monto:*\n${amount:,} {currency}"
                    }
                ]
            }
        ]

        if transaction_id:
            blocks.append({
                "type": "context",
                "elements": [
                    {
                        "type": "mrkdwn",
                        "text": f"ID Transaccion: `{transaction_id}`"
                    }
                ]
            })

        text = f"{emoji} Pago {status_text}: {tenant_name} - ${amount:,} {currency}"

        if channel:
            return await self.send_message(channel, text, blocks)
        else:
            return await self.send_webhook(text, blocks)

    async def send_new_tenant_notification(
        self,
        tenant_name: str,
        tenant_email: str,
        plan: str,
        channel: str = None,
    ) -> dict:
        """Send new tenant registration notification."""
        blocks = [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": "🎉 Nuevo Tenant Registrado",
                    "emoji": True,
                }
            },
            {
                "type": "section",
                "fields": [
                    {
                        "type": "mrkdwn",
                        "text": f"*Nombre:*\n{tenant_name}"
                    },
                    {
                        "type": "mrkdwn",
                        "text": f"*Email:*\n{tenant_email}"
                    },
                    {
                        "type": "mrkdwn",
                        "text": f"*Plan:*\n{plan}"
                    }
                ]
            }
        ]

        text = f"🎉 Nuevo tenant: {tenant_name} ({tenant_email}) - Plan: {plan}"

        if channel:
            return await self.send_message(channel, text, blocks)
        else:
            return await self.send_webhook(text, blocks)

    async def send_error_alert(
        self,
        error_type: str,
        error_message: str,
        context: Dict[str, Any] = None,
        channel: str = None,
    ) -> dict:
        """Send error alert notification."""
        blocks = [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": "🚨 Error en AIPanel",
                    "emoji": True,
                }
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*Tipo:* {error_type}\n*Mensaje:* {error_message}"
                }
            }
        ]

        if context:
            context_str = "\n".join([f"• {k}: {v}" for k, v in context.items()])
            blocks.append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*Contexto:*\n{context_str}"
                }
            })

        text = f"🚨 Error: {error_type} - {error_message}"

        if channel:
            return await self.send_message(channel, text, blocks)
        else:
            return await self.send_webhook(text, blocks)


# Global client instance
slack_client = SlackClient()
