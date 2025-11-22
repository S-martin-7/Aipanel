"""
Email router for managing templates and sending notifications.
"""
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import TenantUserAuth, get_current_admin
from app.modules.email.service import email_service
from app.modules.email.schemas import (
    EmailTemplateCreate, EmailTemplateUpdate, EmailTemplateResponse, EmailTemplateListResponse,
    SendEmailRequest, SendEmailResponse,
    EmailLogResponse, EmailLogListResponse,
    EmailPreferenceUpdate, EmailPreferenceResponse,
    EmailStats, EmailTypesResponse,
    EmailPreviewRequest, EmailPreviewResponse
)
from app.models.email import EmailType


router = APIRouter()


# ============ Email Types ============

@router.get("/types", response_model=EmailTypesResponse)
async def list_email_types(
    current_user: TenantUserAuth
):
    """List all available email types."""
    types = email_service.get_available_types()
    return EmailTypesResponse(types=types)


# ============ Templates ============

@router.get("/templates", response_model=EmailTemplateListResponse)
async def list_templates(
    current_user: TenantUserAuth,
    db: AsyncSession = Depends(get_db),
    email_type: Optional[str] = None
):
    """List email templates."""
    templates, total = await email_service.list_templates(
        db, tenant_id=current_user["tenant_id"], email_type=email_type
    )
    return EmailTemplateListResponse(
        templates=[EmailTemplateResponse.model_validate(t) for t in templates],
        total=total
    )


@router.post("/templates", response_model=EmailTemplateResponse, status_code=status.HTTP_201_CREATED)
async def create_template(
    data: EmailTemplateCreate,
    current_user: TenantUserAuth,
    db: AsyncSession = Depends(get_db)
):
    """Create a custom email template."""
    if current_user["role"] not in ["admin", "owner"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can create templates"
        )

    template = await email_service.create_template(
        db, data, tenant_id=current_user["tenant_id"]
    )
    return EmailTemplateResponse.model_validate(template)


@router.get("/templates/{template_id}", response_model=EmailTemplateResponse)
async def get_template(
    template_id: str,
    current_user: TenantUserAuth,
    db: AsyncSession = Depends(get_db)
):
    """Get an email template."""
    template = await email_service.get_template(
        db, template_id, tenant_id=current_user["tenant_id"]
    )
    if not template:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Template not found"
        )
    return EmailTemplateResponse.model_validate(template)


@router.patch("/templates/{template_id}", response_model=EmailTemplateResponse)
async def update_template(
    template_id: str,
    data: EmailTemplateUpdate,
    current_user: TenantUserAuth,
    db: AsyncSession = Depends(get_db)
):
    """Update an email template."""
    if current_user["role"] not in ["admin", "owner"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can update templates"
        )

    template = await email_service.get_template(
        db, template_id, tenant_id=current_user["tenant_id"]
    )
    if not template:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Template not found"
        )

    # Can only update tenant-specific templates
    if template.tenant_id != current_user["tenant_id"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot modify system templates"
        )

    updated = await email_service.update_template(db, template, data)
    return EmailTemplateResponse.model_validate(updated)


@router.delete("/templates/{template_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_template(
    template_id: str,
    current_user: TenantUserAuth,
    db: AsyncSession = Depends(get_db)
):
    """Delete an email template."""
    if current_user["role"] not in ["admin", "owner"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can delete templates"
        )

    template = await email_service.get_template(
        db, template_id, tenant_id=current_user["tenant_id"]
    )
    if not template:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Template not found"
        )

    if template.tenant_id != current_user["tenant_id"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot delete system templates"
        )

    await email_service.delete_template(db, template)


@router.post("/templates/preview", response_model=EmailPreviewResponse)
async def preview_template(
    data: EmailPreviewRequest,
    current_user: TenantUserAuth,
    db: AsyncSession = Depends(get_db)
):
    """Preview an email with sample variables."""
    template = None

    if data.template_id:
        template = await email_service.get_template(
            db, data.template_id, tenant_id=current_user["tenant_id"]
        )
    elif data.email_type:
        template = await email_service.get_template_for_type(
            db, data.email_type, tenant_id=current_user["tenant_id"]
        )

    if not template:
        # Use default
        default = email_service.DEFAULT_TEMPLATES.get(
            data.email_type or EmailType.CUSTOM, {}
        )
        subject = default.get("subject", "Preview")
        body_html = default.get("body_html", "<p>No template</p>")
        body_text = None
    else:
        subject = template.subject
        body_html = template.body_html
        body_text = template.body_text

    variables = data.variables or {}
    rendered_subject, rendered_html, rendered_text = email_service.render_template(
        subject, body_html, body_text, variables
    )

    return EmailPreviewResponse(
        subject=rendered_subject,
        body_html=rendered_html,
        body_text=rendered_text
    )


# ============ Send Email ============

@router.post("/send", response_model=SendEmailResponse)
async def send_email(
    data: SendEmailRequest,
    current_user: TenantUserAuth,
    db: AsyncSession = Depends(get_db)
):
    """Send an email notification."""
    if current_user["role"] not in ["admin", "owner"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can send emails"
        )

    email_log = await email_service.send_email(
        db, data, tenant_id=current_user["tenant_id"]
    )

    return SendEmailResponse(
        email_log_id=email_log.id,
        status=email_log.status,
        message="Email queued for delivery" if email_log.status != "failed" else email_log.error_message
    )


# ============ Email Logs ============

