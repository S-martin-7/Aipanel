"""
Billing Module - Schemas.

Pydantic schemas for subscriptions, invoices, and revenue analytics.
"""

from datetime import datetime
from decimal import Decimal
from typing import Optional, List
from pydantic import BaseModel, Field


# ============================================================
# Subscription Schemas
# ============================================================

class CreateSubscriptionRequest(BaseModel):
    """Request to create a subscription."""
    tenant_id: str
    plan_code: str
    billing_cycle: str = Field(default="monthly", pattern="^(monthly|yearly)$")
    trial_days: int = Field(default=0, ge=0)
    payment_method_id: Optional[str] = None


class UpdateSubscriptionRequest(BaseModel):
    """Request to update a subscription."""
    plan_code: Optional[str] = None
    billing_cycle: Optional[str] = Field(default=None, pattern="^(monthly|yearly)$")
    cancel_at_period_end: Optional[bool] = None
    payment_method_id: Optional[str] = None


class CancelSubscriptionRequest(BaseModel):
    """Request to cancel a subscription."""
    reason: Optional[str] = None
    cancel_immediately: bool = False


class SubscriptionResponse(BaseModel):
    """Subscription response."""
    id: str
    tenant_id: str
    plan_code: str
    status: str
    billing_cycle: str
    current_period_start: Optional[datetime] = None
    current_period_end: Optional[datetime] = None
    trial_start: Optional[datetime] = None
    trial_end: Optional[datetime] = None
    cancelled_at: Optional[datetime] = None
    cancel_at_period_end: bool
    base_amount: Decimal
    discount_amount: Decimal
    tax_amount: Decimal
    total_amount: Decimal
    currency: str
    next_payment_date: Optional[datetime] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class SubscriptionListResponse(BaseModel):
    """List of subscriptions."""
    items: List[SubscriptionResponse]
    total: int


# ============================================================
# Invoice Schemas
# ============================================================

class InvoiceLineItem(BaseModel):
    """Invoice line item."""
    description: str
    quantity: int = 1
    unit_price: Decimal
    total: Decimal


class CreateInvoiceRequest(BaseModel):
    """Request to create an invoice manually."""
    tenant_id: str
    subscription_id: Optional[str] = None
    period_start: datetime
    period_end: datetime
    due_date: datetime
    line_items: List[InvoiceLineItem]
    notes: Optional[str] = None


class InvoiceResponse(BaseModel):
    """Invoice response."""
    id: str
    tenant_id: str
    subscription_id: Optional[str] = None
    invoice_number: str
    status: str
    period_start: datetime
    period_end: datetime
    due_date: datetime
    paid_at: Optional[datetime] = None
    subtotal: Decimal
    discount_amount: Decimal
    tax_rate: Decimal
    tax_amount: Decimal
    total: Decimal
    currency: str
    line_items: List[dict]
    payment_method: Optional[str] = None
    notes: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class InvoiceListResponse(BaseModel):
    """List of invoices."""
    items: List[InvoiceResponse]
    total: int


class PayInvoiceRequest(BaseModel):
    """Request to pay an invoice."""
    payment_method: str = "webpay"


# ============================================================
# Revenue Analytics Schemas
# ============================================================

class RevenueByPeriod(BaseModel):
    """Revenue for a specific period."""
    period: str  # e.g., "2024-01", "2024-W01", "2024-01-01"
    revenue: Decimal
    transactions: int
    new_subscriptions: int
    churned_subscriptions: int


class RevenueSummary(BaseModel):
    """Revenue summary."""
    total_mrr: Decimal  # Monthly Recurring Revenue
    total_arr: Decimal  # Annual Recurring Revenue
    total_revenue_ytd: Decimal
    total_revenue_mtd: Decimal
    active_subscriptions: int
    trial_subscriptions: int
    churned_subscriptions_mtd: int
    average_revenue_per_user: Decimal
    currency: str = "CLP"


class RevenueByPlan(BaseModel):
    """Revenue breakdown by plan."""
    plan_code: str
    plan_name: str
    active_subscriptions: int
    mrr: Decimal
    percentage: Decimal


class RevenueAnalyticsResponse(BaseModel):
    """Complete revenue analytics."""
    summary: RevenueSummary
    by_period: List[RevenueByPeriod]
    by_plan: List[RevenueByPlan]


class PendingInvoicesSummary(BaseModel):
    """Summary of pending invoices."""
    total_pending: int
    total_overdue: int
    pending_amount: Decimal
    overdue_amount: Decimal
    currency: str = "CLP"
