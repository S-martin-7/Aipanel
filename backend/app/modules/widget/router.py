"""
Widget Module - Router.

API endpoints for embeddable chat widget.
"""

from fastapi import APIRouter, Depends, HTTPException, Header
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import TenantUser

from .service import WidgetService
from .schemas import (
    WidgetConfig,
    UpdateWidgetConfigRequest,
    WidgetEmbedCode,
    WidgetChatRequest,
    WidgetChatResponse,
    AgentPublicInfo,
)

router = APIRouter()


def get_widget_service(db: AsyncSession = Depends(get_db)) -> WidgetService:
    return WidgetService(db)


# ============================================================
# Widget Configuration (Tenant authenticated)
# ============================================================

@router.get("/agents/{agent_id}/config", response_model=WidgetConfig)
async def get_widget_config(
    agent_id: str,
    current_user: TenantUser,
    service: WidgetService = Depends(get_widget_service),
):
    """
    Get widget configuration for an agent.

    Tenant users can customize the widget appearance and behavior.
    """
    config = await service.get_widget_config(agent_id, current_user.get("tenant_id"))
    if not config:
        raise HTTPException(status_code=404, detail="Agent not found")
    return config


@router.patch("/agents/{agent_id}/config", response_model=WidgetConfig)
async def update_widget_config(
    agent_id: str,
    request: UpdateWidgetConfigRequest,
    current_user: TenantUser,
    service: WidgetService = Depends(get_widget_service),
):
    """
    Update widget configuration.

    Customize:
    - Theme (light/dark/auto)
    - Colors
    - Position
    - Messages
    - Behavior (auto-open, email collection)
    """
    config = await service.update_widget_config(
        agent_id,
        current_user.get("tenant_id"),
        request
    )
    if not config:
        raise HTTPException(status_code=404, detail="Agent not found")
    return config


@router.get("/agents/{agent_id}/embed", response_model=WidgetEmbedCode)
async def get_embed_code(
    agent_id: str,
    current_user: TenantUser,
    service: WidgetService = Depends(get_widget_service),
):
    """
    Get embed code for an agent widget.

    Returns:
    - JavaScript snippet for script tag embedding
    - iFrame code for alternative embedding
    - Public key for authentication
    """
    embed = await service.get_embed_code(agent_id, current_user.get("tenant_id"))
    if not embed:
        raise HTTPException(status_code=404, detail="Agent not found")
    return embed


# ============================================================
# Public Widget Endpoints (No auth - uses public key)
# ============================================================

@router.get("/public/{agent_id}/info", response_model=AgentPublicInfo)
async def get_public_agent_info(
    agent_id: str,
    x_widget_key: str = Header(..., alias="X-Widget-Key"),
    service: WidgetService = Depends(get_widget_service),
):
    """
    Get public agent info for widget initialization.

    Requires X-Widget-Key header with the public key.
    No authentication required.
    """
    info = await service.get_agent_public_info(agent_id, x_widget_key)
    if not info:
        raise HTTPException(status_code=404, detail="Agent not found or invalid key")
    return info


@router.post("/public/{agent_id}/chat", response_model=WidgetChatResponse)
async def widget_chat(
    agent_id: str,
    request: WidgetChatRequest,
    x_widget_key: str = Header(..., alias="X-Widget-Key"),
    service: WidgetService = Depends(get_widget_service),
):
    """
    Send a chat message from widget.

    Requires X-Widget-Key header.
    Returns the assistant's response.
    """
    try:
        response = await service.widget_chat(agent_id, x_widget_key, request)
        if not response:
            raise HTTPException(status_code=404, detail="Agent not found or invalid key")
        return response
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/public/{agent_id}/chat/stream")
async def widget_chat_stream(
    agent_id: str,
    request: WidgetChatRequest,
    x_widget_key: str = Header(..., alias="X-Widget-Key"),
    service: WidgetService = Depends(get_widget_service),
):
    """
    Stream chat response for widget.

    Requires X-Widget-Key header.
    Returns Server-Sent Events stream.
    """
    return StreamingResponse(
        service.stream_widget_chat(agent_id, x_widget_key, request),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
            "Access-Control-Allow-Origin": "*",
        },
    )
