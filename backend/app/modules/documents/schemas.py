"""
Documents Module - Schemas

Pydantic schemas for document management.
"""

from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
from enum import Enum


class DocumentStatus(str, Enum):
    """Document processing status."""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class DocumentType(str, Enum):
    """Supported document types."""
    PDF = "pdf"
    TXT = "txt"
    MD = "md"
    HTML = "html"


class DocumentUploadResponse(BaseModel):
    """Response after document upload."""
    id: str
    filename: str
    status: DocumentStatus
    message: str


class DocumentResponse(BaseModel):
    """Full document response."""
    id: str
    agent_id: str
    filename: str
    file_type: DocumentType
    file_size: int
    status: DocumentStatus
    chunk_count: int = 0
    summary: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class DocumentListItem(BaseModel):
    """Document summary for listing."""
    id: str
    filename: str
    file_type: DocumentType
    file_size: int
    status: DocumentStatus
    chunk_count: int = 0
    created_at: datetime

    class Config:
        from_attributes = True


class DocumentListResponse(BaseModel):
    """Paginated document list."""
    documents: list[DocumentListItem]
    total: int
    page: int
    page_size: int


class ChunkResponse(BaseModel):
    """Document chunk response."""
    id: str
    document_id: str
    chunk_index: int
    content: str
    summary: Optional[str] = None
    token_count: int

    class Config:
        from_attributes = True


class SearchRequest(BaseModel):
    """Search request."""
    query: str = Field(..., min_length=1, max_length=500)
    agent_id: Optional[str] = None
    limit: int = Field(10, ge=1, le=50)


class SearchResult(BaseModel):
    """Single search result."""
    document_id: str
    chunk_id: str
    filename: str
    content: str
    summary: Optional[str] = None
    relevance_score: float
    highlight: Optional[str] = None


class SearchResponse(BaseModel):
    """Search results response."""
    results: list[SearchResult]
    total: int
    query: str


class ProcessingStatus(BaseModel):
    """Document processing status."""
    document_id: str
    status: DocumentStatus
    progress: float = 0.0
    chunks_processed: int = 0
    total_chunks: int = 0
    error: Optional[str] = None
