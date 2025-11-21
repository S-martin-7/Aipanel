# AIPanel - Documento de Onboarding para Desarrolladores

**Fecha:** 2025-01-21
**Version:** 1.0.0
**Proyecto:** AIPanel - Sistema Multi-Tenant de Gestion de Agentes AI

---

## RESUMEN EJECUTIVO

AIPanel es una plataforma SaaS multi-tenant para gestionar agentes de IA personalizados. Permite a empresas crear, configurar y monetizar agentes AI usando modelos de OpenAI y Anthropic, con sistema de pagos local (Transbank) y tracking de uso de tokens.

### Tecnologias Principales

**Backend:**
- Python 3.11
- FastAPI (framework web)
- SQLAlchemy 2.0 (ORM)
- PostgreSQL 15
- Redis 7
- Celery (tareas asincronas)

**Frontend:**
- Next.js 14 (App Router)
- TypeScript
- Tailwind CSS + shadcn/ui

**AI/ML:**
- OpenAI SDK (GPT-5, GPT-Realtime)
- Anthropic SDK (Claude)

**Pagos:**
- Transbank SDK (Chile)

---

## ARQUITECTURA DEL SISTEMA

### Modelo Multi-Tenant de 2 Niveles

```
Nivel 1: ADMINISTRADORES
├── Gestion de servidores
├── Gestion de tenants
└── Analytics globales

Nivel 2: TENANTS (Clientes)
├── Gestion de agentes AI
├── Playground de chat
├── Documentos y conocimiento
├── Metricas de uso
└── Facturacion
```

### Stack Tecnico Completo

```
┌─────────────────────────────────────────┐
│         Frontend (Next.js)              │
│    Panel Admin + Panel Tenant           │
└─────────────────┬───────────────────────┘
                  │ REST API
┌─────────────────▼───────────────────────┐
│       Backend API (FastAPI)             │
│    - Autenticacion JWT                  │
│    - CRUD de recursos                   │
│    - Chat con AI (streaming)            │
│    - Procesamiento de documentos        │
└─────────────────┬───────────────────────┘
                  │
     ┌────────────┼────────────┐
     ▼            ▼            ▼
┌─────────┐ ┌─────────┐ ┌─────────┐
│PostgreSQL│ │  Redis  │ │ Celery  │
│  (BD)   │ │ (Cache) │ │(Workers)│
└─────────┘ └─────────┘ └─────────┘
     │
     ▼
┌─────────────────────────────────────────┐
│         Servicios Externos              │
│  - OpenAI API                           │
│  - Anthropic API                        │
│  - Transbank API                        │
│  - AWS S3 (opcional)                    │
└─────────────────────────────────────────┘
```

---

## ESTRUCTURA MODULAR DEL PROYECTO

### Principio: Separacion Total de Responsabilidades

```
aipanel/
│
├── backend/                      # Backend Python
│   ├── app/                      # Codigo de la aplicacion
│   │   ├── main.py              # ORQUESTADOR PRINCIPAL
│   │   │
│   │   ├── core/                # Nucleo del sistema
│   │   │   ├── config.py        # Configuracion centralizada
│   │   │   ├── database.py      # Conexion a BD
│   │   │   ├── security.py      # JWT, hashing
│   │   │   ├── dependencies.py  # Dependencies de FastAPI
│   │   │   └── exceptions.py    # Excepciones custom
│   │   │
│   │   ├── modules/             # MODULOS INDEPENDIENTES
│   │   │   ├── auth/            # Autenticacion
│   │   │   ├── tenants/         # Gestion de tenants
│   │   │   ├── agents/          # Gestion de agentes AI
│   │   │   ├── chat/            # Chat con AI
│   │   │   ├── documents/       # Procesamiento de docs
│   │   │   ├── search/          # Busqueda hibrida
│   │   │   ├── payments/        # Transbank
│   │   │   ├── usage/           # Tracking de tokens
│   │   │   └── monitoring/      # Health checks
│   │   │
│   │   ├── integrations/        # Clientes externos
│   │   │   ├── openai_client.py
│   │   │   ├── anthropic_client.py
│   │   │   ├── transbank.py
│   │   │   └── s3_client.py
│   │   │
│   │   ├── tasks/               # Tareas Celery
│   │   │   ├── celery.py
│   │   │   ├── document_tasks.py
│   │   │   └── billing_tasks.py
│   │   │
│   │   └── utils/               # Utilidades
│   │       ├── logger.py
│   │       ├── validators.py
│   │       └── helpers.py
│   │
│   ├── testing/                 # TESTS (separado)
│   │   ├── conftest.py
│   │   ├── test_auth.py
│   │   ├── test_tenants.py
│   │   └── test_agents.py
│   │
│   ├── debugging/               # DEBUGGING (separado)
│   │   ├── debug_database.py
│   │   ├── debug_openai.py
│   │   └── debug_transbank.py
│   │
│   ├── logs/                    # LOGS (separado)
│   │   ├── app.log
│   │   └── error.log
│   │
│   ├── errors/                  # ERRORES (separado)
│   │   └── exceptions/
│   │
│   └── migrations/              # Migraciones Alembic
│
├── frontend/                    # Frontend Next.js
│   └── src/
│       ├── app/                 # App Router
│       ├── components/          # Componentes React
│       ├── lib/                 # Utilidades
│       └── stores/              # Zustand stores
│
├── database/                    # Schemas de BD
│   └── schema.prisma
│
├── documentation/               # Documentacion
│   ├── architecture/
│   ├── api/
│   └── guides/
│
└── deployment/                  # Scripts de deployment
    ├── systemd/
    ├── nginx/
    └── scripts/
```

