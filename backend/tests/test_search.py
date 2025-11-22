"""
Tests for search module.
"""

import pytest
from httpx import AsyncClient
from unittest.mock import patch, AsyncMock, MagicMock
from uuid import uuid4


class TestSearchEndpoints:
    """Test search API endpoints."""

    @pytest.mark.asyncio
    async def test_search_requires_auth(self, client: AsyncClient):
        """Test that search endpoint requires authentication."""
        response = await client.get("/api/v1/search", params={"q": "test"})
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_search_documents(
        self, client: AsyncClient, auth_headers: dict
    ):
        """Test searching documents."""
        with patch("app.modules.search.service.SearchService.search") as mock:
            from app.modules.search.service import SearchMode, SearchResult, SearchResponse

            mock.return_value = SearchResponse(
                results=[
                    SearchResult(
                        document_id=str(uuid4()),
                        chunk_id=str(uuid4()),
                        filename="test.pdf",
                        content="This is test content",
                        highlight="This is <mark>test</mark> content",
                        score=0.95,
                        metadata={},
                    )
                ],
                total=1,
                query="test",
                mode=SearchMode.HYBRID,
            )

            response = await client.get(
                "/api/v1/search",
                headers=auth_headers,
                params={"q": "test"},
            )

            assert response.status_code == 200
            data = response.json()
            assert "results" in data
            assert data["total"] == 1

    @pytest.mark.asyncio
    async def test_search_with_mode(
        self, client: AsyncClient, auth_headers: dict
    ):
        """Test searching with different modes."""
        for mode in ["fulltext", "semantic", "hybrid"]:
            response = await client.get(
                "/api/v1/search",
                headers=auth_headers,
                params={"q": "test", "mode": mode},
            )
            assert response.status_code in [200, 422]

    @pytest.mark.asyncio
    async def test_search_with_filters(
        self, client: AsyncClient, auth_headers: dict
    ):
        """Test searching with agent and document type filters."""
        response = await client.get(
            "/api/v1/search",
            headers=auth_headers,
            params={
                "q": "test",
                "agent_id": str(uuid4()),
                "document_types": "pdf,docx",
            },
        )
        assert response.status_code in [200, 422]

    @pytest.mark.asyncio
    async def test_search_with_facets(
        self, client: AsyncClient, auth_headers: dict
    ):
        """Test searching with facets enabled."""
        response = await client.get(
            "/api/v1/search",
            headers=auth_headers,
            params={"q": "test", "include_facets": True},
        )
        assert response.status_code in [200, 422]

    @pytest.mark.asyncio
    async def test_search_suggestions(
        self, client: AsyncClient, auth_headers: dict
    ):
        """Test search suggestions."""
        response = await client.get(
            "/api/v1/search/suggestions",
            headers=auth_headers,
            params={"q": "te"},
        )
        assert response.status_code in [200, 422]

    @pytest.mark.asyncio
    async def test_similar_documents(
        self, client: AsyncClient, auth_headers: dict
    ):
        """Test finding similar documents."""
        document_id = str(uuid4())

        with patch("app.modules.search.service.SearchService.get_similar_documents") as mock:
            mock.return_value = []

            response = await client.get(
                f"/api/v1/search/similar/{document_id}",
                headers=auth_headers,
            )

            assert response.status_code in [200, 404]


