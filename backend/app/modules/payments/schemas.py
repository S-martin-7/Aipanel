"""
Payments Module - Schemas

Pydantic schemas for payments and subscriptions with Transbank.
"""

from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
from enum import Enum


class PaymentStatus(str, Enum):
    """Payment status."""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    REFUNDED = "refunded"
    CANCELLED = "cancelled"


class PaymentMethod(str, Enum):
    """Payment methods."""
    WEBPAY = "webpay"
    ONECLICK = "oneclick"


class SubscriptionPlan(str, Enum):
    """Available subscription plans."""
    FREE = "free"
    STARTER = "starter"
    PROFESSIONAL = "professional"
    ENTERPRISE = "enterprise"


class PlanDetails(BaseModel):
    """Subscription plan details."""
    plan: SubscriptionPlan
    name: str
    price_clp: int  # Chilean Pesos
    tokens_monthly: int
    agents_limit: int
    documents_limit: int
    features: list[str]


# Plan definitions
PLANS = {
    SubscriptionPlan.FREE: PlanDetails(
        plan=SubscriptionPlan.FREE,
        name="Gratis",
        price_clp=0,
        tokens_monthly=10000,
        agents_limit=1,
        documents_limit=5,
        features=["1 agente", "10K tokens/mes", "5 documentos"],
    ),
    SubscriptionPlan.STARTER: PlanDetails(
        plan=SubscriptionPlan.STARTER,
        name="Inicial",
        price_clp=19990,
        tokens_monthly=100000,
        agents_limit=3,
        documents_limit=50,
        features=["3 agentes", "100K tokens/mes", "50 documentos", "Soporte email"],
    ),
    SubscriptionPlan.PROFESSIONAL: PlanDetails(
        plan=SubscriptionPlan.PROFESSIONAL,
        name="Profesional",
        price_clp=49990,
        tokens_monthly=500000,
        agents_limit=10,
        documents_limit=200,
        features=["10 agentes", "500K tokens/mes", "200 documentos", "Soporte prioritario", "API access"],
    ),
    SubscriptionPlan.ENTERPRISE: PlanDetails(
        plan=SubscriptionPlan.ENTERPRISE,
        name="Empresa",
        price_clp=149990,
        tokens_monthly=2000000,
        agents_limit=50,
        documents_limit=1000,
        features=["50 agentes", "2M tokens/mes", "1000 documentos", "Soporte 24/7", "SLA garantizado"],
    ),
}


class CreatePaymentRequest(BaseModel):
    """Request to create a payment."""
    plan: SubscriptionPlan
    return_url: str = Field(..., description="URL to return after payment")


class PaymentResponse(BaseModel):
    """Payment response."""
    id: str
    tenant_id: str
    amount: int
    currency: str = "CLP"
    status: PaymentStatus
    payment_method: PaymentMethod
    plan: SubscriptionPlan
    transbank_token: Optional[str] = None
    redirect_url: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class PaymentConfirmRequest(BaseModel):
    """Request to confirm a payment (from Transbank callback)."""
    token_ws: str = Field(..., description="Token from Transbank")


class PaymentConfirmResponse(BaseModel):
    """Response after payment confirmation."""
    payment_id: str
    status: PaymentStatus
    authorization_code: Optional[str] = None
    transaction_date: Optional[datetime] = None
    amount: int
    message: str


class SubscriptionResponse(BaseModel):
    """Current subscription details."""
    tenant_id: str
    plan: SubscriptionPlan
    plan_details: PlanDetails
    tokens_used: int
    tokens_remaining: int
    agents_count: int
    documents_count: int
    current_period_start: datetime
    current_period_end: datetime
    is_active: bool


class PaymentHistoryItem(BaseModel):
    """Payment history item."""
    id: str
    amount: int
    currency: str
    status: PaymentStatus
    plan: SubscriptionPlan
    created_at: datetime
    completed_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class PaymentHistoryResponse(BaseModel):
    """Payment history response."""
    payments: list[PaymentHistoryItem]
    total: int


class InvoiceResponse(BaseModel):
    """Invoice/receipt response."""
    id: str
    payment_id: str
    tenant_id: str
    amount: int
    tax: int  # IVA 19%
    total: int
    plan: SubscriptionPlan
    period_start: datetime
    period_end: datetime
    issued_at: datetime
    invoice_number: str
