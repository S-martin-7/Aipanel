"""
Monitoring module - Health checks

Endpoints for application health monitoring.
"""

from fastapi import APIRouter, Depends
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

from app.core.database import get_db
from app.core.config import settings
from app.utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter()


async def check_database(db: AsyncSession) -> tuple[str, dict]:
    """Check database connectivity."""
    try:
        result = await db.execute(text("SELECT 1"))
        result.scalar()
        return "ok", {"latency_ms": 0}
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        return "error", {"error": str(e)}


async def check_redis() -> tuple[str, dict]:
    """Check Redis connectivity."""
    try:
        import redis.asyncio as redis

        client = redis.from_url(settings.REDIS_URL)
        start = datetime.utcnow()
        await client.ping()
        latency = (datetime.utcnow() - start).total_seconds() * 1000
        await client.aclose()

        return "ok", {"latency_ms": round(latency, 2)}
    except Exception as e:
        logger.error(f"Redis health check failed: {e}")
        return "error", {"error": str(e)}


async def check_external_apis() -> tuple[str, dict]:
    """Check external API connectivity (OpenAI, Anthropic)."""
    results = {}

    # Check OpenAI
    try:
        import httpx
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(
                "https://api.openai.com/v1/models",
                headers={"Authorization": f"Bearer {settings.OPENAI_API_KEY}"}
            )
            results["openai"] = "ok" if response.status_code in (200, 401) else "degraded"
    except Exception as e:
        logger.warning(f"OpenAI health check failed: {e}")
        results["openai"] = "error"

    # Check Anthropic
    try:
        import httpx
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(
                "https://api.anthropic.com/v1/models",
                headers={
                    "x-api-key": settings.ANTHROPIC_API_KEY,
                    "anthropic-version": "2023-06-01"
                }
            )
            results["anthropic"] = "ok" if response.status_code in (200, 401) else "degraded"
    except Exception as e:
        logger.warning(f"Anthropic health check failed: {e}")
        results["anthropic"] = "error"

    all_ok = all(v == "ok" for v in results.values())
    return "ok" if all_ok else "degraded", results


@router.get("/health")
async def health_check():
    """
    Basic health check endpoint.

    Returns 200 if the application is running.
    """
    return {
        "status": "healthy",
        "version": settings.VERSION,
        "environment": settings.ENVIRONMENT,
        "timestamp": datetime.utcnow().isoformat()
    }


@router.get("/ready")
async def readiness_check(db: AsyncSession = Depends(get_db)):
    """
    Readiness check endpoint.

    Verifies all dependencies are available.
    """
    checks = {}
    details = {}

    # Check database
    db_status, db_details = await check_database(db)
    checks["database"] = db_status
    details["database"] = db_details

    # Check Redis
    redis_status, redis_details = await check_redis()
    checks["redis"] = redis_status
    details["redis"] = redis_details

    # Check external APIs (optional, don't fail readiness)
    api_status, api_details = await check_external_apis()
    checks["external_apis"] = api_status
    details["external_apis"] = api_details

    # Core services must be ok for ready status
    core_ok = checks["database"] == "ok" and checks["redis"] == "ok"

    return {
        "status": "ready" if core_ok else "not_ready",
        "checks": checks,
        "details": details,
        "timestamp": datetime.utcnow().isoformat()
    }


@router.get("/live")
async def liveness_check():
    """
    Liveness check endpoint.

    Simple check that the application is alive.
    """
    return {"status": "alive"}


@router.get("/metrics")
async def metrics_endpoint(db: AsyncSession = Depends(get_db)):
    """
    Basic metrics endpoint for monitoring.

    Returns key application metrics.
    """
    from sqlalchemy import select, func
    from app.models.tenant import Tenant
    from app.models.agent import Agent, Conversation
    from app.models.enums import TenantStatus, AgentStatus

    try:
        # Get tenant count
        result = await db.execute(
            select(func.count(Tenant.id)).where(Tenant.status == TenantStatus.ACTIVE)
        )
        active_tenants = result.scalar() or 0

        # Get agent count
        result = await db.execute(
            select(func.count(Agent.id)).where(Agent.status == AgentStatus.ACTIVE)
        )
        active_agents = result.scalar() or 0

        # Get conversation count (last 24h)
        from datetime import timedelta
        yesterday = datetime.utcnow() - timedelta(days=1)
        result = await db.execute(
            select(func.count(Conversation.id)).where(Conversation.created_at >= yesterday)
        )
        conversations_24h = result.scalar() or 0

        return {
            "active_tenants": active_tenants,
            "active_agents": active_agents,
            "conversations_24h": conversations_24h,
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        logger.error(f"Failed to collect metrics: {e}")
        return {
            "error": "Failed to collect metrics",
            "timestamp": datetime.utcnow().isoformat()
        }
