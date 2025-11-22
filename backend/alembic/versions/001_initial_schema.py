"""Initial database schema

Revision ID: 001_initial
Revises:
Create Date: 2024-01-01 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '001_initial'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Users table (Level 1 - Admin users)
    op.create_table(
        'users',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('email', sa.String(255), unique=True, nullable=False),
        sa.Column('password_hash', sa.String(255), nullable=False),
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('role', sa.Enum('SUPER_ADMIN', 'ADMIN', 'VIEWER', name='userrole'), default='ADMIN', nullable=False),
        sa.Column('is_active', sa.Boolean(), default=True, nullable=False),
        sa.Column('last_login', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), onupdate=sa.func.now(), nullable=True),
    )
    op.create_index('ix_users_email', 'users', ['email'])

    # Refresh tokens table
    op.create_table(
        'refresh_tokens',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('user_id', sa.String(36), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('token_hash', sa.String(255), unique=True, nullable=False),
        sa.Column('expires_at', sa.DateTime(), nullable=False),
        sa.Column('revoked', sa.Boolean(), default=False, nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), onupdate=sa.func.now(), nullable=True),
    )
    op.create_index('ix_refresh_tokens_user_id', 'refresh_tokens', ['user_id'])

    # Tenants table
    op.create_table(
        'tenants',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('slug', sa.String(50), unique=True, nullable=False),
        sa.Column('email', sa.String(255), nullable=False),
        sa.Column('status', sa.Enum('ACTIVE', 'SUSPENDED', 'PENDING', 'CANCELLED', name='tenantstatus'), default='ACTIVE', nullable=False),
        sa.Column('plan', sa.Enum('FREE', 'STARTER', 'PROFESSIONAL', 'ENTERPRISE', name='tenantplan'), default='FREE', nullable=False),
        sa.Column('monthly_token_limit', sa.Integer(), default=100000, nullable=False),
        sa.Column('current_month_usage', sa.Integer(), default=0, nullable=False),
        sa.Column('max_agents', sa.Integer(), default=3, nullable=False),
        sa.Column('max_documents', sa.Integer(), default=50, nullable=False),
        sa.Column('auto_suspend_on_overage', sa.Boolean(), default=True, nullable=False),
        sa.Column('logo_url', sa.String(500), nullable=True),
        sa.Column('primary_color', sa.String(7), nullable=True),
        sa.Column('api_key_hash', sa.String(255), unique=True, nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), onupdate=sa.func.now(), nullable=True),
    )
    op.create_index('ix_tenants_slug', 'tenants', ['slug'])

    # Tenant users table (Level 2 users)
    op.create_table(
        'tenant_users',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('tenant_id', sa.String(36), sa.ForeignKey('tenants.id', ondelete='CASCADE'), nullable=False),
        sa.Column('email', sa.String(255), nullable=False),
        sa.Column('password_hash', sa.String(255), nullable=False),
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('role', sa.Enum('OWNER', 'ADMIN', 'MEMBER', 'VIEWER', name='tenantuserrole'), default='MEMBER', nullable=False),
        sa.Column('is_active', sa.Boolean(), default=True, nullable=False),
        sa.Column('phone', sa.String(20), nullable=True),
        sa.Column('avatar_url', sa.String(500), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), onupdate=sa.func.now(), nullable=True),
    )
    op.create_index('ix_tenant_users_tenant_id', 'tenant_users', ['tenant_id'])

    # Tenant API keys table
    op.create_table(
        'tenant_api_keys',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('tenant_id', sa.String(36), sa.ForeignKey('tenants.id', ondelete='CASCADE'), nullable=False),
        sa.Column('provider_type', sa.Enum('OPENAI', 'ANTHROPIC', 'GOOGLE', 'CUSTOM', name='aiprovidertype'), nullable=False),
        sa.Column('provider_name', sa.String(50), nullable=False),
        sa.Column('api_key_encrypted', sa.Text(), nullable=False),
        sa.Column('organization_id', sa.String(100), nullable=True),
        sa.Column('base_url', sa.String(500), nullable=True),
        sa.Column('is_active', sa.Boolean(), default=True, nullable=False),
        sa.Column('is_valid', sa.Boolean(), default=True, nullable=False),
        sa.Column('last_validated_at', sa.DateTime(), nullable=True),
        sa.Column('last_error', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), onupdate=sa.func.now(), nullable=True),
    )
    op.create_index('ix_tenant_api_keys_tenant_id', 'tenant_api_keys', ['tenant_id'])

    # AI Providers table
    op.create_table(
        'ai_providers',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('name', sa.String(50), unique=True, nullable=False),
        sa.Column('display_name', sa.String(100), nullable=True),
        sa.Column('handler_module', sa.String(200), nullable=False),
        sa.Column('handler_class', sa.String(100), nullable=False),
        sa.Column('config_json', postgresql.JSONB(), nullable=True),
        sa.Column('is_active', sa.Boolean(), default=True, nullable=False),
        sa.Column('allowed_in_prod', sa.Boolean(), default=False, nullable=False),
        sa.Column('requests_per_minute', sa.Integer(), nullable=True),
        sa.Column('tokens_per_minute', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), onupdate=sa.func.now(), nullable=True),
    )

    # AI Models table
    op.create_table(
        'ai_models',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('provider_id', sa.String(36), sa.ForeignKey('ai_providers.id', ondelete='CASCADE'), nullable=False),
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('display_name', sa.String(100), nullable=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('capabilities', postgresql.ARRAY(sa.String()), nullable=True),
        sa.Column('status', sa.Enum('EXPERIMENTAL', 'STABLE', 'DEPRECATED', name='aimodelstatus'), default='EXPERIMENTAL', nullable=False),
        sa.Column('pricing_input', sa.Float(), nullable=True),
        sa.Column('pricing_output', sa.Float(), nullable=True),
        sa.Column('pricing_cached', sa.Float(), nullable=True),
        sa.Column('max_tokens', sa.Integer(), nullable=True),
        sa.Column('context_window', sa.Integer(), nullable=True),
        sa.Column('supports_streaming', sa.Boolean(), default=True, nullable=False),
        sa.Column('supports_vision', sa.Boolean(), default=False, nullable=False),
        sa.Column('supports_tools', sa.Boolean(), default=False, nullable=False),
        sa.Column('supports_json_mode', sa.Boolean(), default=False, nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), onupdate=sa.func.now(), nullable=True),
    )
    op.create_index('ix_ai_models_provider_id', 'ai_models', ['provider_id'])

    # AI Parameter Profiles table
    op.create_table(
        'ai_param_profiles',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('name', sa.String(50), unique=True, nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('temperature', sa.Float(), nullable=True),
        sa.Column('max_tokens', sa.Integer(), nullable=True),
        sa.Column('top_p', sa.Float(), nullable=True),
        sa.Column('frequency_penalty', sa.Float(), nullable=True),
        sa.Column('presence_penalty', sa.Float(), nullable=True),
        sa.Column('system_prompt_suffix', sa.Text(), nullable=True),
        sa.Column('is_active', sa.Boolean(), default=True, nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), onupdate=sa.func.now(), nullable=True),
    )

    # Agents table
    op.create_table(
        'agents',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('tenant_id', sa.String(36), sa.ForeignKey('tenants.id', ondelete='CASCADE'), nullable=False),
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('avatar_url', sa.String(500), nullable=True),
        sa.Column('status', sa.Enum('ACTIVE', 'INACTIVE', 'DRAFT', name='agentstatus'), default='DRAFT', nullable=False),
        sa.Column('mode', sa.Enum('CHAT', 'REALTIME', 'ASSISTANT', name='agentmode'), default='CHAT', nullable=False),
        sa.Column('system_prompt', sa.Text(), nullable=False),
        sa.Column('welcome_message', sa.Text(), nullable=True),
        sa.Column('default_model_id', sa.String(36), sa.ForeignKey('ai_models.id'), nullable=True),
        sa.Column('temperature', sa.Float(), default=0.7, nullable=False),
        sa.Column('max_tokens', sa.Integer(), default=2048, nullable=False),
        sa.Column('top_p', sa.Float(), default=1.0, nullable=False),
        sa.Column('enable_memory', sa.Boolean(), default=True, nullable=False),
        sa.Column('enable_documents', sa.Boolean(), default=True, nullable=False),
        sa.Column('enable_web_search', sa.Boolean(), default=False, nullable=False),
        sa.Column('allowed_topics', postgresql.ARRAY(sa.String()), nullable=True),
        sa.Column('blocked_topics', postgresql.ARRAY(sa.String()), nullable=True),
        sa.Column('total_interactions', sa.Integer(), default=0, nullable=False),
        sa.Column('total_tokens_used', sa.Integer(), default=0, nullable=False),
        sa.Column('metadata', postgresql.JSONB(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), onupdate=sa.func.now(), nullable=True),
    )
    op.create_index('ix_agents_tenant_id', 'agents', ['tenant_id'])

    # AI Routes table
    op.create_table(
        'ai_routes',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('tenant_id', sa.String(36), sa.ForeignKey('tenants.id', ondelete='CASCADE'), nullable=True),
        sa.Column('agent_id', sa.String(36), sa.ForeignKey('agents.id', ondelete='CASCADE'), nullable=True),
        sa.Column('mode', sa.String(20), default='CHAT', nullable=False),
        sa.Column('model_id', sa.String(36), sa.ForeignKey('ai_models.id', ondelete='CASCADE'), nullable=False),
        sa.Column('param_profile_id', sa.String(36), sa.ForeignKey('ai_param_profiles.id'), nullable=True),
        sa.Column('priority', sa.Integer(), default=0, nullable=False),
        sa.Column('condition_json', postgresql.JSONB(), nullable=True),
        sa.Column('fallback_route_id', sa.String(36), sa.ForeignKey('ai_routes.id'), nullable=True),
        sa.Column('is_active', sa.Boolean(), default=True, nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), onupdate=sa.func.now(), nullable=True),
    )
    op.create_index('ix_ai_routes_tenant_id', 'ai_routes', ['tenant_id'])
    op.create_index('ix_ai_routes_agent_id', 'ai_routes', ['agent_id'])

    # Conversations table
    op.create_table(
        'conversations',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('agent_id', sa.String(36), sa.ForeignKey('agents.id', ondelete='CASCADE'), nullable=False),
        sa.Column('tenant_id', sa.String(36), sa.ForeignKey('tenants.id', ondelete='CASCADE'), nullable=False),
        sa.Column('user_id', sa.String(36), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
        sa.Column('tenant_user_id', sa.String(36), sa.ForeignKey('tenant_users.id', ondelete='SET NULL'), nullable=True),
        sa.Column('title', sa.String(200), nullable=True),
        sa.Column('summary', sa.Text(), nullable=True),
        sa.Column('message_count', sa.Integer(), default=0, nullable=False),
        sa.Column('total_tokens', sa.Integer(), default=0, nullable=False),
        sa.Column('status', sa.Enum('ACTIVE', 'ARCHIVED', 'DELETED', name='conversationstatus'), default='ACTIVE', nullable=False),
        sa.Column('is_archived', sa.Boolean(), default=False, nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), onupdate=sa.func.now(), nullable=True),
    )
    op.create_index('ix_conversations_agent_id', 'conversations', ['agent_id'])
    op.create_index('ix_conversations_tenant_id', 'conversations', ['tenant_id'])
    op.create_index('ix_conversations_user_id', 'conversations', ['user_id'])
    op.create_index('ix_conversations_tenant_user_id', 'conversations', ['tenant_user_id'])

    # Messages table
    op.create_table(
        'messages',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('conversation_id', sa.String(36), sa.ForeignKey('conversations.id', ondelete='CASCADE'), nullable=False),
        sa.Column('role', sa.Enum('system', 'user', 'assistant', name='messagerole'), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('input_tokens', sa.Integer(), default=0, nullable=False),
        sa.Column('output_tokens', sa.Integer(), default=0, nullable=False),
        sa.Column('tokens_used', sa.Integer(), nullable=True),
        sa.Column('model', sa.String(50), nullable=True),
        sa.Column('metadata', postgresql.JSONB(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), onupdate=sa.func.now(), nullable=True),
    )
    op.create_index('ix_messages_conversation_id', 'messages', ['conversation_id'])

    # Documents table
    op.create_table(
        'documents',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('tenant_id', sa.String(36), sa.ForeignKey('tenants.id', ondelete='CASCADE'), nullable=False),
        sa.Column('agent_id', sa.String(36), sa.ForeignKey('agents.id', ondelete='SET NULL'), nullable=True),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('file_path', sa.String(500), nullable=True),
        sa.Column('file_type', sa.String(50), nullable=False),
        sa.Column('file_size', sa.Integer(), nullable=True),
        sa.Column('status', sa.Enum('PENDING', 'PROCESSING', 'COMPLETED', 'FAILED', name='documentstatus'), default='PENDING', nullable=False),
        sa.Column('chunk_count', sa.Integer(), default=0, nullable=False),
        sa.Column('metadata', postgresql.JSONB(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), onupdate=sa.func.now(), nullable=True),
    )
    op.create_index('ix_documents_tenant_id', 'documents', ['tenant_id'])
    op.create_index('ix_documents_agent_id', 'documents', ['agent_id'])

    # Document chunks table
    op.create_table(
        'document_chunks',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('document_id', sa.String(36), sa.ForeignKey('documents.id', ondelete='CASCADE'), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('chunk_index', sa.Integer(), nullable=False),
        sa.Column('start_char', sa.Integer(), nullable=True),
        sa.Column('end_char', sa.Integer(), nullable=True),
        sa.Column('metadata', postgresql.JSONB(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), onupdate=sa.func.now(), nullable=True),
    )
    op.create_index('ix_document_chunks_document_id', 'document_chunks', ['document_id'])

    # Chunk summaries table
    op.create_table(
        'chunk_summaries',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('chunk_id', sa.String(36), sa.ForeignKey('document_chunks.id', ondelete='CASCADE'), nullable=False),
        sa.Column('summary', sa.Text(), nullable=False),
        sa.Column('keywords', postgresql.ARRAY(sa.String()), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), onupdate=sa.func.now(), nullable=True),
    )
    op.create_index('ix_chunk_summaries_chunk_id', 'chunk_summaries', ['chunk_id'])

    # Document summaries table
    op.create_table(
        'document_summaries',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('document_id', sa.String(36), sa.ForeignKey('documents.id', ondelete='CASCADE'), nullable=False),
        sa.Column('summary', sa.Text(), nullable=False),
        sa.Column('key_topics', postgresql.ARRAY(sa.String()), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), onupdate=sa.func.now(), nullable=True),
    )
    op.create_index('ix_document_summaries_document_id', 'document_summaries', ['document_id'])

    # Token usage table
    op.create_table(
        'token_usage',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('tenant_id', sa.String(36), sa.ForeignKey('tenants.id', ondelete='CASCADE'), nullable=False),
        sa.Column('agent_id', sa.String(36), sa.ForeignKey('agents.id', ondelete='SET NULL'), nullable=True),
        sa.Column('model', sa.String(50), nullable=False),
        sa.Column('input_tokens', sa.Integer(), default=0, nullable=False),
        sa.Column('output_tokens', sa.Integer(), default=0, nullable=False),
        sa.Column('total_tokens', sa.Integer(), default=0, nullable=False),
        sa.Column('cost_usd', sa.Numeric(10, 6), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), onupdate=sa.func.now(), nullable=True),
    )
    op.create_index('ix_token_usage_tenant_id', 'token_usage', ['tenant_id'])
    op.create_index('ix_token_usage_agent_id', 'token_usage', ['agent_id'])

    # Usage summaries table
    op.create_table(
        'usage_summaries',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('tenant_id', sa.String(36), sa.ForeignKey('tenants.id', ondelete='CASCADE'), nullable=False),
        sa.Column('period_type', sa.String(20), nullable=False),
        sa.Column('period_start', sa.DateTime(), nullable=False),
        sa.Column('period_end', sa.DateTime(), nullable=False),
        sa.Column('total_tokens', sa.Integer(), default=0, nullable=False),
        sa.Column('total_cost_usd', sa.Numeric(10, 6), nullable=True),
        sa.Column('breakdown', postgresql.JSONB(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), onupdate=sa.func.now(), nullable=True),
    )
    op.create_index('ix_usage_summaries_tenant_id', 'usage_summaries', ['tenant_id'])

    # Usage thresholds table
    op.create_table(
        'usage_thresholds',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('tenant_id', sa.String(36), sa.ForeignKey('tenants.id', ondelete='CASCADE'), nullable=False),
        sa.Column('threshold_percent', sa.Integer(), nullable=False),
        sa.Column('is_active', sa.Boolean(), default=True, nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), onupdate=sa.func.now(), nullable=True),
    )
    op.create_index('ix_usage_thresholds_tenant_id', 'usage_thresholds', ['tenant_id'])

    # Usage alerts table
    op.create_table(
        'usage_alerts',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('tenant_id', sa.String(36), sa.ForeignKey('tenants.id', ondelete='CASCADE'), nullable=False),
        sa.Column('threshold_id', sa.String(36), sa.ForeignKey('usage_thresholds.id', ondelete='SET NULL'), nullable=True),
        sa.Column('level', sa.Enum('INFO', 'WARNING', 'CRITICAL', name='alertlevel'), nullable=False),
        sa.Column('message', sa.Text(), nullable=False),
        sa.Column('is_read', sa.Boolean(), default=False, nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), onupdate=sa.func.now(), nullable=True),
    )
    op.create_index('ix_usage_alerts_tenant_id', 'usage_alerts', ['tenant_id'])

    # Payments table
    op.create_table(
        'payments',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('tenant_id', sa.String(36), sa.ForeignKey('tenants.id', ondelete='CASCADE'), nullable=False),
        sa.Column('amount', sa.Numeric(10, 2), nullable=False),
        sa.Column('currency', sa.String(3), default='CLP', nullable=False),
        sa.Column('status', sa.Enum('PENDING', 'COMPLETED', 'FAILED', 'REFUNDED', name='paymentstatus'), default='PENDING', nullable=False),
        sa.Column('payment_method', sa.String(50), nullable=True),
        sa.Column('external_id', sa.String(255), nullable=True),
        sa.Column('metadata', postgresql.JSONB(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), onupdate=sa.func.now(), nullable=True),
    )
    op.create_index('ix_payments_tenant_id', 'payments', ['tenant_id'])

    # Feature flags table
    op.create_table(
        'feature_flags',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('name', sa.String(100), unique=True, nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('scope', sa.String(20), default='GLOBAL', nullable=False),
        sa.Column('is_enabled', sa.Boolean(), default=False, nullable=False),
        sa.Column('config_json', postgresql.JSONB(), nullable=True),
        sa.Column('rollout_percentage', sa.Integer(), default=100, nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), onupdate=sa.func.now(), nullable=True),
    )


def downgrade() -> None:
    op.drop_table('feature_flags')
    op.drop_table('payments')
    op.drop_table('usage_alerts')
    op.drop_table('usage_thresholds')
    op.drop_table('usage_summaries')
    op.drop_table('token_usage')
    op.drop_table('document_summaries')
    op.drop_table('chunk_summaries')
    op.drop_table('document_chunks')
    op.drop_table('documents')
    op.drop_table('messages')
    op.drop_table('conversations')
    op.drop_table('ai_routes')
    op.drop_table('agents')
    op.drop_table('ai_param_profiles')
    op.drop_table('ai_models')
    op.drop_table('ai_providers')
    op.drop_table('tenant_api_keys')
    op.drop_table('tenant_users')
    op.drop_table('tenants')
    op.drop_table('refresh_tokens')
    op.drop_table('users')

    # Drop enums
    op.execute('DROP TYPE IF EXISTS userrole')
    op.execute('DROP TYPE IF EXISTS tenantstatus')
    op.execute('DROP TYPE IF EXISTS tenantplan')
    op.execute('DROP TYPE IF EXISTS tenantuserrole')
    op.execute('DROP TYPE IF EXISTS aiprovidertype')
    op.execute('DROP TYPE IF EXISTS aimodelstatus')
    op.execute('DROP TYPE IF EXISTS agentstatus')
    op.execute('DROP TYPE IF EXISTS agentmode')
    op.execute('DROP TYPE IF EXISTS conversationstatus')
    op.execute('DROP TYPE IF EXISTS messagerole')
    op.execute('DROP TYPE IF EXISTS documentstatus')
    op.execute('DROP TYPE IF EXISTS alertlevel')
    op.execute('DROP TYPE IF EXISTS paymentstatus')
