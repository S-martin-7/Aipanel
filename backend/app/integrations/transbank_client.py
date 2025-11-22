"""
Transbank Integration - WebPay Plus Client

Handles payment processing with Transbank's WebPay Plus for Chilean market.
"""

import httpx
from typing import Optional
from dataclasses import dataclass
from datetime import datetime

from app.core.config import settings
from app.utils.logger import get_logger

logger = get_logger(__name__)

# Transbank endpoints
TRANSBANK_INTEGRATION_URL = "https://webpay3gint.transbank.cl"
TRANSBANK_PRODUCTION_URL = "https://webpay3g.transbank.cl"

# Integration credentials (for testing)
INTEGRATION_COMMERCE_CODE = "597055555532"
INTEGRATION_API_KEY = "579B532A7440BB0C9079DED94D31EA1615BACEB56610332264630D42D0A36B1C"


@dataclass
class TransactionResult:
    """Result of a Transbank transaction."""
    success: bool
    token: Optional[str] = None
    url: Optional[str] = None
    authorization_code: Optional[str] = None
    response_code: Optional[int] = None
    transaction_date: Optional[datetime] = None
    amount: Optional[int] = None
    buy_order: Optional[str] = None
    session_id: Optional[str] = None
    card_number: Optional[str] = None  # Last 4 digits
    error_message: Optional[str] = None


