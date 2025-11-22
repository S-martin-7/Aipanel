"""
Webhook router for managing webhooks and deliveries.
"""
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_user, TenantUserAuth
from app.modules.webhooks.service import webhook_service
from app.modules.webhooks.schemas import (
    WebhookCreate, WebhookUpdate, WebhookResponse, WebhookListResponse,
    WebhookTestRequest, WebhookTestResponse,
    WebhookDeliveryResponse, WebhookDeliveryListResponse,
    WebhookEventsResponse, WebhookStats
)


router = APIRouter()


# ============ Webhook CRUD ============

@router.get("/events", response_model=WebhookEventsResponse)
async def list_available_events(
    current_user: TenantUserAuth
):
    """List all available webhook event types."""
    events = webhook_service.get_available_events()
    return WebhookEventsResponse(events=events)


@router.get("", response_model=WebhookListResponse)
async def list_webhooks(
    current_user: TenantUserAuth,
    db: AsyncSession = Depends(get_db),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100)
):
    """List webhooks for the current tenant."""
    webhooks, total = await webhook_service.list_webhooks(
        db, current_user["tenant_id"], skip, limit
    )
    return WebhookListResponse(
        webhooks=[WebhookResponse.model_validate(w) for w in webhooks],
        total=total
    )


@router.post("", response_model=WebhookResponse, status_code=status.HTTP_201_CREATED)
async def create_webhook(
    data: WebhookCreate,
    current_user: TenantUserAuth,
    db: AsyncSession = Depends(get_db)
):
    """Create a new webhook."""
    # Check permission (admin or owner)
    if current_user["role"] not in ["admin", "owner"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can manage webhooks"
        )

    webhook = await webhook_service.create_webhook(
        db, current_user["tenant_id"], data
    )
    return WebhookResponse.model_validate(webhook)


@router.get("/{webhook_id}", response_model=WebhookResponse)
async def get_webhook(
    webhook_id: str,
    current_user: TenantUserAuth,
    db: AsyncSession = Depends(get_db)
):
    """Get a webhook by ID."""
    webhook = await webhook_service.get_webhook(
        db, webhook_id, current_user["tenant_id"]
    )
    if not webhook:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Webhook not found"
        )
    return WebhookResponse.model_validate(webhook)


@router.patch("/{webhook_id}", response_model=WebhookResponse)
async def update_webhook(
    webhook_id: str,
    data: WebhookUpdate,
    current_user: TenantUserAuth,
    db: AsyncSession = Depends(get_db)
):
    """Update a webhook."""
    if current_user["role"] not in ["admin", "owner"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can manage webhooks"
        )

    webhook = await webhook_service.get_webhook(
        db, webhook_id, current_user["tenant_id"]
    )
    if not webhook:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Webhook not found"
        )

    updated = await webhook_service.update_webhook(db, webhook, data)
    return WebhookResponse.model_validate(updated)


@router.delete("/{webhook_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_webhook(
    webhook_id: str,
    current_user: TenantUserAuth,
    db: AsyncSession = Depends(get_db)
):
    """Delete a webhook."""
    if current_user["role"] not in ["admin", "owner"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can manage webhooks"
        )

    webhook = await webhook_service.get_webhook(
        db, webhook_id, current_user["tenant_id"]
    )
    if not webhook:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Webhook not found"
        )

    await webhook_service.delete_webhook(db, webhook)


@router.post("/{webhook_id}/regenerate-secret")
async def regenerate_webhook_secret(
    webhook_id: str,
    current_user: TenantUserAuth,
    db: AsyncSession = Depends(get_db)
):
    """Regenerate the webhook signing secret."""
    if current_user["role"] not in ["admin", "owner"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can manage webhooks"
        )

    webhook = await webhook_service.get_webhook(
        db, webhook_id, current_user["tenant_id"]
    )
    if not webhook:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Webhook not found"
        )

    new_secret = await webhook_service.regenerate_secret(db, webhook)
    return {"secret": new_secret}


@router.post("/{webhook_id}/test", response_model=WebhookTestResponse)
async def test_webhook(
    webhook_id: str,
    data: WebhookTestRequest,
    current_user: TenantUserAuth,
    db: AsyncSession = Depends(get_db)
):
    """Test a webhook with a sample payload."""
    webhook = await webhook_service.get_webhook(
        db, webhook_id, current_user["tenant_id"]
    )
    if not webhook:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Webhook not found"
        )

    result = await webhook_service.test_webhook(webhook, data)
    return WebhookTestResponse(**result)


# ============ Webhook Deliveries ============

@router.get("/{webhook_id}/deliveries", response_model=WebhookDeliveryListResponse)
async def list_webhook_deliveries(
    webhook_id: str,
    current_user: TenantUserAuth,
    db: AsyncSession = Depends(get_db),
    status_filter: Optional[str] = Query(None, alias="status"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100)
):
    """List deliveries for a webhook."""
    deliveries, total = await webhook_service.get_deliveries(
        db, webhook_id, current_user["tenant_id"],
        status=status_filter, skip=skip, limit=limit
    )
    return WebhookDeliveryListResponse(
        deliveries=[WebhookDeliveryResponse.model_validate(d) for d in deliveries],
        total=total
    )


@router.post("/{webhook_id}/deliveries/{delivery_id}/retry", response_model=WebhookDeliveryResponse)
async def retry_webhook_delivery(
    webhook_id: str,
    delivery_id: str,
    current_user: TenantUserAuth,
    db: AsyncSession = Depends(get_db)
):
    """Manually retry a failed webhook delivery."""
    if current_user["role"] not in ["admin", "owner"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can retry deliveries"
        )

    delivery = await webhook_service.retry_delivery(
        db, delivery_id, current_user["tenant_id"]
    )
    if not delivery:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Delivery not found"
        )

    return WebhookDeliveryResponse.model_validate(delivery)


# ============ Stats ============

@router.get("/stats/overview", response_model=WebhookStats)
async def get_webhook_stats(
    current_user: TenantUserAuth,
    db: AsyncSession = Depends(get_db)
):
    """Get webhook statistics for the tenant."""
    stats = await webhook_service.get_stats(db, current_user["tenant_id"])
    return WebhookStats(**stats)
