# AIPanel - Asignacion de Tareas

**Version:** 1.0.0
**Fecha:** 2025-01-21
**Proyecto:** AIPanel

---

## ROADMAP GENERAL

```
Semana 1: Core Backend
Semana 2: Modulos Basicos (Tenants, Agents)
Semana 3: AI Features (Chat, Documents)
Semana 4: Payments & Usage Tracking
Semana 5-6: Frontend
Semana 7: Testing & Deployment
```

---

## SPRINT 1 - CORE BACKEND (Semana 1)

**Objetivo:** Establecer la base del backend con autenticacion funcional

### Tarea 1.1: Database Connection
**Asignado a:** _______________
**Estimacion:** 1 dia
**Prioridad:** ALTA

**Archivos a crear:**
- [ ] `backend/app/core/database.py`

**Requisitos:**
- Configurar SQLAlchemy 2.0 con asyncio
- Pool de conexiones
- Session management
- Base class para modelos
- Dependency injection para FastAPI

**Criterios de aceptacion:**
- Conexion exitosa a PostgreSQL
- Pool de conexiones configurado
- Dependency `get_db()` funcional
- Script de debug ejecuta sin errores

**Codigo de referencia:**
```python
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, declarative_base

engine = create_async_engine(settings.DATABASE_URL, echo=settings.DATABASE_ECHO)
AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
Base = declarative_base()

async def get_db():
    async with AsyncSessionLocal() as session:
        yield session
```

---

### Tarea 1.2: Security Module
**Asignado a:** _______________
**Estimacion:** 1 dia
**Prioridad:** ALTA

**Archivos a crear:**
- [ ] `backend/app/core/security.py`

**Requisitos:**
- Password hashing con bcrypt
- JWT token creation
- JWT token validation
- Token refresh logic
- API key generation y encryption

**Funciones requeridas:**
- `hash_password(password: str) -> str`
- `verify_password(plain: str, hashed: str) -> bool`
- `create_access_token(user_id: str, type: str) -> str`
- `create_refresh_token(user_id: str) -> str`
- `verify_token(token: str) -> dict`
- `generate_api_key() -> str`

**Criterios de aceptacion:**
- Tests de hashing pasan
- JWT se genera correctamente
- JWT se valida correctamente
- Tokens expiran segun configuracion

---

### Tarea 1.3: Dependencies
**Asignado a:** _______________
**Estimacion:** 0.5 dias
**Prioridad:** ALTA

**Archivos a crear:**
- [ ] `backend/app/core/dependencies.py`

**Requisitos:**
- Dependency para obtener usuario actual
- Dependency para verificar permisos
- Dependency para obtener tenant actual

**Funciones requeridas:**
- `get_current_user(token: str) -> User`
- `get_current_tenant_user(token: str) -> TenantUser`
- `require_role(role: str) -> Dependency`

**Criterios de aceptacion:**
- Dependency injection funciona en routers
- Errores 401 cuando token invalido
- Errores 403 cuando sin permisos

---

### Tarea 1.4: Auth Module - Complete
**Asignado a:** _______________
**Estimacion:** 2 dias
**Prioridad:** ALTA

**Archivos a completar:**
- [ ] `backend/app/modules/auth/models.py`
- [ ] `backend/app/modules/auth/service.py` (implementar TODOs)
- [ ] `backend/app/modules/auth/router.py` (ya existe)
- [ ] `backend/app/modules/auth/schemas.py` (ya existe)

**Requisitos:**
- Modelo User con SQLAlchemy
- Modelo RefreshToken
- Implementar login completo
- Implementar register completo
- Implementar refresh token
- Implementar logout

**Criterios de aceptacion:**
- Login exitoso retorna tokens validos
- Register crea usuario en BD
- Refresh token renueva access token
- Logout invalida refresh token
- Tests unitarios pasan (test_auth.py)

---

### Tarea 1.5: Migrations Setup
**Asignado a:** _______________
**Estimacion:** 0.5 dias
**Prioridad:** MEDIA

