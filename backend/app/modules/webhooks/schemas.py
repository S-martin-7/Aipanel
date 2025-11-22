"""
Webhook schemas for request/response validation.
"""
from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, HttpUrl
from app.models.webhook import WebhookEvent, DeliveryStatus


# ============ Webhook Configuration ============

class WebhookCreate(BaseModel):
    """Schema for creating a webhook."""
    name: str = Field(..., min_length=1, max_length=100)
    url: HttpUrl
    events: List[WebhookEvent]
    agent_id: Optional[str] = None
    max_retries: int = Field(default=3, ge=0, le=10)
    retry_delay_seconds: int = Field(default=60, ge=10, le=3600)
    custom_headers: Optional[Dict[str, str]] = None
    is_active: bool = True


class WebhookUpdate(BaseModel):
    """Schema for updating a webhook."""
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    url: Optional[HttpUrl] = None
    events: Optional[List[WebhookEvent]] = None
    agent_id: Optional[str] = None
    max_retries: Optional[int] = Field(None, ge=0, le=10)
    retry_delay_seconds: Optional[int] = Field(None, ge=10, le=3600)
    custom_headers: Optional[Dict[str, str]] = None
    is_active: Optional[bool] = None


class WebhookResponse(BaseModel):
    """Schema for webhook response."""
    id: str
    tenant_id: str
    name: str
    url: str
    events: List[str]
    agent_id: Optional[str]
    is_active: bool
    max_retries: int
    retry_delay_seconds: int
    custom_headers: Optional[Dict[str, str]]
    total_deliveries: int
    successful_deliveries: int
    failed_deliveries: int
    last_triggered_at: Optional[datetime]
    last_success_at: Optional[datetime]
    last_failure_at: Optional[datetime]
    last_failure_reason: Optional[str]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class WebhookListResponse(BaseModel):
    """Schema for listing webhooks."""
    webhooks: List[WebhookResponse]
    total: int


# ============ Webhook Deliveries ============

class WebhookDeliveryResponse(BaseModel):
    """Schema for webhook delivery response."""
    id: str
    webhook_id: str
    event_type: str
    event_id: str
    payload: Dict[str, Any]
    status: str
    attempts: int
    next_retry_at: Optional[datetime]
    response_status_code: Optional[int]
    response_body: Optional[str]
    response_time_ms: Optional[int]
    error_message: Optional[str]
    delivered_at: Optional[datetime]
    created_at: datetime

    class Config:
        from_attributes = True


class WebhookDeliveryListResponse(BaseModel):
    """Schema for listing webhook deliveries."""
    deliveries: List[WebhookDeliveryResponse]
    total: int


# ============ Webhook Testing ============

class WebhookTestRequest(BaseModel):
    """Schema for testing a webhook."""
    event_type: WebhookEvent = WebhookEvent.MESSAGE_RECEIVED
    sample_payload: Optional[Dict[str, Any]] = None


class WebhookTestResponse(BaseModel):
    """Schema for webhook test response."""
    success: bool
    status_code: Optional[int]
    response_time_ms: Optional[int]
    response_body: Optional[str]
    error: Optional[str]


# ============ Event Types ============

class WebhookEventInfo(BaseModel):
    """Information about a webhook event type."""
    event: str
    category: str
    description: str
    sample_payload: Dict[str, Any]


class WebhookEventsResponse(BaseModel):
    """List of available webhook events."""
    events: List[WebhookEventInfo]


# ============ Stats ============

class WebhookStats(BaseModel):
    """Webhook statistics for a tenant."""
    total_webhooks: int
    active_webhooks: int
    total_deliveries: int
    successful_deliveries: int
    failed_deliveries: int
    success_rate: float
    deliveries_by_event: Dict[str, int]
    deliveries_by_status: Dict[str, int]
