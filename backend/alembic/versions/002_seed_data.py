"""Seed initial data

Revision ID: 002_seed_data
Revises: 001_initial
Create Date: 2024-01-01 00:01:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.sql import table, column
import uuid
from datetime import datetime
from passlib.context import CryptContext

# revision identifiers, used by Alembic.
revision = '002_seed_data'
down_revision = '001_initial'
branch_labels = None
depends_on = None

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def upgrade() -> None:
    # Create admin user
    users = table('users',
        column('id', sa.String),
        column('email', sa.String),
        column('password_hash', sa.String),
        column('name', sa.String),
        column('role', sa.String),
        column('is_active', sa.Boolean),
        column('created_at', sa.DateTime),
    )

    admin_id = str(uuid.uuid4())
    op.bulk_insert(users, [
        {
            'id': admin_id,
            'email': 'admin@aipanel.cl',
            'password_hash': pwd_context.hash('admin123'),
            'name': 'Admin',
            'role': 'SUPER_ADMIN',
            'is_active': True,
            'created_at': datetime.utcnow(),
        }
    ])

    # Create AI Providers
    providers = table('ai_providers',
        column('id', sa.String),
        column('name', sa.String),
        column('display_name', sa.String),
        column('handler_module', sa.String),
        column('handler_class', sa.String),
        column('is_active', sa.Boolean),
        column('allowed_in_prod', sa.Boolean),
        column('created_at', sa.DateTime),
    )

    openai_id = str(uuid.uuid4())
    anthropic_id = str(uuid.uuid4())

    op.bulk_insert(providers, [
        {
            'id': openai_id,
            'name': 'OpenAI',
            'display_name': 'OpenAI',
            'handler_module': 'app.integrations.openai_client',
            'handler_class': 'OpenAIProvider',
            'is_active': True,
            'allowed_in_prod': True,
            'created_at': datetime.utcnow(),
        },
        {
            'id': anthropic_id,
            'name': 'Anthropic',
            'display_name': 'Anthropic Claude',
            'handler_module': 'app.integrations.anthropic_client',
            'handler_class': 'AnthropicProvider',
            'is_active': True,
            'allowed_in_prod': True,
            'created_at': datetime.utcnow(),
        }
    ])

    # Create AI Models
    models = table('ai_models',
        column('id', sa.String),
        column('provider_id', sa.String),
        column('name', sa.String),
        column('display_name', sa.String),
        column('description', sa.String),
        column('status', sa.String),
        column('pricing_input', sa.Float),
        column('pricing_output', sa.Float),
        column('max_tokens', sa.Integer),
        column('context_window', sa.Integer),
        column('supports_streaming', sa.Boolean),
        column('supports_vision', sa.Boolean),
        column('supports_tools', sa.Boolean),
        column('supports_json_mode', sa.Boolean),
        column('created_at', sa.DateTime),
    )

    gpt4o_mini_id = str(uuid.uuid4())
    gpt4o_id = str(uuid.uuid4())
    claude_sonnet_id = str(uuid.uuid4())
    claude_haiku_id = str(uuid.uuid4())

    op.bulk_insert(models, [
        {
            'id': gpt4o_mini_id,
            'provider_id': openai_id,
            'name': 'gpt-4o-mini',
            'display_name': 'GPT-4o Mini',
            'description': 'Fast and affordable model for most tasks',
            'status': 'STABLE',
            'pricing_input': 0.00015,
            'pricing_output': 0.0006,
            'max_tokens': 16384,
            'context_window': 128000,
            'supports_streaming': True,
            'supports_vision': True,
            'supports_tools': True,
            'supports_json_mode': True,
            'created_at': datetime.utcnow(),
        },
        {
            'id': gpt4o_id,
            'provider_id': openai_id,
            'name': 'gpt-4o',
            'display_name': 'GPT-4o',
            'description': 'Most capable OpenAI model',
            'status': 'STABLE',
            'pricing_input': 0.005,
            'pricing_output': 0.015,
            'max_tokens': 16384,
            'context_window': 128000,
            'supports_streaming': True,
            'supports_vision': True,
            'supports_tools': True,
            'supports_json_mode': True,
            'created_at': datetime.utcnow(),
        },
        {
            'id': claude_sonnet_id,
            'provider_id': anthropic_id,
            'name': 'claude-sonnet-4-5-20250929',
            'display_name': 'Claude Sonnet 4.5',
            'description': 'Most capable Claude model with extended thinking',
            'status': 'STABLE',
            'pricing_input': 0.003,
            'pricing_output': 0.015,
            'max_tokens': 8192,
            'context_window': 200000,
            'supports_streaming': True,
            'supports_vision': True,
            'supports_tools': True,
            'supports_json_mode': False,
            'created_at': datetime.utcnow(),
        },
        {
            'id': claude_haiku_id,
            'provider_id': anthropic_id,
            'name': 'claude-3-5-haiku-20241022',
            'display_name': 'Claude 3.5 Haiku',
            'description': 'Fast and affordable Claude model',
            'status': 'STABLE',
            'pricing_input': 0.0008,
            'pricing_output': 0.004,
            'max_tokens': 8192,
            'context_window': 200000,
            'supports_streaming': True,
            'supports_vision': True,
            'supports_tools': True,
            'supports_json_mode': False,
            'created_at': datetime.utcnow(),
        }
    ])

    # Create default parameter profiles
    profiles = table('ai_param_profiles',
        column('id', sa.String),
        column('name', sa.String),
        column('description', sa.String),
        column('temperature', sa.Float),
        column('max_tokens', sa.Integer),
        column('top_p', sa.Float),
        column('is_active', sa.Boolean),
        column('created_at', sa.DateTime),
    )

    balanced_id = str(uuid.uuid4())
    creative_id = str(uuid.uuid4())
    precise_id = str(uuid.uuid4())

    op.bulk_insert(profiles, [
        {
            'id': balanced_id,
            'name': 'balanced',
            'description': 'Balanced responses for general use',
            'temperature': 0.7,
            'max_tokens': 2048,
            'top_p': 1.0,
            'is_active': True,
            'created_at': datetime.utcnow(),
        },
        {
            'id': creative_id,
            'name': 'creative',
            'description': 'More creative and varied responses',
            'temperature': 1.0,
            'max_tokens': 4096,
            'top_p': 0.95,
            'is_active': True,
            'created_at': datetime.utcnow(),
        },
        {
            'id': precise_id,
            'name': 'precise',
            'description': 'More focused and deterministic responses',
            'temperature': 0.3,
            'max_tokens': 2048,
            'top_p': 0.8,
            'is_active': True,
            'created_at': datetime.utcnow(),
        }
    ])

    # Create default global route
    routes = table('ai_routes',
        column('id', sa.String),
        column('name', sa.String),
        column('description', sa.String),
        column('mode', sa.String),
        column('model_id', sa.String),
        column('param_profile_id', sa.String),
        column('priority', sa.Integer),
        column('is_active', sa.Boolean),
        column('created_at', sa.DateTime),
    )

    op.bulk_insert(routes, [
        {
            'id': str(uuid.uuid4()),
            'name': 'Default Chat Route',
            'description': 'Default route for chat mode using GPT-4o Mini',
            'mode': 'CHAT',
            'model_id': gpt4o_mini_id,
            'param_profile_id': balanced_id,
            'priority': 0,
            'is_active': True,
            'created_at': datetime.utcnow(),
        }
    ])


def downgrade() -> None:
    # Remove seeded data
    op.execute("DELETE FROM ai_routes")
    op.execute("DELETE FROM ai_param_profiles")
    op.execute("DELETE FROM ai_models")
    op.execute("DELETE FROM ai_providers")
    op.execute("DELETE FROM users WHERE email = 'admin@aipanel.cl'")
