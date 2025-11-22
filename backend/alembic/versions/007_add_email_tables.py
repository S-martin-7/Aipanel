"""Add email templates, logs, and preferences tables

Revision ID: 007
Revises: 006
Create Date: 2024-01-01
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = '007'
down_revision = '006'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create email_templates table
    op.create_table(
        'email_templates',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('tenant_id', sa.String(36), sa.ForeignKey('tenants.id', ondelete='CASCADE'), nullable=True, index=True),
        sa.Column('email_type', sa.String(50), nullable=False, index=True),
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('description', sa.Text, nullable=True),
        sa.Column('subject', sa.String(255), nullable=False),
        sa.Column('body_html', sa.Text, nullable=False),
        sa.Column('body_text', sa.Text, nullable=True),
        sa.Column('header_image_url', sa.String(500), nullable=True),
        sa.Column('footer_text', sa.Text, nullable=True),
        sa.Column('primary_color', sa.String(7), nullable=True),
        sa.Column('available_variables', postgresql.ARRAY(sa.String), nullable=True),
        sa.Column('is_active', sa.Boolean, default=True, nullable=False),
        sa.Column('is_default', sa.Boolean, default=False, nullable=False),
        sa.Column('created_at', sa.DateTime, server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime, server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
    )

    # Create email_logs table
    op.create_table(
        'email_logs',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('tenant_id', sa.String(36), sa.ForeignKey('tenants.id', ondelete='SET NULL'), nullable=True, index=True),
        sa.Column('to_email', sa.String(255), nullable=False, index=True),
        sa.Column('to_name', sa.String(100), nullable=True),
        sa.Column('cc_emails', postgresql.ARRAY(sa.String), nullable=True),
        sa.Column('bcc_emails', postgresql.ARRAY(sa.String), nullable=True),
        sa.Column('email_type', sa.String(50), nullable=False, index=True),
        sa.Column('template_id', sa.String(36), sa.ForeignKey('email_templates.id', ondelete='SET NULL'), nullable=True),
        sa.Column('subject', sa.String(255), nullable=False),
        sa.Column('body_html', sa.Text, nullable=True),
        sa.Column('variables', postgresql.JSONB, nullable=True),
        sa.Column('status', sa.String(20), default='pending', nullable=False, index=True),
        sa.Column('attempts', sa.Integer, default=0, nullable=False),
        sa.Column('last_attempt_at', sa.DateTime, nullable=True),
        sa.Column('sent_at', sa.DateTime, nullable=True),
        sa.Column('delivered_at', sa.DateTime, nullable=True),
        sa.Column('provider', sa.String(50), nullable=True),
        sa.Column('provider_message_id', sa.String(255), nullable=True),
        sa.Column('error_message', sa.Text, nullable=True),
        sa.Column('error_code', sa.String(50), nullable=True),
        sa.Column('opened_at', sa.DateTime, nullable=True),
        sa.Column('clicked_at', sa.DateTime, nullable=True),
        sa.Column('related_type', sa.String(50), nullable=True),
        sa.Column('related_id', sa.String(36), nullable=True),
        sa.Column('created_at', sa.DateTime, server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime, server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
    )

    # Create email_preferences table
    op.create_table(
        'email_preferences',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('tenant_id', sa.String(36), sa.ForeignKey('tenants.id', ondelete='CASCADE'), nullable=True, index=True),
        sa.Column('user_id', sa.String(36), nullable=True, index=True),
        sa.Column('email', sa.String(255), nullable=False, index=True),
        sa.Column('marketing_emails', sa.Boolean, default=True, nullable=False),
        sa.Column('billing_emails', sa.Boolean, default=True, nullable=False),
        sa.Column('security_emails', sa.Boolean, default=True, nullable=False),
        sa.Column('usage_alerts', sa.Boolean, default=True, nullable=False),
        sa.Column('product_updates', sa.Boolean, default=True, nullable=False),
        sa.Column('weekly_summary', sa.Boolean, default=False, nullable=False),
        sa.Column('unsubscribed_all', sa.Boolean, default=False, nullable=False),
        sa.Column('unsubscribe_token', sa.String(64), nullable=True, unique=True),
        sa.Column('created_at', sa.DateTime, server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime, server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table('email_preferences')
    op.drop_table('email_logs')
    op.drop_table('email_templates')
