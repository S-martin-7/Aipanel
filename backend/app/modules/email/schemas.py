"""
Email schemas for request/response validation.
"""
from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, EmailStr
from app.models.email import EmailType, EmailStatus


# ============ Email Templates ============

class EmailTemplateCreate(BaseModel):
    """Schema for creating an email template."""
    email_type: EmailType
    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = None
    subject: str = Field(..., min_length=1, max_length=255)
    body_html: str = Field(..., min_length=1)
    body_text: Optional[str] = None
    header_image_url: Optional[str] = None
    footer_text: Optional[str] = None
    primary_color: Optional[str] = Field(None, pattern="^#[0-9A-Fa-f]{6}$")
    available_variables: Optional[List[str]] = None
    is_active: bool = True


class EmailTemplateUpdate(BaseModel):
    """Schema for updating an email template."""
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = None
    subject: Optional[str] = Field(None, min_length=1, max_length=255)
    body_html: Optional[str] = None
    body_text: Optional[str] = None
    header_image_url: Optional[str] = None
    footer_text: Optional[str] = None
    primary_color: Optional[str] = Field(None, pattern="^#[0-9A-Fa-f]{6}$")
    available_variables: Optional[List[str]] = None
    is_active: Optional[bool] = None


class EmailTemplateResponse(BaseModel):
    """Schema for email template response."""
    id: str
    tenant_id: Optional[str]
    email_type: str
    name: str
    description: Optional[str]
    subject: str
    body_html: str
    body_text: Optional[str]
    header_image_url: Optional[str]
    footer_text: Optional[str]
    primary_color: Optional[str]
    available_variables: Optional[List[str]]
    is_active: bool
    is_default: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class EmailTemplateListResponse(BaseModel):
    """Schema for listing email templates."""
    templates: List[EmailTemplateResponse]
    total: int


# ============ Send Email ============

class SendEmailRequest(BaseModel):
    """Schema for sending an email."""
    to_email: EmailStr
    to_name: Optional[str] = None
    cc_emails: Optional[List[EmailStr]] = None
    bcc_emails: Optional[List[EmailStr]] = None
    email_type: EmailType
    template_id: Optional[str] = None  # If not provided, uses default
    variables: Optional[Dict[str, Any]] = None
    subject_override: Optional[str] = None  # Override template subject


class SendEmailResponse(BaseModel):
    """Response after sending an email."""
    email_log_id: str
    status: str
    message: str


class BulkSendEmailRequest(BaseModel):
    """Schema for sending bulk emails."""
    email_type: EmailType
    recipients: List[Dict[str, Any]]  # [{email, name, variables}, ...]
    template_id: Optional[str] = None


class BulkSendEmailResponse(BaseModel):
    """Response after sending bulk emails."""
    total_queued: int
    email_log_ids: List[str]
    failed: List[Dict[str, str]]


# ============ Email Logs ============

class EmailLogResponse(BaseModel):
    """Schema for email log response."""
    id: str
    tenant_id: Optional[str]
    to_email: str
    to_name: Optional[str]
    cc_emails: Optional[List[str]]
    email_type: str
    template_id: Optional[str]
    subject: str
    status: str
    attempts: int
    last_attempt_at: Optional[datetime]
    sent_at: Optional[datetime]
    delivered_at: Optional[datetime]
    provider: Optional[str]
    error_message: Optional[str]
    opened_at: Optional[datetime]
    clicked_at: Optional[datetime]
    related_type: Optional[str]
    related_id: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


class EmailLogListResponse(BaseModel):
    """Schema for listing email logs."""
    logs: List[EmailLogResponse]
    total: int
    page: int
    page_size: int


# ============ Email Preferences ============

class EmailPreferenceUpdate(BaseModel):
    """Schema for updating email preferences."""
    marketing_emails: Optional[bool] = None
    billing_emails: Optional[bool] = None
    usage_alerts: Optional[bool] = None
    product_updates: Optional[bool] = None
    weekly_summary: Optional[bool] = None
    unsubscribed_all: Optional[bool] = None


class EmailPreferenceResponse(BaseModel):
    """Schema for email preference response."""
    id: str
    email: str
    marketing_emails: bool
    billing_emails: bool
    security_emails: bool
    usage_alerts: bool
    product_updates: bool
    weekly_summary: bool
    unsubscribed_all: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ============ Email Stats ============

class EmailStats(BaseModel):
    """Email statistics."""
    total_sent: int
    total_delivered: int
    total_failed: int
    total_bounced: int
    delivery_rate: float
    open_rate: float
    click_rate: float
    by_type: Dict[str, int]
    by_status: Dict[str, int]
    recent_failures: List[EmailLogResponse]


# ============ Available Email Types ============

class EmailTypeInfo(BaseModel):
    """Information about an email type."""
    email_type: str
    category: str
    description: str
    default_variables: List[str]


class EmailTypesResponse(BaseModel):
    """List of available email types."""
    types: List[EmailTypeInfo]


# ============ Preview ============

class EmailPreviewRequest(BaseModel):
    """Request to preview an email."""
    template_id: Optional[str] = None
    email_type: Optional[EmailType] = None
    variables: Optional[Dict[str, Any]] = None


class EmailPreviewResponse(BaseModel):
    """Rendered email preview."""
    subject: str
    body_html: str
    body_text: Optional[str]
