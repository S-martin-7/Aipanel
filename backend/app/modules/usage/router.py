"""
Usage module - Router

Endpoints for token usage tracking and metrics.
"""

from fastapi import APIRouter, Depends, Query
from app.core.dependencies import TenantUser

router = APIRouter()


@router.get("/summary")
async def get_usage_summary(current_user: TenantUser):
    """Get usage summary for current tenant."""
    # TODO: Implement
    return {
        "current_month": {
            "tokens_used": 0,
            "tokens_limit": 100000,
            "percentage": 0,
            "total_cost": 0.0
        },
        "today": {
            "tokens_used": 0,
            "total_cost": 0.0,
            "requests": 0
        }
    }


@router.get("/history")
async def get_usage_history(
    days: int = Query(30, ge=1, le=365),
    current_user: TenantUser = Depends()
):
    """Get usage history for the specified period."""
    # TODO: Implement
    return {"history": [], "days": days}


@router.get("/by-agent")
async def get_usage_by_agent(current_user: TenantUser):
    """Get token usage breakdown by agent."""
    # TODO: Implement
    return {"agents": []}


@router.get("/by-model")
async def get_usage_by_model(current_user: TenantUser):
    """Get token usage breakdown by AI model."""
    # TODO: Implement
    return {"models": []}
