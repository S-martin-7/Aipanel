"""
Widget Module - Schemas.

Pydantic schemas for embeddable chat widget.
"""

from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


# ============================================================
# Widget Configuration
# ============================================================

class WidgetConfig(BaseModel):
    """Widget configuration options."""
    # Appearance
    theme: str = Field(default="light", pattern="^(light|dark|auto)$")
    primary_color: str = Field(default="#3B82F6", pattern="^#[0-9A-Fa-f]{6}$")
    position: str = Field(default="bottom-right", pattern="^(bottom-right|bottom-left)$")
    width: int = Field(default=380, ge=280, le=600)
    height: int = Field(default=600, ge=400, le=800)
    border_radius: int = Field(default=16, ge=0, le=32)

    # Behavior
    auto_open: bool = False
    auto_open_delay: int = Field(default=3000, ge=0)  # ms
    show_powered_by: bool = True
    collect_email: bool = False
    require_email: bool = False

    # Messages
    welcome_message: Optional[str] = None
    placeholder_text: str = "Escribe tu mensaje..."
    offline_message: str = "Lo siento, no estamos disponibles en este momento."

    # Custom CSS (advanced)
    custom_css: Optional[str] = None


class UpdateWidgetConfigRequest(BaseModel):
    """Request to update widget configuration."""
    theme: Optional[str] = Field(default=None, pattern="^(light|dark|auto)$")
    primary_color: Optional[str] = Field(default=None, pattern="^#[0-9A-Fa-f]{6}$")
    position: Optional[str] = Field(default=None, pattern="^(bottom-right|bottom-left)$")
    width: Optional[int] = Field(default=None, ge=280, le=600)
    height: Optional[int] = Field(default=None, ge=400, le=800)
    border_radius: Optional[int] = Field(default=None, ge=0, le=32)
    auto_open: Optional[bool] = None
    auto_open_delay: Optional[int] = Field(default=None, ge=0)
    show_powered_by: Optional[bool] = None
    collect_email: Optional[bool] = None
    require_email: Optional[bool] = None
    welcome_message: Optional[str] = None
    placeholder_text: Optional[str] = None
    offline_message: Optional[str] = None
    custom_css: Optional[str] = None


# ============================================================
# Widget Embed Code
# ============================================================

class WidgetEmbedCode(BaseModel):
    """Widget embed code response."""
    agent_id: str
    public_key: str
    script_url: str
    embed_code: str
    iframe_code: str


# ============================================================
# Public Chat (for widget)
# ============================================================

class WidgetChatMessage(BaseModel):
    """Message in widget chat."""
    role: str
    content: str
    timestamp: Optional[datetime] = None


class WidgetChatRequest(BaseModel):
    """Request from widget to send message."""
    message: str = Field(..., min_length=1, max_length=4000)
    session_id: Optional[str] = None
    visitor_email: Optional[str] = None
    visitor_name: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class WidgetChatResponse(BaseModel):
    """Response to widget chat."""
    session_id: str
    message: WidgetChatMessage
    agent_name: str
    agent_avatar: Optional[str] = None


# ============================================================
# Widget Session
# ============================================================

class WidgetSession(BaseModel):
    """Widget chat session."""
    id: str
    agent_id: str
    visitor_email: Optional[str] = None
    visitor_name: Optional[str] = None
    messages: List[WidgetChatMessage]
    created_at: datetime
    last_message_at: datetime


# ============================================================
# Agent Public Info (for widget)
# ============================================================

class AgentPublicInfo(BaseModel):
    """Public agent info for widget."""
    id: str
    name: str
    description: Optional[str] = None
    avatar_url: Optional[str] = None
    welcome_message: Optional[str] = None
    is_online: bool = True
