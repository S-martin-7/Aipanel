"""
AI Execution Log Service.

Provides logging and querying capabilities for AI executions.
"""

import time
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from uuid import UUID
from dataclasses import dataclass, field

from sqlalchemy import select, func, desc, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.ai_execution_log import AIExecutionLog, ExecutionStatus, RequestType
from app.utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class ExecutionContext:
    """Context for an AI execution."""
    tenant_id: str
    agent_id: Optional[str] = None
    conversation_id: Optional[str] = None
    request_type: str = "chat"
    request_id: Optional[str] = None
    source: str = "panel"  # panel, widget, api, webhook
    client_ip: Optional[str] = None
    user_agent: Optional[str] = None


@dataclass
class ExecutionResult:
    """Result of an AI execution."""
    status: str = "success"
    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0
    latency_ms: int = 0
    ttft_ms: Optional[int] = None
    error_code: Optional[str] = None
    error_message: Optional[str] = None
    fallback_used: bool = False
    fallback_model_id: Optional[str] = None
    retry_count: int = 0
    cost_usd: Optional[float] = None
    params_used: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)


class ExecutionTimer:
    """Context manager for timing AI executions."""

    def __init__(self):
        self.start_time: Optional[float] = None
        self.first_token_time: Optional[float] = None
        self.end_time: Optional[float] = None

    def __enter__(self):
        self.start_time = time.time()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.end_time = time.time()

    def mark_first_token(self):
        """Mark time of first token (for streaming)."""
        if self.first_token_time is None:
            self.first_token_time = time.time()

    @property
    def latency_ms(self) -> int:
        """Total latency in milliseconds."""
        if self.start_time and self.end_time:
            return int((self.end_time - self.start_time) * 1000)
        return 0

    @property
    def ttft_ms(self) -> Optional[int]:
        """Time to first token in milliseconds."""
        if self.start_time and self.first_token_time:
            return int((self.first_token_time - self.start_time) * 1000)
        return None