---

## ESTRUCTURA DE UN MODULO

Todos los modulos siguen la misma estructura:

```
modules/ejemplo_modulo/
├── __init__.py          # Exporta interfaces publicas
├── router.py            # Endpoints REST (FastAPI)
├── service.py           # Logica de negocio (sin FastAPI)
├── models.py            # Modelos de BD (SQLAlchemy)
├── schemas.py           # Schemas de validacion (Pydantic)
└── utils.py             # Utilidades del modulo
```

### Responsabilidades:

**router.py:**
- Define endpoints REST
- Valida parametros de entrada
- Maneja errores HTTP
- NO contiene logica de negocio

**service.py:**
- Contiene TODA la logica de negocio
- Interactua con base de datos
- Llama a servicios externos
- NO tiene codigo de FastAPI

**schemas.py:**
- Define schemas Pydantic
- Validacion de datos
- Serializacion/deserializacion

**models.py:**
- Define modelos SQLAlchemy
- Estructura de tablas
- Relaciones entre modelos

---

## CONVENCIONES DE CODIGO

### Reglas Estrictas

1. **SIN EMOJIS EN CODIGO**
   - Solo caracteres ASCII
   - Razon: Compatibilidad Windows/Linux/Mac
   - Evita errores de encoding

2. **Type Hints Obligatorios**
   ```python
   def get_user(user_id: str) -> User:
       pass
   ```

3. **Docstrings en Funciones Publicas**
   ```python
   def login(email: str, password: str) -> AuthResponse:
       """
       Autenticar usuario.

       Args:
           email: Email del usuario
           password: Password en texto plano

       Returns:
           AuthResponse: Tokens de autenticacion

       Raises:
           ValueError: Si credenciales son invalidas
       """
       pass
   ```

4. **Nomenclatura:**
   - Variables/funciones: `snake_case`
   - Clases: `PascalCase`
   - Constantes: `UPPER_CASE`
   - Archivos: `snake_case.py`

5. **Imports Ordenados:**
   ```python
   # 1. Standard library
   import os
   from datetime import datetime

   # 2. Third party
   from fastapi import APIRouter
   from sqlalchemy import Column

   # 3. Local
   from app.core.config import settings
   ```

### Manejo de Errores

**En service.py:**
```python
# Usar excepciones de Python
if not user:
    raise ValueError("User not found")
```

**En router.py:**
```python
# Convertir a HTTPException
try:
    return await service.get_user(user_id)
except ValueError as exc:
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=str(exc)
    )
```

### Logging

```python
from app.utils.logger import get_logger

logger = get_logger(__name__)

logger.info(f"User logged in: {user.email}")
logger.error(f"Failed to process: {error}", exc_info=True)
```

---

## SETUP INICIAL

### 1. Requisitos del Sistema

- Python 3.11+
- Node.js 20+
- PostgreSQL 15+
- Redis 7+
- Git

### 2. Instalacion

```bash
# Clonar repositorio
git clone <repo-url> aipanel
cd aipanel

# Backend - Crear virtual environment
cd backend
python3.11 -m venv venv

# Activar virtual environment
source venv/bin/activate          # Linux/Mac
# o
venv\Scripts\activate              # Windows

# Instalar dependencias
pip install -r requirements.txt
pip install -r requirements-dev.txt

# Frontend - Instalar dependencias
cd ../frontend
npm install

# Volver a raiz
cd ..
```

### 3. Configuracion

