"""
Chat Module - Router

Endpoints for AI chat interactions with streaming support.
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import TenantUser
from app.utils.logger import get_logger

from .schemas import (
    ChatCompletionRequest,
    ChatCompletionResponse,
    ConversationResponse,
    ConversationListItem,
)
from .service import ChatService

logger = get_logger(__name__)
router = APIRouter()


def get_chat_service(db: AsyncSession = Depends(get_db)) -> ChatService:
    """Dependency to get chat service."""
    return ChatService(db)


@router.post("/completions", response_model=ChatCompletionResponse)
async def create_completion(
    request: ChatCompletionRequest,
    current_user: TenantUser,
    service: ChatService = Depends(get_chat_service),
):
    """
    Create a chat completion.

    Sends message to AI and returns response.
    """
    try:
        # Get tenant_id from user's tenant association
        tenant_id = getattr(current_user, "tenant_id", None)
        if not tenant_id:
            raise HTTPException(status_code=400, detail="User not associated with a tenant")

        return await service.create_completion(
            request=request,
            user=current_user,
            tenant_id=tenant_id,
        )
    except ValueError as e:
        logger.warning(f"Completion error: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Completion failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to create completion")


@router.post("/stream")
async def create_stream_completion(
    request: ChatCompletionRequest,
    current_user: TenantUser,
    service: ChatService = Depends(get_chat_service),
):
    """
    Create a streaming chat completion.

    Returns Server-Sent Events (SSE) stream.
    """
    tenant_id = getattr(current_user, "tenant_id", None)
    if not tenant_id:
        raise HTTPException(status_code=400, detail="User not associated with a tenant")

    async def event_generator():
        try:
            async for chunk in service.stream_completion(
                request=request,
                user=current_user,
                tenant_id=tenant_id,
            ):
                yield chunk
        except Exception as e:
            logger.error(f"Stream error: {e}")
            yield f"data: {{\"error\": \"Stream failed\"}}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/conversations", response_model=list[ConversationListItem])
async def list_conversations(
    current_user: TenantUser,
    agent_id: str = Query(None, description="Filter by agent"),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    service: ChatService = Depends(get_chat_service),
):
    """List user's conversations."""
    return await service.list_conversations(
        user_id=current_user.id,
        agent_id=agent_id,
        limit=limit,
        offset=offset,
    )


@router.get("/conversations/{conversation_id}", response_model=ConversationResponse)
async def get_conversation(
    conversation_id: str,
    current_user: TenantUser,
    service: ChatService = Depends(get_chat_service),
):
    """Get a conversation with its messages."""
    conversation = await service.get_conversation(
        conversation_id=conversation_id,
        user_id=current_user.id,
    )
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")

    return conversation


@router.delete("/conversations/{conversation_id}")
async def delete_conversation(
    conversation_id: str,
    current_user: TenantUser,
    service: ChatService = Depends(get_chat_service),
):
    """Delete (archive) a conversation."""
    deleted = await service.delete_conversation(
        conversation_id=conversation_id,
        user_id=current_user.id,
    )
    if not deleted:
        raise HTTPException(status_code=404, detail="Conversation not found")

    return {"message": "Conversation deleted"}
