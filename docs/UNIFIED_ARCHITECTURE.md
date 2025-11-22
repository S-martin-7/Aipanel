# AIPanel - Arquitectura Unificada

**Version:** 2.0.0
**Fecha:** 2025-01-22

---

## 1. DECISIONES ARQUITECTONICAS DEFINITIVAS

### 1.1 Stack Tecnologico

| Capa | Tecnologia | Justificacion |
|------|------------|---------------|
| **Backend** | Python 3.11 + FastAPI | Ecosistema AI nativo, async, type-safe |
| **Frontend** | Next.js 14 + TypeScript | App Router, SSR, shadcn/ui |
| **Base de Datos** | PostgreSQL 15 | Full-text search, JSONB, confiable |
| **Cache** | Redis 7 | Sessions, cache, rate limiting |
| **Tasks** | Celery + Redis | Procesamiento asincrono |
| **Deployment** | Systemd (sin Docker) | Menor overhead, nativo Linux |

### 1.2 Sistema de Pagos

**DEFINITIVO: Transbank (Chile)**

- Webpay Plus para pagos unicos
- OneClick para suscripciones
- Facturacion electronica SII
- Moneda: CLP (pesos chilenos)

> Stripe queda como opcion futura para expansion internacional.

### 1.3 Estructura de Carpetas

**DEFINITIVO: Patron Modular**

```
backend/app/
├── core/                 # Nucleo del sistema
├── modules/              # Modulos independientes (auth, tenants, agents, etc.)
├── integrations/         # Clientes externos (OpenAI, Anthropic, Transbank)
├── tasks/                # Tareas Celery
└── utils/                # Utilidades globales
```

---

## 2. MODELO MULTI-TENANT

```
NIVEL 1: ADMINISTRADORES (users)
├── Gestion global de servidores
├── Gestion de tenants
├── AI Lab (pruebas de modelos)
└── Analytics globales

NIVEL 2: TENANTS (tenants + tenant_users)
├── Gestion de agentes AI
├── Documentos y conocimiento
├── Chat con agentes
├── Metricas de uso
└── Facturacion
```

---

## 3. SISTEMA DE PROVEEDORES DE IA (DINAMICO)

### 3.1 Tablas de Configuracion

```sql
-- Proveedores (OpenAI, Anthropic, etc.)
CREATE TABLE ai_providers (
    id VARCHAR PRIMARY KEY,
    name VARCHAR NOT NULL,              -- "OpenAI", "Anthropic"
    handler_module VARCHAR NOT NULL,    -- "integrations.openai_client"
    handler_class VARCHAR NOT NULL,     -- "OpenAIProviderClient"
    config_json JSONB,                  -- API keys, endpoints
    is_active BOOLEAN DEFAULT true,
    allowed_in_prod BOOLEAN DEFAULT false
);

-- Modelos disponibles
CREATE TABLE ai_models (
    id VARCHAR PRIMARY KEY,
    provider_id VARCHAR REFERENCES ai_providers(id),
    name VARCHAR NOT NULL,              -- "gpt-4o-mini"
    display_name VARCHAR,               -- "GPT-4o Mini"
    capabilities TEXT[],                -- ['chat', 'vision', 'streaming']
    status VARCHAR DEFAULT 'EXPERIMENTAL', -- EXPERIMENTAL, STABLE, DEPRECATED
    pricing_input DECIMAL(10,6),        -- Costo por 1K tokens input
    pricing_output DECIMAL(10,6),       -- Costo por 1K tokens output
    max_tokens INTEGER,
    supports_streaming BOOLEAN DEFAULT true,
    supports_vision BOOLEAN DEFAULT false
);

-- Perfiles de parametros reutilizables
CREATE TABLE ai_param_profiles (
    id VARCHAR PRIMARY KEY,
    name VARCHAR NOT NULL,              -- "creative", "precise", "balanced"
    temperature FLOAT,
    max_tokens INTEGER,
    top_p FLOAT,
    frequency_penalty FLOAT,
    presence_penalty FLOAT
);

-- Rutas de ruteo (que modelo usar segun contexto)
CREATE TABLE ai_routes (
    id VARCHAR PRIMARY KEY,
    name VARCHAR NOT NULL,
    tenant_id VARCHAR,                  -- NULL = global
    agent_id VARCHAR,                   -- NULL = cualquier agente
    mode VARCHAR DEFAULT 'CHAT',        -- CHAT, REALTIME
    model_id VARCHAR REFERENCES ai_models(id),
    param_profile_id VARCHAR REFERENCES ai_param_profiles(id),
    priority INTEGER DEFAULT 0,
    condition_json JSONB,               -- Condiciones adicionales
    fallback_route_id VARCHAR,          -- Ruta de fallback
    is_active BOOLEAN DEFAULT true
);

-- Feature flags
CREATE TABLE feature_flags (
    id VARCHAR PRIMARY KEY,
    name VARCHAR NOT NULL UNIQUE,       -- "enable_realtime", "enable_vision"
    scope VARCHAR DEFAULT 'GLOBAL',     -- GLOBAL, TENANT, USER
    is_enabled BOOLEAN DEFAULT false,
    config_json JSONB
);
```

### 3.2 AI Engine (Motor de Ruteo)

