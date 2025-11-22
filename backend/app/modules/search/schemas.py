"""
Search Module - Schemas

Request/Response schemas for search endpoints.
"""

from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from enum import Enum


class SearchMode(str, Enum):
    """Search modes available."""
    FULLTEXT = "fulltext"
    SEMANTIC = "semantic"
    HYBRID = "hybrid"


class SearchRequest(BaseModel):
    """Search request schema."""
    query: str = Field(..., min_length=2, max_length=500)
    mode: SearchMode = SearchMode.HYBRID
    agent_id: Optional[str] = None
    document_types: Optional[List[str]] = None
    limit: int = Field(10, ge=1, le=50)
    offset: int = Field(0, ge=0)
    include_facets: bool = False


class SearchResultItem(BaseModel):
    """Individual search result item."""
    document_id: str
    chunk_id: Optional[str] = None
    filename: str
    content: str
    highlight: Optional[str] = None
    score: float
    metadata: Dict[str, Any] = Field(default_factory=dict)


class FacetValue(BaseModel):
    """Facet value with count."""
    value: str
    label: Optional[str] = None
    count: int


class SearchFacets(BaseModel):
    """Search facets for filtering."""
    document_types: List[FacetValue] = Field(default_factory=list)
    agents: List[FacetValue] = Field(default_factory=list)


class SearchResponse(BaseModel):
    """Search response with results and metadata."""
    results: List[SearchResultItem]
    total: int
    query: str
    mode: SearchMode
    facets: Optional[SearchFacets] = None


class SimilarDocumentsRequest(BaseModel):
    """Request for similar documents."""
    document_id: str
    limit: int = Field(5, ge=1, le=20)


class MetadataSearchRequest(BaseModel):
    """Search by metadata filters."""
    filters: Dict[str, Any]
    limit: int = Field(10, ge=1, le=50)


class SearchSuggestion(BaseModel):
    """Search suggestion item."""
    text: str
    type: str  # "document" or "snippet"
    document_id: str
    chunk_id: Optional[str] = None


class SearchSuggestionsResponse(BaseModel):
    """Search suggestions response."""
    suggestions: List[SearchSuggestion]