**Archivos a crear:**
- [ ] `backend/alembic.ini`
- [ ] `backend/migrations/env.py`
- [ ] Primera migracion con tabla users

**Requisitos:**
- Configurar Alembic
- Crear migracion inicial
- Script para ejecutar migraciones

**Comandos:**
```bash
alembic init migrations
alembic revision --autogenerate -m "Initial migration"
alembic upgrade head
```

---

## SPRINT 2 - MODULOS BASICOS (Semana 2)

**Objetivo:** Implementar gestion de Tenants y Agents

### Tarea 2.1: Tenants Module
**Asignado a:** _______________
**Estimacion:** 2 dias
**Prioridad:** ALTA

**Archivos a crear:**
- [ ] `backend/app/modules/tenants/__init__.py`
- [ ] `backend/app/modules/tenants/models.py`
- [ ] `backend/app/modules/tenants/schemas.py`
- [ ] `backend/app/modules/tenants/service.py`
- [ ] `backend/app/modules/tenants/router.py`

**Endpoints requeridos:**
- GET /api/v1/tenants
- GET /api/v1/tenants/{id}
- POST /api/v1/tenants
- PUT /api/v1/tenants/{id}
- DELETE /api/v1/tenants/{id}
- POST /api/v1/tenants/{id}/api-key/rotate

**Funcionalidades:**
- CRUD completo
- Generacion de API key automatica
- Rotacion de API key
- Activacion/suspension
- Validacion de API key en requests

**Criterios de aceptacion:**
- Todos los endpoints funcionan
- API key se genera correctamente
- Rotacion invalida key anterior
- Tests unitarios pasan

---

### Tarea 2.2: Agents Module
**Asignado a:** _______________
**Estimacion:** 2 dias
**Prioridad:** ALTA

**Archivos a crear:**
- [ ] `backend/app/modules/agents/__init__.py`
- [ ] `backend/app/modules/agents/models.py`
- [ ] `backend/app/modules/agents/schemas.py`
- [ ] `backend/app/modules/agents/service.py`
- [ ] `backend/app/modules/agents/router.py`

**Endpoints requeridos:**
- GET /api/v1/agents
- GET /api/v1/agents/{id}
- POST /api/v1/agents
- PUT /api/v1/agents/{id}
- DELETE /api/v1/agents/{id}
- GET /api/v1/agents/{id}/stats

**Modelos AI soportados:**
- GPT5_MINI
- GPT5
- GPT_REALTIME_MINI
- CLAUDE_SONNET_4_5
- CLAUDE_OPUS_4

**Criterios de aceptacion:**
- CRUD completo funcional
- Validacion de parametros segun modelo
- Stats retornan metricas de uso
- Tests unitarios pasan

---

### Tarea 2.3: Tests Unitarios
**Asignado a:** _______________
**Estimacion:** 1 dia
**Prioridad:** MEDIA

**Archivos a crear:**
- [ ] `backend/testing/test_tenants.py`
- [ ] `backend/testing/test_agents.py`

**Tests requeridos:**
- Test CRUD de tenants
- Test rotacion de API key
- Test suspension de tenant
- Test CRUD de agents
- Test validacion de parametros
- Test stats de agentes

**Criterios de aceptacion:**
- Coverage > 80%
- Todos los tests pasan
- Tests se ejecutan en <10 segundos

---

## SPRINT 3 - AI FEATURES (Semana 3)

**Objetivo:** Implementar chat con AI y procesamiento de documentos

### Tarea 3.1: OpenAI Client
**Asignado a:** _______________
**Estimacion:** 1 dia
**Prioridad:** ALTA

**Archivos a crear:**
- [ ] `backend/app/integrations/openai_client.py`

**Requisitos:**
- Wrapper del SDK de OpenAI
- Chat completions
- Streaming support
- Retry logic (3 intentos)
- Error handling
- Cost calculation

**Funciones requeridas:**
- `chat_completion(model, messages, **params) -> Response`
- `chat_completion_stream(model, messages, **params) -> AsyncGenerator`
- `calculate_cost(model, usage) -> Cost`

