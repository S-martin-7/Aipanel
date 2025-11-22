"""Add vector embeddings table for RAG

Revision ID: 008
Revises: 007
Create Date: 2025-01-22

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers
revision = '008'
down_revision = '007'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Enable pgvector extension
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    # Create chunk_embeddings table
    op.create_table(
        'chunk_embeddings',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('chunk_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('document_chunks.id', ondelete='CASCADE'), nullable=False),
        sa.Column('document_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('documents.id', ondelete='CASCADE'), nullable=False),
        sa.Column('content_hash', sa.String(64), nullable=False, unique=True),
        sa.Column('embedding', sa.Text(), nullable=False),  # Will store as vector type
        sa.Column('metadata', postgresql.JSONB, server_default='{}'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
    )

    # Alter embedding column to vector type (1536 dimensions for OpenAI ada/small)
    op.execute("ALTER TABLE chunk_embeddings ALTER COLUMN embedding TYPE vector(1536) USING embedding::vector(1536)")

    # Create indexes
    op.create_index(
        'ix_chunk_embeddings_document_id',
        'chunk_embeddings',
        ['document_id']
    )

    # Create vector similarity index (IVFFlat for faster search)
    op.execute("""
        CREATE INDEX ix_chunk_embeddings_vector
        ON chunk_embeddings
        USING ivfflat (embedding vector_cosine_ops)
        WITH (lists = 100)
    """)

    # Add embedding_model column to documents to track which model was used
    op.add_column(
        'documents',
        sa.Column('embedding_model', sa.String(50), nullable=True)
    )

    # Add embeddings_generated flag
    op.add_column(
        'documents',
        sa.Column('embeddings_generated', sa.Boolean(), server_default='false')
    )


def downgrade() -> None:
    # Drop columns from documents
    op.drop_column('documents', 'embeddings_generated')
    op.drop_column('documents', 'embedding_model')

    # Drop table
    op.drop_table('chunk_embeddings')

    # Note: Not dropping pgvector extension as it might be used elsewhere