```bash
# Copiar archivo de ejemplo
cp .env.example .env

# Editar con tus credenciales
nano .env  # o tu editor preferido
```

**Variables Obligatorias:**

```bash
# Database
DATABASE_URL=postgresql://user:pass@localhost:5432/aipanel

# Redis
REDIS_URL=redis://localhost:6379

# JWT
JWT_SECRET=tu_secret_aqui
JWT_REFRESH_SECRET=otro_secret_aqui

# OpenAI
OPENAI_API_KEY=sk-...

# Anthropic
ANTHROPIC_API_KEY=sk-ant-...

# Transbank
TRANSBANK_ENV=integration
TRANSBANK_COMMERCE_CODE=597055555532
TRANSBANK_API_KEY=579B...
```

### 4. Base de Datos

```bash
cd backend

# Crear base de datos
createdb aipanel

# Ejecutar migraciones
alembic upgrade head
```

### 5. Ejecutar en Desarrollo

```bash
# Terminal 1: Backend
cd backend
source venv/bin/activate
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Terminal 2: Frontend
cd frontend
npm run dev

# Terminal 3: Celery Worker (opcional)
cd backend
celery -A app.tasks.celery worker --loglevel=info

# Terminal 4: Redis (si no esta corriendo)
redis-server
```

**URLs:**
- Backend API: http://localhost:8000
- API Docs: http://localhost:8000/api/docs
- Frontend: http://localhost:3000

---

## WORKFLOW DE DESARROLLO

### 1. Crear Nueva Funcionalidad

```bash
# 1. Crear rama
git checkout -b feature/nombre-funcionalidad

# 2. Implementar modulo (ver seccion siguiente)

# 3. Ejecutar tests
pytest backend/testing/

# 4. Commit
git add .
git commit -m "Add: descripcion de la funcionalidad"

# 5. Push
git push origin feature/nombre-funcionalidad

# 6. Crear Pull Request
```

### 2. Testing

```bash
# Todos los tests
pytest backend/testing/

# Test especifico
pytest backend/testing/test_auth.py

# Con coverage
pytest backend/testing/ --cov=backend/app --cov-report=html

# Ver reporte
open htmlcov/index.html
```

### 3. Debugging

```bash
# Ejecutar script de debug
python backend/debugging/debug_database.py

# Ver logs en tiempo real
tail -f backend/logs/app.log

# Buscar errores
grep "ERROR" backend/logs/app.log
```

### 4. Code Quality

```bash
# Formatear codigo
black backend/app/

# Lint
ruff check backend/app/

# Type checking
mypy backend/app/
```

---

## COMO CREAR UN MODULO NUEVO

### Checklist:

- [ ] 1. Crear directorio del modulo
- [ ] 2. Crear schemas.py (Pydantic)
- [ ] 3. Crear models.py (SQLAlchemy)
- [ ] 4. Crear service.py (logica de negocio)
- [ ] 5. Crear router.py (endpoints REST)
- [ ] 6. Crear __init__.py (exportar interfaces)
- [ ] 7. Registrar router en main.py
- [ ] 8. Crear test_modulo.py
- [ ] 9. Ejecutar tests
- [ ] 10. Crear debug_modulo.py (opcional)

### Ejemplo Completo:

Ver archivo `DEVELOPMENT_GUIDE.md` para tutorial paso a paso.

---

## TAREAS PRIORITARIAS

### Fase 1: Core (Semana 1)

**Backend Core:**
- [ ] `core/database.py` - Conexion a BD con SQLAlchemy
- [ ] `core/security.py` - JWT creation/validation, password hashing
- [ ] `core/dependencies.py` - Dependencies de FastAPI
- [ ] `core/exceptions.py` - Excepciones custom

**Asignado:** [Pendiente]
**Estimacion:** 5 dias

### Fase 2: Modulos Basicos (Semana 2)

**Modulo de Tenants:**
- [ ] `modules/tenants/models.py`
- [ ] `modules/tenants/schemas.py`
- [ ] `modules/tenants/service.py`
- [ ] `modules/tenants/router.py`
- [ ] Tests unitarios

**Modulo de Agentes:**
- [ ] `modules/agents/models.py`
- [ ] `modules/agents/schemas.py`
- [ ] `modules/agents/service.py`
- [ ] `modules/agents/router.py`
- [ ] Tests unitarios

**Asignado:** [Pendiente]
**Estimacion:** 5 dias

### Fase 3: Funcionalidades AI (Semana 3)

**Integracion OpenAI:**
- [ ] `integrations/openai_client.py` - Wrapper de OpenAI SDK
- [ ] `modules/chat/service.py` - Logica de chat
- [ ] `modules/chat/router.py` - Endpoints de chat
- [ ] Streaming de respuestas