**Criterios de aceptacion:**
- Chat funciona con GPT-5-mini
- Streaming retorna chunks correctamente
- Retry funciona ante errores
- Costos se calculan correctamente

---

### Tarea 3.2: Chat Module
**Asignado a:** _______________
**Estimacion:** 2 dias
**Prioridad:** ALTA

**Archivos a crear:**
- [ ] `backend/app/modules/chat/__init__.py`
- [ ] `backend/app/modules/chat/models.py`
- [ ] `backend/app/modules/chat/schemas.py`
- [ ] `backend/app/modules/chat/service.py`
- [ ] `backend/app/modules/chat/router.py`
- [ ] `backend/app/modules/chat/streaming.py`

**Endpoints requeridos:**
- POST /api/v1/chat/completions
- POST /api/v1/chat/stream
- GET /api/v1/chat/conversations
- GET /api/v1/chat/conversations/{id}
- GET /api/v1/chat/conversations/{id}/messages

**Funcionalidades:**
- Chat con agente especifico
- Streaming via Server-Sent Events
- Historial de conversaciones
- Contexto de documentos (RAG basico)
- Tracking automatico de tokens

**Criterios de aceptacion:**
- Chat retorna respuestas coherentes
- Streaming funciona en frontend
- Historial se guarda correctamente
- Tokens se trackean automaticamente

---

### Tarea 3.3: Documents Module - Basic
**Asignado a:** _______________
**Estimacion:** 2 dias
**Prioridad:** ALTA

**Archivos a crear:**
- [ ] `backend/app/modules/documents/__init__.py`
- [ ] `backend/app/modules/documents/models.py`
- [ ] `backend/app/modules/documents/schemas.py`
- [ ] `backend/app/modules/documents/service.py`
- [ ] `backend/app/modules/documents/router.py`
- [ ] `backend/app/modules/documents/processor.py`

**Endpoints requeridos:**
- GET /api/v1/documents
- POST /api/v1/documents/upload
- DELETE /api/v1/documents/{id}

**Funcionalidades:**
- Upload de PDF
- Extraccion de texto con PyPDF2
- Guardar en BD
- Deteccion de duplicados (hash)

**Criterios de aceptacion:**
- PDFs se procesan correctamente
- Texto se extrae sin errores
- Duplicados se detectan
- Tests con archivo de ejemplo pasan

---

### Tarea 3.4: Documents Module - Summarization
**Asignado a:** _______________
**Estimacion:** 2 dias
**Prioridad:** MEDIA

**Archivos a crear:**
- [ ] `backend/app/modules/documents/chunking.py`
- [ ] `backend/app/modules/documents/summarizer.py`
- [ ] `backend/app/tasks/document_tasks.py`

**Funcionalidades:**
- Chunking inteligente (por parrafos)
- Generacion de resumenes con GPT-4o-mini
- Extraccion de keywords y topics
- Procesamiento asincrono con Celery

**Proceso:**
1. Dividir documento en chunks (~500 palabras)
2. Para cada chunk: generar resumen + keywords
3. Generar resumen del documento completo
4. Guardar en BD con indices

**Criterios de aceptacion:**
- Chunks tienen overlap adecuado
- Resumenes son coherentes
- Keywords son relevantes
- Procesamiento asincrono funciona

---

## SPRINT 4 - PAYMENTS & USAGE (Semana 4)

**Objetivo:** Implementar pagos con Transbank y tracking de uso

### Tarea 4.1: Transbank Client
**Asignado a:** _______________
**Estimacion:** 1 dia
**Prioridad:** ALTA

**Archivos a crear:**
- [ ] `backend/app/integrations/transbank.py`

**Requisitos:**
- Wrapper del SDK de Transbank
- Create transaction (Webpay Plus)
- Commit transaction
- Manejo de errores

**Funciones requeridas:**
- `create_payment(buy_order, amount, return_url) -> {token, url}`
- `confirm_payment(token) -> {status, amount, transaction_id}`

