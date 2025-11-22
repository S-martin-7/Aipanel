"""
Document models for RAG (Retrieval Augmented Generation).

Stores documents, chunks, and summaries for context retrieval.
"""

from sqlalchemy import Column, String, Boolean, Enum, Integer, Text, ForeignKey
from sqlalchemy.dialects.postgresql import JSONB, ARRAY, TSVECTOR
from sqlalchemy.orm import relationship

from .base import BaseModel
from .enums import DocumentStatus


class Document(BaseModel):
    """
    Uploaded document for knowledge base.

    Documents are chunked and summarized for RAG.
    """

    __tablename__ = "documents"

    tenant_id = Column(String(36), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    agent_id = Column(String(36), ForeignKey("agents.id", ondelete="SET NULL"), nullable=True, index=True)

    # File info
    name = Column(String(255), nullable=False)
    original_filename = Column(String(255), nullable=False)
    file_type = Column(String(20), nullable=False)  # pdf, txt, url, md
    file_size = Column(Integer, nullable=True)  # bytes

    # Storage
    s3_key = Column(String(500), nullable=True)
    content_hash = Column(String(64), nullable=True, unique=True)  # SHA256

    # Content
    raw_content = Column(Text, nullable=True)
    word_count = Column(Integer, default=0, nullable=False)

    # Processing status
    status = Column(Enum(DocumentStatus), default=DocumentStatus.PENDING, nullable=False)
    error_message = Column(Text, nullable=True)

    # Metadata
    metadata = Column(JSONB, nullable=True)  # author, date, source, etc.

    # Relationships
    tenant = relationship("Tenant", back_populates="documents")
    agent = relationship("Agent", back_populates="documents")
    chunks = relationship("DocumentChunk", back_populates="document", cascade="all, delete-orphan")
    summary = relationship("DocumentSummary", back_populates="document", uselist=False, cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Document {self.name}>"


class DocumentChunk(BaseModel):
    """
    Chunk of a document for granular retrieval.

    Documents are split into chunks for better search results.
    """

    __tablename__ = "document_chunks"

    document_id = Column(String(36), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True)

    # Position
    chunk_index = Column(Integer, nullable=False)

    # Content
    content = Column(Text, nullable=False)
    word_count = Column(Integer, default=0, nullable=False)

    # Full-text search vector
    search_vector = Column(TSVECTOR, nullable=True)

    # Relationships
    document = relationship("Document", back_populates="chunks")
    summary = relationship("ChunkSummary", back_populates="chunk", uselist=False, cascade="all, delete-orphan")

    def __repr__(self):
        return f"<DocumentChunk {self.document_id}:{self.chunk_index}>"


class ChunkSummary(BaseModel):
    """
    AI-generated summary of a document chunk.

    Used for efficient search and context building.
    """

    __tablename__ = "chunk_summaries"

    chunk_id = Column(String(36), ForeignKey("document_chunks.id", ondelete="CASCADE"), nullable=False, unique=True)

    # Summary content
    summary = Column(Text, nullable=False)
    keywords = Column(ARRAY(String), nullable=True)
    topics = Column(ARRAY(String), nullable=True)

    # Generation metadata
    model_used = Column(String(50), nullable=True)
    tokens_used = Column(Integer, default=0, nullable=False)

    # Full-text search vector
    search_vector = Column(TSVECTOR, nullable=True)

    # Relationships
    chunk = relationship("DocumentChunk", back_populates="summary")

    def __repr__(self):
        return f"<ChunkSummary {self.chunk_id[:8]}>"


class DocumentSummary(BaseModel):
    """
    AI-generated summary of entire document.

    High-level overview for quick context.
    """

    __tablename__ = "document_summaries"

    document_id = Column(String(36), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, unique=True)

    # Summary content
    summary = Column(Text, nullable=False)
    key_points = Column(ARRAY(String), nullable=True)
    keywords = Column(ARRAY(String), nullable=True)
    topics = Column(ARRAY(String), nullable=True)

    # Level of abstraction (for multi-level summaries)
    level = Column(Integer, default=1, nullable=False)

    # Generation metadata
    model_used = Column(String(50), nullable=True)
    tokens_used = Column(Integer, default=0, nullable=False)

    # Full-text search vector
    search_vector = Column(TSVECTOR, nullable=True)

    # Relationships
    document = relationship("Document", back_populates="summary")

    def __repr__(self):
        return f"<DocumentSummary {self.document_id[:8]}>"
