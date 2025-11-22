"""
Search Service - Unified search across documents and content.

Provides full-text search, semantic/vector search, and hybrid search capabilities.
"""

from typing import Optional, List, Dict, Any
from uuid import UUID
from dataclasses import dataclass
from enum import Enum
import asyncio

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.utils.logger import get_logger
from app.integrations.embeddings import EmbeddingService

logger = get_logger(__name__)


class SearchMode(str, Enum):
    """Search modes available."""
    FULLTEXT = "fulltext"      # PostgreSQL full-text search
    SEMANTIC = "semantic"       # Vector/embedding search
    HYBRID = "hybrid"          # Combined search


@dataclass
class SearchResult:
    """Individual search result."""
    document_id: str
    chunk_id: Optional[str]
    filename: str
    content: str
    highlight: Optional[str]
    score: float
    metadata: Dict[str, Any]


@dataclass
class SearchResponse:
    """Search response with results and metadata."""
    results: List[SearchResult]
    total: int
    query: str
    mode: SearchMode
    facets: Optional[Dict[str, List[Dict]]] = None


class SearchService:
    """
    Unified search service combining multiple search strategies.

    Supports:
    - Full-text search using PostgreSQL tsvector
    - Semantic search using vector embeddings
    - Hybrid search combining both approaches
    - Faceted search for filtering
    """

    def __init__(self, db: AsyncSession):
        self.db = db
        self.embedding_service = EmbeddingService()

    async def search(
        self,
        query: str,
        tenant_id: str,
        mode: SearchMode = SearchMode.HYBRID,
        agent_id: Optional[str] = None,
        document_types: Optional[List[str]] = None,
        limit: int = 10,
        offset: int = 0,
        include_facets: bool = False,
    ) -> SearchResponse:
        """
        Perform search based on specified mode.

        Args:
            query: Search query string
            tenant_id: Tenant ID for multi-tenancy
            mode: Search mode (fulltext, semantic, hybrid)
            agent_id: Optional agent filter
            document_types: Optional document type filter
            limit: Maximum results to return
            offset: Pagination offset
            include_facets: Whether to include facet counts

        Returns:
            SearchResponse with results and metadata
        """
        if mode == SearchMode.FULLTEXT:
            results = await self._fulltext_search(
                query, tenant_id, agent_id, document_types, limit, offset
            )
        elif mode == SearchMode.SEMANTIC:
            results = await self._semantic_search(
                query, tenant_id, agent_id, document_types, limit, offset
            )
        else:  # HYBRID
            results = await self._hybrid_search(
                query, tenant_id, agent_id, document_types, limit, offset
            )

        facets = None
        if include_facets:
            facets = await self._get_facets(query, tenant_id, agent_id)

        return SearchResponse(
            results=results,
            total=len(results),
            query=query,
            mode=mode,
            facets=facets,
        )

    async def _fulltext_search(
        self,
        query: str,
        tenant_id: str,
        agent_id: Optional[str],
        document_types: Optional[List[str]],
        limit: int,
        offset: int,
    ) -> List[SearchResult]:
        """
        PostgreSQL full-text search using tsvector.

        Uses ts_rank for relevance scoring and ts_headline for highlighting.
        """
        # Build the search query
        sql = """
        SELECT
            dc.id as chunk_id,
            dc.document_id,
            d.filename,
            dc.content,
            ts_headline('spanish', dc.content, plainto_tsquery('spanish', :query),
                'StartSel=<mark>, StopSel=</mark>, MaxWords=50, MinWords=20') as highlight,
            ts_rank(dc.search_vector, plainto_tsquery('spanish', :query)) as score,
            d.metadata
        FROM document_chunks dc
        JOIN documents d ON d.id = dc.document_id
        WHERE d.tenant_id = :tenant_id
            AND dc.search_vector @@ plainto_tsquery('spanish', :query)
        """

        params: Dict[str, Any] = {
            "query": query,
            "tenant_id": tenant_id,
        }

        if agent_id:
            sql += " AND d.agent_id = :agent_id"
            params["agent_id"] = agent_id

        if document_types:
            sql += " AND d.content_type = ANY(:doc_types)"
            params["doc_types"] = document_types

        sql += """
        ORDER BY score DESC
        LIMIT :limit OFFSET :offset
        """
        params["limit"] = limit
        params["offset"] = offset

        result = await self.db.execute(text(sql), params)
        rows = result.fetchall()

        return [
            SearchResult(
                document_id=str(row.document_id),
                chunk_id=str(row.chunk_id),
                filename=row.filename,
                content=row.content[:500],
                highlight=row.highlight,
                score=float(row.score),
                metadata=row.metadata or {},
            )
            for row in rows
        ]

    async def _semantic_search(
        self,
        query: str,
        tenant_id: str,
        agent_id: Optional[str],
        document_types: Optional[List[str]],
        limit: int,
        offset: int,
    ) -> List[SearchResult]:
        """
        Semantic search using vector embeddings.

        Uses pgvector for similarity search.
        """
        # Get embedding for query
        query_embedding = await self.embedding_service.generate_embedding(query)

        # Vector similarity search
        sql = """
        SELECT
            dc.id as chunk_id,
            dc.document_id,
            d.filename,
            dc.content,
            1 - (dc.embedding <=> :embedding::vector) as score,
            d.metadata
        FROM document_chunks dc
        JOIN documents d ON d.id = dc.document_id
        WHERE d.tenant_id = :tenant_id
            AND dc.embedding IS NOT NULL
        """

        params: Dict[str, Any] = {
            "embedding": str(query_embedding),
            "tenant_id": tenant_id,
        }

        if agent_id:
            sql += " AND d.agent_id = :agent_id"
            params["agent_id"] = agent_id

        if document_types:
            sql += " AND d.content_type = ANY(:doc_types)"
            params["doc_types"] = document_types

        sql += """
        ORDER BY dc.embedding <=> :embedding::vector
        LIMIT :limit OFFSET :offset
        """
        params["limit"] = limit
        params["offset"] = offset

        result = await self.db.execute(text(sql), params)
        rows = result.fetchall()

        return [
            SearchResult(
                document_id=str(row.document_id),
                chunk_id=str(row.chunk_id),
                filename=row.filename,
                content=row.content[:500],
                highlight=self._create_highlight(row.content, query),
                score=float(row.score) if row.score else 0.0,
                metadata=row.metadata or {},
            )
            for row in rows
        ]

    async def _hybrid_search(
        self,
        query: str,
        tenant_id: str,
        agent_id: Optional[str],
        document_types: Optional[List[str]],
        limit: int,
        offset: int,
    ) -> List[SearchResult]:
        """
        Hybrid search combining full-text and semantic search.

        Uses Reciprocal Rank Fusion (RRF) to combine scores.
        """
        # Run both searches in parallel
        fulltext_task = self._fulltext_search(
            query, tenant_id, agent_id, document_types, limit * 2, 0
        )
        semantic_task = self._semantic_search(
            query, tenant_id, agent_id, document_types, limit * 2, 0
        )

        fulltext_results, semantic_results = await asyncio.gather(
            fulltext_task, semantic_task
        )

        # Combine using RRF
        combined = self._reciprocal_rank_fusion(
            fulltext_results, semantic_results, k=60
        )

        # Apply pagination
        return combined[offset:offset + limit]

    def _reciprocal_rank_fusion(
        self,
        results_a: List[SearchResult],
        results_b: List[SearchResult],
        k: int = 60,
    ) -> List[SearchResult]:
        """
        Combine two ranked lists using Reciprocal Rank Fusion.

        RRF score = sum(1 / (k + rank)) across all lists
        """
        scores: Dict[str, float] = {}
        results_map: Dict[str, SearchResult] = {}

        # Score from first list
        for rank, result in enumerate(results_a, 1):
            key = f"{result.document_id}:{result.chunk_id}"
            scores[key] = scores.get(key, 0) + 1 / (k + rank)
            results_map[key] = result

        # Score from second list
        for rank, result in enumerate(results_b, 1):
            key = f"{result.document_id}:{result.chunk_id}"
            scores[key] = scores.get(key, 0) + 1 / (k + rank)
            if key not in results_map:
                results_map[key] = result

        # Sort by combined score
        sorted_keys = sorted(scores.keys(), key=lambda x: scores[x], reverse=True)

        return [
            SearchResult(
                document_id=results_map[key].document_id,
                chunk_id=results_map[key].chunk_id,
                filename=results_map[key].filename,
                content=results_map[key].content,
                highlight=results_map[key].highlight,
                score=scores[key],
                metadata=results_map[key].metadata,
            )
            for key in sorted_keys
        ]

    async def _get_facets(
        self,
        query: str,
        tenant_id: str,
        agent_id: Optional[str],
    ) -> Dict[str, List[Dict]]:
        """
        Get facet counts for search filters.

        Returns counts by document type, agent, and date.
        """
        facets = {}

        # Document type facets
        type_sql = """
        SELECT d.content_type, COUNT(*) as count
        FROM documents d
        JOIN document_chunks dc ON dc.document_id = d.id
        WHERE d.tenant_id = :tenant_id
            AND dc.search_vector @@ plainto_tsquery('spanish', :query)
        GROUP BY d.content_type
        ORDER BY count DESC
        """

        result = await self.db.execute(
            text(type_sql),
            {"tenant_id": tenant_id, "query": query}
        )
        facets["document_types"] = [
            {"value": row.content_type, "count": row.count}
            for row in result.fetchall()
        ]

        # Agent facets
        agent_sql = """
        SELECT d.agent_id, a.name as agent_name, COUNT(*) as count
        FROM documents d
        JOIN document_chunks dc ON dc.document_id = d.id
        JOIN agents a ON a.id = d.agent_id
        WHERE d.tenant_id = :tenant_id
            AND dc.search_vector @@ plainto_tsquery('spanish', :query)
        GROUP BY d.agent_id, a.name
        ORDER BY count DESC
        """

        result = await self.db.execute(
            text(agent_sql),
            {"tenant_id": tenant_id, "query": query}
        )
        facets["agents"] = [
            {"value": str(row.agent_id), "label": row.agent_name, "count": row.count}
            for row in result.fetchall()
        ]

        return facets

    def _create_highlight(self, content: str, query: str, max_length: int = 200) -> str:
        """Create a simple highlight by finding query terms in content."""
        query_terms = query.lower().split()
        content_lower = content.lower()

        # Find first occurrence of any query term
        best_pos = len(content)
        for term in query_terms:
            pos = content_lower.find(term)
            if pos != -1 and pos < best_pos:
                best_pos = pos

        if best_pos == len(content):
            # No match found, return start of content
            return content[:max_length] + "..." if len(content) > max_length else content

        # Center the highlight around the match
        start = max(0, best_pos - max_length // 2)
        end = min(len(content), start + max_length)

        snippet = content[start:end]

        # Add ellipsis if truncated
        if start > 0:
            snippet = "..." + snippet
        if end < len(content):
            snippet = snippet + "..."

        return snippet

    async def get_similar_documents(
        self,
        document_id: str,
        tenant_id: str,
        limit: int = 5,
    ) -> List[SearchResult]:
        """
        Find documents similar to a given document.

        Uses average embedding of document chunks for similarity.
        """
        # Get average embedding of the document
        sql = """
        SELECT AVG(dc.embedding) as avg_embedding
        FROM document_chunks dc
        WHERE dc.document_id = :document_id
            AND dc.embedding IS NOT NULL
        """

        result = await self.db.execute(
            text(sql), {"document_id": document_id}
        )
        row = result.fetchone()

        if not row or not row.avg_embedding:
            return []

        # Find similar documents
        similar_sql = """
        SELECT DISTINCT ON (d.id)
            d.id as document_id,
            d.filename,
            dc.content,
            1 - (dc.embedding <=> :embedding::vector) as score,
            d.metadata
        FROM document_chunks dc
        JOIN documents d ON d.id = dc.document_id
        WHERE d.tenant_id = :tenant_id
            AND d.id != :document_id
            AND dc.embedding IS NOT NULL
        ORDER BY d.id, dc.embedding <=> :embedding::vector
        LIMIT :limit
        """

        result = await self.db.execute(
            text(similar_sql),
            {
                "embedding": str(row.avg_embedding),
                "tenant_id": tenant_id,
                "document_id": document_id,
                "limit": limit,
            }
        )

        return [
            SearchResult(
                document_id=str(r.document_id),
                chunk_id=None,
                filename=r.filename,
                content=r.content[:300] if r.content else "",
                highlight=None,
                score=float(r.score) if r.score else 0.0,
                metadata=r.metadata or {},
            )
            for r in result.fetchall()
        ]

    async def search_by_metadata(
        self,
        tenant_id: str,
        filters: Dict[str, Any],
        limit: int = 10,
    ) -> List[SearchResult]:
        """
        Search documents by metadata filters.

        Useful for filtering by custom document attributes.
        """
        sql = """
        SELECT
            d.id as document_id,
            d.filename,
            dc.content,
            d.metadata
        FROM documents d
        LEFT JOIN document_chunks dc ON dc.document_id = d.id
        WHERE d.tenant_id = :tenant_id
        """

        params: Dict[str, Any] = {"tenant_id": tenant_id}

        # Add metadata filters
        for key, value in filters.items():
            param_name = f"meta_{key}"
            sql += f" AND d.metadata->>'{key}' = :{param_name}"
            params[param_name] = str(value)

        sql += " LIMIT :limit"
        params["limit"] = limit

        result = await self.db.execute(text(sql), params)

        return [
            SearchResult(
                document_id=str(row.document_id),
                chunk_id=None,
                filename=row.filename,
                content=row.content[:300] if row.content else "",
                highlight=None,
                score=1.0,
                metadata=row.metadata or {},
            )
            for row in result.fetchall()
        ]
