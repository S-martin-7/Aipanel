"""
Add dynamic AI architecture tables.

This migration creates the core tables for AIPanel's dynamic AI system:
- ai_providers: Pluggable AI provider configurations
- ai_models: Model definitions per provider
- ai_param_profiles: Reusable parameter presets (temperature, etc.)
- ai_routes: Dynamic routing rules with fallbacks
- feature_flags: Hot-toggleable AI capabilities

Revision ID: 009
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB, ARRAY
from datetime import datetime


revision = "009"
down_revision = "008"
branch_labels = None
depends_on = None


def upgrade():
    # ===========================================
    # AI PROVIDERS - Pluggable provider registry
    # ===========================================
    op.create_table(
        "ai_providers",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("code", sa.String(50), unique=True, nullable=False),  # OPENAI, ANTHROPIC, GOOGLE, etc.
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("description", sa.Text),
        sa.Column("provider_class", sa.String(200), nullable=False),  # app.integrations.providers.openai.OpenAIProvider
        sa.Column("base_url", sa.String(500)),  # For custom endpoints
        sa.Column("auth_type", sa.String(50), default="api_key"),  # api_key, oauth, custom
        sa.Column("default_headers", JSONB, default={}),
        sa.Column("rate_limit_rpm", sa.Integer, default=60),
        sa.Column("rate_limit_tpm", sa.Integer, default=100000),
        sa.Column("supports_streaming", sa.Boolean, default=True),
        sa.Column("supports_functions", sa.Boolean, default=True),
        sa.Column("supports_vision", sa.Boolean, default=False),
        sa.Column("supports_realtime", sa.Boolean, default=False),
        sa.Column("health_check_endpoint", sa.String(200)),
        sa.Column("is_active", sa.Boolean, default=True),
        sa.Column("is_default", sa.Boolean, default=False),
        sa.Column("priority", sa.Integer, default=100),  # Lower = higher priority
        sa.Column("metadata", JSONB, default={}),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), onupdate=sa.func.now()),
    )
    op.create_index("ix_ai_providers_code", "ai_providers", ["code"])
    op.create_index("ix_ai_providers_is_active", "ai_providers", ["is_active"])

    # ===========================================
    # AI MODELS - Model definitions per provider
    # ===========================================
    op.create_table(
        "ai_models",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("provider_id", UUID(as_uuid=True), sa.ForeignKey("ai_providers.id", ondelete="CASCADE"), nullable=False),
        sa.Column("code", sa.String(100), nullable=False),  # gpt-4o, claude-3-5-sonnet, etc.
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("description", sa.Text),
        sa.Column("model_type", sa.String(50), default="chat"),  # chat, completion, embedding, realtime
        sa.Column("context_window", sa.Integer, default=4096),
        sa.Column("max_output_tokens", sa.Integer, default=4096),
        sa.Column("input_price_per_1k", sa.Numeric(10, 6)),  # USD per 1K tokens
        sa.Column("output_price_per_1k", sa.Numeric(10, 6)),
        sa.Column("supports_streaming", sa.Boolean, default=True),
        sa.Column("supports_functions", sa.Boolean, default=True),
        sa.Column("supports_vision", sa.Boolean, default=False),
        sa.Column("supports_json_mode", sa.Boolean, default=False),
        sa.Column("supports_realtime", sa.Boolean, default=False),
        sa.Column("default_params", JSONB, default={}),  # Default temperature, top_p, etc.
        sa.Column("capabilities", ARRAY(sa.String), default=[]),  # ["reasoning", "coding", "creative"]
        sa.Column("is_active", sa.Boolean, default=True),
        sa.Column("is_deprecated", sa.Boolean, default=False),
        sa.Column("deprecation_date", sa.Date),
        sa.Column("replacement_model_id", UUID(as_uuid=True)),
        sa.Column("priority", sa.Integer, default=100),
        sa.Column("metadata", JSONB, default={}),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), onupdate=sa.func.now()),
        sa.UniqueConstraint("provider_id", "code", name="uq_ai_models_provider_code"),
    )
    op.create_index("ix_ai_models_provider_id", "ai_models", ["provider_id"])
    op.create_index("ix_ai_models_code", "ai_models", ["code"])
    op.create_index("ix_ai_models_model_type", "ai_models", ["model_type"])
    op.create_index("ix_ai_models_is_active", "ai_models", ["is_active"])

    # ===========================================
    # AI PARAM PROFILES - Reusable parameter presets
    # ===========================================
    op.create_table(
        "ai_param_profiles",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="CASCADE")),  # NULL = global
        sa.Column("code", sa.String(100), nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("description", sa.Text),
        sa.Column("temperature", sa.Numeric(3, 2), default=0.7),
        sa.Column("top_p", sa.Numeric(3, 2), default=1.0),
        sa.Column("top_k", sa.Integer),
        sa.Column("frequency_penalty", sa.Numeric(3, 2), default=0.0),
        sa.Column("presence_penalty", sa.Numeric(3, 2), default=0.0),
        sa.Column("max_tokens", sa.Integer, default=2048),
        sa.Column("stop_sequences", ARRAY(sa.String), default=[]),
        sa.Column("response_format", sa.String(50)),  # text, json_object
        sa.Column("seed", sa.Integer),  # For reproducibility
        sa.Column("extra_params", JSONB, default={}),  # Provider-specific params
        sa.Column("is_default", sa.Boolean, default=False),
        sa.Column("is_active", sa.Boolean, default=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), onupdate=sa.func.now()),
    )
    op.create_index("ix_ai_param_profiles_tenant_id", "ai_param_profiles", ["tenant_id"])
    op.create_index("ix_ai_param_profiles_code", "ai_param_profiles", ["code"])

    # ===========================================
    # AI ROUTES - Dynamic routing rules
    # ===========================================
    op.create_table(
        "ai_routes",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="CASCADE")),  # NULL = global
        sa.Column("code", sa.String(100), nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("description", sa.Text),
        sa.Column("route_type", sa.String(50), default="chat"),  # chat, completion, embedding, realtime
        sa.Column("primary_model_id", UUID(as_uuid=True), sa.ForeignKey("ai_models.id"), nullable=False),
        sa.Column("fallback_model_ids", ARRAY(UUID(as_uuid=True)), default=[]),
        sa.Column("param_profile_id", UUID(as_uuid=True), sa.ForeignKey("ai_param_profiles.id")),
        sa.Column("conditions", JSONB, default={}),  # {"agent_type": "support", "language": "es"}
        sa.Column("priority", sa.Integer, default=100),  # Lower = evaluated first
        sa.Column("timeout_ms", sa.Integer, default=30000),
        sa.Column("retry_count", sa.Integer, default=2),
        sa.Column("retry_delay_ms", sa.Integer, default=1000),
        sa.Column("circuit_breaker_threshold", sa.Integer, default=5),
        sa.Column("circuit_breaker_timeout_s", sa.Integer, default=60),
        sa.Column("rate_limit_rpm", sa.Integer),  # Override provider limit
        sa.Column("is_active", sa.Boolean, default=True),
        sa.Column("valid_from", sa.DateTime(timezone=True)),
        sa.Column("valid_until", sa.DateTime(timezone=True)),
        sa.Column("metadata", JSONB, default={}),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), onupdate=sa.func.now()),
    )
    op.create_index("ix_ai_routes_tenant_id", "ai_routes", ["tenant_id"])
    op.create_index("ix_ai_routes_route_type", "ai_routes", ["route_type"])
    op.create_index("ix_ai_routes_priority", "ai_routes", ["priority"])
    op.create_index("ix_ai_routes_is_active", "ai_routes", ["is_active"])

    # ===========================================
    # FEATURE FLAGS - Hot-toggleable capabilities
    # ===========================================
    op.create_table(
        "feature_flags",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="CASCADE")),  # NULL = global
        sa.Column("code", sa.String(100), nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("description", sa.Text),
        sa.Column("category", sa.String(50), default="ai"),  # ai, billing, ui, experiment
        sa.Column("is_enabled", sa.Boolean, default=False),
        sa.Column("rollout_percentage", sa.Integer, default=100),  # 0-100 for gradual rollout
        sa.Column("conditions", JSONB, default={}),  # {"plan": ["professional", "enterprise"]}
        sa.Column("value", JSONB),  # For feature configs, not just on/off
        sa.Column("valid_from", sa.DateTime(timezone=True)),
        sa.Column("valid_until", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), onupdate=sa.func.now()),
    )
    op.create_index("ix_feature_flags_tenant_id", "feature_flags", ["tenant_id"])
    op.create_index("ix_feature_flags_code", "feature_flags", ["code"])
    op.create_index("ix_feature_flags_category", "feature_flags", ["category"])

    # ===========================================
    # AI CONFIG CACHE - For hot reload
    # ===========================================
    op.create_table(
        "ai_config_cache",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("cache_key", sa.String(200), unique=True, nullable=False),
        sa.Column("cache_value", JSONB, nullable=False),
        sa.Column("ttl_seconds", sa.Integer, default=300),
        sa.Column("version", sa.Integer, default=1),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("expires_at", sa.DateTime(timezone=True)),
    )
    op.create_index("ix_ai_config_cache_key", "ai_config_cache", ["cache_key"])
    op.create_index("ix_ai_config_cache_expires", "ai_config_cache", ["expires_at"])

    # ===========================================
    # AI EXECUTION LOGS - Detailed logging per request
    # ===========================================
    op.create_table(
        "ai_execution_logs",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="CASCADE")),
        sa.Column("agent_id", UUID(as_uuid=True), sa.ForeignKey("agents.id", ondelete="SET NULL")),
        sa.Column("conversation_id", UUID(as_uuid=True)),
        sa.Column("route_id", UUID(as_uuid=True), sa.ForeignKey("ai_routes.id", ondelete="SET NULL")),
        sa.Column("provider_id", UUID(as_uuid=True), sa.ForeignKey("ai_providers.id", ondelete="SET NULL")),
        sa.Column("model_id", UUID(as_uuid=True), sa.ForeignKey("ai_models.id", ondelete="SET NULL")),
        sa.Column("param_profile_id", UUID(as_uuid=True), sa.ForeignKey("ai_param_profiles.id", ondelete="SET NULL")),
        sa.Column("request_type", sa.String(50)),  # chat, completion, embedding, realtime
        sa.Column("input_tokens", sa.Integer),
        sa.Column("output_tokens", sa.Integer),
        sa.Column("total_tokens", sa.Integer),
        sa.Column("latency_ms", sa.Integer),
        sa.Column("ttft_ms", sa.Integer),  # Time to first token (streaming)
        sa.Column("status", sa.String(50)),  # success, error, timeout, rate_limited
        sa.Column("error_code", sa.String(100)),
        sa.Column("error_message", sa.Text),
        sa.Column("fallback_used", sa.Boolean, default=False),
        sa.Column("fallback_model_id", UUID(as_uuid=True)),
        sa.Column("retry_count", sa.Integer, default=0),
        sa.Column("cost_usd", sa.Numeric(10, 6)),
        sa.Column("params_used", JSONB),  # Actual params sent
        sa.Column("metadata", JSONB, default={}),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_ai_execution_logs_tenant_id", "ai_execution_logs", ["tenant_id"])
    op.create_index("ix_ai_execution_logs_created_at", "ai_execution_logs", ["created_at"])
    op.create_index("ix_ai_execution_logs_provider_id", "ai_execution_logs", ["provider_id"])
    op.create_index("ix_ai_execution_logs_model_id", "ai_execution_logs", ["model_id"])
    op.create_index("ix_ai_execution_logs_status", "ai_execution_logs", ["status"])

    # ===========================================
    # UPDATE AGENTS TABLE - Add dynamic model references
    # ===========================================
    op.add_column("agents", sa.Column("model_id", UUID(as_uuid=True), sa.ForeignKey("ai_models.id", ondelete="SET NULL")))
    op.add_column("agents", sa.Column("param_profile_id", UUID(as_uuid=True), sa.ForeignKey("ai_param_profiles.id", ondelete="SET NULL")))
    op.add_column("agents", sa.Column("route_id", UUID(as_uuid=True), sa.ForeignKey("ai_routes.id", ondelete="SET NULL")))
    op.add_column("agents", sa.Column("config_version", sa.Integer, default=1))
    op.add_column("agents", sa.Column("feature_overrides", JSONB, default={}))

    # ===========================================
    # SEED DEFAULT PROVIDERS AND MODELS
    # ===========================================
    op.execute("""
        -- OpenAI Provider
        INSERT INTO ai_providers (code, name, description, provider_class, supports_streaming, supports_functions, supports_vision, is_active, is_default, priority)
        VALUES
        ('OPENAI', 'OpenAI', 'OpenAI GPT models', 'app.integrations.providers.openai_provider.OpenAIProvider', true, true, true, true, true, 10),
        ('ANTHROPIC', 'Anthropic', 'Anthropic Claude models', 'app.integrations.providers.anthropic_provider.AnthropicProvider', true, true, true, true, false, 20),
        ('GOOGLE', 'Google AI', 'Google Gemini models', 'app.integrations.providers.google_provider.GoogleProvider', true, true, true, false, false, 30);
    """)

    op.execute("""
        -- OpenAI Models
        INSERT INTO ai_models (provider_id, code, name, model_type, context_window, max_output_tokens, input_price_per_1k, output_price_per_1k, supports_streaming, supports_functions, supports_vision, supports_json_mode, is_active, priority)
        SELECT
            p.id,
            m.code,
            m.name,
            m.model_type,
            m.context_window,
            m.max_output_tokens,
            m.input_price,
            m.output_price,
            m.supports_streaming,
            m.supports_functions,
            m.supports_vision,
            m.supports_json,
            true,
            m.priority
        FROM ai_providers p
        CROSS JOIN (VALUES
            ('gpt-4o', 'GPT-4o', 'chat', 128000, 16384, 0.005, 0.015, true, true, true, true, 10),
            ('gpt-4o-mini', 'GPT-4o Mini', 'chat', 128000, 16384, 0.00015, 0.0006, true, true, true, true, 20),
            ('gpt-4-turbo', 'GPT-4 Turbo', 'chat', 128000, 4096, 0.01, 0.03, true, true, true, true, 30),
            ('gpt-3.5-turbo', 'GPT-3.5 Turbo', 'chat', 16385, 4096, 0.0005, 0.0015, true, true, false, true, 40),
            ('text-embedding-3-small', 'Embedding Small', 'embedding', 8191, 0, 0.00002, 0, false, false, false, false, 100),
            ('text-embedding-3-large', 'Embedding Large', 'embedding', 8191, 0, 0.00013, 0, false, false, false, false, 110)
        ) AS m(code, name, model_type, context_window, max_output_tokens, input_price, output_price, supports_streaming, supports_functions, supports_vision, supports_json, priority)
        WHERE p.code = 'OPENAI';
    """)

    op.execute("""
        -- Anthropic Models
        INSERT INTO ai_models (provider_id, code, name, model_type, context_window, max_output_tokens, input_price_per_1k, output_price_per_1k, supports_streaming, supports_functions, supports_vision, is_active, priority)
        SELECT
            p.id,
            m.code,
            m.name,
            m.model_type,
            m.context_window,
            m.max_output_tokens,
            m.input_price,
            m.output_price,
            m.supports_streaming,
            m.supports_functions,
            m.supports_vision,
            true,
            m.priority
        FROM ai_providers p
        CROSS JOIN (VALUES
            ('claude-3-5-sonnet-20241022', 'Claude 3.5 Sonnet', 'chat', 200000, 8192, 0.003, 0.015, true, true, true, 10),
            ('claude-3-5-haiku-20241022', 'Claude 3.5 Haiku', 'chat', 200000, 8192, 0.001, 0.005, true, true, true, 20),
            ('claude-3-opus-20240229', 'Claude 3 Opus', 'chat', 200000, 4096, 0.015, 0.075, true, true, true, 30)
        ) AS m(code, name, model_type, context_window, max_output_tokens, input_price, output_price, supports_streaming, supports_functions, supports_vision, priority)
        WHERE p.code = 'ANTHROPIC';
    """)

    op.execute("""
        -- Default Parameter Profiles (Global)
        INSERT INTO ai_param_profiles (tenant_id, code, name, description, temperature, top_p, max_tokens, is_default, is_active)
        VALUES
        (NULL, 'balanced', 'Balanced', 'Default balanced settings', 0.7, 1.0, 2048, true, true),
        (NULL, 'creative', 'Creative', 'Higher temperature for creative tasks', 1.0, 0.95, 4096, false, true),
        (NULL, 'precise', 'Precise', 'Lower temperature for factual responses', 0.3, 0.9, 2048, false, true),
        (NULL, 'coding', 'Coding', 'Optimized for code generation', 0.2, 0.95, 4096, false, true);
    """)

    op.execute("""
        -- Default Feature Flags
        INSERT INTO feature_flags (tenant_id, code, name, description, category, is_enabled)
        VALUES
        (NULL, 'ai_streaming', 'AI Streaming', 'Enable streaming responses', 'ai', true),
        (NULL, 'ai_functions', 'AI Functions', 'Enable function calling', 'ai', true),
        (NULL, 'ai_vision', 'AI Vision', 'Enable vision/image input', 'ai', true),
        (NULL, 'ai_realtime', 'AI Realtime', 'Enable realtime voice mode', 'ai', false),
        (NULL, 'ai_fallback', 'AI Fallback', 'Enable automatic model fallback', 'ai', true),
        (NULL, 'ai_caching', 'AI Caching', 'Enable response caching', 'ai', false);
    """)


def downgrade():
    # Remove agent columns
    op.drop_column("agents", "feature_overrides")
    op.drop_column("agents", "config_version")
    op.drop_column("agents", "route_id")
    op.drop_column("agents", "param_profile_id")
    op.drop_column("agents", "model_id")

    # Drop tables in reverse order
    op.drop_table("ai_execution_logs")
    op.drop_table("ai_config_cache")
    op.drop_table("feature_flags")
    op.drop_table("ai_routes")
    op.drop_table("ai_param_profiles")
    op.drop_table("ai_models")
    op.drop_table("ai_providers")
