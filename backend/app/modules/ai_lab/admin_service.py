"""
AI Lab Admin Service.

Complete CRUD operations for the dynamic AI architecture:
- Providers, Models, Parameter Profiles, Routes, Feature Flags
- Cache management and hot reload
- Test chat functionality

This service is used by the Admin panel for AI configuration.
"""

from typing import List, Optional, Dict, Any
from uuid import UUID
from datetime import datetime

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.utils.logger import get_logger
from app.ai_config.provider_loader import provider_loader, ProviderConfig
from app.integrations.providers.base import Message, GenerationParams

logger = get_logger(__name__)


class AILabAdminService:
    """
    Admin service for AI Lab.

    Provides full CRUD operations for the dynamic AI configuration
    system, including providers, models, profiles, routes, and flags.
    """

    def __init__(self, db: AsyncSession):
        self.db = db

    # ==========================================
    # PROVIDERS CRUD
    # ==========================================

    async def list_providers(
        self,
        is_active: Optional[bool] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> Dict[str, Any]:
        """List all AI providers."""
        sql = "SELECT * FROM ai_providers WHERE 1=1"
        params: Dict[str, Any] = {}

        if is_active is not None:
            sql += " AND is_active = :is_active"
            params["is_active"] = is_active

        sql += " ORDER BY priority ASC, name ASC LIMIT :limit OFFSET :offset"
        params["limit"] = limit
        params["offset"] = offset

        result = await self.db.execute(text(sql), params)
        rows = result.fetchall()

        count_sql = "SELECT COUNT(*) FROM ai_providers WHERE 1=1"
        if is_active is not None:
            count_sql += " AND is_active = :is_active"
        count_result = await self.db.execute(
            text(count_sql),
            {"is_active": is_active} if is_active is not None else {}
        )
        total = count_result.scalar()

        return {
            "items": [dict(row._mapping) for row in rows],
            "total": total,
        }

    async def get_provider(self, provider_id: UUID) -> Optional[Dict]:
        """Get a single provider by ID."""
        result = await self.db.execute(
            text("SELECT * FROM ai_providers WHERE id = :id"),
            {"id": str(provider_id)}
        )
        row = result.fetchone()
        return dict(row._mapping) if row else None

    async def create_provider(self, data: Dict[str, Any]) -> Dict:
        """Create a new AI provider."""
        sql = """
            INSERT INTO ai_providers (
                code, name, description, provider_class, base_url,
                auth_type, default_headers, rate_limit_rpm, rate_limit_tpm,
                supports_streaming, supports_functions, supports_vision,
                supports_realtime, is_active, is_default, priority, metadata
            ) VALUES (
                :code, :name, :description, :provider_class, :base_url,
                :auth_type, :default_headers::jsonb, :rate_limit_rpm, :rate_limit_tpm,
                :supports_streaming, :supports_functions, :supports_vision,
                :supports_realtime, :is_active, :is_default, :priority, :metadata::jsonb
            )
            RETURNING *
        """
        import json

        result = await self.db.execute(text(sql), {
            "code": data["code"],
            "name": data["name"],
            "description": data.get("description"),
            "provider_class": data["provider_class"],
            "base_url": data.get("base_url"),
            "auth_type": data.get("auth_type", "api_key"),
            "default_headers": json.dumps(data.get("default_headers", {})),
            "rate_limit_rpm": data.get("rate_limit_rpm", 60),
            "rate_limit_tpm": data.get("rate_limit_tpm", 100000),
            "supports_streaming": data.get("supports_streaming", True),
            "supports_functions": data.get("supports_functions", True),
            "supports_vision": data.get("supports_vision", False),
            "supports_realtime": data.get("supports_realtime", False),
            "is_active": data.get("is_active", True),
            "is_default": data.get("is_default", False),
            "priority": data.get("priority", 100),
            "metadata": json.dumps(data.get("metadata", {})),
        })
        await self.db.commit()

        row = result.fetchone()
        logger.info(f"Created provider: {data['code']}")
        return dict(row._mapping)

    async def update_provider(self, provider_id: UUID, data: Dict[str, Any]) -> Optional[Dict]:
        """Update a provider."""
        import json

        set_clauses = []
        params = {"id": str(provider_id)}

        for key, value in data.items():
            if key not in ["id", "created_at"]:
                if key in ["default_headers", "metadata"]:
                    set_clauses.append(f"{key} = :{key}::jsonb")
                    params[key] = json.dumps(value)
                else:
                    set_clauses.append(f"{key} = :{key}")
                    params[key] = value

        if not set_clauses:
            return await self.get_provider(provider_id)

        sql = f"""
            UPDATE ai_providers
            SET {', '.join(set_clauses)}, updated_at = NOW()
            WHERE id = :id
            RETURNING *
        """

        result = await self.db.execute(text(sql), params)
        await self.db.commit()
        await provider_loader.invalidate()

        row = result.fetchone()
        return dict(row._mapping) if row else None

    async def delete_provider(self, provider_id: UUID) -> bool:
        """Delete a provider."""
        result = await self.db.execute(
            text("DELETE FROM ai_providers WHERE id = :id RETURNING id"),
            {"id": str(provider_id)}
        )
        await self.db.commit()
        await provider_loader.invalidate()
        return result.rowcount > 0

    # ==========================================
    # MODELS CRUD
    # ==========================================

    async def list_models(
        self,
        provider_id: Optional[UUID] = None,
        model_type: Optional[str] = None,
        is_active: Optional[bool] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> Dict[str, Any]:
        """List AI models."""
        sql = """
            SELECT m.*, p.code as provider_code, p.name as provider_name
            FROM ai_models m
            JOIN ai_providers p ON p.id = m.provider_id
            WHERE 1=1
        """
        params: Dict[str, Any] = {}

        if provider_id:
            sql += " AND m.provider_id = :provider_id"
            params["provider_id"] = str(provider_id)
        if model_type:
            sql += " AND m.model_type = :model_type"
            params["model_type"] = model_type
        if is_active is not None:
            sql += " AND m.is_active = :is_active"
            params["is_active"] = is_active

        sql += " ORDER BY p.priority ASC, m.priority ASC LIMIT :limit OFFSET :offset"
        params["limit"] = limit
        params["offset"] = offset

        result = await self.db.execute(text(sql), params)
        rows = result.fetchall()

        return {
            "items": [dict(row._mapping) for row in rows],
            "total": len(rows),
        }

    async def get_model(self, model_id: UUID) -> Optional[Dict]:
        """Get a model."""
        result = await self.db.execute(
            text("""
                SELECT m.*, p.code as provider_code, p.name as provider_name
                FROM ai_models m
                JOIN ai_providers p ON p.id = m.provider_id
                WHERE m.id = :id
            """),
            {"id": str(model_id)}
        )
        row = result.fetchone()
        return dict(row._mapping) if row else None

    async def create_model(self, data: Dict[str, Any]) -> Dict:
        """Create a model."""
        import json

        sql = """
            INSERT INTO ai_models (
                provider_id, code, name, description, model_type,
                context_window, max_output_tokens, input_price_per_1k,
                output_price_per_1k, supports_streaming, supports_functions,
                supports_vision, supports_json_mode, supports_realtime,
                default_params, capabilities, is_active, priority, metadata
            ) VALUES (
                :provider_id, :code, :name, :description, :model_type,
                :context_window, :max_output_tokens, :input_price_per_1k,
                :output_price_per_1k, :supports_streaming, :supports_functions,
                :supports_vision, :supports_json_mode, :supports_realtime,
                :default_params::jsonb, :capabilities, :is_active, :priority, :metadata::jsonb
            )
            RETURNING *
        """

        result = await self.db.execute(text(sql), {
            "provider_id": str(data["provider_id"]),
            "code": data["code"],
            "name": data["name"],
            "description": data.get("description"),
            "model_type": data.get("model_type", "chat"),
            "context_window": data.get("context_window", 4096),
            "max_output_tokens": data.get("max_output_tokens", 4096),
            "input_price_per_1k": data.get("input_price_per_1k"),
            "output_price_per_1k": data.get("output_price_per_1k"),
            "supports_streaming": data.get("supports_streaming", True),
            "supports_functions": data.get("supports_functions", True),
            "supports_vision": data.get("supports_vision", False),
            "supports_json_mode": data.get("supports_json_mode", False),
            "supports_realtime": data.get("supports_realtime", False),
            "default_params": json.dumps(data.get("default_params", {})),
            "capabilities": data.get("capabilities", []),
            "is_active": data.get("is_active", True),
            "priority": data.get("priority", 100),
            "metadata": json.dumps(data.get("metadata", {})),
        })
        await self.db.commit()

        row = result.fetchone()
        logger.info(f"Created model: {data['code']}")
        return dict(row._mapping)

    async def update_model(self, model_id: UUID, data: Dict[str, Any]) -> Optional[Dict]:
        """Update a model."""
        import json

        set_clauses = []
        params = {"id": str(model_id)}

        for key, value in data.items():
            if key not in ["id", "created_at"]:
                if key in ["default_params", "metadata"]:
                    set_clauses.append(f"{key} = :{key}::jsonb")
                    params[key] = json.dumps(value)
                else:
                    set_clauses.append(f"{key} = :{key}")
                    params[key] = value

        if not set_clauses:
            return await self.get_model(model_id)

        sql = f"""
            UPDATE ai_models
            SET {', '.join(set_clauses)}, updated_at = NOW()
            WHERE id = :id
            RETURNING *
        """

        result = await self.db.execute(text(sql), params)
        await self.db.commit()

        row = result.fetchone()
        return dict(row._mapping) if row else None

    async def delete_model(self, model_id: UUID) -> bool:
        """Delete a model."""
        result = await self.db.execute(
            text("DELETE FROM ai_models WHERE id = :id RETURNING id"),
            {"id": str(model_id)}
        )
        await self.db.commit()
        return result.rowcount > 0

    # ==========================================
    # PARAMETER PROFILES CRUD
    # ==========================================

    async def list_param_profiles(
        self,
        tenant_id: Optional[UUID] = None,
        include_global: bool = True,
    ) -> Dict[str, Any]:
        """List parameter profiles."""
        sql = "SELECT * FROM ai_param_profiles WHERE 1=1"
        params: Dict[str, Any] = {}

        if tenant_id and include_global:
            sql += " AND (tenant_id = :tenant_id OR tenant_id IS NULL)"
            params["tenant_id"] = str(tenant_id)
        elif tenant_id:
            sql += " AND tenant_id = :tenant_id"
            params["tenant_id"] = str(tenant_id)
        else:
            sql += " AND tenant_id IS NULL"

        sql += " ORDER BY is_default DESC, name ASC"

        result = await self.db.execute(text(sql), params)
        rows = result.fetchall()

        return {
            "items": [dict(row._mapping) for row in rows],
            "total": len(rows),
        }

    async def create_param_profile(self, data: Dict[str, Any]) -> Dict:
        """Create a parameter profile."""
        import json

        sql = """
            INSERT INTO ai_param_profiles (
                tenant_id, code, name, description, temperature, top_p,
                top_k, frequency_penalty, presence_penalty, max_tokens,
                stop_sequences, response_format, seed, extra_params,
                is_default, is_active
            ) VALUES (
                :tenant_id, :code, :name, :description, :temperature, :top_p,
                :top_k, :frequency_penalty, :presence_penalty, :max_tokens,
                :stop_sequences, :response_format, :seed, :extra_params::jsonb,
                :is_default, :is_active
            )
            RETURNING *
        """

        result = await self.db.execute(text(sql), {
            "tenant_id": str(data["tenant_id"]) if data.get("tenant_id") else None,
            "code": data["code"],
            "name": data["name"],
            "description": data.get("description"),
            "temperature": data.get("temperature", 0.7),
            "top_p": data.get("top_p", 1.0),
            "top_k": data.get("top_k"),
            "frequency_penalty": data.get("frequency_penalty", 0),
            "presence_penalty": data.get("presence_penalty", 0),
            "max_tokens": data.get("max_tokens", 2048),
            "stop_sequences": data.get("stop_sequences", []),
            "response_format": data.get("response_format"),
            "seed": data.get("seed"),
            "extra_params": json.dumps(data.get("extra_params", {})),
            "is_default": data.get("is_default", False),
            "is_active": data.get("is_active", True),
        })
        await self.db.commit()

        row = result.fetchone()
        return dict(row._mapping)

    # ==========================================
    # ROUTES CRUD
    # ==========================================

    async def list_routes(
        self,
        tenant_id: Optional[UUID] = None,
        route_type: Optional[str] = None,
        is_active: Optional[bool] = None,
    ) -> Dict[str, Any]:
        """List AI routes."""
        sql = """
            SELECT r.*, m.code as model_code, m.name as model_name,
                   p.code as provider_code
            FROM ai_routes r
            JOIN ai_models m ON m.id = r.primary_model_id
            JOIN ai_providers p ON p.id = m.provider_id
            WHERE 1=1
        """
        params: Dict[str, Any] = {}

        if tenant_id:
            sql += " AND (r.tenant_id = :tenant_id OR r.tenant_id IS NULL)"
            params["tenant_id"] = str(tenant_id)
        if route_type:
            sql += " AND r.route_type = :route_type"
            params["route_type"] = route_type
        if is_active is not None:
            sql += " AND r.is_active = :is_active"
            params["is_active"] = is_active

        sql += " ORDER BY r.priority ASC"

        result = await self.db.execute(text(sql), params)
        rows = result.fetchall()

        return {
            "items": [dict(row._mapping) for row in rows],
            "total": len(rows),
        }

    async def create_route(self, data: Dict[str, Any]) -> Dict:
        """Create a route."""
        import json

        sql = """
            INSERT INTO ai_routes (
                tenant_id, code, name, description, route_type,
                primary_model_id, fallback_model_ids, param_profile_id,
                conditions, priority, timeout_ms, retry_count,
                is_active, metadata
            ) VALUES (
                :tenant_id, :code, :name, :description, :route_type,
                :primary_model_id, :fallback_model_ids, :param_profile_id,
                :conditions::jsonb, :priority, :timeout_ms, :retry_count,
                :is_active, :metadata::jsonb
            )
            RETURNING *
        """

        result = await self.db.execute(text(sql), {
            "tenant_id": str(data["tenant_id"]) if data.get("tenant_id") else None,
            "code": data["code"],
            "name": data["name"],
            "description": data.get("description"),
            "route_type": data.get("route_type", "chat"),
            "primary_model_id": str(data["primary_model_id"]),
            "fallback_model_ids": data.get("fallback_model_ids", []),
            "param_profile_id": str(data["param_profile_id"]) if data.get("param_profile_id") else None,
            "conditions": json.dumps(data.get("conditions", {})),
            "priority": data.get("priority", 100),
            "timeout_ms": data.get("timeout_ms", 30000),
            "retry_count": data.get("retry_count", 2),
            "is_active": data.get("is_active", True),
            "metadata": json.dumps(data.get("metadata", {})),
        })
        await self.db.commit()

        row = result.fetchone()
        logger.info(f"Created route: {data['code']}")
        return dict(row._mapping)

    # ==========================================
    # FEATURE FLAGS
    # ==========================================

    async def list_feature_flags(
        self,
        tenant_id: Optional[UUID] = None,
        category: Optional[str] = None,
    ) -> Dict[str, Any]:
        """List feature flags."""
        sql = "SELECT * FROM feature_flags WHERE 1=1"
        params: Dict[str, Any] = {}

        if tenant_id:
            sql += " AND (tenant_id = :tenant_id OR tenant_id IS NULL)"
            params["tenant_id"] = str(tenant_id)
        if category:
            sql += " AND category = :category"
            params["category"] = category

        sql += " ORDER BY category ASC, code ASC"

        result = await self.db.execute(text(sql), params)
        rows = result.fetchall()

        return {
            "items": [dict(row._mapping) for row in rows],
            "total": len(rows),
        }

    async def set_feature_flag(
        self,
        code: str,
        is_enabled: bool,
        tenant_id: Optional[UUID] = None,
    ) -> Dict:
        """Set a feature flag."""
        import json

        # Check if exists
        check_sql = "SELECT id FROM feature_flags WHERE code = :code"
        check_params: Dict[str, Any] = {"code": code}

        if tenant_id:
            check_sql += " AND tenant_id = :tenant_id"
            check_params["tenant_id"] = str(tenant_id)
        else:
            check_sql += " AND tenant_id IS NULL"

        existing = await self.db.execute(text(check_sql), check_params)

        if existing.fetchone():
            # Update
            sql = """
                UPDATE feature_flags
                SET is_enabled = :is_enabled, updated_at = NOW()
                WHERE code = :code
            """
            if tenant_id:
                sql += " AND tenant_id = :tenant_id"
            else:
                sql += " AND tenant_id IS NULL"
            sql += " RETURNING *"
        else:
            # Insert
            sql = """
                INSERT INTO feature_flags (code, name, tenant_id, is_enabled, category)
                VALUES (:code, :code, :tenant_id, :is_enabled, 'ai')
                RETURNING *
            """

        result = await self.db.execute(text(sql), {
            "code": code,
            "tenant_id": str(tenant_id) if tenant_id else None,
            "is_enabled": is_enabled,
        })
        await self.db.commit()

        row = result.fetchone()
        return dict(row._mapping)

    # ==========================================
    # CACHE & HOT RELOAD
    # ==========================================

    async def invalidate_cache(self) -> Dict:
        """Invalidate all caches."""
        provider_count = await provider_loader.invalidate()

        return {
            "success": True,
            "providers_invalidated": provider_count,
            "timestamp": datetime.utcnow().isoformat(),
        }

    # ==========================================
    # TEST CHAT
    # ==========================================

    async def test_chat(
        self,
        provider_code: str,
        model_code: str,
        messages: List[Dict[str, str]],
        params: Optional[Dict[str, Any]] = None,
    ) -> Dict:
        """Test a model with chat."""
        import time

        # Get provider
        provider_result = await self.db.execute(
            text("SELECT * FROM ai_providers WHERE code = :code"),
            {"code": provider_code}
        )
        provider_row = provider_result.fetchone()

        if not provider_row:
            return {"success": False, "error": f"Provider {provider_code} not found"}

        provider_data = dict(provider_row._mapping)

        # Get API key
        api_key = await self._get_api_key(provider_code)
        if not api_key:
            return {"success": False, "error": f"No API key configured for {provider_code}"}

        try:
            # Load provider
            config = ProviderConfig(
                provider_id=str(provider_data["id"]),
                code=provider_code,
                name=provider_data["name"],
                provider_class=provider_data["provider_class"],
                api_key=api_key,
                base_url=provider_data.get("base_url"),
            )

            provider = await provider_loader.load_provider(config)

            # Convert messages
            formatted_messages = [
                Message(role=m["role"], content=m["content"])
                for m in messages
            ]

            # Build params
            gen_params = GenerationParams(
                temperature=params.get("temperature", 0.7) if params else 0.7,
                max_tokens=params.get("max_tokens", 1024) if params else 1024,
                top_p=params.get("top_p", 1.0) if params else 1.0,
            )

            start_time = time.time()
            result = await provider.generate(
                messages=formatted_messages,
                model=model_code,
                params=gen_params,
            )
            latency_ms = int((time.time() - start_time) * 1000)

            return {
                "success": True,
                "content": result.content,
                "model": result.model,
                "provider": provider_code,
                "usage": {
                    "input_tokens": result.usage.input_tokens,
                    "output_tokens": result.usage.output_tokens,
                    "total_tokens": result.usage.total_tokens,
                },
                "latency_ms": latency_ms,
                "finish_reason": result.finish_reason,
            }

        except Exception as e:
            logger.error(f"Test chat failed: {e}")
            return {
                "success": False,
                "error": str(e),
            }

    async def _get_api_key(self, provider_code: str) -> Optional[str]:
        """Get API key for a provider."""
        from app.core.config import settings

        if provider_code == "OPENAI":
            return settings.OPENAI_API_KEY
        elif provider_code == "ANTHROPIC":
            return settings.ANTHROPIC_API_KEY
        elif provider_code == "GOOGLE":
            return getattr(settings, "GOOGLE_API_KEY", None)
        return None

    # ==========================================
    # STATS
    # ==========================================

    async def get_stats(self) -> Dict:
        """Get AI Lab statistics."""
        providers = await self.db.execute(
            text("SELECT COUNT(*) as total, COUNT(*) FILTER (WHERE is_active) as active FROM ai_providers")
        )
        p_row = providers.fetchone()

        models = await self.db.execute(
            text("SELECT COUNT(*) as total, COUNT(*) FILTER (WHERE is_active) as active FROM ai_models")
        )
        m_row = models.fetchone()

        profiles = await self.db.execute(
            text("SELECT COUNT(*) FROM ai_param_profiles")
        )

        routes = await self.db.execute(
            text("SELECT COUNT(*) as total, COUNT(*) FILTER (WHERE is_active) as active FROM ai_routes")
        )
        r_row = routes.fetchone()

        flags = await self.db.execute(
            text("SELECT COUNT(*) as total, COUNT(*) FILTER (WHERE is_enabled) as enabled FROM feature_flags")
        )
        f_row = flags.fetchone()

        return {
            "providers": {"total": p_row.total, "active": p_row.active},
            "models": {"total": m_row.total, "active": m_row.active},
            "param_profiles": profiles.scalar(),
            "routes": {"total": r_row.total, "active": r_row.active},
            "feature_flags": {"total": f_row.total, "enabled": f_row.enabled},
            "cache_stats": provider_loader.get_stats(),
        }