class TransbankClient:
    """
    Transbank WebPay Plus client.

    Supports:
    - Transaction creation
    - Transaction confirmation
    - Transaction status check
    - Refunds
    """

    def __init__(
        self,
        commerce_code: Optional[str] = None,
        api_key: Optional[str] = None,
        is_production: bool = False,
    ):
        """
        Initialize Transbank client.

        Args:
            commerce_code: Transbank commerce code
            api_key: Transbank API key
            is_production: Use production environment
        """
        self.is_production = is_production

        if is_production:
            self.commerce_code = commerce_code or settings.TRANSBANK_COMMERCE_CODE
            self.api_key = api_key or settings.TRANSBANK_API_KEY
            self.base_url = TRANSBANK_PRODUCTION_URL
        else:
            # Use integration (test) credentials
            self.commerce_code = INTEGRATION_COMMERCE_CODE
            self.api_key = INTEGRATION_API_KEY
            self.base_url = TRANSBANK_INTEGRATION_URL

        self.headers = {
            "Tbk-Api-Key-Id": self.commerce_code,
            "Tbk-Api-Key-Secret": self.api_key,
            "Content-Type": "application/json",
        }

    async def create_transaction(
        self,
        buy_order: str,
        session_id: str,
        amount: int,
        return_url: str,
    ) -> TransactionResult:
        """
        Create a new WebPay Plus transaction.

        Args:
            buy_order: Unique order identifier (max 26 chars)
            session_id: Session identifier (max 61 chars)
            amount: Amount in CLP (Chilean Pesos)
            return_url: URL to redirect after payment

        Returns:
            TransactionResult with token and redirect URL
        """
        url = f"{self.base_url}/rswebpaytransaction/api/webpay/v1.2/transactions"

        payload = {
            "buy_order": buy_order[:26],
            "session_id": session_id[:61],
            "amount": amount,
            "return_url": return_url,
        }

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    url,
                    json=payload,
                    headers=self.headers,
                    timeout=30.0,
                )

                if response.status_code == 200:
                    data = response.json()
                    return TransactionResult(
                        success=True,
                        token=data.get("token"),
                        url=data.get("url"),
                        buy_order=buy_order,
                        session_id=session_id,
                        amount=amount,
                    )
                else:
                    logger.error(f"Transbank create error: {response.status_code} - {response.text}")
                    return TransactionResult(
                        success=False,
                        error_message=f"Error {response.status_code}: {response.text}",
                    )

        except Exception as e:
            logger.error(f"Transbank create exception: {e}")
            return TransactionResult(
                success=False,
                error_message=str(e),
            )

    async def confirm_transaction(self, token: str) -> TransactionResult:
        """
        Confirm a WebPay Plus transaction.

        Called after user returns from Transbank payment page.

        Args:
            token: Transaction token (token_ws from callback)

        Returns:
            TransactionResult with authorization details
        """
        url = f"{self.base_url}/rswebpaytransaction/api/webpay/v1.2/transactions/{token}"

        try:
            async with httpx.AsyncClient() as client:
                response = await client.put(
                    url,
                    headers=self.headers,
                    timeout=30.0,
                )

                if response.status_code == 200:
                    data = response.json()

                    # Check response code (0 = approved)
                    response_code = data.get("response_code", -1)
                    success = response_code == 0

                    # Parse transaction date
                    tx_date = None
                    if data.get("transaction_date"):
                        try:
                            tx_date = datetime.fromisoformat(
                                data["transaction_date"].replace("Z", "+00:00")
                            )
                        except (ValueError, TypeError):
                            pass

                    return TransactionResult(
                        success=success,
                        token=token,
                        authorization_code=data.get("authorization_code"),
                        response_code=response_code,
                        transaction_date=tx_date,
                        amount=data.get("amount"),
                        buy_order=data.get("buy_order"),
                        session_id=data.get("session_id"),
                        card_number=data.get("card_detail", {}).get("card_number"),
                        error_message=None if success else f"Response code: {response_code}",
                    )
                else:
                    logger.error(f"Transbank confirm error: {response.status_code} - {response.text}")
                    return TransactionResult(
                        success=False,
                        token=token,
                        error_message=f"Error {response.status_code}: {response.text}",
                    )

        except Exception as e:
            logger.error(f"Transbank confirm exception: {e}")
            return TransactionResult(
                success=False,
                token=token,
                error_message=str(e),
            )

    async def get_transaction_status(self, token: str) -> TransactionResult:
        """
        Get status of a transaction.

        Args:
            token: Transaction token

        Returns:
            TransactionResult with current status
        """
        url = f"{self.base_url}/rswebpaytransaction/api/webpay/v1.2/transactions/{token}"

        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    url,
                    headers=self.headers,
                    timeout=30.0,
                )

                if response.status_code == 200:
                    data = response.json()
                    return TransactionResult(
                        success=True,
                        token=token,
                        authorization_code=data.get("authorization_code"),
                        response_code=data.get("response_code"),
                        amount=data.get("amount"),
                        buy_order=data.get("buy_order"),
                    )
                else:
                    return TransactionResult(
                        success=False,
                        token=token,
                        error_message=f"Error {response.status_code}",
                    )

        except Exception as e:
            logger.error(f"Transbank status exception: {e}")
            return TransactionResult(
                success=False,
                token=token,
                error_message=str(e),
            )

    async def refund_transaction(
        self,
        token: str,
        amount: int,
    ) -> TransactionResult:
        """
        Refund a transaction (partial or full).

        Args:
            token: Transaction token
            amount: Amount to refund in CLP

        Returns:
            TransactionResult with refund status
        """
        url = f"{self.base_url}/rswebpaytransaction/api/webpay/v1.2/transactions/{token}/refunds"

        payload = {"amount": amount}

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    url,
                    json=payload,
                    headers=self.headers,
                    timeout=30.0,
                )

                if response.status_code == 200:
                    data = response.json()
                    return TransactionResult(
                        success=data.get("type") == "REVERSED" or data.get("type") == "NULLIFIED",
                        token=token,
                        amount=amount,
                        authorization_code=data.get("authorization_code"),
                    )
                else:
                    return TransactionResult(
                        success=False,
                        token=token,
                        error_message=f"Refund error: {response.status_code}",
                    )

        except Exception as e:
            logger.error(f"Transbank refund exception: {e}")
            return TransactionResult(
                success=False,
                token=token,
                error_message=str(e),
            )


# Singleton instance
_transbank_client: Optional[TransbankClient] = None


def get_transbank_client() -> TransbankClient:
    """Get or create Transbank client instance."""
    global _transbank_client
    if _transbank_client is None:
        is_production = getattr(settings, "TRANSBANK_PRODUCTION", False)
        _transbank_client = TransbankClient(is_production=is_production)
    return _transbank_client
