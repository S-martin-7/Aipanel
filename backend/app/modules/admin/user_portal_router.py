"""
User Portal Router - Level 3 (End User).

REST endpoints for end user portal.
Accessible by any authenticated tenant user.
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_user, CurrentUser
from app.utils.logger import get_logger

from .user_portal_service import UserPortalService

logger = get_logger(__name__)

router = APIRouter()


def get_portal_service(
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = None,
) -> UserPortalService:
    """Get UserPortalService with user context."""
    user_id = current_user.get("id") if current_user else None
    tenant_id = current_user.get("tenant_id") if current_user else None

    if not user_id or not tenant_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required"
        )

    return UserPortalService(db, user_id, tenant_id)


# ============================================================
# Dashboard
# ============================================================

@router.get("/dashboard")
async def get_dashboard(
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    """
    Get user's personal dashboard.

    Shows conversations, messages, and available agents.
    """
    service = get_portal_service(db, current_user)
    return await service.get_dashboard()


# ============================================================
# Conversations
# ============================================================

@router.get("/conversations")
async def list_conversations(
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
    agent_id: str = Query(None, description="Filter by agent"),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
):
    """
    List user's conversations.

    Returns conversation list with message counts.
    """
    service = get_portal_service(db, current_user)
    conversations, total = await service.list_conversations(
        agent_id=agent_id,
        limit=limit,
        offset=offset
    )

    return {
        "conversations": conversations,
        "total": total,
        "limit": limit,
        "offset": offset,
    }


@router.get("/conversations/{conversation_id}")
async def get_conversation(
    conversation_id: str,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    """
    Get a specific conversation with messages.

    Returns conversation details and full message history.
    """
    service = get_portal_service(db, current_user)
    conversation = await service.get_conversation(conversation_id)

    if not conversation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found"
        )

    return conversation


# ============================================================
# Agents
# ============================================================

@router.get("/agents")
async def list_available_agents(
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    """
    List agents available to the user.

    Shows active agents in the tenant.
    """
    service = get_portal_service(db, current_user)
    return await service.list_available_agents()


@router.get("/agents/{agent_id}")
async def get_agent_info(
    agent_id: str,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    """
    Get public info about an agent.

    Returns agent details and document count.
    """
    service = get_portal_service(db, current_user)
    agent = await service.get_agent_info(agent_id)

    if not agent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Agent not found or not available"
        )

    return agent


# ============================================================
# Usage
# ============================================================

@router.get("/usage")
async def get_usage_summary(
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
    days: int = Query(30, ge=1, le=90),
):
    """
    Get user's personal usage summary.

    Shows token usage and request counts.
    """
    service = get_portal_service(db, current_user)
    return await service.get_usage_summary(days=days)


@router.get("/activity")
async def get_activity_history(
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
    days: int = Query(7, ge=1, le=30),
):
    """
    Get user's daily activity history.

    Shows conversation counts per day.
    """
    service = get_portal_service(db, current_user)
    return await service.get_activity_history(days=days)


# ============================================================
# Account
# ============================================================

@router.get("/account")
async def get_account_info(
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    """
    Get user's account information.
    """
    service = get_portal_service(db, current_user)
    account = await service.get_account_info()

    if not account:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Account not found"
        )

    return account
