"""
Payments Module - Router

Endpoints for payment processing with Transbank WebPay Plus.
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import TenantUser
from app.utils.logger import get_logger

from .schemas import (
    CreatePaymentRequest,
    PaymentResponse,
    PaymentConfirmRequest,
    PaymentConfirmResponse,
    SubscriptionResponse,
    PaymentHistoryResponse,
    InvoiceResponse,
    SubscriptionPlan,
    PlanDetails,
    PLANS,
)
from .service import PaymentService

logger = get_logger(__name__)
router = APIRouter()


def get_payment_service(db: AsyncSession = Depends(get_db)) -> PaymentService:
    """Dependency to get payment service."""
    return PaymentService(db)


@router.get("/plans", response_model=list[PlanDetails])
async def list_plans():
    """
    List available subscription plans.

    Returns all plans with pricing in CLP.
    """
    return list(PLANS.values())


@router.post("/checkout", response_model=PaymentResponse)
async def create_checkout(
    request: CreatePaymentRequest,
    current_user: TenantUser,
    service: PaymentService = Depends(get_payment_service),
):
    """
    Create a Transbank WebPay Plus checkout session.

    Returns a redirect URL to Transbank payment page.
    """
    tenant_id = current_user.get("tenant_id")
    if not tenant_id:
        raise HTTPException(status_code=400, detail="User not associated with a tenant")

    try:
        return await service.create_payment(
            tenant_id=tenant_id,
            plan=request.plan,
            return_url=request.return_url,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Checkout creation failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to create checkout")


@router.post("/confirm", response_model=PaymentConfirmResponse)
async def confirm_payment(
    request: PaymentConfirmRequest,
    service: PaymentService = Depends(get_payment_service),
):
    """
    Confirm a payment after Transbank callback.

    Called when user returns from Transbank payment page.
    The token_ws parameter is provided by Transbank.
    """
    try:
        return await service.confirm_payment(token_ws=request.token_ws)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Payment confirmation failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to confirm payment")


@router.get("/callback")
async def payment_callback(
    token_ws: str = Query(..., description="Transbank token"),
    service: PaymentService = Depends(get_payment_service),
):
    """
    Handle Transbank payment callback (GET).

    This endpoint receives the redirect from Transbank.
    Returns confirmation result.
    """
    try:
        result = await service.confirm_payment(token_ws=token_ws)
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/subscription", response_model=SubscriptionResponse)
async def get_subscription(
    current_user: TenantUser,
    service: PaymentService = Depends(get_payment_service),
):
    """Get current subscription status and usage."""
    tenant_id = current_user.get("tenant_id")
    if not tenant_id:
        raise HTTPException(status_code=400, detail="User not associated with a tenant")

    try:
        return await service.get_subscription(tenant_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/history", response_model=PaymentHistoryResponse)
async def get_payment_history(
    current_user: TenantUser,
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    service: PaymentService = Depends(get_payment_service),
):
    """Get payment history for current tenant."""
    tenant_id = current_user.get("tenant_id")
    if not tenant_id:
        raise HTTPException(status_code=400, detail="User not associated with a tenant")

    return await service.get_payment_history(
        tenant_id=tenant_id,
        limit=limit,
        offset=offset,
    )


@router.get("/invoices/{payment_id}", response_model=InvoiceResponse)
async def get_invoice(
    payment_id: str,
    current_user: TenantUser,
    service: PaymentService = Depends(get_payment_service),
):
    """Get invoice for a completed payment."""
    tenant_id = current_user.get("tenant_id")
    if not tenant_id:
        raise HTTPException(status_code=400, detail="User not associated with a tenant")

    invoice = await service.get_invoice(payment_id, tenant_id)
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")

    return invoice