**Criterios de aceptacion:**
- Transaccion se crea correctamente
- URL de pago es valida
- Confirmacion funciona
- Ambiente de integracion funciona con tarjetas de prueba

---

### Tarea 4.2: Payments Module
**Asignado a:** _______________
**Estimacion:** 2 dias
**Prioridad:** ALTA

**Archivos a crear:**
- [ ] `backend/app/modules/payments/__init__.py`
- [ ] `backend/app/modules/payments/models.py`
- [ ] `backend/app/modules/payments/schemas.py`
- [ ] `backend/app/modules/payments/service.py`
- [ ] `backend/app/modules/payments/router.py`
- [ ] `backend/app/modules/payments/webhooks.py`

**Endpoints requeridos:**
- POST /api/v1/payments/subscribe
- GET /api/v1/payments/confirm
- POST /api/v1/payments/webhooks/transbank
- GET /api/v1/payments/invoices

**Funcionalidades:**
- Crear pago de suscripcion
- Confirmar pago y activar tenant
- Recibir webhooks de Transbank
- Listar historial de pagos

**Criterios de aceptacion:**
- Flujo completo de pago funciona
- Tenant se activa al pagar
- Webhooks se procesan correctamente
- Tests con ambiente de integracion pasan

---

### Tarea 4.3: Usage Tracking Module
**Asignado a:** _______________
**Estimacion:** 2 dias
**Prioridad:** ALTA

**Archivos a crear:**
- [ ] `backend/app/modules/usage/__init__.py`
- [ ] `backend/app/modules/usage/models.py`
- [ ] `backend/app/modules/usage/schemas.py`
- [ ] `backend/app/modules/usage/service.py`
- [ ] `backend/app/modules/usage/router.py`
- [ ] `backend/app/modules/usage/tracker.py`
- [ ] `backend/app/modules/usage/thresholds.py`

**Endpoints requeridos:**
- GET /api/v1/usage/current
- GET /api/v1/usage/history
- GET /api/v1/usage/by-agent
- GET /api/v1/usage/thresholds
- PUT /api/v1/usage/thresholds

**Funcionalidades:**
- Track tokens por request
- Calcular costos segun modelo
- Verificar umbrales (warning, critical, suspend)
- Alertas automaticas
- Agregacion diaria/mensual

**Criterios de aceptacion:**
- Tokens se trackean en cada chat
- Costos se calculan correctamente
- Umbrales se verifican automaticamente
- Alertas se envian cuando se exceden
- Dashboard muestra metricas correctamente

---

### Tarea 4.4: Search Module
**Asignado a:** _______________
**Estimacion:** 1 dia
**Prioridad:** MEDIA

**Archivos a crear:**
- [ ] `backend/app/modules/search/__init__.py`
- [ ] `backend/app/modules/search/schemas.py`
- [ ] `backend/app/modules/search/service.py`
- [ ] `backend/app/modules/search/router.py`
- [ ] `backend/app/modules/search/fulltext.py`

**Endpoints requeridos:**
- POST /api/v1/search/query

**Funcionalidades:**
- Busqueda full-text en resumenes
- Busqueda por keywords
- Ranking de resultados
- Limit y offset para paginacion

**Criterios de aceptacion:**
- Busqueda retorna resultados relevantes
- Ranking funciona correctamente
- Paginacion funciona
- Tests con queries de ejemplo pasan

---

## SPRINT 5-6 - FRONTEND (Semana 5-6)

**Objetivo:** Implementar interfaces de usuario

### Tarea 5.1: Frontend Setup
**Asignado a:** _______________
**Estimacion:** 1 dia
**Prioridad:** ALTA

**Tareas:**
- [ ] Configurar Next.js 14
- [ ] Configurar Tailwind CSS
- [ ] Instalar shadcn/ui
- [ ] Configurar TypeScript
- [ ] Setup de variables de entorno

**Archivos a crear:**
- [ ] `frontend/next.config.js`
- [ ] `frontend/tailwind.config.js`
- [ ] `frontend/tsconfig.json`
- [ ] `frontend/.env.local`

