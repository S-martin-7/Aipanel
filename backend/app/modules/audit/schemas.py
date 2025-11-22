"""
Audit log schemas for request/response validation.
"""
from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from app.models.audit_log import AuditAction


# ============ Audit Log Entries ============

class AuditLogResponse(BaseModel):
    """Schema for audit log response."""
    id: str
    tenant_id: Optional[str]
    user_id: Optional[str]
    user_email: Optional[str]
    user_type: Optional[str]
    action: str
    resource_type: Optional[str]
    resource_id: Optional[str]
    resource_name: Optional[str]
    description: Optional[str]
    old_values: Optional[Dict[str, Any]]
    new_values: Optional[Dict[str, Any]]
    metadata: Optional[Dict[str, Any]]
    ip_address: Optional[str]
    user_agent: Optional[str]
    request_id: Optional[str]
    status: str
    error_message: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


class AuditLogListResponse(BaseModel):
    """Schema for listing audit logs."""
    logs: List[AuditLogResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


# ============ Filters ============

class AuditLogFilters(BaseModel):
    """Filters for querying audit logs."""
    action: Optional[str] = None
    resource_type: Optional[str] = None
    resource_id: Optional[str] = None
    user_id: Optional[str] = None
    user_email: Optional[str] = None
    status: Optional[str] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    ip_address: Optional[str] = None


# ============ Stats ============

class AuditStats(BaseModel):
    """Audit log statistics."""
    total_logs: int
    logs_today: int
    logs_this_week: int
    logs_this_month: int
    by_action: Dict[str, int]
    by_resource_type: Dict[str, int]
    by_status: Dict[str, int]
    by_user: List[Dict[str, Any]]
    recent_failures: List[AuditLogResponse]


# ============ Available Actions ============

class AuditActionInfo(BaseModel):
    """Information about an audit action."""
    action: str
    category: str
    description: str


class AuditActionsResponse(BaseModel):
    """List of available audit actions."""
    actions: List[AuditActionInfo]


# ============ Export ============

class AuditExportRequest(BaseModel):
    """Request to export audit logs."""
    format: str = Field(default="csv", pattern="^(csv|json)$")
    filters: Optional[AuditLogFilters] = None
    include_metadata: bool = False


class AuditExportResponse(BaseModel):
    """Response for audit log export."""
    download_url: str
    expires_at: datetime
    record_count: int
    file_size_bytes: int
