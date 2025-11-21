# AIPanel - Especificaciones Tecnicas

**Version:** 1.0.0
**Fecha:** 2025-01-21

---

## TABLA DE CONTENIDOS

1. [Especificaciones de Base de Datos](#1-especificaciones-de-base-de-datos)
2. [Especificaciones de API](#2-especificaciones-de-api)
3. [Especificaciones de Autenticacion](#3-especificaciones-de-autenticacion)
4. [Especificaciones de Modulos](#4-especificaciones-de-modulos)
5. [Integraciones Externas](#5-integraciones-externas)
6. [Tareas Asincronas](#6-tareas-asincronas)
7. [Frontend Specifications](#7-frontend-specifications)

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

## 4. ESPECIFICACIONES DE MODULOS

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

---

## 5. INTEGRACIONES EXTERNAS

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

## 6. TAREAS ASINCRONAS

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

## 7. FRONTEND SPECIFICATIONS

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
