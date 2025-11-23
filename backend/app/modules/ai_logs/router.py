"""
AI Execution Logs Router.

Endpoints for viewing and querying AI execution logs.
"""

from datetime import datetime, timedelta
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel

from app.core.database import get_db
from app.core.dependencies import TenantUser
from app.utils.logger import get_logger

from .service import AIExecutionLogService

logger = get_logger(__name__)
router = APIRouter()


# ============ Schemas ============

class ExecutionLogResponse(BaseModel):
    """Single execution log entry."""
    id: str
    agent_id: Optional[str]
    conversation_id: Optional[str]
    request_type: Optional[str]
    status: Optional[str]
    input_tokens: int
    output_tokens: int
    total_tokens: int
    latency_ms: Optional[int]
    ttft_ms: Optional[int]
    error_code: Optional[str]
    error_message: Optional[str]
    fallback_used: bool
    source: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


class LogListResponse(BaseModel):
    """Paginated list of logs."""
    logs: List[ExecutionLogResponse]
    total: int
    page: int
    page_size: int


class StatsResponse(BaseModel):
    """Aggregated statistics."""
    period: dict
    total_requests: int
    success_count: int
    error_count: int
    success_rate: float
    tokens: dict
    latency: dict
    cost_usd: float
    error_breakdown: dict


class AgentStatsItem(BaseModel):
    """Stats for a single agent."""
    agent_id: Optional[str]
    requests: int
    tokens: int
    avg_latency_ms: float
    errors: int


# ============ Dependencies ============

def get_log_service(db: AsyncSession = Depends(get_db)) -> AIExecutionLogService:
    """Dependency to get log service."""
    return AIExecutionLogService(db)


# ============ Endpoints ============

