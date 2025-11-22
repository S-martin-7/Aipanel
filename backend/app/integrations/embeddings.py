"""
Vector embeddings service for AIPanel RAG system.

Supports multiple embedding providers (OpenAI, local models).
Uses pgvector for PostgreSQL vector storage.
"""

from typing import List, Optional
from abc import ABC, abstractmethod
import numpy as np
import hashlib

from openai import AsyncOpenAI
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

from app.core.config import settings
from app.utils.logger import get_logger

logger = get_logger(__name__)

# Embedding dimensions per model
EMBEDDING_DIMENSIONS = {
    "text-embedding-3-small": 1536,
    "text-embedding-3-large": 3072,
    "text-embedding-ada-002": 1536,
}


class EmbeddingProvider(ABC):
    """Base class for embedding providers."""

    @abstractmethod
    async def embed_text(self, text: str) -> List[float]:
        """Generate embedding for a single text."""
        pass

    @abstractmethod
    async def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for multiple texts."""
        pass


class OpenAIEmbeddings(EmbeddingProvider):
    """OpenAI embedding provider."""

    def __init__(
        self,
        api_key: str = None,
        model: str = "text-embedding-3-small",
    ):
        self.client = AsyncOpenAI(api_key=api_key or settings.OPENAI_API_KEY)
        self.model = model
        self.dimensions = EMBEDDING_DIMENSIONS.get(model, 1536)

    async def embed_text(self, text: str) -> List[float]:
        """Generate embedding for a single text."""
        response = await self.client.embeddings.create(
            model=self.model,
            input=text,
        )
        return response.data[0].embedding

    async def embed_batch(self, texts: List[str], batch_size: int = 100) -> List[List[float]]:
        """Generate embeddings for multiple texts in batches."""
        all_embeddings = []

        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]
            response = await self.client.embeddings.create(
                model=self.model,
                input=batch,
            )
            batch_embeddings = [item.embedding for item in response.data]
            all_embeddings.extend(batch_embeddings)

        return all_embeddings


class EmbeddingService:
    """
    Service for managing document embeddings and vector search.
    """

    def __init__(self, provider: EmbeddingProvider = None):
        self.provider = provider or OpenAIEmbeddings()

    async def generate_embedding(self, text: str) -> List[float]:
        """Generate embedding for text."""
        # Truncate text if too long (max ~8000 tokens for OpenAI)
        max_chars = 30000
        if len(text) > max_chars:
            text = text[:max_chars]

        return await self.provider.embed_text(text)

    async def generate_embeddings(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for multiple texts."""
        # Truncate texts
        max_chars = 30000
        texts = [t[:max_chars] if len(t) > max_chars else t for t in texts]

        return await self.provider.embed_batch(texts)

    def compute_content_hash(self, content: str) -> str:
        """Compute hash of content for deduplication."""
        return hashlib.sha256(content.encode()).hexdigest()

    async def store_chunk_embedding(
        self,
        db: AsyncSession,
        chunk_id: str,
        document_id: str,
        content: str,
        embedding: List[float],
        metadata: dict = None,
    ) -> None:
        """Store chunk embedding in database."""
        content_hash = self.compute_content_hash(content)

        # Convert embedding to pgvector format
        embedding_str = "[" + ",".join(map(str, embedding)) + "]"

        await db.execute(
            text("""
                INSERT INTO chunk_embeddings (
                    id, chunk_id, document_id, content_hash, embedding, metadata, created_at
                ) VALUES (
                    gen_random_uuid(), :chunk_id, :document_id, :content_hash,
                    :embedding::vector, :metadata::jsonb, NOW()
                )
                ON CONFLICT (content_hash) DO UPDATE SET
                    embedding = :embedding::vector,
                    updated_at = NOW()
            """),
            {
                "chunk_id": chunk_id,
                "document_id": document_id,
                "content_hash": content_hash,
                "embedding": embedding_str,
                "metadata": metadata or {},
            }
        )
        await db.commit()

    async def search_similar(
        self,
        db: AsyncSession,
        query_embedding: List[float],
        tenant_id: str,
        agent_id: str = None,
        limit: int = 5,
        threshold: float = 0.7,
    ) -> List[dict]:
        """
        Search for similar chunks using cosine similarity.

        Args:
            db: Database session
            query_embedding: Query vector
            tenant_id: Tenant ID for filtering
            agent_id: Optional agent ID for filtering
            limit: Maximum results to return
            threshold: Minimum similarity score (0-1)

        Returns:
            List of similar chunks with scores
        """
        embedding_str = "[" + ",".join(map(str, query_embedding)) + "]"

        # Build query with optional agent filter
        agent_filter = "AND d.agent_id = :agent_id" if agent_id else ""

        result = await db.execute(
            text(f"""
                SELECT
                    ce.chunk_id,
                    ce.document_id,
                    dc.content,
                    dc.chunk_index,
                    d.name as document_name,
                    1 - (ce.embedding <=> :embedding::vector) as similarity
                FROM chunk_embeddings ce
                JOIN document_chunks dc ON dc.id = ce.chunk_id
                JOIN documents d ON d.id = ce.document_id
                WHERE d.tenant_id = :tenant_id
                {agent_filter}
                AND 1 - (ce.embedding <=> :embedding::vector) >= :threshold
                ORDER BY ce.embedding <=> :embedding::vector
                LIMIT :limit
            """),
            {
                "embedding": embedding_str,
                "tenant_id": tenant_id,
                "agent_id": agent_id,
                "threshold": threshold,
                "limit": limit,
            }
        )

        rows = result.fetchall()
        return [
            {
                "chunk_id": row.chunk_id,
                "document_id": row.document_id,
                "content": row.content,
                "chunk_index": row.chunk_index,
                "document_name": row.document_name,
                "similarity": float(row.similarity),
            }
            for row in rows
        ]

    async def search_by_text(
        self,
        db: AsyncSession,
        query: str,
        tenant_id: str,
        agent_id: str = None,
        limit: int = 5,
        threshold: float = 0.7,
    ) -> List[dict]:
        """
        Search for similar chunks by text query.

        Generates embedding for query and performs vector search.
        """
        query_embedding = await self.generate_embedding(query)
        return await self.search_similar(
            db=db,
            query_embedding=query_embedding,
            tenant_id=tenant_id,
            agent_id=agent_id,
            limit=limit,
            threshold=threshold,
        )

    async def rerank_results(
        self,
        query: str,
        results: List[dict],
        top_k: int = 3,
    ) -> List[dict]:
        """
        Rerank search results using cross-encoder or simple heuristics.

        For now, uses simple keyword matching + semantic score.
        """
        query_words = set(query.lower().split())

        for result in results:
            content_words = set(result["content"].lower().split())
            keyword_overlap = len(query_words & content_words) / max(len(query_words), 1)

            # Combine semantic similarity with keyword overlap
            result["combined_score"] = (
                0.7 * result["similarity"] +
                0.3 * keyword_overlap
            )

        # Sort by combined score
        results.sort(key=lambda x: x["combined_score"], reverse=True)

        return results[:top_k]


# Global service instance
embedding_service = EmbeddingService()
