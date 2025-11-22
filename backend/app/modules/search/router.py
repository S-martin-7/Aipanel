"""
Search module - Router

Endpoints for document and content search.
"""

from fastapi import APIRouter, Depends, Query
from app.core.dependencies import TenantUser

router = APIRouter()


@router.get("/")
async def search_documents(
    q: str = Query(..., min_length=2, description="Search query"),
    limit: int = Query(10, ge=1, le=100),
    current_user: TenantUser = Depends()
):
    """Search documents using full-text search."""
    # TODO: Implement PostgreSQL full-text search
    return {
        "query": q,
        "results": [],
        "total": 0
    }


@router.get("/suggestions")
async def get_search_suggestions(
    q: str = Query(..., min_length=2),
    current_user: TenantUser = Depends()
):
    """Get search suggestions based on query."""
    # TODO: Implement
    return {"suggestions": []}
