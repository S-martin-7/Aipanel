"""
Payments module - Router

Endpoints for payment processing with Transbank.
"""

from fastapi import APIRouter, Depends, status
from app.core.dependencies import TenantUser, AdminUser

router = APIRouter()


@router.post("/checkout")
async def create_checkout(current_user: TenantUser):
    """Create a Transbank checkout session."""
    # TODO: Implement Transbank Webpay Plus
    return {
        "url": "https://placeholder.transbank.cl",
        "token": "placeholder",
        "message": "Not implemented"
    }


@router.post("/webhook")
async def payment_webhook():
    """Handle Transbank payment webhooks."""
    # TODO: Implement webhook handling
    return {"status": "received"}


@router.get("/transactions")
async def list_transactions(current_user: TenantUser):
    """List payment transactions for tenant."""
    # TODO: Implement
    return {"transactions": [], "total": 0}


@router.get("/subscriptions")
async def get_subscription(current_user: TenantUser):
    """Get current subscription status."""
    # TODO: Implement
    return {
        "plan": "FREE",
        "status": "ACTIVE",
        "message": "Not implemented"
    }
