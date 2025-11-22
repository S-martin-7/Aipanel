"""
Monitoring module - Health checks

Endpoints for application health monitoring.
"""

from fastapi import APIRouter
from datetime import datetime

router = APIRouter()


@router.get("/health")
async def health_check():
    """
    Basic health check endpoint.

    Returns 200 if the application is running.
    """
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat()
    }


@router.get("/ready")
async def readiness_check():
    """
    Readiness check endpoint.

    Verifies all dependencies are available.
    """
    # TODO: Add actual checks for DB, Redis, etc.
    checks = {
        "database": "ok",
        "redis": "ok",
        "external_apis": "ok"
    }

    all_ok = all(v == "ok" for v in checks.values())

    return {
        "status": "ready" if all_ok else "not_ready",
        "checks": checks,
        "timestamp": datetime.utcnow().isoformat()
    }


@router.get("/live")
async def liveness_check():
    """
    Liveness check endpoint.

    Simple check that the application is alive.
    """
    return {"status": "alive"}
