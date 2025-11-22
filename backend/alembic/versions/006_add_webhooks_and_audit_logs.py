"""Add webhooks and audit logs tables

Revision ID: 006
Revises: 005
Create Date: 2024-01-01
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = '006'
down_revision = '005'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create webhooks table
    op.create_table(
        'webhooks',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('tenant_id', sa.String(36), sa.ForeignKey('tenants.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('url', sa.String(500), nullable=False),
        sa.Column('secret', sa.String(64), nullable=False),
        sa.Column('events', postgresql.ARRAY(sa.String), nullable=False, default=[]),
        sa.Column('agent_id', sa.String(36), sa.ForeignKey('agents.id', ondelete='SET NULL'), nullable=True),
        sa.Column('is_active', sa.Boolean, default=True, nullable=False),
        sa.Column('max_retries', sa.Integer, default=3, nullable=False),
        sa.Column('retry_delay_seconds', sa.Integer, default=60, nullable=False),
        sa.Column('custom_headers', postgresql.JSONB, nullable=True),
        sa.Column('total_deliveries', sa.Integer, default=0, nullable=False),
        sa.Column('successful_deliveries', sa.Integer, default=0, nullable=False),
        sa.Column('failed_deliveries', sa.Integer, default=0, nullable=False),
        sa.Column('last_triggered_at', sa.DateTime, nullable=True),
        sa.Column('last_success_at', sa.DateTime, nullable=True),
        sa.Column('last_failure_at', sa.DateTime, nullable=True),
        sa.Column('last_failure_reason', sa.Text, nullable=True),
        sa.Column('created_at', sa.DateTime, server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime, server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
    )

    # Create webhook_deliveries table
    op.create_table(
        'webhook_deliveries',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('webhook_id', sa.String(36), sa.ForeignKey('webhooks.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('event_type', sa.String(50), nullable=False),
        sa.Column('event_id', sa.String(36), nullable=False, unique=True),
        sa.Column('payload', postgresql.JSONB, nullable=False),
        sa.Column('status', sa.String(20), default='pending', nullable=False),
        sa.Column('attempts', sa.Integer, default=0, nullable=False),
        sa.Column('next_retry_at', sa.DateTime, nullable=True),
        sa.Column('response_status_code', sa.Integer, nullable=True),
        sa.Column('response_body', sa.Text, nullable=True),
        sa.Column('response_time_ms', sa.Integer, nullable=True),
        sa.Column('error_message', sa.Text, nullable=True),
        sa.Column('delivered_at', sa.DateTime, nullable=True),
        sa.Column('created_at', sa.DateTime, server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime, server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
    )

    # Create audit_logs table
    op.create_table(
        'audit_logs',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('tenant_id', sa.String(36), sa.ForeignKey('tenants.id', ondelete='CASCADE'), nullable=True, index=True),
        sa.Column('user_id', sa.String(36), nullable=True, index=True),
        sa.Column('user_email', sa.String(255), nullable=True),
        sa.Column('user_type', sa.String(20), nullable=True),
        sa.Column('action', sa.String(50), nullable=False, index=True),
        sa.Column('resource_type', sa.String(50), nullable=True),
        sa.Column('resource_id', sa.String(36), nullable=True, index=True),
        sa.Column('resource_name', sa.String(255), nullable=True),
        sa.Column('description', sa.Text, nullable=True),
        sa.Column('old_values', postgresql.JSONB, nullable=True),
        sa.Column('new_values', postgresql.JSONB, nullable=True),
        sa.Column('metadata', postgresql.JSONB, nullable=True),
        sa.Column('ip_address', postgresql.INET, nullable=True),
        sa.Column('user_agent', sa.String(500), nullable=True),
        sa.Column('request_id', sa.String(36), nullable=True),
        sa.Column('status', sa.String(20), default='success', nullable=False),
        sa.Column('error_message', sa.Text, nullable=True),
        sa.Column('created_at', sa.DateTime, server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime, server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
    )

    # Create composite indexes for audit_logs
    op.create_index('ix_audit_logs_tenant_action', 'audit_logs', ['tenant_id', 'action'])
    op.create_index('ix_audit_logs_tenant_created', 'audit_logs', ['tenant_id', 'created_at'])
    op.create_index('ix_audit_logs_resource', 'audit_logs', ['resource_type', 'resource_id'])


def downgrade() -> None:
    # Drop indexes
    op.drop_index('ix_audit_logs_resource', table_name='audit_logs')
    op.drop_index('ix_audit_logs_tenant_created', table_name='audit_logs')
    op.drop_index('ix_audit_logs_tenant_action', table_name='audit_logs')

    # Drop tables
    op.drop_table('audit_logs')
    op.drop_table('webhook_deliveries')
    op.drop_table('webhooks')