@router.get("/logs", response_model=EmailLogListResponse)
async def list_email_logs(
    current_user: TenantUserAuth,
    db: AsyncSession = Depends(get_db),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    email_type: Optional[str] = None,
    status_filter: Optional[str] = Query(None, alias="status"),
    to_email: Optional[str] = None
):
    """List email logs."""
    if current_user["role"] not in ["admin", "owner"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can view email logs"
        )

    logs, total = await email_service.get_email_logs(
        db,
        tenant_id=current_user["tenant_id"],
        email_type=email_type,
        status=status_filter,
        to_email=to_email,
        page=page,
        page_size=page_size
    )

    return EmailLogListResponse(
        logs=[EmailLogResponse.model_validate(log) for log in logs],
        total=total,
        page=page,
        page_size=page_size
    )


@router.get("/stats", response_model=EmailStats)
async def get_email_stats(
    current_user: TenantUserAuth,
    db: AsyncSession = Depends(get_db),
    days: int = Query(30, ge=1, le=365)
):
    """Get email statistics."""
    if current_user["role"] not in ["admin", "owner"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can view email stats"
        )

    stats = await email_service.get_email_stats(
        db, tenant_id=current_user["tenant_id"], days=days
    )

    return EmailStats(
        total_sent=stats["total_sent"],
        total_delivered=stats["total_delivered"],
        total_failed=stats["total_failed"],
        total_bounced=stats["total_bounced"],
        delivery_rate=stats["delivery_rate"],
        open_rate=stats["open_rate"],
        click_rate=stats["click_rate"],
        by_type=stats["by_type"],
        by_status=stats["by_status"],
        recent_failures=[EmailLogResponse.model_validate(f) for f in stats["recent_failures"]]
    )


# ============ Email Preferences ============

@router.get("/preferences", response_model=EmailPreferenceResponse)
async def get_my_preferences(
    current_user: TenantUserAuth,
    db: AsyncSession = Depends(get_db)
):
    """Get current user's email preferences."""
    pref = await email_service.get_or_create_preferences(
        db,
        email=current_user["email"],
        tenant_id=current_user["tenant_id"],
        user_id=current_user["user_id"]
    )
    return EmailPreferenceResponse.model_validate(pref)


@router.patch("/preferences", response_model=EmailPreferenceResponse)
async def update_my_preferences(
    data: EmailPreferenceUpdate,
    current_user: TenantUserAuth,
    db: AsyncSession = Depends(get_db)
):
    """Update current user's email preferences."""
    pref = await email_service.get_or_create_preferences(
        db,
        email=current_user["email"],
        tenant_id=current_user["tenant_id"],
        user_id=current_user["user_id"]
    )
    updated = await email_service.update_preferences(db, pref, data)
    return EmailPreferenceResponse.model_validate(updated)


# ============ Public Unsubscribe ============

@router.get("/unsubscribe/{token}")
async def unsubscribe(
    token: str,
    db: AsyncSession = Depends(get_db)
):
    """Unsubscribe from emails using token."""
    pref = await email_service.unsubscribe_by_token(db, token)
    if not pref:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invalid unsubscribe token"
        )
    return {"message": "Successfully unsubscribed", "email": pref.email}


# ============ Admin Endpoints ============

@router.get("/admin/templates", response_model=EmailTemplateListResponse)
async def admin_list_all_templates(
    current_admin = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
    tenant_id: Optional[str] = None,
    email_type: Optional[str] = None
):
    """List all email templates (admin only)."""
    templates, total = await email_service.list_templates(
        db, tenant_id=tenant_id, email_type=email_type
    )
    return EmailTemplateListResponse(
        templates=[EmailTemplateResponse.model_validate(t) for t in templates],
        total=total
    )


@router.post("/admin/templates", response_model=EmailTemplateResponse, status_code=status.HTTP_201_CREATED)
async def admin_create_system_template(
    data: EmailTemplateCreate,
    current_admin = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db)
):
    """Create a system-wide email template (admin only)."""
    template = await email_service.create_template(db, data, tenant_id=None)
    return EmailTemplateResponse.model_validate(template)


@router.get("/admin/logs", response_model=EmailLogListResponse)
async def admin_list_all_logs(
    current_admin = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    tenant_id: Optional[str] = None,
    email_type: Optional[str] = None,
    status_filter: Optional[str] = Query(None, alias="status")
):
    """List all email logs (admin only)."""
    logs, total = await email_service.get_email_logs(
        db,
        tenant_id=tenant_id,
        email_type=email_type,
        status=status_filter,
        page=page,
        page_size=page_size
    )

    return EmailLogListResponse(
        logs=[EmailLogResponse.model_validate(log) for log in logs],
        total=total,
        page=page,
        page_size=page_size
    )


@router.get("/admin/stats", response_model=EmailStats)
async def admin_get_platform_stats(
    current_admin = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
    days: int = Query(30, ge=1, le=365)
):
    """Get platform-wide email statistics (admin only)."""
    stats = await email_service.get_email_stats(db, tenant_id=None, days=days)

    return EmailStats(
        total_sent=stats["total_sent"],
        total_delivered=stats["total_delivered"],
        total_failed=stats["total_failed"],
        total_bounced=stats["total_bounced"],
        delivery_rate=stats["delivery_rate"],
        open_rate=stats["open_rate"],
        click_rate=stats["click_rate"],
        by_type=stats["by_type"],
        by_status=stats["by_status"],
        recent_failures=[EmailLogResponse.model_validate(f) for f in stats["recent_failures"]]
    )