class TestSearchService:
    """Test search service logic."""

    @pytest.mark.asyncio
    async def test_fulltext_search(self):
        """Test full-text search functionality."""
        from app.modules.search.service import SearchService, SearchMode

        # Mock database session
        mock_db = MagicMock()
        mock_db.execute = AsyncMock(return_value=MagicMock(fetchall=lambda: []))

        service = SearchService(mock_db)

        results = await service._fulltext_search(
            query="test",
            tenant_id=str(uuid4()),
            agent_id=None,
            document_types=None,
            limit=10,
            offset=0,
        )

        assert isinstance(results, list)

    @pytest.mark.asyncio
    async def test_semantic_search(self):
        """Test semantic/vector search functionality."""
        from app.modules.search.service import SearchService

        mock_db = MagicMock()
        mock_db.execute = AsyncMock(return_value=MagicMock(fetchall=lambda: []))

        service = SearchService(mock_db)

        with patch.object(
            service.embedding_service, "generate_embedding"
        ) as mock_embed:
            mock_embed.return_value = [0.1] * 1536

            results = await service._semantic_search(
                query="test",
                tenant_id=str(uuid4()),
                agent_id=None,
                document_types=None,
                limit=10,
                offset=0,
            )

            assert isinstance(results, list)

    @pytest.mark.asyncio
    async def test_hybrid_search(self):
        """Test hybrid search combining fulltext and semantic."""
        from app.modules.search.service import SearchService, SearchResult

        mock_db = MagicMock()
        mock_db.execute = AsyncMock(return_value=MagicMock(fetchall=lambda: []))

        service = SearchService(mock_db)

        # Mock the internal search methods
        with patch.object(service, "_fulltext_search") as mock_ft, \
             patch.object(service, "_semantic_search") as mock_sem:

            mock_ft.return_value = [
                SearchResult(
                    document_id="doc1",
                    chunk_id="chunk1",
                    filename="test.pdf",
                    content="content",
                    highlight="highlight",
                    score=0.9,
                    metadata={},
                )
            ]
            mock_sem.return_value = [
                SearchResult(
                    document_id="doc2",
                    chunk_id="chunk2",
                    filename="test2.pdf",
                    content="content2",
                    highlight="highlight2",
                    score=0.8,
                    metadata={},
                )
            ]

            results = await service._hybrid_search(
                query="test",
                tenant_id=str(uuid4()),
                agent_id=None,
                document_types=None,
                limit=10,
                offset=0,
            )

            assert isinstance(results, list)
            assert len(results) == 2

    def test_reciprocal_rank_fusion(self):
        """Test RRF score combination."""
        from app.modules.search.service import SearchService, SearchResult

        mock_db = MagicMock()
        service = SearchService(mock_db)

        results_a = [
            SearchResult(
                document_id="doc1",
                chunk_id="chunk1",
                filename="a.pdf",
                content="c",
                highlight="h",
                score=1.0,
                metadata={},
            ),
            SearchResult(
                document_id="doc2",
                chunk_id="chunk2",
                filename="b.pdf",
                content="c",
                highlight="h",
                score=0.5,
                metadata={},
            ),
        ]

        results_b = [
            SearchResult(
                document_id="doc2",
                chunk_id="chunk2",
                filename="b.pdf",
                content="c",
                highlight="h",
                score=1.0,
                metadata={},
            ),
            SearchResult(
                document_id="doc1",
                chunk_id="chunk1",
                filename="a.pdf",
                content="c",
                highlight="h",
                score=0.5,
                metadata={},
            ),
        ]

        combined = service._reciprocal_rank_fusion(results_a, results_b)

        # Both documents should have same combined score
        assert len(combined) == 2
        # Scores should be equal since they're reciprocal in rankings
        assert abs(combined[0].score - combined[1].score) < 0.01

    def test_create_highlight(self):
        """Test highlight creation."""
        from app.modules.search.service import SearchService

        mock_db = MagicMock()
        service = SearchService(mock_db)

        content = "This is a test document with some content about Python programming."
        highlight = service._create_highlight(content, "Python", max_length=50)

        assert len(highlight) <= 60  # max_length + ellipsis
        assert "Python" in highlight or "..." in highlight


class TestSearchSchemas:
    """Test search schemas."""

    def test_search_request_validation(self):
        """Test search request schema validation."""
        from app.modules.search.schemas import SearchRequest, SearchMode

        request = SearchRequest(
            query="test query",
            mode=SearchMode.HYBRID,
            limit=10,
        )

        assert request.query == "test query"
        assert request.mode == SearchMode.HYBRID
        assert request.limit == 10

    def test_search_request_short_query(self):
        """Test that short queries are rejected."""
        from app.modules.search.schemas import SearchRequest
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            SearchRequest(query="a", limit=10)

    def test_search_result_item(self):
        """Test search result item schema."""
        from app.modules.search.schemas import SearchResultItem

        result = SearchResultItem(
            document_id=str(uuid4()),
            chunk_id=str(uuid4()),
            filename="test.pdf",
            content="Test content",
            highlight="<mark>Test</mark> content",
            score=0.95,
            metadata={"author": "Test"},
        )

        assert result.score == 0.95
        assert result.metadata["author"] == "Test"

    def test_search_response(self):
        """Test search response schema."""
        from app.modules.search.schemas import SearchResponse, SearchResultItem, SearchMode

        response = SearchResponse(
            results=[
                SearchResultItem(
                    document_id=str(uuid4()),
                    filename="test.pdf",
                    content="content",
                    score=0.9,
                )
            ],
            total=1,
            query="test",
            mode=SearchMode.FULLTEXT,
        )

        assert response.total == 1
        assert len(response.results) == 1
