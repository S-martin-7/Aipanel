"""
AI Lab Module - Schemas.

Pydantic schemas for AI testing and experimentation.
"""

from datetime import datetime
from decimal import Decimal
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


# ============================================================
# Provider Schemas
# ============================================================

class ProviderResponse(BaseModel):
    """AI provider response."""
    id: str
    name: str
    display_name: Optional[str] = None
    is_active: bool
    allowed_in_prod: bool
    models_count: int = 0
    config: Optional[Dict[str, Any]] = None

    class Config:
        from_attributes = True


class ProviderListResponse(BaseModel):
    """List of providers."""
    items: List[ProviderResponse]
    total: int


# ============================================================
# Model Schemas
# ============================================================

class ModelResponse(BaseModel):
    """AI model response."""
    id: str
    provider_id: str
    provider_name: Optional[str] = None
    name: str
    display_name: Optional[str] = None
    description: Optional[str] = None
    capabilities: Optional[List[str]] = None
    status: str
    pricing_input: Optional[Decimal] = None
    pricing_output: Optional[Decimal] = None
    max_tokens: Optional[int] = None
    context_window: Optional[int] = None
    supports_streaming: bool = True
    supports_vision: bool = False
    supports_tools: bool = False

    class Config:
        from_attributes = True


class ModelListResponse(BaseModel):
    """List of models."""
    items: List[ModelResponse]
    total: int


# ============================================================
# Test Completion Schemas
# ============================================================

class TestMessage(BaseModel):
    """Message for test completion."""
    role: str = Field(..., pattern="^(system|user|assistant)$")
    content: str


class TestCompletionRequest(BaseModel):
    """Request to test a completion."""
    model_id: str
    messages: List[TestMessage]
    temperature: float = Field(default=0.7, ge=0, le=2)
    max_tokens: int = Field(default=1024, ge=1, le=32000)
    top_p: float = Field(default=1.0, ge=0, le=1)
    stream: bool = False


class TestCompletionResponse(BaseModel):
    """Response from test completion."""
    id: str
    model: str
    provider: str
    content: str
    finish_reason: Optional[str] = None
    usage: Dict[str, int]
    latency_ms: int
    estimated_cost: Decimal


class StreamChunk(BaseModel):
    """Streaming chunk."""
    id: str
    delta: str
    finish_reason: Optional[str] = None


# ============================================================
# Compare Models Schemas
# ============================================================

class CompareModelsRequest(BaseModel):
    """Request to compare multiple models."""
    model_ids: List[str] = Field(..., min_length=2, max_length=5)
    messages: List[TestMessage]
    temperature: float = Field(default=0.7, ge=0, le=2)
    max_tokens: int = Field(default=1024, ge=1, le=32000)


class ModelComparisonResult(BaseModel):
    """Result from one model in comparison."""
    model_id: str
    model_name: str
    provider: str
    content: str
    usage: Dict[str, int]
    latency_ms: int
    estimated_cost: Decimal
    error: Optional[str] = None


class CompareModelsResponse(BaseModel):
    """Response from model comparison."""
    results: List[ModelComparisonResult]
    fastest_model: str
    cheapest_model: str


# ============================================================
# Param Profile Schemas
# ============================================================

class ParamProfileResponse(BaseModel):
    """Parameter profile response."""
    id: str
    name: str
    description: Optional[str] = None
    temperature: Optional[float] = None
    max_tokens: Optional[int] = None
    top_p: Optional[float] = None
    frequency_penalty: Optional[float] = None
    presence_penalty: Optional[float] = None
    is_active: bool

    class Config:
        from_attributes = True


class ParamProfileListResponse(BaseModel):
    """List of param profiles."""
    items: List[ParamProfileResponse]
    total: int


# ============================================================
# Stats Schemas
# ============================================================

class AILabStats(BaseModel):
    """AI Lab statistics."""
    total_providers: int
    active_providers: int
    total_models: int
    active_models: int
    total_param_profiles: int
    tests_today: int
    tests_this_month: int
