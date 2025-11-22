"""
Documents Module - Service

Business logic for document management with RAG support.
"""

from typing import Optional
from datetime import datetime

from sqlalchemy import select, func, or_, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import Document, DocumentChunk, ChunkSummary, DocumentSummary, Agent
from app.models.enums import DocumentStatus
from app.integrations import AIEngine
from app.utils.logger import get_logger

from .processor import TextProcessor
from .schemas import (
    DocumentResponse,
    DocumentListItem,
    DocumentListResponse,
    ChunkResponse,
    SearchResult,
    SearchResponse,
    ProcessingStatus,
)

logger = get_logger(__name__)


class DocumentService:
    """
    Document service for upload, processing, and search.

    Features:
    - Document upload and storage
    - Text extraction and chunking
    - Summary generation
    - Full-text search with PostgreSQL
    """

    def __init__(self, db: AsyncSession):
        """Initialize with database session."""
        self.db = db
        self.ai_engine = AIEngine(db)
        self.processor = TextProcessor(ai_engine=self.ai_engine)

    async def upload_document(
        self,
        filename: str,
        content: bytes,
        agent_id: str,
        tenant_id: str,
    ) -> Document:
        """
        Upload and start processing a document.

        Args:
            filename: Original filename
            content: File bytes
            agent_id: Target agent ID
            tenant_id: Tenant ID

        Returns:
            Created document record
        """
        # Determine file type
        file_type = filename.rsplit(".", 1)[-1].lower() if "." in filename else "txt"

        # Validate agent belongs to tenant
        agent = await self._get_agent(agent_id, tenant_id)
        if not agent:
            raise ValueError("Agent not found or not accessible")

        # Create document record
        document = Document(
            agent_id=agent_id,
            tenant_id=tenant_id,
            filename=filename,
            file_type=file_type,
            file_size=len(content),
            status=DocumentStatus.PENDING,
            content=content,  # Store raw content
        )
        self.db.add(document)
        await self.db.flush()

        logger.info(f"Document uploaded: {document.id} ({filename})")
        return document

    async def process_document(
        self,
        document_id: str,
        tenant_id: str,
        generate_summaries: bool = True,
    ) -> ProcessingStatus:
        """
        Process a document: extract text, chunk, and generate summaries.

        Args:
            document_id: Document ID to process
            tenant_id: Tenant ID
            generate_summaries: Whether to generate AI summaries

        Returns:
            Processing status
        """
        # Get document
        result = await self.db.execute(
            select(Document).where(
                Document.id == document_id,
                Document.tenant_id == tenant_id,
            )
        )
        document = result.scalar_one_or_none()

        if not document:
            raise ValueError("Document not found")

        if document.status == DocumentStatus.COMPLETED:
            return ProcessingStatus(
                document_id=document_id,
                status=DocumentStatus.COMPLETED,
                progress=1.0,
            )

        try:
            # Update status
            document.status = DocumentStatus.PROCESSING
            await self.db.commit()

            # Process document
            processed = await self.processor.process_document(
                content=document.content,
                file_type=document.file_type,
                tenant_id=tenant_id,
                agent_id=document.agent_id,
                generate_summaries=generate_summaries,
            )

            # Create chunks
            for chunk in processed.chunks:
                db_chunk = DocumentChunk(
                    document_id=document.id,
                    chunk_index=chunk.index,
                    content=chunk.content,
                    token_count=chunk.token_count,
                    start_char=chunk.start_char,
                    end_char=chunk.end_char,
                )
                self.db.add(db_chunk)
                await self.db.flush()

                # Generate and save chunk summary
                if generate_summaries:
                    summary_text = await self.processor.generate_chunk_summary(
                        chunk, tenant_id, document.agent_id
                    )
                    chunk_summary = ChunkSummary(
                        chunk_id=db_chunk.id,
                        summary=summary_text,
                    )
                    self.db.add(chunk_summary)

            # Save document summary
            if processed.summary:
                doc_summary = DocumentSummary(
                    document_id=document.id,
                    summary=processed.summary,
                )
                self.db.add(doc_summary)

            # Update document
            document.status = DocumentStatus.COMPLETED
            document.chunk_count = len(processed.chunks)
            document.total_tokens = processed.total_tokens
            document.updated_at = datetime.utcnow()

            await self.db.commit()

            logger.info(f"Document processed: {document_id}, {len(processed.chunks)} chunks")

            return ProcessingStatus(
                document_id=document_id,
                status=DocumentStatus.COMPLETED,
                progress=1.0,
                chunks_processed=len(processed.chunks),
                total_chunks=len(processed.chunks),
            )

        except Exception as e:
            logger.error(f"Document processing failed: {e}")
            document.status = DocumentStatus.FAILED
            await self.db.commit()

            return ProcessingStatus(
                document_id=document_id,
                status=DocumentStatus.FAILED,
                error=str(e),
            )

    async def get_document(
        self,
        document_id: str,
        tenant_id: str,
    ) -> Optional[DocumentResponse]:
        """Get document by ID."""
        result = await self.db.execute(
            select(Document)
            .options(selectinload(Document.summary))
            .where(
                Document.id == document_id,
                Document.tenant_id == tenant_id,
            )
        )
        doc = result.scalar_one_or_none()

        if not doc:
            return None

        return DocumentResponse(
            id=doc.id,
            agent_id=doc.agent_id,
            filename=doc.filename,
            file_type=doc.file_type,
            file_size=doc.file_size,
            status=doc.status,
            chunk_count=doc.chunk_count or 0,
            summary=doc.summary.summary if doc.summary else None,
            created_at=doc.created_at,
            updated_at=doc.updated_at,
        )

    async def list_documents(
        self,
        tenant_id: str,
        agent_id: Optional[str] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> DocumentListResponse:
        """List documents with pagination."""
        query = select(Document).where(Document.tenant_id == tenant_id)

        if agent_id:
            query = query.where(Document.agent_id == agent_id)

        # Count total
        count_result = await self.db.execute(
            select(func.count(Document.id)).where(Document.tenant_id == tenant_id)
        )
        total = count_result.scalar() or 0

        # Get page
        query = query.order_by(Document.created_at.desc())
        query = query.offset((page - 1) * page_size).limit(page_size)

        result = await self.db.execute(query)
        documents = result.scalars().all()

        return DocumentListResponse(
            documents=[
                DocumentListItem(
                    id=doc.id,
                    filename=doc.filename,
                    file_type=doc.file_type,
                    file_size=doc.file_size,
                    status=doc.status,
                    chunk_count=doc.chunk_count or 0,
                    created_at=doc.created_at,
                )
                for doc in documents
            ],
            total=total,
            page=page,
            page_size=page_size,
        )

    async def delete_document(
        self,
        document_id: str,
        tenant_id: str,
    ) -> bool:
        """Delete a document and its chunks."""
        result = await self.db.execute(
            select(Document).where(
                Document.id == document_id,
                Document.tenant_id == tenant_id,
            )
        )
        doc = result.scalar_one_or_none()

        if not doc:
            return False

        # Delete chunks (cascade should handle this, but be explicit)
        await self.db.execute(
            text("DELETE FROM document_chunks WHERE document_id = :doc_id"),
            {"doc_id": document_id},
        )

        # Delete document
        await self.db.delete(doc)
        await self.db.commit()

        logger.info(f"Document deleted: {document_id}")
        return True

    async def search(
        self,
        query: str,
        tenant_id: str,
        agent_id: Optional[str] = None,
        limit: int = 10,
    ) -> SearchResponse:
        """
        Full-text search across documents.

        Uses PostgreSQL full-text search on chunks and summaries.
        """
        # Build search query using PostgreSQL ts_rank
        # This is a simplified version - production would use proper tsvector columns
        search_term = query.replace("'", "''")

        sql = """
        SELECT
            dc.id as chunk_id,
            dc.document_id,
            dc.content,
            d.filename,
            cs.summary,
            ts_rank(
                to_tsvector('english', dc.content),
                plainto_tsquery('english', :query)
            ) as relevance
        FROM document_chunks dc
        JOIN documents d ON d.id = dc.document_id
        LEFT JOIN chunk_summaries cs ON cs.chunk_id = dc.id
        WHERE d.tenant_id = :tenant_id
        AND d.status = 'completed'
        AND (
            to_tsvector('english', dc.content) @@ plainto_tsquery('english', :query)
            OR dc.content ILIKE :like_query
        )
        """

        params = {
            "query": query,
            "tenant_id": tenant_id,
            "like_query": f"%{query}%",
        }

        if agent_id:
            sql += " AND d.agent_id = :agent_id"
            params["agent_id"] = agent_id

        sql += " ORDER BY relevance DESC LIMIT :limit"
        params["limit"] = limit

        result = await self.db.execute(text(sql), params)
        rows = result.fetchall()

        results = []
        for row in rows:
            # Create highlight snippet
            content = row.content
            highlight = self._create_highlight(content, query)

            results.append(SearchResult(
                document_id=row.document_id,
                chunk_id=row.chunk_id,
                filename=row.filename,
                content=content[:500] + "..." if len(content) > 500 else content,
                summary=row.summary,
                relevance_score=float(row.relevance) if row.relevance else 0.0,
                highlight=highlight,
            ))

        return SearchResponse(
            results=results,
            total=len(results),
            query=query,
        )

    async def get_chunks(
        self,
        document_id: str,
        tenant_id: str,
    ) -> list[ChunkResponse]:
        """Get all chunks for a document."""
        # Verify document belongs to tenant
        doc_result = await self.db.execute(
            select(Document).where(
                Document.id == document_id,
                Document.tenant_id == tenant_id,
            )
        )
        if not doc_result.scalar_one_or_none():
            return []

        # Get chunks with summaries
        result = await self.db.execute(
            select(DocumentChunk)
            .options(selectinload(DocumentChunk.summary))
            .where(DocumentChunk.document_id == document_id)
            .order_by(DocumentChunk.chunk_index)
        )
        chunks = result.scalars().all()

        return [
            ChunkResponse(
                id=chunk.id,
                document_id=document_id,
                chunk_index=chunk.chunk_index,
                content=chunk.content,
                summary=chunk.summary.summary if chunk.summary else None,
                token_count=chunk.token_count,
            )
            for chunk in chunks
        ]

    def _create_highlight(self, content: str, query: str, context: int = 100) -> str:
        """Create highlighted snippet around query match."""
        query_lower = query.lower()
        content_lower = content.lower()

        pos = content_lower.find(query_lower)
        if pos == -1:
            return content[:200] + "..."

        start = max(0, pos - context)
        end = min(len(content), pos + len(query) + context)

        snippet = content[start:end]
        if start > 0:
            snippet = "..." + snippet
        if end < len(content):
            snippet = snippet + "..."

        return snippet

    async def _get_agent(self, agent_id: str, tenant_id: str) -> Optional[Agent]:
        """Get agent by ID and tenant."""
        result = await self.db.execute(
            select(Agent).where(
                Agent.id == agent_id,
                Agent.tenant_id == tenant_id,
            )
        )
        return result.scalar_one_or_none()
