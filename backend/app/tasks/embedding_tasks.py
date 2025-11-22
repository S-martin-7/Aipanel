"""
Celery tasks for generating document embeddings.
"""

import asyncio
from typing import List

from app.tasks.celery_app import celery_app
from app.core.database import async_session_maker
from app.integrations.embeddings import embedding_service
from app.utils.logger import get_logger
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

logger = get_logger(__name__)


async def _generate_document_embeddings(document_id: str) -> dict:
    """
    Generate embeddings for all chunks of a document.
    """
    from app.models.document import Document, DocumentChunk

    async with async_session_maker() as db:
        # Get document
        result = await db.execute(
            select(Document).where(Document.id == document_id)
        )
        document = result.scalar_one_or_none()

        if not document:
            logger.error(f"Document {document_id} not found")
            return {"success": False, "error": "Document not found"}

        # Get all chunks
        result = await db.execute(
            select(DocumentChunk)
            .where(DocumentChunk.document_id == document_id)
            .order_by(DocumentChunk.chunk_index)
        )
        chunks = result.scalars().all()

        if not chunks:
            logger.warning(f"No chunks found for document {document_id}")
            return {"success": True, "chunks_processed": 0}

        # Generate embeddings in batches
        chunk_contents = [chunk.content for chunk in chunks]
        embeddings = await embedding_service.generate_embeddings(chunk_contents)

        # Store embeddings
        for chunk, embedding in zip(chunks, embeddings):
            await embedding_service.store_chunk_embedding(
                db=db,
                chunk_id=str(chunk.id),
                document_id=document_id,
                content=chunk.content,
                embedding=embedding,
                metadata={
                    "chunk_index": chunk.chunk_index,
                    "word_count": chunk.word_count,
                }
            )

        # Update document status
        await db.execute(
            update(Document)
            .where(Document.id == document_id)
            .values(
                embeddings_generated=True,
                embedding_model="text-embedding-3-small"
            )
        )
        await db.commit()

        logger.info(f"Generated embeddings for {len(chunks)} chunks of document {document_id}")

        return {
            "success": True,
            "document_id": document_id,
            "chunks_processed": len(chunks),
        }


@celery_app.task(
    name="tasks.generate_document_embeddings",
    bind=True,
    max_retries=3,
    default_retry_delay=60,
)
def generate_document_embeddings(self, document_id: str) -> dict:
    """
    Celery task to generate embeddings for a document.
    """
    try:
        result = asyncio.get_event_loop().run_until_complete(
            _generate_document_embeddings(document_id)
        )
        return result
    except Exception as e:
        logger.error(f"Error generating embeddings for document {document_id}: {e}")
        raise self.retry(exc=e)


async def _regenerate_tenant_embeddings(tenant_id: str) -> dict:
    """
    Regenerate embeddings for all documents of a tenant.
    """
    from app.models.document import Document

    async with async_session_maker() as db:
        # Get all documents
        result = await db.execute(
            select(Document.id)
            .where(Document.tenant_id == tenant_id)
        )
        document_ids = [str(row[0]) for row in result.fetchall()]

        # Queue embedding generation for each document
        for doc_id in document_ids:
            generate_document_embeddings.delay(doc_id)

        return {
            "success": True,
            "documents_queued": len(document_ids),
        }


@celery_app.task(
    name="tasks.regenerate_tenant_embeddings",
    bind=True,
)
def regenerate_tenant_embeddings(self, tenant_id: str) -> dict:
    """
    Celery task to regenerate embeddings for all tenant documents.
    """
    try:
        result = asyncio.get_event_loop().run_until_complete(
            _regenerate_tenant_embeddings(tenant_id)
        )
        return result
    except Exception as e:
        logger.error(f"Error regenerating embeddings for tenant {tenant_id}: {e}")
        raise


async def _search_similar_chunks(
    query: str,
    tenant_id: str,
    agent_id: str = None,
    limit: int = 5,
) -> List[dict]:
    """
    Search for similar chunks using vector similarity.
    """
    async with async_session_maker() as db:
        results = await embedding_service.search_by_text(
            db=db,
            query=query,
            tenant_id=tenant_id,
            agent_id=agent_id,
            limit=limit,
        )

        # Rerank results
        reranked = await embedding_service.rerank_results(
            query=query,
            results=results,
            top_k=limit,
        )

        return reranked


@celery_app.task(name="tasks.search_similar_chunks")
def search_similar_chunks(
    query: str,
    tenant_id: str,
    agent_id: str = None,
    limit: int = 5,
) -> List[dict]:
    """
    Celery task to search similar chunks (for async API calls).
    """
    return asyncio.get_event_loop().run_until_complete(
        _search_similar_chunks(query, tenant_id, agent_id, limit)
    )
