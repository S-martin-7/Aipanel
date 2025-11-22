"""Add external API keys table

Revision ID: 004_external_api_keys
Revises: 003_plans_system
Create Date: 2024-01-22 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '004_external_api_keys'
down_revision = '003_plans_system'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # External API keys table
    op.create_table(
        'external_api_keys',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('tenant_id', sa.String(36), sa.ForeignKey('tenants.id', ondelete='CASCADE'), nullable=False),
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('key_hash', sa.String(64), nullable=False, unique=True),
        sa.Column('key_prefix', sa.String(12), nullable=False),
        sa.Column('scopes', postgresql.ARRAY(sa.String()), nullable=True),
        sa.Column('agent_id', sa.String(36), sa.ForeignKey('agents.id', ondelete='SET NULL'), nullable=True),
        sa.Column('rate_limit', sa.Integer(), default=60, nullable=False),
        sa.Column('is_active', sa.Boolean(), default=True, nullable=False),
        sa.Column('last_used_at', sa.DateTime(), nullable=True),
        sa.Column('total_requests', sa.Integer(), default=0, nullable=False),
        sa.Column('expires_at', sa.DateTime(), nullable=True),
        sa.Column('allowed_ips', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), onupdate=sa.func.now(), nullable=True),
    )
    op.create_index('ix_external_api_keys_tenant_id', 'external_api_keys', ['tenant_id'])
    op.create_index('ix_external_api_keys_key_hash', 'external_api_keys', ['key_hash'])
    op.create_index('ix_external_api_keys_agent_id', 'external_api_keys', ['agent_id'])


def downgrade() -> None:
    op.drop_index('ix_external_api_keys_agent_id', 'external_api_keys')
    op.drop_index('ix_external_api_keys_key_hash', 'external_api_keys')
    op.drop_index('ix_external_api_keys_tenant_id', 'external_api_keys')
    op.drop_table('external_api_keys')