**Criterios de aceptacion:**
- App de Next.js corre sin errores
- Tailwind funciona
- shadcn/ui componentes se pueden usar

---

### Tarea 5.2: Authentication UI
**Asignado a:** _______________
**Estimacion:** 2 dias
**Prioridad:** ALTA

**Paginas a crear:**
- [ ] `frontend/src/app/(auth)/login/page.tsx`
- [ ] `frontend/src/app/(auth)/register/page.tsx`

**Componentes:**
- [ ] `frontend/src/lib/auth.tsx` - AuthProvider
- [ ] `frontend/src/lib/api.ts` - API Client
- [ ] `frontend/src/components/protected-route.tsx`

**Funcionalidades:**
- Login form con validacion
- Register form con validacion
- Auth context con JWT
- Protected routes
- Auto-refresh de token

**Criterios de aceptacion:**
- Login funciona y guarda token
- Register crea usuario
- Protected routes bloquean sin auth
- Token se refreshea automaticamente

---

### Tarea 5.3: Admin Dashboard
**Asignado a:** _______________
**Estimacion:** 2 dias
**Prioridad:** ALTA

**Paginas a crear:**
- [ ] `frontend/src/app/(admin)/dashboard/page.tsx`
- [ ] `frontend/src/app/(admin)/tenants/page.tsx`
- [ ] `frontend/src/app/(admin)/analytics/page.tsx`

**Componentes:**
- [ ] Sidebar de navegacion
- [ ] Cards de stats
- [ ] Tabla de tenants
- [ ] Graficos de analytics (Recharts)

**Funcionalidades:**
- Ver stats globales
- Listar todos los tenants
- Crear/editar/eliminar tenants
- Ver metricas de uso global

**Criterios de aceptacion:**
- Dashboard muestra datos correctos
- CRUD de tenants funciona
- Graficos se renderizan correctamente

---

### Tarea 5.4: Tenant Dashboard
**Asignado a:** _______________
**Estimacion:** 3 dias
**Prioridad:** ALTA

**Paginas a crear:**
- [ ] `frontend/src/app/(tenant)/dashboard/page.tsx`
- [ ] `frontend/src/app/(tenant)/agents/page.tsx`
- [ ] `frontend/src/app/(tenant)/agents/[id]/page.tsx`
- [ ] `frontend/src/app/(tenant)/agents/new/page.tsx`
- [ ] `frontend/src/app/(tenant)/playground/page.tsx`
- [ ] `frontend/src/app/(tenant)/documents/page.tsx`
- [ ] `frontend/src/app/(tenant)/usage/page.tsx`
- [ ] `frontend/src/app/(tenant)/billing/page.tsx`

**Componentes clave:**
- [ ] Agent creation form
- [ ] Chat interface con streaming
- [ ] Document upload
- [ ] Usage charts
- [ ] Billing page con Transbank

**Funcionalidades:**
- CRUD de agentes
- Playground de chat
- Upload de documentos
- Ver metricas de uso
- Suscribirse/pagar

**Criterios de aceptacion:**
- Todas las funcionalidades funcionan
- UI es responsiva
- Streaming de chat funciona
- Upload de docs funciona
- Pago con Transbank funciona

---

## SPRINT 7 - TESTING & DEPLOYMENT (Semana 7)

**Objetivo:** Tests completos y deployment

### Tarea 7.1: Integration Tests
**Asignado a:** _______________
**Estimacion:** 2 dias
**Prioridad:** ALTA

**Archivos a crear:**
- [ ] `backend/testing/test_integration_chat.py`
- [ ] `backend/testing/test_integration_documents.py`
- [ ] `backend/testing/test_integration_payments.py`

**Tests requeridos:**
- Flujo completo de chat
- Flujo completo de procesamiento de docs
- Flujo completo de pago

**Criterios de aceptacion:**
- Tests de integracion pasan
- Coverage total > 80%

---

### Tarea 7.2: Deployment Scripts
**Asignado a:** _______________
**Estimacion:** 1 dia
**Prioridad:** ALTA

