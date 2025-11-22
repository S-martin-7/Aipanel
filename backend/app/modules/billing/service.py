"""
Billing Module - Service.

Business logic for subscriptions, invoices, and revenue analytics.
"""

from datetime import datetime, timedelta
from decimal import Decimal
from typing import Optional, List
import uuid

from sqlalchemy import select, func, and_, extract
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import (
    Subscription, Invoice, Payment, Tenant, Plan,
    SubscriptionStatus, InvoiceStatus
)
from app.utils.logger import get_logger

from .schemas import (
    CreateSubscriptionRequest,
    UpdateSubscriptionRequest,
    CancelSubscriptionRequest,
    SubscriptionResponse,
    SubscriptionListResponse,
    CreateInvoiceRequest,
    InvoiceResponse,
    InvoiceListResponse,
    RevenueSummary,
    RevenueByPeriod,
    RevenueByPlan,
    RevenueAnalyticsResponse,
    PendingInvoicesSummary,
)

logger = get_logger(__name__)

# IVA Chile
TAX_RATE = Decimal("19")


class BillingService:
    """Service for billing operations."""

    def __init__(self, db: AsyncSession):
        self.db = db

    # ============================================================
    # Subscription Operations
    # ============================================================

    async def create_subscription(
        self,
        request: CreateSubscriptionRequest
    ) -> SubscriptionResponse:
        """Create a new subscription for a tenant."""
        # Verify tenant exists
        tenant_result = await self.db.execute(
            select(Tenant).where(Tenant.id == request.tenant_id)
        )
        tenant = tenant_result.scalar_one_or_none()
        if not tenant:
            raise ValueError("Tenant not found")

        # Get plan details
        plan_result = await self.db.execute(
            select(Plan).where(Plan.code == request.plan_code)
        )
        plan = plan_result.scalar_one_or_none()
        if not plan:
            raise ValueError(f"Plan '{request.plan_code}' not found")

        # Check if tenant already has active subscription
        existing_result = await self.db.execute(
            select(Subscription).where(
                Subscription.tenant_id == request.tenant_id,
                Subscription.status.in_([SubscriptionStatus.ACTIVE, SubscriptionStatus.TRIAL])
            )
        )
        if existing_result.scalar_one_or_none():
            raise ValueError("Tenant already has an active subscription")

        # Calculate amounts
        base_amount = Decimal(plan.price_monthly if request.billing_cycle == "monthly" else plan.price_yearly or plan.price_monthly * 10)
        tax_amount = base_amount * TAX_RATE / 100
        total_amount = base_amount + tax_amount

        # Set dates
        now = datetime.utcnow()
        trial_days = request.trial_days or plan.trial_days

        if trial_days > 0:
            status = SubscriptionStatus.TRIAL
            trial_start = now
            trial_end = now + timedelta(days=trial_days)
            current_period_start = trial_start
            current_period_end = trial_end
            next_payment_date = trial_end
        else:
            status = SubscriptionStatus.ACTIVE
            trial_start = None
            trial_end = None
            current_period_start = now
            if request.billing_cycle == "yearly":
                current_period_end = now + timedelta(days=365)
            else:
                current_period_end = now + timedelta(days=30)
            next_payment_date = current_period_end

        subscription = Subscription(
            tenant_id=request.tenant_id,
            plan_code=request.plan_code,
            status=status,
            billing_cycle=request.billing_cycle,
            current_period_start=current_period_start,
            current_period_end=current_period_end,
            trial_start=trial_start,
            trial_end=trial_end,
            payment_method_id=request.payment_method_id,
            next_payment_date=next_payment_date,
            base_amount=base_amount,
            tax_amount=tax_amount,
            total_amount=total_amount,
        )

        self.db.add(subscription)

        # Update tenant's plan
        tenant.plan_code = request.plan_code
        if trial_days > 0:
            tenant.trial_start = trial_start
            tenant.trial_end = trial_end

        await self.db.commit()
        await self.db.refresh(subscription)

        logger.info(f"Created subscription {subscription.id} for tenant {request.tenant_id}")

        return self._subscription_to_response(subscription)

    async def get_subscription(self, subscription_id: str) -> Optional[SubscriptionResponse]:
        """Get subscription by ID."""
        result = await self.db.execute(
            select(Subscription).where(Subscription.id == subscription_id)
        )
        subscription = result.scalar_one_or_none()
        if not subscription:
            return None
        return self._subscription_to_response(subscription)

    async def get_tenant_subscription(self, tenant_id: str) -> Optional[SubscriptionResponse]:
        """Get active subscription for a tenant."""
        result = await self.db.execute(
            select(Subscription).where(
                Subscription.tenant_id == tenant_id,
                Subscription.status.in_([SubscriptionStatus.ACTIVE, SubscriptionStatus.TRIAL])
            )
        )
        subscription = result.scalar_one_or_none()
        if not subscription:
            return None
        return self._subscription_to_response(subscription)

    async def list_subscriptions(
        self,
        status: Optional[str] = None,
        plan_code: Optional[str] = None,
        limit: int = 50,
        offset: int = 0
    ) -> SubscriptionListResponse:
        """List subscriptions with optional filters."""
        query = select(Subscription)

        if status:
            query = query.where(Subscription.status == status)
        if plan_code:
            query = query.where(Subscription.plan_code == plan_code)

        query = query.order_by(Subscription.created_at.desc()).offset(offset).limit(limit)

        result = await self.db.execute(query)
        subscriptions = result.scalars().all()

        # Get total count
        count_query = select(func.count(Subscription.id))
        if status:
            count_query = count_query.where(Subscription.status == status)
        if plan_code:
            count_query = count_query.where(Subscription.plan_code == plan_code)
        count_result = await self.db.execute(count_query)
        total = count_result.scalar() or 0

        return SubscriptionListResponse(
            items=[self._subscription_to_response(s) for s in subscriptions],
            total=total
        )

    async def cancel_subscription(
        self,
        subscription_id: str,
        request: CancelSubscriptionRequest
    ) -> Optional[SubscriptionResponse]:
        """Cancel a subscription."""
        result = await self.db.execute(
            select(Subscription).where(Subscription.id == subscription_id)
        )
        subscription = result.scalar_one_or_none()
        if not subscription:
            return None

        if request.cancel_immediately:
            subscription.status = SubscriptionStatus.CANCELLED
            subscription.cancelled_at = datetime.utcnow()
        else:
            subscription.cancel_at_period_end = True

        subscription.cancellation_reason = request.reason
        subscription.updated_at = datetime.utcnow()

        await self.db.commit()
        await self.db.refresh(subscription)

        logger.info(f"Cancelled subscription {subscription_id}")

        return self._subscription_to_response(subscription)

    def _subscription_to_response(self, subscription: Subscription) -> SubscriptionResponse:
        """Convert subscription model to response."""
        return SubscriptionResponse(
            id=subscription.id,
            tenant_id=subscription.tenant_id,
            plan_code=subscription.plan_code,
            status=subscription.status,
            billing_cycle=subscription.billing_cycle,
            current_period_start=subscription.current_period_start,
            current_period_end=subscription.current_period_end,
            trial_start=subscription.trial_start,
            trial_end=subscription.trial_end,
            cancelled_at=subscription.cancelled_at,
            cancel_at_period_end=subscription.cancel_at_period_end,
            base_amount=subscription.base_amount,
            discount_amount=subscription.discount_amount,
            tax_amount=subscription.tax_amount,
            total_amount=subscription.total_amount,
            currency=subscription.currency,
            next_payment_date=subscription.next_payment_date,
            created_at=subscription.created_at,
            updated_at=subscription.updated_at,
        )

    # ============================================================
    # Invoice Operations
    # ============================================================

    async def create_invoice(self, request: CreateInvoiceRequest) -> InvoiceResponse:
        """Create an invoice manually."""
        # Generate invoice number
        year = datetime.utcnow().year
        count_result = await self.db.execute(
            select(func.count(Invoice.id)).where(
                extract('year', Invoice.created_at) == year
            )
        )
        count = (count_result.scalar() or 0) + 1
        invoice_number = f"INV-{year}-{count:06d}"

        # Calculate totals
        subtotal = sum(item.total for item in request.line_items)
        tax_amount = subtotal * TAX_RATE / 100
        total = subtotal + tax_amount

        invoice = Invoice(
            tenant_id=request.tenant_id,
            subscription_id=request.subscription_id,
            invoice_number=invoice_number,
            status=InvoiceStatus.PENDING,
            period_start=request.period_start,
            period_end=request.period_end,
            due_date=request.due_date,
            subtotal=subtotal,
            tax_rate=TAX_RATE,
            tax_amount=tax_amount,
            total=total,
            line_items=[item.model_dump() for item in request.line_items],
            notes=request.notes,
        )

        self.db.add(invoice)
        await self.db.commit()
        await self.db.refresh(invoice)

        logger.info(f"Created invoice {invoice_number} for tenant {request.tenant_id}")

        return self._invoice_to_response(invoice)

    async def get_invoice(self, invoice_id: str) -> Optional[InvoiceResponse]:
        """Get invoice by ID."""
        result = await self.db.execute(
            select(Invoice).where(Invoice.id == invoice_id)
        )
        invoice = result.scalar_one_or_none()
        if not invoice:
            return None
        return self._invoice_to_response(invoice)

    async def list_invoices(
        self,
        tenant_id: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 50,
        offset: int = 0
    ) -> InvoiceListResponse:
        """List invoices with optional filters."""
        query = select(Invoice)

        if tenant_id:
            query = query.where(Invoice.tenant_id == tenant_id)
        if status:
            query = query.where(Invoice.status == status)

        query = query.order_by(Invoice.created_at.desc()).offset(offset).limit(limit)

        result = await self.db.execute(query)
        invoices = result.scalars().all()

        # Get total
        count_query = select(func.count(Invoice.id))
        if tenant_id:
            count_query = count_query.where(Invoice.tenant_id == tenant_id)
        if status:
            count_query = count_query.where(Invoice.status == status)
        count_result = await self.db.execute(count_query)
        total = count_result.scalar() or 0

        return InvoiceListResponse(
            items=[self._invoice_to_response(i) for i in invoices],
            total=total
        )

    async def mark_invoice_paid(
        self,
        invoice_id: str,
        payment_method: str,
        payment_id: Optional[str] = None
    ) -> Optional[InvoiceResponse]:
        """Mark an invoice as paid."""
        result = await self.db.execute(
            select(Invoice).where(Invoice.id == invoice_id)
        )
        invoice = result.scalar_one_or_none()
        if not invoice:
            return None

        invoice.status = InvoiceStatus.PAID
        invoice.paid_at = datetime.utcnow()
        invoice.payment_method = payment_method
        invoice.payment_id = payment_id
        invoice.updated_at = datetime.utcnow()

        await self.db.commit()
        await self.db.refresh(invoice)

        logger.info(f"Marked invoice {invoice.invoice_number} as paid")

        return self._invoice_to_response(invoice)

    def _invoice_to_response(self, invoice: Invoice) -> InvoiceResponse:
        """Convert invoice model to response."""
        return InvoiceResponse(
            id=invoice.id,
            tenant_id=invoice.tenant_id,
            subscription_id=invoice.subscription_id,
            invoice_number=invoice.invoice_number,
            status=invoice.status,
            period_start=invoice.period_start,
            period_end=invoice.period_end,
            due_date=invoice.due_date,
            paid_at=invoice.paid_at,
            subtotal=invoice.subtotal,
            discount_amount=invoice.discount_amount,
            tax_rate=invoice.tax_rate,
            tax_amount=invoice.tax_amount,
            total=invoice.total,
            currency=invoice.currency,
            line_items=invoice.line_items or [],
            payment_method=invoice.payment_method,
            notes=invoice.notes,
            created_at=invoice.created_at,
            updated_at=invoice.updated_at,
        )

    # ============================================================
    # Revenue Analytics
    # ============================================================

    async def get_revenue_analytics(
        self,
        period_type: str = "monthly",  # daily, weekly, monthly
        periods: int = 12
    ) -> RevenueAnalyticsResponse:
        """Get revenue analytics."""
        now = datetime.utcnow()

        # Get summary
        summary = await self._get_revenue_summary()

        # Get revenue by period
        by_period = await self._get_revenue_by_period(period_type, periods)

        # Get revenue by plan
        by_plan = await self._get_revenue_by_plan()

        return RevenueAnalyticsResponse(
            summary=summary,
            by_period=by_period,
            by_plan=by_plan
        )

    async def _get_revenue_summary(self) -> RevenueSummary:
        """Calculate revenue summary."""
        now = datetime.utcnow()
        start_of_month = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        start_of_year = now.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)

        # Active subscriptions
        active_result = await self.db.execute(
            select(func.count(Subscription.id)).where(
                Subscription.status == SubscriptionStatus.ACTIVE
            )
        )
        active_subscriptions = active_result.scalar() or 0

        # Trial subscriptions
        trial_result = await self.db.execute(
            select(func.count(Subscription.id)).where(
                Subscription.status == SubscriptionStatus.TRIAL
            )
        )
        trial_subscriptions = trial_result.scalar() or 0

        # Calculate MRR from active subscriptions
        mrr_result = await self.db.execute(
            select(func.sum(Subscription.total_amount)).where(
                Subscription.status == SubscriptionStatus.ACTIVE,
                Subscription.billing_cycle == "monthly"
            )
        )
        monthly_mrr = Decimal(mrr_result.scalar() or 0)

        # Add yearly subscriptions (divided by 12)
        yearly_result = await self.db.execute(
            select(func.sum(Subscription.total_amount)).where(
                Subscription.status == SubscriptionStatus.ACTIVE,
                Subscription.billing_cycle == "yearly"
            )
        )
        yearly_mrr = Decimal(yearly_result.scalar() or 0) / 12
        total_mrr = monthly_mrr + yearly_mrr

        # Revenue MTD
        mtd_result = await self.db.execute(
            select(func.sum(Invoice.total)).where(
                Invoice.status == InvoiceStatus.PAID,
                Invoice.paid_at >= start_of_month
            )
        )
        revenue_mtd = Decimal(mtd_result.scalar() or 0)

        # Revenue YTD
        ytd_result = await self.db.execute(
            select(func.sum(Invoice.total)).where(
                Invoice.status == InvoiceStatus.PAID,
                Invoice.paid_at >= start_of_year
            )
        )
        revenue_ytd = Decimal(ytd_result.scalar() or 0)

        # Churned MTD
        churned_result = await self.db.execute(
            select(func.count(Subscription.id)).where(
                Subscription.status == SubscriptionStatus.CANCELLED,
                Subscription.cancelled_at >= start_of_month
            )
        )
        churned_mtd = churned_result.scalar() or 0

        # ARPU
        total_active = active_subscriptions + trial_subscriptions
        arpu = total_mrr / total_active if total_active > 0 else Decimal(0)

        return RevenueSummary(
            total_mrr=total_mrr,
            total_arr=total_mrr * 12,
            total_revenue_ytd=revenue_ytd,
            total_revenue_mtd=revenue_mtd,
            active_subscriptions=active_subscriptions,
            trial_subscriptions=trial_subscriptions,
            churned_subscriptions_mtd=churned_mtd,
            average_revenue_per_user=arpu,
        )

    async def _get_revenue_by_period(
        self,
        period_type: str,
        periods: int
    ) -> List[RevenueByPeriod]:
        """Get revenue breakdown by time period."""
        # Simplified implementation - returns empty for now
        # In production, this would aggregate invoices by period
        return []

    async def _get_revenue_by_plan(self) -> List[RevenueByPlan]:
        """Get revenue breakdown by plan."""
        result = await self.db.execute(
            select(
                Subscription.plan_code,
                func.count(Subscription.id).label('count'),
                func.sum(Subscription.total_amount).label('total')
            ).where(
                Subscription.status == SubscriptionStatus.ACTIVE
            ).group_by(Subscription.plan_code)
        )
        rows = result.all()

        total_mrr = sum(row.total or 0 for row in rows)
        plans = []

        for row in rows:
            # Get plan name
            plan_result = await self.db.execute(
                select(Plan.name).where(Plan.code == row.plan_code)
            )
            plan_name = plan_result.scalar() or row.plan_code

            mrr = Decimal(row.total or 0)
            percentage = (mrr / total_mrr * 100) if total_mrr > 0 else Decimal(0)

            plans.append(RevenueByPlan(
                plan_code=row.plan_code,
                plan_name=plan_name,
                active_subscriptions=row.count,
                mrr=mrr,
                percentage=percentage
            ))

        return plans

    async def get_pending_invoices_summary(self) -> PendingInvoicesSummary:
        """Get summary of pending and overdue invoices."""
        now = datetime.utcnow()

        # Pending invoices
        pending_result = await self.db.execute(
            select(
                func.count(Invoice.id),
                func.sum(Invoice.total)
            ).where(
                Invoice.status == InvoiceStatus.PENDING,
                Invoice.due_date >= now
            )
        )
        pending_row = pending_result.one()
        total_pending = pending_row[0] or 0
        pending_amount = Decimal(pending_row[1] or 0)

        # Overdue invoices
        overdue_result = await self.db.execute(
            select(
                func.count(Invoice.id),
                func.sum(Invoice.total)
            ).where(
                Invoice.status == InvoiceStatus.PENDING,
                Invoice.due_date < now
            )
        )
        overdue_row = overdue_result.one()
        total_overdue = overdue_row[0] or 0
        overdue_amount = Decimal(overdue_row[1] or 0)

        return PendingInvoicesSummary(
            total_pending=total_pending,
            total_overdue=total_overdue,
            pending_amount=pending_amount,
            overdue_amount=overdue_amount,
        )
