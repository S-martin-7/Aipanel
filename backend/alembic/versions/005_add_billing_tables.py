"""Add billing tables - subscriptions and invoices

Revision ID: 005_billing_tables
Revises: 004_external_api_keys
Create Date: 2024-01-22 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '005_billing_tables'
down_revision = '004_external_api_keys'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Subscriptions table
    op.create_table(
        'subscriptions',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('tenant_id', sa.String(36), sa.ForeignKey('tenants.id', ondelete='CASCADE'), nullable=False),
        sa.Column('plan_code', sa.String(50), nullable=False),
        sa.Column('status', sa.String(20), default='TRIAL', nullable=False),
        sa.Column('billing_cycle', sa.String(20), default='monthly', nullable=False),
        sa.Column('billing_day', sa.Integer(), default=1, nullable=False),
        sa.Column('current_period_start', sa.DateTime(), nullable=True),
        sa.Column('current_period_end', sa.DateTime(), nullable=True),
        sa.Column('trial_start', sa.DateTime(), nullable=True),
        sa.Column('trial_end', sa.DateTime(), nullable=True),
        sa.Column('cancelled_at', sa.DateTime(), nullable=True),
        sa.Column('cancel_at_period_end', sa.Boolean(), default=False, nullable=False),
        sa.Column('cancellation_reason', sa.Text(), nullable=True),
        sa.Column('payment_method_id', sa.String(100), nullable=True),
        sa.Column('last_payment_date', sa.DateTime(), nullable=True),
        sa.Column('next_payment_date', sa.DateTime(), nullable=True),
        sa.Column('base_amount', sa.Numeric(10, 2), default=0, nullable=False),
        sa.Column('discount_amount', sa.Numeric(10, 2), default=0, nullable=False),
        sa.Column('tax_amount', sa.Numeric(10, 2), default=0, nullable=False),
        sa.Column('total_amount', sa.Numeric(10, 2), default=0, nullable=False),
        sa.Column('currency', sa.String(3), default='CLP', nullable=False),
        sa.Column('metadata', postgresql.JSONB(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), onupdate=sa.func.now(), nullable=True),
    )
    op.create_index('ix_subscriptions_tenant_id', 'subscriptions', ['tenant_id'])
    op.create_index('ix_subscriptions_status', 'subscriptions', ['status'])
    op.create_index('ix_subscriptions_plan_code', 'subscriptions', ['plan_code'])

    # Invoices table
    op.create_table(
        'invoices',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('tenant_id', sa.String(36), sa.ForeignKey('tenants.id', ondelete='CASCADE'), nullable=False),
        sa.Column('subscription_id', sa.String(36), sa.ForeignKey('subscriptions.id', ondelete='SET NULL'), nullable=True),
        sa.Column('invoice_number', sa.String(50), unique=True, nullable=False),
        sa.Column('status', sa.String(20), default='DRAFT', nullable=False),
        sa.Column('period_start', sa.DateTime(), nullable=False),
        sa.Column('period_end', sa.DateTime(), nullable=False),
        sa.Column('due_date', sa.DateTime(), nullable=False),
        sa.Column('paid_at', sa.DateTime(), nullable=True),
        sa.Column('subtotal', sa.Numeric(10, 2), default=0, nullable=False),
        sa.Column('discount_amount', sa.Numeric(10, 2), default=0, nullable=False),
        sa.Column('tax_rate', sa.Numeric(5, 2), default=19, nullable=False),
        sa.Column('tax_amount', sa.Numeric(10, 2), default=0, nullable=False),
        sa.Column('total', sa.Numeric(10, 2), default=0, nullable=False),
        sa.Column('currency', sa.String(3), default='CLP', nullable=False),
        sa.Column('line_items', postgresql.JSONB(), default=list, nullable=False),
        sa.Column('payment_id', sa.String(36), sa.ForeignKey('payments.id', ondelete='SET NULL'), nullable=True),
        sa.Column('payment_method', sa.String(50), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('metadata', postgresql.JSONB(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), onupdate=sa.func.now(), nullable=True),
    )
    op.create_index('ix_invoices_tenant_id', 'invoices', ['tenant_id'])
    op.create_index('ix_invoices_subscription_id', 'invoices', ['subscription_id'])
    op.create_index('ix_invoices_status', 'invoices', ['status'])
    op.create_index('ix_invoices_invoice_number', 'invoices', ['invoice_number'])
    op.create_index('ix_invoices_due_date', 'invoices', ['due_date'])


def downgrade() -> None:
    op.drop_index('ix_invoices_due_date', 'invoices')
    op.drop_index('ix_invoices_invoice_number', 'invoices')
    op.drop_index('ix_invoices_status', 'invoices')
    op.drop_index('ix_invoices_subscription_id', 'invoices')
    op.drop_index('ix_invoices_tenant_id', 'invoices')
    op.drop_table('invoices')

    op.drop_index('ix_subscriptions_plan_code', 'subscriptions')
    op.drop_index('ix_subscriptions_status', 'subscriptions')
    op.drop_index('ix_subscriptions_tenant_id', 'subscriptions')
    op.drop_table('subscriptions')
