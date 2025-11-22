"""
Search Module - Router

Endpoints for document and content search using PostgreSQL full-text search
and vector embeddings for semantic search.
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, List

from app.core.database import get_db
from app.core.dependencies import TenantUser
from app.modules.search.service import SearchService, SearchMode
from app.modules.search.schemas import (
    SearchRequest,
    SearchResponse,
    SearchResultItem,
    SearchSuggestionsResponse,
    SimilarDocumentsRequest,
    MetadataSearchRequest,
)

router = APIRouter()


def get_search_service(db: AsyncSession = Depends(get_db)) -> SearchService:
    """Dependency to get search service."""
    return SearchService(db)


@router.get("/", response_model=SearchResponse)
async def search_documents(
    q: str = Query(..., min_length=2, max_length=500, description="Search query"),
    mode: SearchMode = Query(SearchMode.HYBRID, description="Search mode"),
    agent_id: Optional[str] = Query(None, description="Filter by agent"),
    document_types: Optional[List[str]] = Query(None, description="Filter by document types"),
    limit: int = Query(10, ge=1, le=50),
    offset: int = Query(0, ge=0),
    include_facets: bool = Query(False, description="Include facet counts"),
    current_user: TenantUser = Depends(),
    service: SearchService = Depends(get_search_service),
):
    """
    Search documents using full-text, semantic, or hybrid search.

    - **fulltext**: PostgreSQL full-text search with tsvector
    - **semantic**: Vector similarity search using embeddings
    - **hybrid**: Combined search using Reciprocal Rank Fusion

    Returns relevant snippets with highlighting and optional facets.
    """
    tenant_id = getattr(current_user, "tenant_id", None)
    if not tenant_id:
        raise HTTPException(status_code=400, detail="User not associated with a tenant")

    result = await service.search(
        query=q,
        tenant_id=str(tenant_id),
        mode=mode,
        agent_id=agent_id,
        document_types=document_types,
        limit=limit,
        offset=offset,
        include_facets=include_facets,
    )

    return SearchResponse(
        results=[
            SearchResultItem(
                document_id=r.document_id,
                chunk_id=r.chunk_id,
                filename=r.filename,
                content=r.content,
                highlight=r.highlight,
                score=r.score,
                metadata=r.metadata,
            )
            for r in result.results
        ],
        total=result.total,
        query=result.query,
        mode=result.mode,
        facets=result.facets,
    )


@router.get("/suggestions", response_model=SearchSuggestionsResponse)
async def get_search_suggestions(
    q: str = Query(..., min_length=2, max_length=100),
    limit: int = Query(5, ge=1, le=10),
    current_user: TenantUser = Depends(),
    service: SearchService = Depends(get_search_service),
):
    """
    Get search suggestions based on query.

    Returns document titles and chunk snippets that match the query.
    """
    tenant_id = getattr(current_user, "tenant_id", None)
    if not tenant_id:
        raise HTTPException(status_code=400, detail="User not associated with a tenant")

    results = await service.search(
        query=q,
        tenant_id=str(tenant_id),
        mode=SearchMode.FULLTEXT,
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

    return SearchSuggestionsResponse(suggestions=suggestions[:limit])


@router.get("/similar/{document_id}")
async def get_similar_documents(
    document_id: str,
    limit: int = Query(5, ge=1, le=20),
    current_user: TenantUser = Depends(),
    service: SearchService = Depends(get_search_service),
):
    """
    Find documents similar to a given document.

    Uses vector embeddings to find semantically similar content.
    """
    tenant_id = getattr(current_user, "tenant_id", None)
    if not tenant_id:
        raise HTTPException(status_code=400, detail="User not associated with a tenant")

    results = await service.get_similar_documents(
        document_id=document_id,
        tenant_id=str(tenant_id),
        limit=limit,
    )

    return {
        "document_id": document_id,
        "similar": [
            SearchResultItem(
                document_id=r.document_id,
                chunk_id=r.chunk_id,
                filename=r.filename,
                content=r.content,
                highlight=r.highlight,
                score=r.score,
                metadata=r.metadata,
            )
            for r in results
        ],
    }