**Procesamiento de Documentos:**
- [ ] `modules/documents/processor.py` - Extraccion de texto
- [ ] `modules/documents/chunking.py` - Division inteligente
- [ ] `modules/documents/summarizer.py` - Generacion de resumenes
- [ ] Tests de procesamiento

**Asignado:** [Pendiente]
**Estimacion:** 5 dias

### Fase 4: Pagos y Tracking (Semana 4)

**Transbank Integration:**
- [ ] `integrations/transbank.py` - Cliente Transbank
- [ ] `modules/payments/service.py` - Logica de pagos
- [ ] `modules/payments/router.py` - Endpoints de pagos
- [ ] `modules/payments/webhooks.py` - Webhooks de Transbank

**Token Tracking:**
- [ ] `modules/usage/tracker.py` - Tracking de tokens
- [ ] `modules/usage/thresholds.py` - Verificacion de umbrales
- [ ] `modules/usage/service.py` - Logica de uso
- [ ] Dashboard de metricas

**Asignado:** [Pendiente]
**Estimacion:** 5 dias

### Fase 5: Frontend (Semana 5-6)

**Frontend Core:**
- [ ] Setup de Next.js 14
- [ ] Configuracion de Tailwind + shadcn/ui
- [ ] Sistema de autenticacion
- [ ] Protected routes

**Dashboards:**
- [ ] Dashboard Admin (Nivel 1)
- [ ] Dashboard Tenant (Nivel 2)
- [ ] Componentes reutilizables

**Funcionalidades:**
- [ ] Gestion de agentes
- [ ] Playground de chat
- [ ] Upload de documentos
- [ ] Metricas de uso
- [ ] Sistema de pagos

**Asignado:** [Pendiente]
**Estimacion:** 10 dias

---

## RECURSOS Y DOCUMENTACION

### Documentacion del Proyecto

1. **PROJECT_STRUCTURE.md** - Estructura completa del proyecto
2. **DEVELOPMENT_GUIDE.md** - Guia de desarrollo paso a paso
3. **README.md** - Overview del proyecto
4. **documentation/architecture/** - Documentacion de arquitectura
   - AUTHENTICATION.md
   - TOKEN_TRACKING.md
   - PAYMENT_SYSTEMS_CHILE.md
   - MEMORY_STRATEGY.md
   - TECH_STACK.md

### Documentacion Externa

**FastAPI:**
- Docs: https://fastapi.tiangolo.com/
- Tutorial: https://fastapi.tiangolo.com/tutorial/

**SQLAlchemy:**
- Docs: https://docs.sqlalchemy.org/
- ORM Tutorial: https://docs.sqlalchemy.org/en/20/orm/

**Pydantic:**
- Docs: https://docs.pydantic.dev/
- Validation: https://docs.pydantic.dev/latest/concepts/validation/

**Next.js:**
- Docs: https://nextjs.org/docs
- App Router: https://nextjs.org/docs/app

**OpenAI API:**
- Docs: https://platform.openai.com/docs
- Python SDK: https://github.com/openai/openai-python

**Transbank:**
- Docs: https://www.transbankdevelopers.cl/
- SDK Python: https://github.com/TransbankDevelopers/transbank-sdk-python

---

## CANALES DE COMUNICACION

**Dailies:** [Definir horario]
**Code Reviews:** [Definir proceso]
**Preguntas:** [Definir canal]

---

## TROUBLESHOOTING COMUN

### Error: Module not found

```bash
# Verificar que virtual environment esta activado
which python  # Debe mostrar path de venv

# Reinstalar dependencias
pip install -r requirements.txt
```

### Error: Database connection failed

```bash
# Verificar que PostgreSQL esta corriendo
sudo systemctl status postgresql

# Verificar credenciales en .env
cat .env | grep DATABASE_URL
```

### Error: Tests failing

```bash
# Limpiar cache
pytest --cache-clear

# Recrear base de datos de test
rm backend/testing/test.db
pytest backend/testing/
```

### Error: Port already in use

```bash
# Encontrar proceso usando el puerto
lsof -i :8000

# Matar proceso
kill -9 <PID>
```

---

## CONTACTO

**Tech Lead:** [Definir]
**Backend Lead:** [Definir]
**Frontend Lead:** [Definir]

---

**Ultima actualizacion:** 2025-01-21
**Version del documento:** 1.0.0

**IMPORTANTE:** Este proyecto NO usa emojis en el codigo. Solo caracteres ASCII para garantizar compatibilidad total.