```python
# Pseudocodigo del motor
class AIEngine:
    async def resolve_route(tenant_id, agent_id, mode) -> Route:
        """Encuentra la mejor ruta para el contexto dado"""
        routes = await db.ai_routes.find(
            tenant_id=tenant_id OR NULL,
            agent_id=agent_id OR NULL,
            mode=mode,
            is_active=True
        ).order_by(priority.desc())

        return routes[0] if routes else default_route

    async def get_client(route: Route) -> AIProviderClient:
        """Carga dinamicamente el cliente del proveedor"""
        provider = await db.ai_providers.get(route.model.provider_id)
        module = importlib.import_module(provider.handler_module)
        client_class = getattr(module, provider.handler_class)
        return client_class(provider.config_json)
```

### 3.3 AI Lab

Entorno aislado para probar modelos antes de produccion:
- Usa tenant especial `INTERNAL_LAB`
- Permite modelos no aprobados (`allowed_in_prod=false`)
- Pruebas de chat y realtime
- Comparacion de modelos

---

## 4. ESTRATEGIA DE MEMORIA (RAG SIMPLIFICADO)

**DEFINITIVO: Resumenes Automaticos + Full-Text Search**

Sin vector stores externos. Usamos:
1. Chunking inteligente de documentos
2. Resumenes generados por GPT
3. Full-text search en PostgreSQL
4. Keywords y topics extraidos

```sql
-- Documentos
CREATE TABLE documents (
    id VARCHAR PRIMARY KEY,
    tenant_id VARCHAR NOT NULL,
    agent_id VARCHAR,
    name VARCHAR NOT NULL,
    content TEXT,
    content_hash VARCHAR UNIQUE
);

-- Chunks
CREATE TABLE document_chunks (
    id VARCHAR PRIMARY KEY,
    document_id VARCHAR REFERENCES documents(id),
    chunk_index INTEGER,
    content TEXT,
    word_count INTEGER
);

-- Resumenes de chunks
CREATE TABLE chunk_summaries (
    id VARCHAR PRIMARY KEY,
    chunk_id VARCHAR REFERENCES document_chunks(id),
    summary TEXT,
    keywords TEXT[],
    topics TEXT[]
);
```

---

## 5. TRACKING DE TOKENS

```sql
CREATE TABLE token_usage (
    id VARCHAR PRIMARY KEY,
    tenant_id VARCHAR NOT NULL,
    agent_id VARCHAR,
    model VARCHAR NOT NULL,
    input_tokens INTEGER DEFAULT 0,
    output_tokens INTEGER DEFAULT 0,
    reasoning_tokens INTEGER DEFAULT 0,
    total_tokens INTEGER DEFAULT 0,
    total_cost DECIMAL(10,6),
    created_at TIMESTAMP DEFAULT NOW()
);
```

**Umbrales automaticos:**
- 75% → Warning (email)
- 90% → Critical (email + dashboard)
- 100% → Suspension automatica (opcional)

---

## 6. ORDEN DE DESARROLLO

| Fase | Semana | Entregable |
|------|--------|------------|
| **1. Core** | 1 | FastAPI + DB + Auth basico |
| **2. Auth** | 2 | JWT, login, registro, refresh |
| **3. Multi-tenant** | 3 | Tenants, Agents, isolation |
| **4. AI Providers** | 4 | Proveedores dinamicos, AI Engine |
| **5. Chat** | 5 | Chat con streaming, tokens |
| **6. RAG** | 6 | Documentos, resumenes, busqueda |
| **7. Billing** | 7 | Transbank, suscripciones |
| **8-9. Frontend** | 8-9 | Panel tenant completo |
| **10. Admin** | 10 | Panel admin + AI Lab |
| **11-12. Produccion** | 11-12 | Tests, CI/CD, monitoring |

---

## 7. ENDPOINTS PRINCIPALES

```
# Auth
POST   /api/v1/auth/login
POST   /api/v1/auth/register
POST   /api/v1/auth/refresh

# Tenants (Admin)
GET    /api/v1/tenants
POST   /api/v1/tenants
GET    /api/v1/tenants/:id

# Agents (Tenant)
GET    /api/v1/agents
POST   /api/v1/agents
PUT    /api/v1/agents/:id

# Chat
POST   /api/v1/chat/completions
POST   /api/v1/chat/stream

# Documents
POST   /api/v1/documents/upload
GET    /api/v1/documents

# Usage
GET    /api/v1/usage/summary
GET    /api/v1/usage/history

# AI Lab (Admin)
GET    /api/v1/ai-lab/providers
GET    /api/v1/ai-lab/models
POST   /api/v1/ai-lab/test
```

---

## 8. CONFIGURACION EN CALIENTE

- Todas las configuraciones de AI en BD (no en codigo)
- Cache con TTL de 30-60 segundos
- Endpoint `/admin/config/invalidate-cache` para cambios inmediatos
- Feature flags evaluados en runtime

---

## REFERENCIAS

- [TECHNICAL_SPECIFICATIONS.md](../TECHNICAL_SPECIFICATIONS.md) - Especificaciones detalladas
- [ai_providers_and_routing.md](../ai_providers_and_routing.md) - Sistema de proveedores
- [ai_config_strategy.md](../ai_config_strategy.md) - Estrategia de configuracion
- [docs/architecture/MEMORY_STRATEGY.md](architecture/MEMORY_STRATEGY.md) - RAG simplificado
- [docs/architecture/TOKEN_TRACKING.md](architecture/TOKEN_TRACKING.md) - Tracking de tokens