class AIExecutionLogService:
    """
    Service for logging and querying AI executions.

    Features:
    - Log every AI call with full context
    - Query logs by tenant, agent, date range
    - Aggregate statistics for dashboards
    - Error tracking and alerting
    """

    def __init__(self, db: AsyncSession):
        self.db = db

    async def log_execution(
        self,
        context: ExecutionContext,
        result: ExecutionResult,
        provider_id: Optional[str] = None,
        model_id: Optional[str] = None,
        route_id: Optional[str] = None,
        param_profile_id: Optional[str] = None,
    ) -> AIExecutionLog:
        """
        Log an AI execution.

        Args:
            context: Execution context (tenant, agent, etc.)
            result: Execution result (tokens, latency, status)
            provider_id: Provider used
            model_id: Model used
            route_id: Route used
            param_profile_id: Parameter profile used

        Returns:
            Created AIExecutionLog record
        """
        log_entry = AIExecutionLog(
            tenant_id=context.tenant_id,
            agent_id=context.agent_id,
            conversation_id=context.conversation_id,
            route_id=route_id,
            provider_id=provider_id,
            model_id=model_id,
            param_profile_id=param_profile_id,
            request_type=context.request_type,
            request_id=context.request_id,
            input_tokens=result.input_tokens,
            output_tokens=result.output_tokens,
            total_tokens=result.total_tokens,
            latency_ms=result.latency_ms,
            ttft_ms=result.ttft_ms,
            status=result.status,
            error_code=result.error_code,
            error_message=result.error_message,
            fallback_used=result.fallback_used,
            fallback_model_id=result.fallback_model_id,
            retry_count=result.retry_count,
            cost_usd=result.cost_usd,
            params_used=result.params_used,
            metadata=result.metadata,
            source=context.source,
            client_ip=context.client_ip,
            user_agent=context.user_agent,
        )

        self.db.add(log_entry)
        await self.db.flush()

        # Log for debugging
        if result.status != "success":
            logger.warning(
                f"AI execution failed: {result.status} - {result.error_message}",
                extra={
                    "tenant_id": context.tenant_id,
                    "agent_id": context.agent_id,
                    "error_code": result.error_code,
                }
            )
        else:
            logger.info(
                f"AI execution logged: {result.total_tokens} tokens, {result.latency_ms}ms",
                extra={
                    "tenant_id": context.tenant_id,
                    "agent_id": context.agent_id,
                    "tokens": result.total_tokens,
                    "latency_ms": result.latency_ms,
                }
            )

        return log_entry

    async def get_logs(
        self,
        tenant_id: str,
        agent_id: Optional[str] = None,
        status: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> tuple[List[AIExecutionLog], int]:
        """
        Get execution logs with filters.

        Returns:
            Tuple of (logs, total_count)
        """
        query = select(AIExecutionLog).where(
            AIExecutionLog.tenant_id == tenant_id
        )

        if agent_id:
            query = query.where(AIExecutionLog.agent_id == agent_id)
        if status:
            query = query.where(AIExecutionLog.status == status)
        if start_date:
            query = query.where(AIExecutionLog.created_at >= start_date)
        if end_date:
            query = query.where(AIExecutionLog.created_at <= end_date)

        # Get total count
        count_query = select(func.count(AIExecutionLog.id)).where(
            AIExecutionLog.tenant_id == tenant_id
        )
        if agent_id:
            count_query = count_query.where(AIExecutionLog.agent_id == agent_id)
        if status:
            count_query = count_query.where(AIExecutionLog.status == status)
        if start_date:
            count_query = count_query.where(AIExecutionLog.created_at >= start_date)
        if end_date:
            count_query = count_query.where(AIExecutionLog.created_at <= end_date)

        count_result = await self.db.execute(count_query)
        total = count_result.scalar() or 0

        # Get paginated results
        query = query.order_by(desc(AIExecutionLog.created_at)).offset(offset).limit(limit)
        result = await self.db.execute(query)
        logs = result.scalars().all()

        return list(logs), total

    async def get_errors(
        self,
        tenant_id: str,
        hours: int = 24,
        limit: int = 50,
    ) -> List[AIExecutionLog]:
        """Get recent errors for debugging."""
        since = datetime.utcnow() - timedelta(hours=hours)

        query = select(AIExecutionLog).where(
            AIExecutionLog.tenant_id == tenant_id,
            AIExecutionLog.status != ExecutionStatus.SUCCESS.value,
            AIExecutionLog.created_at >= since,
        ).order_by(desc(AIExecutionLog.created_at)).limit(limit)

        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def get_stats(
        self,
        tenant_id: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        group_by: str = "day",  # day, hour, agent, model
    ) -> Dict[str, Any]:
        """
        Get aggregated statistics.

        Returns:
            Dict with stats like total_requests, success_rate, avg_latency, etc.
        """
        if not start_date:
            start_date = datetime.utcnow() - timedelta(days=7)
        if not end_date:
            end_date = datetime.utcnow()

        # Base query
        base_filter = and_(
            AIExecutionLog.tenant_id == tenant_id,
            AIExecutionLog.created_at >= start_date,
            AIExecutionLog.created_at <= end_date,
        )

        # Total requests
        total_query = select(func.count(AIExecutionLog.id)).where(base_filter)
        total_result = await self.db.execute(total_query)
        total_requests = total_result.scalar() or 0

        # Success count
        success_query = select(func.count(AIExecutionLog.id)).where(
            base_filter,
            AIExecutionLog.status == ExecutionStatus.SUCCESS.value
        )
        success_result = await self.db.execute(success_query)
        success_count = success_result.scalar() or 0

        # Token totals
        tokens_query = select(
            func.sum(AIExecutionLog.input_tokens),
            func.sum(AIExecutionLog.output_tokens),
            func.sum(AIExecutionLog.total_tokens),
        ).where(base_filter)
        tokens_result = await self.db.execute(tokens_query)
        tokens = tokens_result.one()

        # Latency stats
        latency_query = select(
            func.avg(AIExecutionLog.latency_ms),
            func.min(AIExecutionLog.latency_ms),
            func.max(AIExecutionLog.latency_ms),
            func.percentile_cont(0.95).within_group(AIExecutionLog.latency_ms),
        ).where(base_filter, AIExecutionLog.status == ExecutionStatus.SUCCESS.value)
        latency_result = await self.db.execute(latency_query)
        latency = latency_result.one()

        # Cost total
        cost_query = select(func.sum(AIExecutionLog.cost_usd)).where(base_filter)
        cost_result = await self.db.execute(cost_query)
        total_cost = cost_result.scalar() or 0

        # Error breakdown
        error_query = select(
            AIExecutionLog.error_code,
            func.count(AIExecutionLog.id)
        ).where(
            base_filter,
            AIExecutionLog.status != ExecutionStatus.SUCCESS.value
        ).group_by(AIExecutionLog.error_code)
        error_result = await self.db.execute(error_query)
        error_breakdown = {row[0] or "unknown": row[1] for row in error_result}

        return {
            "period": {
                "start": start_date.isoformat(),
                "end": end_date.isoformat(),
            },
            "total_requests": total_requests,
            "success_count": success_count,
            "error_count": total_requests - success_count,
            "success_rate": (success_count / total_requests * 100) if total_requests > 0 else 0,
            "tokens": {
                "input": tokens[0] or 0,
                "output": tokens[1] or 0,
                "total": tokens[2] or 0,
            },
            "latency": {
                "avg_ms": round(latency[0] or 0, 2),
                "min_ms": latency[1] or 0,
                "max_ms": latency[2] or 0,
                "p95_ms": round(latency[3] or 0, 2),
            },
            "cost_usd": float(total_cost),
            "error_breakdown": error_breakdown,
        }

    async def get_agent_stats(
        self,
        tenant_id: str,
        hours: int = 24,
    ) -> List[Dict[str, Any]]:
        """Get stats grouped by agent."""
        since = datetime.utcnow() - timedelta(hours=hours)

        query = select(
            AIExecutionLog.agent_id,
            func.count(AIExecutionLog.id).label("requests"),
            func.sum(AIExecutionLog.total_tokens).label("tokens"),
            func.avg(AIExecutionLog.latency_ms).label("avg_latency"),
            func.count(AIExecutionLog.id).filter(
                AIExecutionLog.status != ExecutionStatus.SUCCESS.value
            ).label("errors"),
        ).where(
            AIExecutionLog.tenant_id == tenant_id,
            AIExecutionLog.created_at >= since,
        ).group_by(AIExecutionLog.agent_id)

        result = await self.db.execute(query)
        return [
            {
                "agent_id": str(row.agent_id) if row.agent_id else None,
                "requests": row.requests,
                "tokens": row.tokens or 0,
                "avg_latency_ms": round(row.avg_latency or 0, 2),
                "errors": row.errors or 0,
            }
            for row in result
        ]
