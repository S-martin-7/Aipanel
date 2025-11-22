"""
Billing Module - Router.

API endpoints for subscriptions, invoices, and revenue analytics.
"""

from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import AdminUser, TenantUser

from .service import BillingService
from .schemas import (
    CreateSubscriptionRequest,
    CancelSubscriptionRequest,
    SubscriptionResponse,
    SubscriptionListResponse,
    CreateInvoiceRequest,
    InvoiceResponse,
    InvoiceListResponse,
    PayInvoiceRequest,
    RevenueAnalyticsResponse,
    PendingInvoicesSummary,
)

router = APIRouter()


def get_billing_service(db: AsyncSession = Depends(get_db)) -> BillingService:
    return BillingService(db)


# ============================================================
# Subscription Endpoints (Admin)
# ============================================================

@router.get("/subscriptions", response_model=SubscriptionListResponse)
async def list_subscriptions(
    current_user: AdminUser,
    service: BillingService = Depends(get_billing_service),
    status: Optional[str] = Query(None, description="Filter by status"),
    plan_code: Optional[str] = Query(None, description="Filter by plan"),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
):
    """
    List all subscriptions.

    Admin only - shows all subscriptions across tenants.
    """
    return await service.list_subscriptions(
        status=status,
        plan_code=plan_code,
        limit=limit,
        offset=offset
    )


@router.post("/subscriptions", response_model=SubscriptionResponse, status_code=status.HTTP_201_CREATED)
async def create_subscription(
    request: CreateSubscriptionRequest,
    current_user: AdminUser,
    service: BillingService = Depends(get_billing_service),
):
    """
    Create a new subscription for a tenant.

    Admin only.
    """
    try:
        return await service.create_subscription(request)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/subscriptions/{subscription_id}", response_model=SubscriptionResponse)
async def get_subscription(
    subscription_id: str,
    current_user: AdminUser,
    service: BillingService = Depends(get_billing_service),
):
    """Get subscription by ID."""
    subscription = await service.get_subscription(subscription_id)
    if not subscription:
        raise HTTPException(status_code=404, detail="Subscription not found")
    return subscription


@router.post("/subscriptions/{subscription_id}/cancel", response_model=SubscriptionResponse)
async def cancel_subscription(
    subscription_id: str,
    request: CancelSubscriptionRequest,
    current_user: AdminUser,
    service: BillingService = Depends(get_billing_service),
):
    """
    Cancel a subscription.

    By default, cancels at end of billing period.
    Set cancel_immediately=true to cancel immediately.
    """
    subscription = await service.cancel_subscription(subscription_id, request)
    if not subscription:
        raise HTTPException(status_code=404, detail="Subscription not found")
    return subscription


# ============================================================
# Tenant's Subscription (Self-service)
# ============================================================

@router.get("/my-subscription", response_model=SubscriptionResponse)
async def get_my_subscription(
    current_user: TenantUser,
    service: BillingService = Depends(get_billing_service),
):
    """
    Get current user's tenant subscription.

    For tenant users to view their subscription details.
    """
    subscription = await service.get_tenant_subscription(current_user.get("tenant_id"))
    if not subscription:
        raise HTTPException(status_code=404, detail="No active subscription found")
    return subscription


# ============================================================
# Invoice Endpoints (Admin)
# ============================================================

@router.get("/invoices", response_model=InvoiceListResponse)
async def list_invoices(
    current_user: AdminUser,
    service: BillingService = Depends(get_billing_service),
    tenant_id: Optional[str] = Query(None, description="Filter by tenant"),
    status: Optional[str] = Query(None, description="Filter by status"),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
):
    """
    List all invoices.

    Admin only.
    """
    return await service.list_invoices(
        tenant_id=tenant_id,
        status=status,
        limit=limit,
        offset=offset
    )


@router.post("/invoices", response_model=InvoiceResponse, status_code=status.HTTP_201_CREATED)
async def create_invoice(
    request: CreateInvoiceRequest,
    current_user: AdminUser,
    service: BillingService = Depends(get_billing_service),
):
    """
    Create an invoice manually.

    Admin only - for one-time charges or adjustments.
    """
    return await service.create_invoice(request)


@router.get("/invoices/{invoice_id}", response_model=InvoiceResponse)
async def get_invoice(
    invoice_id: str,
    current_user: AdminUser,
    service: BillingService = Depends(get_billing_service),
):
    """Get invoice by ID."""
    invoice = await service.get_invoice(invoice_id)
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")
    return invoice


@router.post("/invoices/{invoice_id}/mark-paid", response_model=InvoiceResponse)
async def mark_invoice_paid(
    invoice_id: str,
    request: PayInvoiceRequest,
    current_user: AdminUser,
    service: BillingService = Depends(get_billing_service),
):
    """
    Mark an invoice as paid.

    Admin only - for manual payment recording.
    """
    invoice = await service.mark_invoice_paid(
        invoice_id,
        payment_method=request.payment_method
    )
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")
    return invoice


# ============================================================
# Tenant's Invoices (Self-service)
# ============================================================

@router.get("/my-invoices", response_model=InvoiceListResponse)
async def get_my_invoices(
    current_user: TenantUser,
    service: BillingService = Depends(get_billing_service),
    status: Optional[str] = Query(None, description="Filter by status"),
    limit: int = Query(20, ge=1, le=50),
    offset: int = Query(0, ge=0),
):
    """
    Get current user's tenant invoices.

    For tenant users to view their billing history.
    """
    return await service.list_invoices(
        tenant_id=current_user.get("tenant_id"),
        status=status,
        limit=limit,
        offset=offset
    )


# ============================================================
# Revenue Analytics (Admin)
# ============================================================

@router.get("/analytics/revenue", response_model=RevenueAnalyticsResponse)
async def get_revenue_analytics(
    current_user: AdminUser,
    service: BillingService = Depends(get_billing_service),
    period_type: str = Query("monthly", pattern="^(daily|weekly|monthly)$"),
    periods: int = Query(12, ge=1, le=24),
):
    """
    Get revenue analytics.

    Includes:
    - MRR/ARR
    - Revenue by period
    - Revenue by plan
    - Churn metrics

    Admin only.
    """
    return await service.get_revenue_analytics(
        period_type=period_type,
        periods=periods
    )


@router.get("/analytics/pending-invoices", response_model=PendingInvoicesSummary)
async def get_pending_invoices_summary(
    current_user: AdminUser,
    service: BillingService = Depends(get_billing_service),
):
    """
    Get summary of pending and overdue invoices.

    Admin only.
    """
    return await service.get_pending_invoices_summary()
