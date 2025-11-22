"""Add plans system and tenant trial fields

Revision ID: 003_plans_system
Revises: 002_seed_data
Create Date: 2024-01-22 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '003_plans_system'
down_revision = '002_seed_data'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Plans table
    op.create_table(
        'plans',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('code', sa.String(50), unique=True, nullable=False),
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('plan_type', sa.String(20), nullable=False, default='starter'),
        sa.Column('price_monthly', sa.Integer(), default=0, nullable=False),
        sa.Column('price_yearly', sa.Integer(), nullable=True),
        sa.Column('currency', sa.String(3), default='CLP', nullable=False),
        sa.Column('requires_payment', sa.Boolean(), default=True, nullable=False),
        sa.Column('is_trial', sa.Boolean(), default=False, nullable=False),
        sa.Column('trial_days', sa.Integer(), default=0, nullable=False),
        sa.Column('max_tokens_monthly', sa.Integer(), default=100000, nullable=False),
        sa.Column('max_agents', sa.Integer(), default=1, nullable=False),
        sa.Column('max_documents', sa.Integer(), default=20, nullable=False),
        sa.Column('max_users', sa.Integer(), default=2, nullable=False),
        sa.Column('max_storage_mb', sa.Integer(), default=100, nullable=False),
        sa.Column('features', postgresql.JSONB(), nullable=True),
        sa.Column('is_active', sa.Boolean(), default=True, nullable=False),
        sa.Column('is_public', sa.Boolean(), default=True, nullable=False),
        sa.Column('sort_order', sa.Integer(), default=0, nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), onupdate=sa.func.now(), nullable=True),
    )
    op.create_index('ix_plans_code', 'plans', ['code'])
    op.create_index('ix_plans_is_active', 'plans', ['is_active'])
    op.create_index('ix_plans_is_public', 'plans', ['is_public'])

    # Add new columns to tenants table
    op.add_column('tenants', sa.Column('plan_code', sa.String(50), default='demo', nullable=True))
    op.add_column('tenants', sa.Column('trial_start', sa.DateTime(), nullable=True))
    op.add_column('tenants', sa.Column('trial_end', sa.DateTime(), nullable=True))
    op.add_column('tenants', sa.Column('subscription_start', sa.DateTime(), nullable=True))
    op.add_column('tenants', sa.Column('subscription_end', sa.DateTime(), nullable=True))
    op.add_column('tenants', sa.Column('is_paid', sa.Boolean(), default=False, nullable=True))
    op.add_column('tenants', sa.Column('payment_required', sa.Boolean(), default=True, nullable=True))
    op.add_column('tenants', sa.Column('max_users', sa.Integer(), default=10, nullable=True))
    op.add_column('tenants', sa.Column('max_storage_mb', sa.Integer(), default=500, nullable=True))
    op.add_column('tenants', sa.Column('suspended_at', sa.DateTime(), nullable=True))
    op.add_column('tenants', sa.Column('suspension_reason', sa.Text(), nullable=True))

    # Create index for plan_code
    op.create_index('ix_tenants_plan_code', 'tenants', ['plan_code'])

    # Migrate existing data: set plan_code based on old plan enum
    op.execute("""
        UPDATE tenants
        SET plan_code = CASE
            WHEN plan = 'FREE' THEN 'demo'
            WHEN plan = 'STARTER' THEN 'starter'
            WHEN plan = 'PROFESSIONAL' THEN 'professional'
            WHEN plan = 'ENTERPRISE' THEN 'enterprise'
            ELSE 'demo'
        END,
        is_paid = CASE WHEN plan IN ('STARTER', 'PROFESSIONAL', 'ENTERPRISE') THEN true ELSE false END,
        payment_required = CASE WHEN plan = 'FREE' THEN true ELSE false END
    """)

    # Set default values for non-null columns
    op.execute("""
        UPDATE tenants
        SET max_users = 10,
            max_storage_mb = 500,
            is_paid = COALESCE(is_paid, false),
            payment_required = COALESCE(payment_required, true)
        WHERE max_users IS NULL OR max_storage_mb IS NULL
    """)

    # Insert default plans
    op.execute("""
        INSERT INTO plans (id, code, name, description, plan_type, price_monthly, requires_payment, is_trial, trial_days, max_tokens_monthly, max_agents, max_documents, max_users, max_storage_mb, is_active, is_public, sort_order, created_at)
        VALUES
        (gen_random_uuid()::text, 'demo', 'Demo', 'Plan de prueba por 60 días', 'trial', 0, true, true, 60, 50000, 1, 20, 2, 100, true, true, 1, NOW()),
        (gen_random_uuid()::text, 'starter', 'Starter', 'Para pequeños negocios', 'starter', 29990, true, false, 0, 100000, 3, 50, 5, 500, true, true, 2, NOW()),
        (gen_random_uuid()::text, 'professional', 'Professional', 'Para equipos en crecimiento', 'professional', 79990, true, false, 0, 500000, 10, 200, 20, 2000, true, true, 3, NOW()),
        (gen_random_uuid()::text, 'enterprise', 'Enterprise', 'Para grandes organizaciones', 'enterprise', 199990, true, false, 0, 2000000, 50, 1000, 100, 10000, true, true, 4, NOW()),
        (gen_random_uuid()::text, 'internal', 'Internal', 'Plan interno sin costo', 'internal', 0, false, false, 0, 1000000, 25, 500, 50, 5000, true, false, 99, NOW())
        ON CONFLICT (code) DO NOTHING
    """)


def downgrade() -> None:
    # Remove indexes
    op.drop_index('ix_tenants_plan_code', 'tenants')
    op.drop_index('ix_plans_is_public', 'plans')
    op.drop_index('ix_plans_is_active', 'plans')
    op.drop_index('ix_plans_code', 'plans')

    # Remove tenant columns
    op.drop_column('tenants', 'suspension_reason')
    op.drop_column('tenants', 'suspended_at')
    op.drop_column('tenants', 'max_storage_mb')
    op.drop_column('tenants', 'max_users')
    op.drop_column('tenants', 'payment_required')
    op.drop_column('tenants', 'is_paid')
    op.drop_column('tenants', 'subscription_end')
    op.drop_column('tenants', 'subscription_start')
    op.drop_column('tenants', 'trial_end')
    op.drop_column('tenants', 'trial_start')
    op.drop_column('tenants', 'plan_code')

    # Drop plans table
    op.drop_table('plans')
