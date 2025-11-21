# AIPanel - Especificaciones Tecnicas

**Version:** 1.0.0
**Fecha:** 2025-01-21

---

## TABLA DE CONTENIDOS

1. [Especificaciones de Base de Datos](#1-especificaciones-de-base-de-datos)
2. [Especificaciones de API](#2-especificaciones-de-api)
3. [Especificaciones de Autenticacion](#3-especificaciones-de-autenticacion)
4. [Tenant Isolation (Aislamiento de Tenants)](#4-tenant-isolation-aislamiento-de-tenants)
5. [Especificaciones de Modulos](#5-especificaciones-de-modulos)
6. [Integraciones Externas](#6-integraciones-externas)
7. [Tareas Asincronas](#7-tareas-asincronas)
8. [Frontend Specifications](#8-frontend-specifications)

---

## 1. ESPECIFICACIONES DE BASE DE DATOS

### Schema Prisma

El schema completo esta en: `database/schema.prisma`

### Tablas Principales

**users (Administradores - Nivel 1):**
```sql
CREATE TABLE users (
    id VARCHAR PRIMARY KEY,
    email VARCHAR UNIQUE NOT NULL,
    password VARCHAR NOT NULL,  -- bcrypt hashed
    name VARCHAR NOT NULL,
    role VARCHAR NOT NULL,  -- SUPER_ADMIN, ADMIN, SUPPORT
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);
```

**tenants (Clientes - Nivel 2):**
```sql
CREATE TABLE tenants (
    id VARCHAR PRIMARY KEY,
    server_id VARCHAR REFERENCES servers(id),
    name VARCHAR NOT NULL,
    email VARCHAR UNIQUE NOT NULL,
    api_key VARCHAR UNIQUE NOT NULL,  -- encrypted
    status VARCHAR NOT NULL,  -- ACTIVE, SUSPENDED, TRIAL, BLOCKED
    subscription_status VARCHAR,
    subscription_plan VARCHAR,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);
```

**tenant_users (Usuarios de tenants):**
```sql
CREATE TABLE tenant_users (
    id VARCHAR PRIMARY KEY,
    tenant_id VARCHAR REFERENCES tenants(id),
    email VARCHAR UNIQUE NOT NULL,
    password VARCHAR NOT NULL,
    name VARCHAR NOT NULL,
    role VARCHAR NOT NULL,  -- OWNER, ADMIN, DEVELOPER, VIEWER
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);
```

**agents (Agentes AI):**
```sql
CREATE TABLE agents (
    id VARCHAR PRIMARY KEY,
    tenant_id VARCHAR REFERENCES tenants(id),
    name VARCHAR NOT NULL,
    description TEXT,
    model VARCHAR NOT NULL,  -- GPT5_MINI, CLAUDE_SONNET_4_5, etc
    system_prompt TEXT NOT NULL,
    temperature FLOAT,
    max_tokens INTEGER,
    status VARCHAR DEFAULT 'ACTIVE',
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);
```

**documents (Documentos para RAG):**
```sql
CREATE TABLE documents (
    id VARCHAR PRIMARY KEY,
    tenant_id VARCHAR REFERENCES tenants(id),
    agent_id VARCHAR REFERENCES agents(id),
    name VARCHAR NOT NULL,
    type VARCHAR NOT NULL,  -- pdf, url, docx, txt, image
    content TEXT NOT NULL,  -- texto extraido
    content_hash VARCHAR UNIQUE,  -- SHA256
    size INTEGER NOT NULL,
    status VARCHAR DEFAULT 'PENDING',
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);
```

**document_chunks (Chunks de documentos):**
```sql
CREATE TABLE document_chunks (
    id VARCHAR PRIMARY KEY,
    document_id VARCHAR REFERENCES documents(id),
    chunk_index INTEGER NOT NULL,
    content TEXT NOT NULL,
    word_count INTEGER NOT NULL,
    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(document_id, chunk_index)
);
```

**chunk_summaries (Resumenes de chunks):**
```sql
CREATE TABLE chunk_summaries (
    id VARCHAR PRIMARY KEY,
    chunk_id VARCHAR UNIQUE REFERENCES document_chunks(id),
    summary TEXT NOT NULL,
    keywords TEXT[] NOT NULL,
    topics TEXT[] NOT NULL,
    model VARCHAR NOT NULL,
    tokens_used INTEGER NOT NULL,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_chunk_summaries_keywords ON chunk_summaries USING GIN(keywords);
CREATE INDEX idx_chunk_summaries_topics ON chunk_summaries USING GIN(topics);
```

**token_usage (Tracking de tokens):**
```sql
CREATE TABLE token_usage (
    id VARCHAR PRIMARY KEY,
    request_id VARCHAR UNIQUE NOT NULL,
    tenant_id VARCHAR REFERENCES tenants(id),
    agent_id VARCHAR REFERENCES agents(id),
    model VARCHAR NOT NULL,
    input_tokens INTEGER DEFAULT 0,
    output_tokens INTEGER DEFAULT 0,
    reasoning_tokens INTEGER DEFAULT 0,
    cached_tokens INTEGER DEFAULT 0,
    total_tokens INTEGER DEFAULT 0,
    input_cost DECIMAL(10,6),
    output_cost DECIMAL(10,6),
    reasoning_cost DECIMAL(10,6),
    cache_cost DECIMAL(10,6),
    total_cost DECIMAL(10,6),
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_token_usage_tenant ON token_usage(tenant_id, created_at);
CREATE INDEX idx_token_usage_agent ON token_usage(agent_id, created_at);
```

**subscriptions (Suscripciones de tenants):**
```sql
CREATE TABLE subscriptions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,

    -- Plan y estado
    plan VARCHAR(50) NOT NULL,  -- 'basico', 'pro', 'enterprise'
    status VARCHAR(50) NOT NULL,  -- 'active', 'trialing', 'past_due', 'canceled', 'suspended'

    -- Precios (en CLP)
    base_price INTEGER NOT NULL,
    currency VARCHAR(3) DEFAULT 'CLP',

    -- Cuotas incluidas
    included_memory_gb DECIMAL(10,2) NOT NULL,
    included_tokens INTEGER NOT NULL,
    included_agents INTEGER NOT NULL,
    included_users INTEGER NOT NULL,

    -- Ciclo de facturacion
    billing_cycle VARCHAR(20) DEFAULT 'monthly',
    billing_period_start DATE NOT NULL,
    billing_period_end DATE NOT NULL,
    next_billing_date DATE NOT NULL,

    -- Trial
    trial_start TIMESTAMPTZ,
    trial_end TIMESTAMPTZ,

    -- Cancelacion
    canceled_at TIMESTAMPTZ,
    cancellation_reason TEXT,

    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_subscriptions_tenant_id ON subscriptions(tenant_id);
CREATE INDEX idx_subscriptions_status ON subscriptions(status);
CREATE INDEX idx_subscriptions_next_billing ON subscriptions(next_billing_date);
```

**invoices (Facturas):**
```sql
CREATE TABLE invoices (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES tenants(id),
    subscription_id UUID REFERENCES subscriptions(id),

    invoice_number VARCHAR(50) UNIQUE NOT NULL,
    status VARCHAR(50) NOT NULL,  -- 'draft', 'pending', 'paid', 'failed', 'refunded'

    -- Montos en CLP
    subtotal INTEGER NOT NULL,
    tax INTEGER DEFAULT 0,
    total INTEGER NOT NULL,
    amount_paid INTEGER DEFAULT 0,
    amount_due INTEGER NOT NULL,

    -- Periodo facturado
    period_start DATE NOT NULL,
    period_end DATE NOT NULL,

    -- Fechas
    issue_date DATE NOT NULL,
    due_date DATE NOT NULL,
    paid_at TIMESTAMPTZ,

    -- Transbank
    transbank_token VARCHAR(255),
    transbank_order_id VARCHAR(100),

    -- SII Chile
    sii_folio INTEGER,
    sii_pdf_url TEXT,
    sii_xml_url TEXT,

    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_invoices_tenant_id ON invoices(tenant_id);
CREATE INDEX idx_invoices_status ON invoices(status);
CREATE INDEX idx_invoices_issue_date ON invoices(issue_date);
CREATE INDEX idx_invoices_due_date ON invoices(due_date);
CREATE UNIQUE INDEX idx_invoices_number ON invoices(invoice_number);
```

**invoice_line_items (Detalle de facturas):**
```sql
CREATE TABLE invoice_line_items (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    invoice_id UUID NOT NULL REFERENCES invoices(id) ON DELETE CASCADE,

    description TEXT NOT NULL,
    item_type VARCHAR(50) NOT NULL,  -- 'base_plan', 'memory_overage', 'token_overage', 'addon', 'service'

    quantity DECIMAL(10,2) DEFAULT 1,
    unit_price INTEGER NOT NULL,
    amount INTEGER NOT NULL,

    metadata JSONB,

    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_line_items_invoice_id ON invoice_line_items(invoice_id);
CREATE INDEX idx_line_items_type ON invoice_line_items(item_type);
```

**payments (Pagos recibidos):**
```sql
CREATE TABLE payments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES tenants(id),
    invoice_id UUID REFERENCES invoices(id),

    amount INTEGER NOT NULL,
    currency VARCHAR(3) DEFAULT 'CLP',
    status VARCHAR(50) NOT NULL,  -- 'pending', 'completed', 'failed', 'refunded'

    payment_method VARCHAR(50),  -- 'transbank_webpay', 'transfer', 'khipu'

    -- Transbank
    transbank_transaction_id VARCHAR(255),
    transbank_authorization_code VARCHAR(100),
    transbank_card_type VARCHAR(50),
    transbank_card_last4 VARCHAR(4),

    receipt_url TEXT,

    paid_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_payments_tenant_id ON payments(tenant_id);
CREATE INDEX idx_payments_invoice_id ON payments(invoice_id);
CREATE INDEX idx_payments_status ON payments(status);
CREATE INDEX idx_payments_paid_at ON payments(paid_at);
```

**revenue_events (Eventos de ingresos para analytics):**
```sql
CREATE TABLE revenue_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES tenants(id),

    event_type VARCHAR(50) NOT NULL,  -- 'subscription_started', 'upgraded', 'downgraded', 'canceled', 'payment_received', 'overage_charged'

    amount INTEGER NOT NULL,
    mrr_change INTEGER DEFAULT 0,

    description TEXT,
    metadata JSONB,

    occurred_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_revenue_events_tenant_id ON revenue_events(tenant_id);
CREATE INDEX idx_revenue_events_type ON revenue_events(event_type);
CREATE INDEX idx_revenue_events_occurred_at ON revenue_events(occurred_at);
```

### Indices Importantes

```sql
-- Full-text search indices
CREATE INDEX idx_chunks_fulltext ON document_chunks
USING GIN(to_tsvector('spanish', content));

CREATE INDEX idx_summaries_fulltext ON chunk_summaries
USING GIN(to_tsvector('spanish', summary));

-- Performance indices
CREATE INDEX idx_agents_tenant ON agents(tenant_id);
CREATE INDEX idx_documents_tenant ON documents(tenant_id);
CREATE INDEX idx_documents_hash ON documents(content_hash);
```

---

## 2. ESPECIFICACIONES DE API

### Convencion de Endpoints

**Base URL:** `/api/v1`

**Formato:**
- GET `/api/v1/resource` - Listar todos
- GET `/api/v1/resource/{id}` - Obtener por ID
- POST `/api/v1/resource` - Crear nuevo
- PUT `/api/v1/resource/{id}` - Actualizar
- DELETE `/api/v1/resource/{id}` - Eliminar

### Endpoints Requeridos

#### Autenticacion

```
POST   /api/v1/auth/login
POST   /api/v1/auth/register
POST   /api/v1/auth/refresh
POST   /api/v1/auth/logout
GET    /api/v1/auth/me
```

#### Tenants

```
GET    /api/v1/tenants
GET    /api/v1/tenants/{id}
POST   /api/v1/tenants
PUT    /api/v1/tenants/{id}
DELETE /api/v1/tenants/{id}
POST   /api/v1/tenants/{id}/api-key/rotate
```

#### Agentes

```
GET    /api/v1/agents
GET    /api/v1/agents/{id}
POST   /api/v1/agents
PUT    /api/v1/agents/{id}
DELETE /api/v1/agents/{id}
GET    /api/v1/agents/{id}/stats
```

#### Chat

```
POST   /api/v1/chat/completions
POST   /api/v1/chat/stream          # Server-Sent Events
GET    /api/v1/chat/conversations
GET    /api/v1/chat/conversations/{id}
GET    /api/v1/chat/conversations/{id}/messages
```

#### Documentos

```
GET    /api/v1/documents
GET    /api/v1/documents/{id}
POST   /api/v1/documents/upload
DELETE /api/v1/documents/{id}
GET    /api/v1/documents/{id}/summaries
POST   /api/v1/documents/{id}/reprocess
```

#### Busqueda

```
POST   /api/v1/search/query
GET    /api/v1/search/suggestions
```

#### Pagos (Transbank)

```
POST   /api/v1/payments/subscribe
GET    /api/v1/payments/confirm
POST   /api/v1/payments/webhooks/transbank
GET    /api/v1/payments/invoices
GET    /api/v1/payments/invoices/{id}
```

#### Uso y Metricas

```
GET    /api/v1/usage/current
GET    /api/v1/usage/history
GET    /api/v1/usage/by-agent
GET    /api/v1/usage/by-model
GET    /api/v1/usage/thresholds
PUT    /api/v1/usage/thresholds
```

#### Monitoring

```
GET    /health
GET    /ready
GET    /metrics              # Prometheus metrics
```

### Formato de Respuestas

**Success Response:**
```json
{
  "id": "usr_123",
  "email": "user@example.com",
  "name": "John Doe",
  "created_at": "2025-01-21T10:00:00Z"
}
```

**Error Response:**
```json
{
  "detail": "User not found",
  "status_code": 404
}
```

**List Response:**
```json
{
  "items": [
    {"id": "1", "name": "Item 1"},
    {"id": "2", "name": "Item 2"}
  ],
  "total": 2,
  "page": 1,
  "per_page": 10
}
```

---

## 3. ESPECIFICACIONES DE AUTENTICACION

### JWT Token Structure

**Access Token (15 minutos):**
```json
{
  "sub": "user_123",
  "email": "user@example.com",
  "role": "ADMIN",
  "type": "admin",
  "tenant_id": null,
  "exp": 1674297600,
  "iat": 1674296700
}
```

**Refresh Token (7 dias):**
```json
{
  "sub": "user_123",
  "type": "refresh",
  "exp": 1674901500,
  "iat": 1674296700
}
```

### Flujo de Autenticacion

```
1. Login
   POST /api/v1/auth/login
   Body: { email, password }
   Response: { access_token, refresh_token, user }

2. Request con Token
   GET /api/v1/agents
   Header: Authorization: Bearer <access_token>

3. Refresh Token
   POST /api/v1/auth/refresh
   Body: { refresh_token }
   Response: { access_token, refresh_token }

4. Logout
   POST /api/v1/auth/logout
   Header: Authorization: Bearer <access_token>
```

### Password Hashing

- Usar bcrypt con salt rounds = 12
- NUNCA guardar passwords en texto plano

```python
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Hash password
hashed = pwd_context.hash("plain_password")

# Verify password
is_valid = pwd_context.verify("plain_password", hashed)
```

---

## 4. TENANT ISOLATION (AISLAMIENTO DE TENANTS)

### Resumen

AIPanel es una plataforma **multi-tenant** donde cada cliente (tenant) debe tener sus datos completamente aislados de otros clientes. El aislamiento se implementa en multiples capas: base de datos, API, almacenamiento, cache, procesamiento y logs.

### 4.1. Aislamiento a Nivel de Base de Datos

**Estrategia: Shared Database + Discriminator Column**

Todas las tablas que contienen datos de tenants incluyen la columna `tenant_id`:

```sql
-- Ejemplo: tabla agents
CREATE TABLE agents (
    id UUID PRIMARY KEY,
    tenant_id UUID NOT NULL REFERENCES tenants(id),
    name VARCHAR(255),
    model VARCHAR(50),
    -- ...
    CONSTRAINT fk_tenant FOREIGN KEY (tenant_id) REFERENCES tenants(id) ON DELETE CASCADE
);

-- Indice para optimizar queries por tenant
CREATE INDEX idx_agents_tenant_id ON agents(tenant_id);

-- Similar para todas las tablas multi-tenant
CREATE INDEX idx_documents_tenant_id ON documents(tenant_id);
CREATE INDEX idx_chats_tenant_id ON chats(tenant_id);
CREATE INDEX idx_messages_tenant_id ON messages(tenant_id);
CREATE INDEX idx_usage_logs_tenant_id ON usage_logs(tenant_id);
```

**Todas las queries DEBEN incluir tenant_id:**

```python
# CORRECTO
agents = await db.query(Agent).filter(
    Agent.tenant_id == current_tenant_id
).all()

# INCORRECTO - Falta filtro por tenant
agents = await db.query(Agent).all()  # DANGER: Expone datos de otros tenants
```

### 4.2. Row-Level Security (RLS) - Opcional

Para mayor seguridad, se puede implementar RLS en PostgreSQL:

```sql
-- Habilitar RLS en tablas
ALTER TABLE agents ENABLE ROW LEVEL SECURITY;
ALTER TABLE documents ENABLE ROW LEVEL SECURITY;
ALTER TABLE chats ENABLE ROW LEVEL SECURITY;

-- Politica: Solo ver registros del propio tenant
CREATE POLICY tenant_isolation_policy ON agents
    USING (tenant_id = current_setting('app.current_tenant_id')::uuid);

CREATE POLICY tenant_isolation_policy ON documents
    USING (tenant_id = current_setting('app.current_tenant_id')::uuid);

-- En cada request, configurar tenant_id
-- (esto se hace en middleware)
await db.execute(
    f"SET LOCAL app.current_tenant_id = '{tenant_id}'"
)
```

**Ventajas de RLS:**
- Proteccion a nivel de BD (incluso si el codigo tiene bugs)
- Imposible acceder a datos de otros tenants desde SQL

**Desventajas:**
- Overhead adicional (~5-10% performance)
- Complejidad adicional en debugging

**Recomendacion:** Implementar RLS en produccion para plan Enterprise.

### 4.3. Aislamiento a Nivel de API

**Middleware de Tenant Injection:**

Todos los requests autenticados deben inyectar el `tenant_id` del usuario en el contexto del request:

```python
# backend/app/middleware/tenant_middleware.py

from fastapi import Request
from app.core.auth import get_current_user

async def tenant_isolation_middleware(request: Request, call_next):
    """Middleware que inyecta tenant_id en el request."""

    # Obtener usuario del token JWT
    user = await get_current_user(request)

    if user:
        # Usuarios nivel 2 (tenant_users) tienen tenant_id
        if hasattr(user, 'tenant_id'):
            request.state.tenant_id = user.tenant_id

        # Usuarios nivel 1 (admins) NO tienen tenant_id
        else:
            request.state.tenant_id = None

    response = await call_next(request)
    return response
```

**Dependency para extraer tenant_id:**

```python
# backend/app/core/dependencies.py

from fastapi import Depends, HTTPException, status, Request

async def get_current_tenant_id(request: Request) -> str:
    """Extrae tenant_id del request (inyectado por middleware)."""

    tenant_id = getattr(request.state, 'tenant_id', None)

    if not tenant_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tenant context available"
        )

    return tenant_id
```

**Uso en endpoints:**

```python
# backend/app/modules/agents/router.py

from app.core.dependencies import get_current_tenant_id

@router.get("/agents")
async def list_agents(
    tenant_id: str = Depends(get_current_tenant_id),
    service: AgentService = Depends()
):
    """Lista agentes del tenant actual."""
    return await service.list_agents(tenant_id)
```

### 4.4. Aislamiento en Almacenamiento (S3)

Los archivos subidos por cada tenant se almacenan en paths separados:

```
s3://aipanel-documents/
  ├── tenant_<tenant_id_1>/
  │   ├── documents/
  │   │   ├── <document_id>.pdf
  │   │   ├── <document_id>.png
  │   ├── agents/
  │   │   ├── <agent_id>/
  │   │   │   ├── <file_id>.pdf
  │   ├── exports/
  │       ├── <export_id>.zip
  ├── tenant_<tenant_id_2>/
      ├── documents/
      │   ├── ...
```

**Generacion de paths con tenant_id:**

```python
# backend/app/core/storage.py

def get_s3_path(tenant_id: str, file_type: str, file_id: str, extension: str) -> str:
    """Genera path de S3 con aislamiento por tenant."""
    return f"tenant_{tenant_id}/{file_type}/{file_id}.{extension}"

# Ejemplo
path = get_s3_path(tenant_id="123", file_type="documents", file_id="doc_456", extension="pdf")
# Resultado: "tenant_123/documents/doc_456.pdf"
```

**Pre-signed URLs con validacion:**

```python
def get_presigned_url(s3_path: str, tenant_id: str, expires_in: int = 3600) -> str:
    """Genera URL firmada validando que el path pertenece al tenant."""

    # Validar que el path comienza con tenant_id correcto
    if not s3_path.startswith(f"tenant_{tenant_id}/"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied to resource"
        )

    url = s3_client.generate_presigned_url(
        'get_object',
        Params={'Bucket': settings.S3_BUCKET_NAME, 'Key': s3_path},
        ExpiresIn=expires_in
    )

    return url
```

### 4.5. Aislamiento en Cache (Redis)

Las claves de Redis deben incluir el `tenant_id` como prefijo:

```python
# backend/app/core/cache.py

import redis
from app.core.config import settings

redis_client = redis.from_url(settings.REDIS_URL)

def cache_key(tenant_id: str, key_type: str, identifier: str) -> str:
    """Genera clave de Redis con tenant isolation."""
    return f"tenant:{tenant_id}:{key_type}:{identifier}"

# Ejemplo de uso
def get_agent_from_cache(tenant_id: str, agent_id: str):
    """Obtiene agente desde cache."""
    key = cache_key(tenant_id, "agent", agent_id)
    data = redis_client.get(key)
    return json.loads(data) if data else None

def set_agent_cache(tenant_id: str, agent_id: str, data: dict, ttl: int = 3600):
    """Guarda agente en cache."""
    key = cache_key(tenant_id, "agent", agent_id)
    redis_client.setex(key, ttl, json.dumps(data))
```

**Estructura de claves:**
```
tenant:123:agent:456            # Agente 456 del tenant 123
tenant:123:chat:789             # Chat 789 del tenant 123
tenant:123:usage:2025-01        # Uso del tenant 123 en enero 2025
tenant:456:agent:789            # Agente 789 del tenant 456 (diferente)
```

### 4.6. Aislamiento en Tareas Asincronas (Celery)

Todas las tareas Celery deben recibir `tenant_id` como parametro:

```python
# backend/app/modules/documents/tasks.py

from app.core.celery import celery_app

@celery_app.task(name="process_document")
def process_document_task(document_id: str, tenant_id: str):
    """Procesa documento asegurandose de usar tenant_id correcto."""

    logger.info(f"Processing document {document_id} for tenant {tenant_id}")

    # Cargar documento
    document = db.query(Document).filter(
        Document.id == document_id,
        Document.tenant_id == tenant_id  # IMPORTANTE: Validar tenant
    ).first()

    if not document:
        logger.error(f"Document {document_id} not found for tenant {tenant_id}")
        return

    # Procesar...
    # ...
```

**Al lanzar tareas:**

```python
# En el servicio
from app.modules.documents.tasks import process_document_task

def upload_document(file: UploadFile, tenant_id: str, agent_id: str):
    # ... guardar documento ...

    # Lanzar tarea con tenant_id
    process_document_task.delay(
        document_id=str(document.id),
        tenant_id=tenant_id  # Pasar tenant_id explicitamente
    )
```

### 4.7. Aislamiento en Logs y Auditoria

Todos los logs deben incluir `tenant_id` para auditoria:

```python
# backend/app/utils/logger.py

import logging
from pythonjsonlogger import jsonlogger

# Configurar logger con formato JSON
logger = logging.getLogger("aipanel")
handler = logging.StreamHandler()
formatter = jsonlogger.JsonFormatter(
    "%(asctime)s %(name)s %(levelname)s %(message)s %(tenant_id)s %(user_id)s"
)
handler.setFormatter(formatter)
logger.addHandler(handler)

# Uso en servicios
def log_action(tenant_id: str, user_id: str, action: str, details: dict):
    """Log de accion con contexto de tenant."""
    logger.info(
        action,
        extra={
            'tenant_id': tenant_id,
            'user_id': user_id,
            'details': details
        }
    )
```

**Tabla de auditoria:**

```sql
CREATE TABLE audit_logs (
    id UUID PRIMARY KEY,
    tenant_id UUID NOT NULL REFERENCES tenants(id),
    user_id UUID,  -- puede ser user o tenant_user
    action VARCHAR(100) NOT NULL,  -- 'agent.created', 'document.uploaded', etc
    resource_type VARCHAR(50),     -- 'agent', 'document', 'chat'
    resource_id UUID,
    details JSONB,
    ip_address INET,
    user_agent TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_audit_logs_tenant_id ON audit_logs(tenant_id);
CREATE INDEX idx_audit_logs_created_at ON audit_logs(created_at);
```

### 4.8. Rate Limiting por Tenant

Cada tenant tiene limites de requests por minuto segun su plan:

```python
# backend/app/middleware/rate_limit_middleware.py

from fastapi import HTTPException, status
from app.core.cache import redis_client

async def rate_limit_middleware(request: Request, call_next):
    """Middleware de rate limiting por tenant."""

    tenant_id = getattr(request.state, 'tenant_id', None)

    if tenant_id:
        # Obtener limite del plan del tenant
        tenant = await get_tenant(tenant_id)
        limit = get_rate_limit_for_plan(tenant.plan)  # ej: 20 req/min

        # Clave de Redis para contador
        key = f"ratelimit:tenant:{tenant_id}:minute"

        # Incrementar contador
        current = redis_client.incr(key)

        # Establecer TTL de 60 segundos en primera request
        if current == 1:
            redis_client.expire(key, 60)

        # Verificar limite
        if current > limit:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Rate limit exceeded ({limit} requests/minute)"
            )

    response = await call_next(request)
    return response

def get_rate_limit_for_plan(plan: str) -> int:
    """Retorna limite de requests por minuto segun plan."""
    limits = {
        'basico': 5,
        'pro': 20,
        'enterprise': 100
    }
    return limits.get(plan, 5)
```

### 4.9. Calculo de Uso por Tenant

Sistema de metering para calcular uso de recursos:

```python
# backend/app/modules/usage/service.py

from datetime import datetime
from app.models import UsageLog

async def track_usage(
    tenant_id: str,
    resource_type: str,  # 'tokens', 'storage', 'api_calls'
    amount: int,
    metadata: dict = None
):
    """Registra uso de recursos por tenant."""

    usage_log = UsageLog(
        tenant_id=tenant_id,
        resource_type=resource_type,
        amount=amount,
        metadata=metadata,
        timestamp=datetime.now()
    )

    await db.add(usage_log)
    await db.commit()

    # Actualizar cache de uso mensual
    month_key = f"usage:tenant:{tenant_id}:{resource_type}:{datetime.now().strftime('%Y-%m')}"
    redis_client.incr(month_key, amount)

async def get_monthly_usage(tenant_id: str, resource_type: str) -> int:
    """Obtiene uso mensual de un tenant."""

    month_key = f"usage:tenant:{tenant_id}:{resource_type}:{datetime.now().strftime('%Y-%m')}"
    cached = redis_client.get(month_key)

    if cached:
        return int(cached)

    # Si no esta en cache, calcular desde BD
    start_of_month = datetime.now().replace(day=1, hour=0, minute=0, second=0)

    total = await db.query(func.sum(UsageLog.amount)).filter(
        UsageLog.tenant_id == tenant_id,
        UsageLog.resource_type == resource_type,
        UsageLog.timestamp >= start_of_month
    ).scalar()

    return total or 0
```

### 4.10. Checklist de Tenant Isolation

Al implementar nuevas features, verificar:

- [ ] Todas las tablas multi-tenant tienen columna `tenant_id`
- [ ] Todos los queries incluyen filtro por `tenant_id`
- [ ] Los endpoints usan `get_current_tenant_id()` dependency
- [ ] Los paths de S3 incluyen `tenant_<tenant_id>/`
- [ ] Las claves de Redis incluyen `tenant:<tenant_id>:`
- [ ] Las tareas Celery reciben `tenant_id` como parametro
- [ ] Los logs incluyen `tenant_id` en contexto
- [ ] Se valida que el usuario tiene acceso al tenant
- [ ] Se aplica rate limiting por tenant
- [ ] Se trackea uso de recursos por tenant

### 4.11. Testing de Tenant Isolation

**Test de aislamiento:**

```python
# backend/testing/test_tenant_isolation.py

import pytest

async def test_tenant_cannot_access_other_tenant_agents():
    """Test que un tenant no puede ver agentes de otro tenant."""

    # Crear dos tenants
    tenant1 = await create_tenant("Tenant 1")
    tenant2 = await create_tenant("Tenant 2")

    # Crear agente para tenant1
    agent1 = await create_agent(tenant_id=tenant1.id, name="Agent 1")

    # Crear usuario de tenant2
    user2 = await create_tenant_user(tenant_id=tenant2.id)

    # Autenticar como usuario de tenant2
    token = await login(user2.email, user2.password)

    # Intentar acceder a agente de tenant1
    response = client.get(
        f"/api/v1/agents/{agent1.id}",
        headers={"Authorization": f"Bearer {token}"}
    )

    # Debe retornar 403 o 404 (no 200)
    assert response.status_code in [403, 404]

async def test_tenant_can_only_see_own_documents():
    """Test que un tenant solo ve sus propios documentos."""

    tenant1 = await create_tenant("Tenant 1")
    tenant2 = await create_tenant("Tenant 2")

    # Crear documentos para ambos tenants
    doc1 = await create_document(tenant_id=tenant1.id, name="Doc 1")
    doc2 = await create_document(tenant_id=tenant2.id, name="Doc 2")

    # Autenticar como tenant1
    user1 = await create_tenant_user(tenant_id=tenant1.id)
    token1 = await login(user1.email, user1.password)

    # Listar documentos
    response = client.get(
        "/api/v1/documents",
        headers={"Authorization": f"Bearer {token1}"}
    )

    documents = response.json()

    # Solo debe ver doc1, no doc2
    assert len(documents) == 1
    assert documents[0]['id'] == str(doc1.id)
```

---

## 5. ESPECIFICACIONES DE MODULOS

### Modulo: Auth

**Responsabilidad:** Autenticacion y autorizacion de usuarios

**Archivos:**
- `modules/auth/router.py` - Endpoints de login, register, refresh
- `modules/auth/service.py` - Logica de autenticacion
- `modules/auth/schemas.py` - LoginRequest, RegisterRequest, AuthResponse
- `modules/auth/models.py` - User, RefreshToken models

**Funcionalidades:**
- Login con email/password
- Registro de nuevos usuarios
- Refresh token rotation
- Logout (invalidar refresh token)
- Get current user

**Tests:**
- `test_login_success`
- `test_login_invalid_credentials`
- `test_register_success`
- `test_register_duplicate_email`
- `test_refresh_token`
- `test_logout`

### Modulo: Tenants

**Responsabilidad:** Gestion de tenants (clientes)

**Archivos:**
- `modules/tenants/router.py`
- `modules/tenants/service.py`
- `modules/tenants/schemas.py`
- `modules/tenants/models.py`

**Funcionalidades:**
- CRUD de tenants
- Generacion de API keys
- Rotacion de API keys
- Activacion/suspension de tenants
- Metricas por tenant

**Tests:**
- `test_create_tenant`
- `test_get_tenants`
- `test_update_tenant`
- `test_rotate_api_key`
- `test_suspend_tenant`

### Modulo: Agents

**Responsabilidad:** Gestion de agentes AI

**Archivos:**
- `modules/agents/router.py`
- `modules/agents/service.py`
- `modules/agents/schemas.py`
- `modules/agents/models.py`

**Funcionalidades:**
- CRUD de agentes
- Configuracion de modelos (GPT, Claude)
- Configuracion de parametros (temperature, max_tokens)
- Activacion/pausa de agentes
- Estadisticas de uso por agente

**Tests:**
- `test_create_agent`
- `test_get_agents`
- `test_update_agent_config`
- `test_pause_agent`
- `test_agent_stats`

### Modulo: Chat

**Responsabilidad:** Chat con agentes AI

**Archivos:**
- `modules/chat/router.py`
- `modules/chat/service.py`
- `modules/chat/streaming.py`
- `modules/chat/schemas.py`

**Funcionalidades:**
- Chat con streaming (SSE)
- Chat sin streaming
- Historial de conversaciones
- Contexto de documentos (RAG)
- Tracking de tokens

**Implementacion de Streaming:**

```python
from fastapi import APIRouter
from fastapi.responses import StreamingResponse

router = APIRouter()

@router.post("/chat/stream")
async def chat_stream(request: ChatRequest):
    async def generate():
        async for chunk in chat_service.stream_chat(request):
            yield f"data: {chunk}\n\n"

    return StreamingResponse(
        generate(),
        media_type="text/event-stream"
    )
```

**Tests:**
- `test_chat_completion`
- `test_chat_streaming`
- `test_chat_with_context`
- `test_conversation_history`

### Modulo: Documents

**Responsabilidad:** Procesamiento de documentos para RAG

**Archivos:**
- `modules/documents/router.py`
- `modules/documents/service.py`
- `modules/documents/processor.py` - Extraccion de texto
- `modules/documents/chunking.py` - Division inteligente
- `modules/documents/summarizer.py` - Generacion de resumenes
- `modules/documents/schemas.py`
- `modules/documents/models.py`

**Funcionalidades:**
- Upload de documentos (PDF, DOCX, TXT)
- Extraccion de texto
- Chunking inteligente
- Generacion de resumenes con GPT
- Indexacion para busqueda

**Proceso de Ingesta:**

```
1. Upload archivo
2. Extraer texto (PyPDF2, python-docx)
3. Calcular hash (detectar duplicados)
4. Dividir en chunks (~500 palabras)
5. Generar resumen de cada chunk (GPT-4o-mini)
6. Generar resumen del documento completo
7. Guardar en BD con indices
```

**Tests:**
- `test_upload_pdf`
- `test_extract_text`
- `test_chunking`
- `test_summarization`
- `test_duplicate_detection`

### Modulo: Search

**Responsabilidad:** Busqueda hibrida de documentos

**Archivos:**
- `modules/search/router.py`
- `modules/search/service.py`
- `modules/search/fulltext.py`

**Funcionalidades:**
- Busqueda full-text (PostgreSQL)
- Busqueda por keywords
- Busqueda por topics
- Ranking de resultados

**Query de Busqueda:**

```sql
SELECT
    ds.id,
    ds.summary,
    ds.keywords,
    d.name as document_name,
    ts_rank(
        to_tsvector('spanish', ds.summary),
        plainto_tsquery('spanish', $query)
    ) as rank
FROM chunk_summaries ds
JOIN document_chunks c ON c.id = ds.chunk_id
JOIN documents d ON d.id = c.document_id
WHERE
    d.tenant_id = $tenant_id
    AND to_tsvector('spanish', ds.summary) @@ plainto_tsquery('spanish', $query)
ORDER BY rank DESC
LIMIT 10;
```

**Tests:**
- `test_search_by_text`
- `test_search_by_keywords`
- `test_search_ranking`
- `test_search_no_results`

### Modulo: Payments

**Responsabilidad:** Integracion con Transbank

**Archivos:**
- `modules/payments/router.py`
- `modules/payments/service.py`
- `modules/payments/transbank.py`
- `modules/payments/webhooks.py`
- `modules/payments/schemas.py`

**Funcionalidades:**
- Crear pago (Webpay Plus)
- Confirmar pago
- Webhooks de Transbank
- Suscripciones (OneClick)
- Historial de pagos

**Flujo de Pago:**

```
1. Usuario hace click en "Suscribirse"
2. Frontend -> POST /api/v1/payments/subscribe
   Body: { plan_id: "pro", amount: 29990 }
3. Backend crea transaccion en Transbank
4. Backend retorna: { token, url }
5. Frontend redirige a url de Transbank
6. Usuario paga en Webpay
7. Transbank redirige a: /payments/confirm?token=xxx
8. Backend -> Transaction.commit(token)
9. Si exitoso: Activar suscripcion de tenant
10. Redirigir a frontend con status
```

**Tests:**
- `test_create_payment`
- `test_confirm_payment_success`
- `test_confirm_payment_failed`
- `test_webhook_payment_success`

### Modulo: Usage

**Responsabilidad:** Tracking de uso de tokens

**Archivos:**
- `modules/usage/router.py`
- `modules/usage/service.py`
- `modules/usage/tracker.py`
- `modules/usage/thresholds.py`
- `modules/usage/models.py`
- `modules/usage/schemas.py`

**Funcionalidades:**
- Track tokens por request
- Calcular costos
- Verificar umbrales
- Alertas automaticas
- Reportes de uso

**Tracking de Tokens:**

```python
async def track_usage(
    tenant_id: str,
    agent_id: str,
    model: str,
    usage: CompletionUsage  # de OpenAI
) -> TokenUsage:
    # Calcular costos segun modelo
    costs = calculate_cost(model, usage)

    # Guardar en BD
    token_usage = await db.token_usage.create({
        "tenant_id": tenant_id,
        "agent_id": agent_id,
        "model": model,
        "input_tokens": usage.prompt_tokens,
        "output_tokens": usage.completion_tokens,
        "reasoning_tokens": usage.reasoning_tokens,
        "total_tokens": usage.total_tokens,
        "total_cost": costs.total
    })

    # Verificar umbrales
    await check_thresholds(tenant_id)

    return token_usage
```

**Tests:**
- `test_track_tokens`
- `test_calculate_cost`
- `test_threshold_warning`
- `test_threshold_suspension`
- `test_usage_report`

### Modulo: Billing (Control de Ingresos)

**Responsabilidad:** Gestion de suscripciones, facturacion y control de ingresos

**Archivos:**
- `modules/billing/router.py` - Endpoints de API
- `modules/billing/subscription_service.py` - Gestion de suscripciones
- `modules/billing/invoice_service.py` - Generacion de facturas
- `modules/billing/revenue_service.py` - Analisis de ingresos
- `modules/billing/alerts_service.py` - Alertas de billing
- `modules/billing/export_service.py` - Exportacion contable
- `modules/billing/models.py` - Modelos de BD
- `modules/billing/schemas.py` - Schemas de validacion

**Funcionalidades:**

1. **Gestion de Suscripciones:**
   - Crear/actualizar/cancelar suscripciones
   - Upgrade/downgrade de planes
   - Gestion de trials
   - Prorrateo automatico

2. **Generacion de Facturas:**
   - Facturacion automatica mensual
   - Calculo de overages (memoria, tokens, usuarios)
   - Integracion con SII Chile (facturacion electronica)
   - Envio de facturas por email

3. **Control de Ingresos:**
   - Dashboard de KPIs (MRR, ARR, churn, ARPT)
   - Reportes por tenant con desglose detallado
   - Serie temporal de ingresos
   - Proyecciones y forecasting
   - Analisis de cohortes

4. **Alertas Automaticas:**
   - Pagos fallidos
   - Oportunidades de upsell
   - Deteccion de churn risk
   - Overages altos

5. **Exportacion:**
   - CSV para contabilidad
   - Excel con reportes ejecutivos
   - Integracion con API SII

**Endpoints Principales:**

```python
# Suscripciones
POST   /api/v1/billing/subscriptions          # Crear suscripcion
GET    /api/v1/billing/subscriptions/:id      # Obtener suscripcion
PATCH  /api/v1/billing/subscriptions/:id      # Actualizar plan
DELETE /api/v1/billing/subscriptions/:id      # Cancelar

# Facturas
GET    /api/v1/billing/invoices               # Listar facturas (con filtros)
GET    /api/v1/billing/invoices/:id           # Detalle de factura
POST   /api/v1/billing/invoices/:id/send      # Enviar por email
GET    /api/v1/billing/invoices/:id/pdf       # Descargar PDF

# Control de Ingresos (Admin Nivel 1)
GET    /api/v1/billing/revenue/summary        # KPIs principales
GET    /api/v1/billing/revenue/by-tenant      # Ingresos por tenant
GET    /api/v1/billing/revenue/timeline       # Serie temporal
GET    /api/v1/billing/revenue/forecast       # Proyecciones
GET    /api/v1/billing/revenue/cohorts        # Analisis de cohortes

# Alertas
GET    /api/v1/billing/alerts                 # Alertas pendientes

# Exportacion
GET    /api/v1/billing/export/csv             # CSV mensual
GET    /api/v1/billing/export/excel           # Reporte ejecutivo
```

**Ejemplo: Generacion de Factura Automatica**

```python
# backend/app/modules/billing/invoice_service.py

from datetime import datetime, timedelta
from app.models import Subscription, Invoice, InvoiceLineItem
from app.modules.billing.revenue_service import RevenueService

class InvoiceService:
    """Servicio para gestion de facturas."""

    async def generate_monthly_invoices(self):
        """Genera facturas para todas las suscripciones activas."""

        today = datetime.now().date()

        # Buscar suscripciones cuya fecha de billing es hoy
        subscriptions = await db.query(Subscription).filter(
            Subscription.status == 'active',
            Subscription.next_billing_date == today
        ).all()

        logger.info(f"Generating invoices for {len(subscriptions)} subscriptions")

        for subscription in subscriptions:
            try:
                await self._generate_invoice_for_subscription(subscription)
            except Exception as e:
                logger.error(f"Failed to generate invoice for {subscription.id}: {e}")

    async def _generate_invoice_for_subscription(
        self,
        subscription: Subscription
    ) -> Invoice:
        """Genera factura para una suscripcion."""

        period_start = subscription.billing_period_start
        period_end = subscription.billing_period_end

        # Generar numero de factura
        invoice_number = await self._generate_invoice_number()

        # Crear factura
        invoice = Invoice(
            tenant_id=subscription.tenant_id,
            subscription_id=subscription.id,
            invoice_number=invoice_number,
            status='pending',
            period_start=period_start,
            period_end=period_end,
            issue_date=datetime.now().date(),
            due_date=(datetime.now() + timedelta(days=15)).date()
        )

        # Linea de plan base
        base_item = InvoiceLineItem(
            invoice_id=invoice.id,
            description=f"Plan {subscription.plan.title()} - {period_start.strftime('%B %Y')}",
            item_type='base_plan',
            quantity=1,
            unit_price=subscription.base_price,
            amount=subscription.base_price
        )

        # Calcular overages
        revenue_service = RevenueService()
        overages = await revenue_service.calculate_overages(subscription.tenant_id)

        overage_items = []
        for overage in overages['overages']:
            item = InvoiceLineItem(
                invoice_id=invoice.id,
                description=overage['description'],
                item_type=f"{overage['type']}_overage",
                quantity=overage['excess'],
                unit_price=int(overage['cost'] / overage['excess']),
                amount=overage['cost']
            )
            overage_items.append(item)

        # Calcular totales
        subtotal = subscription.base_price + overages['total_overage_cost']
        tax = int(subtotal * 0.19)  # IVA 19%
        total = subtotal + tax

        invoice.subtotal = subtotal
        invoice.tax = tax
        invoice.total = total
        invoice.amount_due = total

        # Guardar en BD
        await db.add(invoice)
        await db.add(base_item)
        for item in overage_items:
            await db.add(item)

        await db.commit()

        # Enviar factura por email
        await self._send_invoice_email(invoice)

        # Actualizar proxima fecha de billing
        subscription.billing_period_start = period_end + timedelta(days=1)
        subscription.billing_period_end = subscription.billing_period_start + timedelta(days=30)
        subscription.next_billing_date = subscription.billing_period_end

        await db.commit()

        logger.info(f"Generated invoice {invoice_number} for tenant {subscription.tenant_id}")

        return invoice
```

**Ejemplo: Dashboard de Ingresos**

```python
# backend/app/modules/billing/revenue_service.py

class RevenueService:
    """Servicio para analisis de ingresos."""

    async def get_revenue_summary(
        self,
        from_date: datetime,
        to_date: datetime
    ) -> Dict:
        """Obtiene resumen de ingresos con KPIs principales."""

        # MRR actual
        mrr_result = await db.query(
            func.sum(Subscription.base_price).label('mrr'),
            func.count(Subscription.id).label('count')
        ).filter(
            Subscription.status == 'active'
        ).first()

        current_mrr = mrr_result.mrr or 0
        active_subs = mrr_result.count or 0

        # Total revenue del periodo (incluye overages)
        revenue_result = await db.query(
            func.sum(Invoice.total).label('total')
        ).filter(
            Invoice.status == 'paid',
            Invoice.paid_at >= from_date,
            Invoice.paid_at <= to_date
        ).first()

        total_revenue = revenue_result.total or 0

        # Calcular revenue de overages
        overage_result = await db.query(
            func.sum(InvoiceLineItem.amount).label('total')
        ).join(Invoice).filter(
            InvoiceLineItem.item_type.in_(['memory_overage', 'token_overage', 'user_overage']),
            Invoice.status == 'paid',
            Invoice.paid_at >= from_date,
            Invoice.paid_at <= to_date
        ).first()

        overage_revenue = overage_result.total or 0
        base_revenue = total_revenue - overage_revenue

        # Nuevas y canceladas
        new_subs = await db.query(func.count(Subscription.id)).filter(
            Subscription.created_at >= from_date,
            Subscription.created_at <= to_date
        ).scalar()

        canceled_subs = await db.query(func.count(Subscription.id)).filter(
            Subscription.canceled_at >= from_date,
            Subscription.canceled_at <= to_date
        ).scalar()

        # Churn rate
        churn_rate = (canceled_subs / active_subs * 100) if active_subs > 0 else 0

        # ARPT (Average Revenue Per Tenant)
        arpt = total_revenue / active_subs if active_subs > 0 else 0

        # Distribucion por plan
        by_plan = await db.query(
            Subscription.plan,
            func.count(Subscription.id).label('count'),
            func.sum(Subscription.base_price).label('mrr')
        ).filter(
            Subscription.status == 'active'
        ).group_by(Subscription.plan).all()

        return {
            'period': {
                'from': from_date.isoformat(),
                'to': to_date.isoformat()
            },
            'metrics': {
                'mrr': current_mrr,
                'arr': current_mrr * 12,
                'total_revenue': total_revenue,
                'base_revenue': base_revenue,
                'overage_revenue': overage_revenue,
                'active_subscriptions': active_subs,
                'new_subscriptions': new_subs,
                'canceled_subscriptions': canceled_subs,
                'churn_rate': round(churn_rate, 2),
                'average_revenue_per_tenant': int(arpt)
            },
            'by_plan': {
                plan.plan: {
                    'count': plan.count,
                    'mrr': plan.mrr
                }
                for plan in by_plan
            }
        }

    async def get_revenue_by_tenant(
        self,
        from_date: datetime,
        to_date: datetime,
        page: int = 1,
        per_page: int = 20
    ) -> Dict:
        """Obtiene ingresos desglosados por tenant."""

        # Query compleja con JOIN
        query = db.query(
            Tenant.id,
            Tenant.name,
            Subscription.plan,
            Subscription.base_price.label('mrr'),
            func.sum(Invoice.total).label('total_revenue'),
            func.sum(
                case(
                    (InvoiceLineItem.item_type == 'base_plan', InvoiceLineItem.amount),
                    else_=0
                )
            ).label('base_revenue'),
            func.sum(
                case(
                    (InvoiceLineItem.item_type.in_(['memory_overage', 'token_overage']), InvoiceLineItem.amount),
                    else_=0
                )
            ).label('overage_revenue')
        ).join(Subscription).join(Invoice).join(InvoiceLineItem).filter(
            Invoice.status == 'paid',
            Invoice.paid_at >= from_date,
            Invoice.paid_at <= to_date
        ).group_by(
            Tenant.id,
            Tenant.name,
            Subscription.plan,
            Subscription.base_price
        ).order_by(
            func.sum(Invoice.total).desc()
        ).offset((page - 1) * per_page).limit(per_page)

        tenants = await query.all()

        return {
            'tenants': [
                {
                    'tenant_id': str(t.id),
                    'tenant_name': t.name,
                    'plan': t.plan,
                    'mrr': t.mrr,
                    'total_revenue': t.total_revenue,
                    'base_revenue': t.base_revenue,
                    'overage_revenue': t.overage_revenue
                }
                for t in tenants
            ],
            'page': page,
            'per_page': per_page
        }
```

**Tests:**
- `test_create_subscription`
- `test_upgrade_plan`
- `test_downgrade_plan`
- `test_cancel_subscription`
- `test_generate_invoice`
- `test_calculate_overages`
- `test_revenue_summary`
- `test_revenue_by_tenant`
- `test_payment_failure_alert`
- `test_upsell_opportunity_detection`

**Documentacion Detallada:**
Ver [docs/REVENUE_CONTROL.md](docs/REVENUE_CONTROL.md) para documentacion completa del sistema de control de ingresos.

---

## 6. INTEGRACIONES EXTERNAS

### OpenAI Client

**Archivo:** `integrations/openai_client.py`

**Funcionalidades:**
- Chat completions
- Streaming
- Embeddings (futuro)
- Error handling
- Retry logic

**Implementacion:**

```python
from openai import AsyncOpenAI
from tenacity import retry, stop_after_attempt, wait_exponential

class OpenAIClient:
    def __init__(self, api_key: str):
        self.client = AsyncOpenAI(api_key=api_key)

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10)
    )
    async def chat_completion(
        self,
        model: str,
        messages: list,
        temperature: float = 0.7,
        max_tokens: int = 1000,
        stream: bool = False
    ):
        response = await self.client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            stream=stream
        )

        return response
```

### Anthropic Client

**Archivo:** `integrations/anthropic_client.py`

Similar a OpenAI pero usando SDK de Anthropic.

### Transbank Client

**Archivo:** `integrations/transbank.py`

**Funcionalidades:**
- Crear transaccion
- Confirmar transaccion
- Validar firma de webhooks

**Implementacion:**

```python
from transbank.webpay.webpay_plus.transaction import Transaction

class TransbankClient:
    def __init__(self, env: str, commerce_code: str, api_key: str):
        self.env = env

        if env == "production":
            Transaction.configure_for_production(commerce_code, api_key)
        else:
            Transaction.configure_for_integration(commerce_code, api_key)

    async def create_payment(
        self,
        buy_order: str,
        session_id: str,
        amount: int,
        return_url: str
    ):
        response = Transaction.create(
            buy_order=buy_order,
            session_id=session_id,
            amount=amount,
            return_url=return_url
        )

        return {
            "token": response.token,
            "url": response.url
        }

    async def confirm_payment(self, token: str):
        response = Transaction.commit(token)

        return {
            "status": response.status,
            "amount": response.amount,
            "transaction_id": response.vci
        }
```

### S3 Client (Opcional)

**Archivo:** `integrations/s3_client.py`

Para almacenar documentos en S3.

---

## 7. TAREAS ASINCRONAS

### Celery Configuration

**Archivo:** `tasks/celery.py`

```python
from celery import Celery
from app.core.config import settings

celery_app = Celery(
    "aipanel",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="America/Santiago",
    enable_utc=True,
)
```

### Tareas de Documentos

**Archivo:** `tasks/document_tasks.py`

```python
from app.tasks.celery import celery_app

@celery_app.task(name="process_document")
def process_document(document_id: str):
    """
    Procesar documento:
    1. Extraer texto
    2. Dividir en chunks
    3. Generar resumenes
    4. Indexar
    """
    pass

@celery_app.task(name="generate_summaries")
def generate_summaries(document_id: str):
    """Generar resumenes de chunks usando GPT."""
    pass
```

### Tareas de Billing

**Archivo:** `tasks/billing_tasks.py`

```python
@celery_app.task(name="generate_monthly_invoice")
def generate_monthly_invoice(tenant_id: str):
    """Generar factura mensual basada en uso."""
    pass

@celery_app.task(name="check_payment_status")
def check_payment_status():
    """Verificar pagos pendientes y suspender si es necesario."""
    pass
```

### Tareas de Email

**Archivo:** `tasks/email_tasks.py`

```python
@celery_app.task(name="send_email")
def send_email(to: str, subject: str, body: str):
    """Enviar email usando SendGrid."""
    pass

@celery_app.task(name="send_threshold_alert")
def send_threshold_alert(tenant_id: str, threshold_type: str):
    """Enviar alerta de umbral excedido."""
    pass
```

---

## 8. FRONTEND SPECIFICATIONS

### Estructura de Rutas

```
app/
├── (auth)/
│   ├── login/
│   └── register/
│
├── (admin)/                    # Panel Admin (Nivel 1)
│   ├── dashboard/
│   ├── servers/
│   ├── tenants/
│   └── analytics/
│
└── (tenant)/                   # Panel Tenant (Nivel 2)
    ├── dashboard/
    ├── agents/
    │   ├── page.tsx
    │   ├── [id]/
    │   └── new/
    ├── playground/
    ├── documents/
    ├── usage/
    └── billing/
```

### Componentes Clave

**AuthProvider:**
```typescript
// lib/auth.tsx
export function AuthProvider({ children }) {
  const [user, setUser] = useState(null)
  const [loading, setLoading] = useState(true)

  // Load user from token
  // Refresh token logic
  // Logout

  return (
    <AuthContext.Provider value={{ user, loading }}>
      {children}
    </AuthContext.Provider>
  )
}
```

**Protected Route:**
```typescript
// components/protected-route.tsx
export function ProtectedRoute({ children, requiredRole }) {
  const { user, loading } = useAuth()

  if (loading) return <LoadingSpinner />
  if (!user) redirect('/login')
  if (requiredRole && user.role !== requiredRole) {
    return <AccessDenied />
  }

  return children
}
```

**API Client:**
```typescript
// lib/api.ts
export class APIClient {
  private baseURL = process.env.NEXT_PUBLIC_API_URL

  async get(endpoint: string) {
    const token = getAccessToken()
    const response = await fetch(`${this.baseURL}${endpoint}`, {
      headers: {
        'Authorization': `Bearer ${token}`
      }
    })
    return response.json()
  }

  async post(endpoint: string, data: any) {
    // Similar implementation
  }
}
```

---

## PRIORIDADES DE IMPLEMENTACION

### Sprint 1 (Semana 1): Core Backend
1. core/database.py
2. core/security.py
3. core/dependencies.py
4. modules/auth/ (completo)

### Sprint 2 (Semana 2): Modulos Basicos
1. modules/tenants/ (completo)
2. modules/agents/ (completo)
3. Tests unitarios

### Sprint 3 (Semana 3): AI Features
1. integrations/openai_client.py
2. modules/chat/ (completo)
3. modules/documents/ (basico)

### Sprint 4 (Semana 4): Payments & Usage
1. integrations/transbank.py
2. modules/payments/ (completo)
3. modules/usage/ (completo)

### Sprint 5-6 (Semana 5-6): Frontend
1. Setup Next.js + Auth
2. Dashboard Admin
3. Dashboard Tenant
4. Playground de chat

---

**Ultima actualizacion:** 2025-01-21
**Version:** 1.0.0
