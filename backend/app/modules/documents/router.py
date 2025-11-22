"""
Documents Module - Router

Endpoints for document upload, processing, and search.
"""

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Query, BackgroundTasks, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import TenantUser
from app.utils.logger import get_logger

from .schemas import (
    DocumentUploadResponse,
    DocumentResponse,
    DocumentListResponse,
    ChunkResponse,
    SearchRequest,
    SearchResponse,
    ProcessingStatus,
    DocumentStatus,
)
from .service import DocumentService

logger = get_logger(__name__)
router = APIRouter()

# Allowed file types
ALLOWED_TYPES = {"pdf", "txt", "md", "html"}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB


def get_document_service(db: AsyncSession = Depends(get_db)) -> DocumentService:
    """Dependency to get document service."""
    return DocumentService(db)


@router.get("/", response_model=DocumentListResponse)
async def list_documents(
    current_user: TenantUser,
    agent_id: str = Query(None, description="Filter by agent"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    service: DocumentService = Depends(get_document_service),
):
    """List all documents for current tenant."""
    tenant_id = getattr(current_user, "tenant_id", None)
    if not tenant_id:
        raise HTTPException(status_code=400, detail="User not associated with a tenant")

    return await service.list_documents(
        tenant_id=tenant_id,
        agent_id=agent_id,
        page=page,
        page_size=page_size,
    )


@router.post("/upload", response_model=DocumentUploadResponse, status_code=status.HTTP_201_CREATED)
async def upload_document(
    background_tasks: BackgroundTasks,
    agent_id: str = Query(..., description="Agent ID for this document"),
    file: UploadFile = File(...),
    current_user: TenantUser = Depends(),
    service: DocumentService = Depends(get_document_service),
):
    """
    Upload a document for processing.

    Supported types: PDF, TXT, MD, HTML
    Max size: 10MB
    """
    tenant_id = getattr(current_user, "tenant_id", None)
    if not tenant_id:
        raise HTTPException(status_code=400, detail="User not associated with a tenant")

    # Validate file type
    if not file.filename:
        raise HTTPException(status_code=400, detail="Filename required")

    file_ext = file.filename.rsplit(".", 1)[-1].lower() if "." in file.filename else ""
    if file_ext not in ALLOWED_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"File type not allowed. Allowed: {', '.join(ALLOWED_TYPES)}"
        )

    # Read content
    content = await file.read()

    # Validate size
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(status_code=400, detail="File too large. Max 10MB")

    try:
        document = await service.upload_document(
            filename=file.filename,
            content=content,
            agent_id=agent_id,
            tenant_id=tenant_id,
        )

        # Process in background
        background_tasks.add_task(
            service.process_document,
            document.id,
            tenant_id,
        )

        return DocumentUploadResponse(
            id=document.id,
            filename=document.filename,
            status=DocumentStatus.PENDING,
            message="Document uploaded, processing started",
        )

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Upload failed: {e}")
        raise HTTPException(status_code=500, detail="Upload failed")


@router.get("/{document_id}", response_model=DocumentResponse)
async def get_document(
    document_id: str,
    current_user: TenantUser,
    service: DocumentService = Depends(get_document_service),
):
    """Get document by ID."""
    tenant_id = getattr(current_user, "tenant_id", None)
    if not tenant_id:
        raise HTTPException(status_code=400, detail="User not associated with a tenant")

    document = await service.get_document(document_id, tenant_id)
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")

    return document


@router.get("/{document_id}/status", response_model=ProcessingStatus)
async def get_document_status(
    document_id: str,
    current_user: TenantUser,
    service: DocumentService = Depends(get_document_service),
):
    """Get document processing status."""
    tenant_id = getattr(current_user, "tenant_id", None)
    if not tenant_id:
        raise HTTPException(status_code=400, detail="User not associated with a tenant")

    document = await service.get_document(document_id, tenant_id)
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")

    return ProcessingStatus(
        document_id=document_id,
        status=document.status,
        progress=1.0 if document.status == DocumentStatus.COMPLETED else 0.5,
        chunks_processed=document.chunk_count,
        total_chunks=document.chunk_count,
    )


@router.get("/{document_id}/chunks", response_model=list[ChunkResponse])
async def get_document_chunks(
    document_id: str,
    current_user: TenantUser,
    service: DocumentService = Depends(get_document_service),
):
    """Get all chunks for a document."""
    tenant_id = getattr(current_user, "tenant_id", None)
    if not tenant_id:
        raise HTTPException(status_code=400, detail="User not associated with a tenant")

    chunks = await service.get_chunks(document_id, tenant_id)
    if not chunks:
        raise HTTPException(status_code=404, detail="Document not found or has no chunks")

    return chunks


@router.delete("/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_document(
    document_id: str,
    current_user: TenantUser,
    service: DocumentService = Depends(get_document_service),
):
    """Delete a document and its chunks."""
    tenant_id = getattr(current_user, "tenant_id", None)
    if not tenant_id:
        raise HTTPException(status_code=400, detail="User not associated with a tenant")

    deleted = await service.delete_document(document_id, tenant_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Document not found")


@router.post("/search", response_model=SearchResponse)
async def search_documents(
    request: SearchRequest,
    current_user: TenantUser,
    service: DocumentService = Depends(get_document_service),
):
    """
    Search across documents using full-text search.

    Searches document chunks and summaries.
    """
    tenant_id = getattr(current_user, "tenant_id", None)
    if not tenant_id:
        raise HTTPException(status_code=400, detail="User not associated with a tenant")

    return await service.search(
        query=request.query,
        tenant_id=tenant_id,
        agent_id=request.agent_id,
        limit=request.limit,
    )
