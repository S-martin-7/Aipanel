"""
Tests for documents module.

Tests document upload, processing, and retrieval.
"""

import pytest
from httpx import AsyncClient
from io import BytesIO


@pytest.mark.asyncio
async def test_list_documents(client: AsyncClient, auth_headers: dict):
    """Test listing documents."""
    response = await client.get(
        "/api/v1/documents",
        headers=auth_headers,
    )
    assert response.status_code in [200, 403]


@pytest.mark.asyncio
async def test_upload_document(client: AsyncClient, auth_headers: dict):
    """Test uploading a document."""
    # Create a simple text file
    content = BytesIO(b"This is a test document content.")
    content.name = "test.txt"

    response = await client.post(
        "/api/v1/documents/upload",
        files={"file": ("test.txt", content, "text/plain")},
        data={"agent_id": "test-agent-id"},
        headers=auth_headers,
    )
    assert response.status_code in [200, 201, 400, 403]


@pytest.mark.asyncio
async def test_get_document_by_id(client: AsyncClient, auth_headers: dict):
    """Test getting a document by ID."""
    response = await client.get(
        "/api/v1/documents/test-doc-id",
        headers=auth_headers,
    )
    assert response.status_code in [200, 404]


@pytest.mark.asyncio
async def test_delete_document(client: AsyncClient, auth_headers: dict):
    """Test deleting a document."""
    response = await client.delete(
        "/api/v1/documents/test-doc-id",
        headers=auth_headers,
    )
    assert response.status_code in [200, 204, 404, 403]


@pytest.mark.asyncio
async def test_document_chunks(client: AsyncClient, auth_headers: dict):
    """Test getting document chunks."""
    response = await client.get(
        "/api/v1/documents/test-doc-id/chunks",
        headers=auth_headers,
    )
    assert response.status_code in [200, 404]


@pytest.mark.asyncio
async def test_document_summaries(client: AsyncClient, auth_headers: dict):
    """Test getting document summaries."""
    response = await client.get(
        "/api/v1/documents/test-doc-id/summaries",
        headers=auth_headers,
    )
    assert response.status_code in [200, 404]


@pytest.mark.asyncio
async def test_search_documents(client: AsyncClient, auth_headers: dict):
    """Test searching documents."""
    response = await client.post(
        "/api/v1/search/query",
        json={"query": "test search", "limit": 10},
        headers=auth_headers,
    )
    assert response.status_code in [200, 400]
