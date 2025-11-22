"""
Payments Module - Service

Business logic for payments and subscriptions with Transbank.
"""

import uuid
from typing import Optional
from datetime import datetime, timedelta

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Payment, Tenant, Agent, Document
from app.models.enums import PaymentStatus as DBPaymentStatus
from app.integrations.transbank_client import get_transbank_client, TransbankClient
from app.utils.logger import get_logger

from .schemas import (
    PaymentStatus,
    PaymentMethod,
    SubscriptionPlan,
    PaymentResponse,
    PaymentConfirmResponse,
    SubscriptionResponse,
    PaymentHistoryItem,
    PaymentHistoryResponse,
    InvoiceResponse,
    PLANS,
)

logger = get_logger(__name__)

# IVA (Chilean VAT) rate
IVA_RATE = 0.19


class PaymentService:
    """
    Payment service for subscriptions and billing.

    Features:
    - Subscription plan management
    - Payment processing with Transbank
    - Invoice generation
    - Payment history
    """

    def __init__(self, db: AsyncSession):
        """Initialize with database session."""
        self.db = db
        self.transbank: TransbankClient = get_transbank_client()

    async def create_payment(
        self,
        tenant_id: str,
        plan: SubscriptionPlan,
        return_url: str,
    ) -> PaymentResponse:
        """
        Create a new payment for subscription.

        Args:
            tenant_id: Tenant ID
            plan: Subscription plan to purchase
            return_url: URL to redirect after payment

        Returns:
            PaymentResponse with redirect URL
        """
        # Get plan details
        plan_details = PLANS.get(plan)
        if not plan_details:
            raise ValueError(f"Invalid plan: {plan}")

        if plan_details.price_clp == 0:
            raise ValueError("Free plan doesn't require payment")

        # Generate unique order ID
        buy_order = f"PAY-{uuid.uuid4().hex[:16].upper()}"
        session_id = f"SES-{tenant_id[:8]}-{uuid.uuid4().hex[:8]}"

        # Create transaction with Transbank
        result = await self.transbank.create_transaction(
            buy_order=buy_order,
            session_id=session_id,
            amount=plan_details.price_clp,
            return_url=return_url,
        )

        if not result.success:
            raise ValueError(f"Payment creation failed: {result.error_message}")

        # Create payment record
        payment = Payment(
            tenant_id=tenant_id,
            amount=plan_details.price_clp,
            currency="CLP",
            status=DBPaymentStatus.PENDING,
            payment_method="webpay",
            plan=plan.value,
            transbank_token=result.token,
            transbank_buy_order=buy_order,
            transbank_session_id=session_id,
        )
        self.db.add(payment)
        await self.db.commit()
        await self.db.refresh(payment)

        logger.info(f"Payment created: {payment.id} for tenant {tenant_id}")

        # Build redirect URL
        redirect_url = f"{result.url}?token_ws={result.token}"

        return PaymentResponse(
            id=payment.id,
            tenant_id=tenant_id,
            amount=plan_details.price_clp,
            currency="CLP",
            status=PaymentStatus.PENDING,
            payment_method=PaymentMethod.WEBPAY,
            plan=plan,
            transbank_token=result.token,
            redirect_url=redirect_url,
            created_at=payment.created_at,
        )

    async def confirm_payment(
        self,
        token_ws: str,
    ) -> PaymentConfirmResponse:
        """
        Confirm a payment after Transbank callback.

        Args:
            token_ws: Token from Transbank callback

        Returns:
            PaymentConfirmResponse with result
        """
        # Find payment by token
        result = await self.db.execute(
            select(Payment).where(Payment.transbank_token == token_ws)
        )
        payment = result.scalar_one_or_none()

        if not payment:
            raise ValueError("Payment not found")

        if payment.status != DBPaymentStatus.PENDING:
            return PaymentConfirmResponse(
                payment_id=payment.id,
                status=PaymentStatus(payment.status.value),
                amount=payment.amount,
                message="Payment already processed",
            )

        # Confirm with Transbank
        tx_result = await self.transbank.confirm_transaction(token_ws)

        if tx_result.success:
            payment.status = DBPaymentStatus.COMPLETED
            payment.transbank_authorization_code = tx_result.authorization_code
            payment.completed_at = tx_result.transaction_date or datetime.utcnow()

            # Update tenant subscription
            await self._update_subscription(
                tenant_id=payment.tenant_id,
                plan=SubscriptionPlan(payment.plan),
            )

            message = "Payment completed successfully"
            logger.info(f"Payment confirmed: {payment.id}")
        else:
            payment.status = DBPaymentStatus.FAILED
            payment.error_message = tx_result.error_message
            message = f"Payment failed: {tx_result.error_message}"
            logger.warning(f"Payment failed: {payment.id} - {tx_result.error_message}")

        await self.db.commit()

        return PaymentConfirmResponse(
            payment_id=payment.id,
            status=PaymentStatus(payment.status.value),
            authorization_code=tx_result.authorization_code,
            transaction_date=tx_result.transaction_date,
            amount=payment.amount,
            message=message,
        )

    async def get_subscription(
        self,
        tenant_id: str,
    ) -> SubscriptionResponse:
        """Get current subscription for a tenant."""
        # Get tenant
        result = await self.db.execute(
            select(Tenant).where(Tenant.id == tenant_id)
        )
        tenant = result.scalar_one_or_none()

        if not tenant:
            raise ValueError("Tenant not found")

        # Get current plan (default to FREE)
        current_plan = SubscriptionPlan(tenant.plan) if hasattr(tenant, 'plan') and tenant.plan else SubscriptionPlan.FREE
        plan_details = PLANS[current_plan]

        # Count agents
        agents_result = await self.db.execute(
            select(func.count(Agent.id)).where(Agent.tenant_id == tenant_id)
        )
        agents_count = agents_result.scalar() or 0

        # Count documents
        docs_result = await self.db.execute(
            select(func.count(Document.id)).where(Document.tenant_id == tenant_id)
        )
        documents_count = docs_result.scalar() or 0

        # Get token usage (from usage module - simplified here)
        tokens_used = getattr(tenant, 'tokens_used_this_period', 0) or 0
        tokens_remaining = max(0, plan_details.tokens_monthly - tokens_used)

        # Period dates
        period_start = getattr(tenant, 'current_period_start', None) or datetime.utcnow().replace(day=1)
        period_end = (period_start + timedelta(days=32)).replace(day=1) - timedelta(days=1)

        return SubscriptionResponse(
            tenant_id=tenant_id,
            plan=current_plan,
            plan_details=plan_details,
            tokens_used=tokens_used,
            tokens_remaining=tokens_remaining,
            agents_count=agents_count,
            documents_count=documents_count,
            current_period_start=period_start,
            current_period_end=period_end,
            is_active=True,
        )

    async def get_payment_history(
        self,
        tenant_id: str,
        limit: int = 20,
        offset: int = 0,
    ) -> PaymentHistoryResponse:
        """Get payment history for a tenant."""
        # Count total
        count_result = await self.db.execute(
            select(func.count(Payment.id)).where(Payment.tenant_id == tenant_id)
        )
        total = count_result.scalar() or 0

        # Get payments
        result = await self.db.execute(
            select(Payment)
            .where(Payment.tenant_id == tenant_id)
            .order_by(Payment.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        payments = result.scalars().all()

        return PaymentHistoryResponse(
            payments=[
                PaymentHistoryItem(
                    id=p.id,
                    amount=p.amount,
                    currency=p.currency,
                    status=PaymentStatus(p.status.value),
                    plan=SubscriptionPlan(p.plan),
                    created_at=p.created_at,
                    completed_at=p.completed_at,
                )
                for p in payments
            ],
            total=total,
        )

    async def get_invoice(
        self,
        payment_id: str,
        tenant_id: str,
    ) -> Optional[InvoiceResponse]:
        """Generate invoice for a completed payment."""
        result = await self.db.execute(
            select(Payment).where(
                Payment.id == payment_id,
                Payment.tenant_id == tenant_id,
                Payment.status == DBPaymentStatus.COMPLETED,
            )
        )
        payment = result.scalar_one_or_none()

        if not payment:
            return None

        # Calculate tax
        net_amount = int(payment.amount / (1 + IVA_RATE))
        tax = payment.amount - net_amount

        # Period calculation
        period_start = payment.completed_at or payment.created_at
        period_end = (period_start + timedelta(days=32)).replace(day=1) - timedelta(days=1)

        # Invoice number
        invoice_number = f"INV-{period_start.strftime('%Y%m')}-{payment.id[:8].upper()}"

        return InvoiceResponse(
            id=str(uuid.uuid4()),
            payment_id=payment.id,
            tenant_id=tenant_id,
            amount=net_amount,
            tax=tax,
            total=payment.amount,
            plan=SubscriptionPlan(payment.plan),
            period_start=period_start,
            period_end=period_end,
            issued_at=datetime.utcnow(),
            invoice_number=invoice_number,
        )

    async def _update_subscription(
        self,
        tenant_id: str,
        plan: SubscriptionPlan,
    ) -> None:
        """Update tenant subscription after successful payment."""
        result = await self.db.execute(
            select(Tenant).where(Tenant.id == tenant_id)
        )
        tenant = result.scalar_one_or_none()

        if tenant:
            tenant.plan = plan.value
            tenant.current_period_start = datetime.utcnow()
            tenant.tokens_used_this_period = 0
            await self.db.flush()

            logger.info(f"Subscription updated: tenant {tenant_id} -> {plan.value}")
