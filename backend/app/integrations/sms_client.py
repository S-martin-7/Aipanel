"""
SMS Client for sending notifications via Twilio.

Provides SMS notification capabilities for alerts, verifications, etc.
"""

from typing import Optional
from twilio.rest import Client
from twilio.base.exceptions import TwilioRestException

from app.core.config import settings
from app.utils.logger import get_logger

logger = get_logger(__name__)


class SMSClient:
    """Twilio SMS client for sending text messages."""

    def __init__(
        self,
        account_sid: Optional[str] = None,
        auth_token: Optional[str] = None,
        from_number: Optional[str] = None,
    ):
        self.account_sid = account_sid or settings.TWILIO_ACCOUNT_SID
        self.auth_token = auth_token or settings.TWILIO_AUTH_TOKEN
        self.from_number = from_number or settings.TWILIO_FROM_NUMBER

        self._client: Optional[Client] = None

    @property
    def client(self) -> Client:
        """Lazy initialization of Twilio client."""
        if self._client is None:
            if not self.account_sid or not self.auth_token:
                raise ValueError("Twilio credentials not configured")
            self._client = Client(self.account_sid, self.auth_token)
        return self._client

    async def send_sms(
        self,
        to: str,
        message: str,
        from_number: Optional[str] = None,
    ) -> dict:
        """
        Send an SMS message.

        Args:
            to: Destination phone number (E.164 format, e.g., +56912345678)
            message: Message content (max 1600 characters)
            from_number: Optional sender number (defaults to configured number)

        Returns:
            dict with message SID and status

        Raises:
            TwilioRestException: If SMS sending fails
        """
        try:
            # Ensure phone number is in E.164 format
            to_normalized = self._normalize_phone(to)

            msg = self.client.messages.create(
                body=message[:1600],  # Twilio limit
                from_=from_number or self.from_number,
                to=to_normalized,
            )

            logger.info(f"SMS sent successfully to {to_normalized}: {msg.sid}")

            return {
                "sid": msg.sid,
                "status": msg.status,
                "to": to_normalized,
                "error": None,
            }

        except TwilioRestException as e:
            logger.error(f"Failed to send SMS to {to}: {e}")
            return {
                "sid": None,
                "status": "failed",
                "to": to,
                "error": str(e),
            }

    def _normalize_phone(self, phone: str) -> str:
        """Normalize phone number to E.164 format."""
        # Remove spaces and dashes
        phone = phone.replace(" ", "").replace("-", "")

        # If Chilean number without country code
        if phone.startswith("9") and len(phone) == 9:
            phone = "+56" + phone
        elif phone.startswith("56") and not phone.startswith("+"):
            phone = "+" + phone
        elif not phone.startswith("+"):
            phone = "+" + phone

        return phone

    async def send_verification_code(
        self,
        to: str,
        code: str,
    ) -> dict:
        """Send a verification code via SMS."""
        message = f"Tu código de verificación de AIPanel es: {code}. Válido por 10 minutos."
        return await self.send_sms(to, message)

    async def send_alert(
        self,
        to: str,
        alert_type: str,
        details: str,
    ) -> dict:
        """Send an alert notification via SMS."""
        message = f"[AIPanel Alerta] {alert_type}: {details}"
        return await self.send_sms(to, message)

    async def send_payment_notification(
        self,
        to: str,
        amount: int,
        status: str,
    ) -> dict:
        """Send a payment notification via SMS."""
        formatted_amount = f"${amount:,.0f}".replace(",", ".")
        if status == "success":
            message = f"Pago recibido en AIPanel por {formatted_amount} CLP. Gracias por tu preferencia."
        else:
            message = f"Tu pago de {formatted_amount} CLP en AIPanel no pudo ser procesado. Por favor verifica tu método de pago."
        return await self.send_sms(to, message)

    async def send_usage_alert(
        self,
        to: str,
        percentage: int,
        resource: str = "tokens",
    ) -> dict:
        """Send a usage threshold alert via SMS."""
        message = f"[AIPanel] Has usado el {percentage}% de tus {resource} mensuales. Considera actualizar tu plan para evitar interrupciones."
        return await self.send_sms(to, message)


# Singleton instance
_sms_client: Optional[SMSClient] = None


def get_sms_client() -> SMSClient:
    """Get or create the SMS client singleton."""
    global _sms_client
    if _sms_client is None:
        _sms_client = SMSClient()
    return _sms_client