**Archivos a verificar/actualizar:**
- [ ] `deployment/scripts/install.sh`
- [ ] `deployment/scripts/deploy.sh`
- [ ] `deployment/systemd/*.service`
- [ ] `deployment/nginx/aipanel.conf`

**Tareas:**
- Verificar scripts de instalacion
- Configurar servicios systemd
- Configurar Nginx
- Setup SSL con Let's Encrypt

**Criterios de aceptacion:**
- Script de instalacion funciona
- Servicios systemd arrancan correctamente
- Nginx sirve frontend y proxy a backend
- SSL funciona

---

### Tarea 7.3: Monitoring Setup
**Asignado a:** _______________
**Estimacion:** 1 dia
**Prioridad:** MEDIA

**Archivos a crear:**
- [ ] `backend/app/modules/monitoring/health.py`
- [ ] `backend/app/modules/monitoring/metrics.py`
- [ ] `deployment/monitoring/prometheus.yml`

**Funcionalidades:**
- Health check endpoint
- Readiness check endpoint
- Prometheus metrics
- Sentry integration

**Criterios de aceptacion:**
- /health retorna 200
- /metrics retorna metricas Prometheus
- Sentry captura errores

---

## TAREAS OPCIONALES (Backlog)

### Anthropic Integration
**Estimacion:** 1 dia
**Prioridad:** BAJA

- [ ] `backend/app/integrations/anthropic_client.py`
- [ ] Soporte para Claude en chat

### S3 Storage
**Estimacion:** 1 dia
**Prioridad:** BAJA

- [ ] `backend/app/integrations/s3_client.py`
- [ ] Upload de documentos a S3

### Email System
**Estimacion:** 1 dia
**Prioridad:** BAJA

- [ ] `backend/app/integrations/email_client.py`
- [ ] `backend/app/tasks/email_tasks.py`
- [ ] Templates de emails

### Advanced Analytics
**Estimacion:** 2 dias
**Prioridad:** BAJA

- [ ] Dashboard avanzado con filtros
- [ ] Exportacion de reportes
- [ ] Graficos personalizables

---

## RESUMEN DE ESTIMACIONES

| Sprint | Dias | Tareas |
|--------|------|--------|
| Sprint 1 | 5 | Core Backend |
| Sprint 2 | 5 | Modulos Basicos |
| Sprint 3 | 7 | AI Features |
| Sprint 4 | 6 | Payments & Usage |
| Sprint 5-6 | 10 | Frontend |
| Sprint 7 | 4 | Testing & Deployment |
| **TOTAL** | **37 dias** | **~8 semanas** |

---

## DISTRIBUCION SUGERIDA DE EQUIPO

**Backend Developer 1:**
- Sprint 1: Core (database, security)
- Sprint 2: Tenants module
- Sprint 4: Payments module

**Backend Developer 2:**
- Sprint 1: Auth module
- Sprint 2: Agents module
- Sprint 4: Usage tracking module

**Backend Developer 3:**
- Sprint 3: OpenAI integration
- Sprint 3: Chat module
- Sprint 4: Search module

**Backend Developer 4:**
- Sprint 3: Documents module
- Sprint 3: Summarization
- Sprint 7: Integration tests

**Frontend Developer 1:**
- Sprint 5: Setup + Auth UI
- Sprint 5: Admin Dashboard

**Frontend Developer 2:**
- Sprint 6: Tenant Dashboard
- Sprint 6: Chat Playground
- Sprint 6: Billing UI

**DevOps:**
- Sprint 7: Deployment
- Sprint 7: Monitoring
- Soporte continuo

---

## COMO USAR ESTE DOCUMENTO

1. **Asignar tareas:** Escribir nombre en "Asignado a"
2. **Marcar completadas:** Marcar checkbox cuando termine
3. **Actualizar estimaciones:** Ajustar si es necesario
4. **Daily standup:** Revisar progreso diario
5. **Bloqueadores:** Marcar tareas bloqueadas y razon

---

**Ultima actualizacion:** 2025-01-21
**Version:** 1.0.0