@router.get("/", response_model=LogListResponse)
async def list_logs(
    current_user: TenantUser,
    agent_id: Optional[str] = Query(None, description="Filter by agent"),
    status: Optional[str] = Query(None, description="Filter by status (success, error, timeout)"),
    start_date: Optional[datetime] = Query(None, description="Start date"),
    end_date: Optional[datetime] = Query(None, description="End date"),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    service: AIExecutionLogService = Depends(get_log_service),
):
    """
    List AI execution logs for current tenant.

    Supports filtering by agent, status, and date range.
    """
    tenant_id = current_user.get("tenant_id")
    if not tenant_id:
        raise HTTPException(status_code=400, detail="User not associated with a tenant")

    offset = (page - 1) * page_size

    logs, total = await service.get_logs(
        tenant_id=tenant_id,
        agent_id=agent_id,
        status=status,
        start_date=start_date,
        end_date=end_date,
        limit=page_size,
        offset=offset,
    )

    return LogListResponse(
        logs=[ExecutionLogResponse(
            id=str(log.id),
            agent_id=str(log.agent_id) if log.agent_id else None,
            conversation_id=str(log.conversation_id) if log.conversation_id else None,
            request_type=log.request_type,
            status=log.status,
            input_tokens=log.input_tokens or 0,
            output_tokens=log.output_tokens or 0,
            total_tokens=log.total_tokens or 0,
            latency_ms=log.latency_ms,
            ttft_ms=log.ttft_ms,
            error_code=log.error_code,
            error_message=log.error_message,
            fallback_used=log.fallback_used or False,
            source=log.source,
            created_at=log.created_at,
        ) for log in logs],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/errors", response_model=List[ExecutionLogResponse])
async def get_recent_errors(
    current_user: TenantUser,
    hours: int = Query(24, ge=1, le=168, description="Hours to look back"),
    limit: int = Query(50, ge=1, le=100),
    service: AIExecutionLogService = Depends(get_log_service),
):
    """
    Get recent error logs for debugging.

    Returns errors from the last N hours.
    """
    tenant_id = current_user.get("tenant_id")
    if not tenant_id:
        raise HTTPException(status_code=400, detail="User not associated with a tenant")

    errors = await service.get_errors(
        tenant_id=tenant_id,
        hours=hours,
        limit=limit,
    )

    return [ExecutionLogResponse(
        id=str(log.id),
        agent_id=str(log.agent_id) if log.agent_id else None,
        conversation_id=str(log.conversation_id) if log.conversation_id else None,
        request_type=log.request_type,
        status=log.status,
        input_tokens=log.input_tokens or 0,
        output_tokens=log.output_tokens or 0,
        total_tokens=log.total_tokens or 0,
        latency_ms=log.latency_ms,
        ttft_ms=log.ttft_ms,
        error_code=log.error_code,
        error_message=log.error_message,
        fallback_used=log.fallback_used or False,
        source=log.source,
        created_at=log.created_at,
    ) for log in errors]


@router.get("/stats", response_model=StatsResponse)
async def get_stats(
    current_user: TenantUser,
    start_date: Optional[datetime] = Query(None),
    end_date: Optional[datetime] = Query(None),
    service: AIExecutionLogService = Depends(get_log_service),
):
    """
    Get aggregated execution statistics.

    Returns totals, success rate, latency stats, and error breakdown.
    """
    tenant_id = current_user.get("tenant_id")
    if not tenant_id:
        raise HTTPException(status_code=400, detail="User not associated with a tenant")

    stats = await service.get_stats(
        tenant_id=tenant_id,
        start_date=start_date,
        end_date=end_date,
    )

    return StatsResponse(**stats)


@router.get("/stats/by-agent", response_model=List[AgentStatsItem])
async def get_stats_by_agent(
    current_user: TenantUser,
    hours: int = Query(24, ge=1, le=168),
    service: AIExecutionLogService = Depends(get_log_service),
):
    """
    Get execution stats grouped by agent.

    Useful for identifying high-usage or problematic agents.
    """
    tenant_id = current_user.get("tenant_id")
    if not tenant_id:
        raise HTTPException(status_code=400, detail="User not associated with a tenant")

    stats = await service.get_agent_stats(
        tenant_id=tenant_id,
        hours=hours,
    )

    return [AgentStatsItem(**s) for s in stats]


@router.get("/{log_id}")
async def get_log_detail(
    log_id: str,
    current_user: TenantUser,
    service: AIExecutionLogService = Depends(get_log_service),
):
    """
    Get detailed execution log by ID.

    Returns full log including params_used and metadata.
    """
    tenant_id = current_user.get("tenant_id")
    if not tenant_id:
        raise HTTPException(status_code=400, detail="User not associated with a tenant")

    logs, _ = await service.get_logs(
        tenant_id=tenant_id,
        limit=1,
        offset=0,
    )

    # Find the specific log
    from sqlalchemy import select
    from app.models.ai_execution_log import AIExecutionLog

    query = select(AIExecutionLog).where(
        AIExecutionLog.id == log_id,
        AIExecutionLog.tenant_id == tenant_id,
    )
    result = await service.db.execute(query)
    log = result.scalar_one_or_none()

    if not log:
        raise HTTPException(status_code=404, detail="Log not found")

    return {
        "id": str(log.id),
        "tenant_id": str(log.tenant_id),
        "agent_id": str(log.agent_id) if log.agent_id else None,
        "conversation_id": str(log.conversation_id) if log.conversation_id else None,
        "provider_id": str(log.provider_id) if log.provider_id else None,
        "model_id": str(log.model_id) if log.model_id else None,
        "request_type": log.request_type,
        "request_id": log.request_id,
        "status": log.status,
        "input_tokens": log.input_tokens or 0,
        "output_tokens": log.output_tokens or 0,
        "total_tokens": log.total_tokens or 0,
        "latency_ms": log.latency_ms,
        "ttft_ms": log.ttft_ms,
        "error_code": log.error_code,
        "error_message": log.error_message,
        "fallback_used": log.fallback_used,
        "retry_count": log.retry_count,
        "cost_usd": float(log.cost_usd) if log.cost_usd else None,
        "params_used": log.params_used or {},
        "metadata": log.metadata or {},
        "source": log.source,
        "client_ip": log.client_ip,
        "user_agent": log.user_agent,
        "created_at": log.created_at.isoformat(),
    }
