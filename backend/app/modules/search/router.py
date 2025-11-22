"""
Search Module - Router

Endpoints for document and content search using PostgreSQL full-text search.
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import TenantUser
from app.modules.documents.service import DocumentService
from app.modules.documents.schemas import SearchResponse

router = APIRouter()


def get_document_service(db: AsyncSession = Depends(get_db)) -> DocumentService:
    """Dependency to get document service."""
    return DocumentService(db)


@router.get("/", response_model=SearchResponse)
async def search_documents(
    q: str = Query(..., min_length=2, max_length=500, description="Search query"),
    agent_id: str = Query(None, description="Filter by agent"),
    limit: int = Query(10, ge=1, le=50),
    current_user: TenantUser = Depends(),
    service: DocumentService = Depends(get_document_service),
):
    """
    Search documents using PostgreSQL full-text search.

    Searches across document chunks and summaries.
    Returns relevant snippets with highlighting.
    """
    tenant_id = getattr(current_user, "tenant_id", None)
    if not tenant_id:
        raise HTTPException(status_code=400, detail="User not associated with a tenant")

    return await service.search(
        query=q,
        tenant_id=tenant_id,
        agent_id=agent_id,
        limit=limit,
    )


@router.get("/suggestions")
async def get_search_suggestions(
    q: str = Query(..., min_length=2, max_length=100),
    limit: int = Query(5, ge=1, le=10),
    current_user: TenantUser = Depends(),
    service: DocumentService = Depends(get_document_service),
):
    """
    Get search suggestions based on query.

    Returns document titles and chunk snippets that match the query.
    """
    tenant_id = getattr(current_user, "tenant_id", None)
    if not tenant_id:
        raise HTTPException(status_code=400, detail="User not associated with a tenant")

    # Use search but return simplified suggestions
    results = await service.search(
        query=q,
        tenant_id=tenant_id,
        limit=limit,
    )

    suggestions = []
    seen_docs = set()

    for result in results.results:
        if result.document_id not in seen_docs:
            suggestions.append({
                "text": result.filename,
                "type": "document",
                "document_id": result.document_id,
            })
            seen_docs.add(result.document_id)

        if result.highlight and len(suggestions) < limit:
            suggestions.append({
                "text": result.highlight[:100],
                "type": "snippet",
                "document_id": result.document_id,
                "chunk_id": result.chunk_id,
            })

    return {"suggestions": suggestions[:limit]}
