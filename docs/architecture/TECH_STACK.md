# Stack Tecnológico - AIPanel (Python-First)

Sistema optimizado para Python con herramientas confiables y probadas en producción.

## [+] Filosofía de Diseño

- **Python-First**: Backend 100% Python con librerías maduras
- **Herramientas Confiables**: Solo librerías con amplio uso en producción
- **Type-Safe**: Validación de tipos con Pydantic y mypy
- **Async-Native**: Operaciones asíncronas para mejor rendimiento
- **Minimal JS**: Solo frontend moderno (Next.js), todo el backend en Python

## [#] Arquitectura General

```
┌─────────────────────────────────────┐
│    Frontend (Next.js + TypeScript)  │
│    Panel Administrativo Moderno     │
└─────────────────────────────────────┘
                 │ HTTP/REST
                 ▼
┌─────────────────────────────────────┐
│  Backend API (Python + FastAPI)     │
│  - Autenticación                    │
│  - Lógica de negocio                │
│  - Integración AI (OpenAI, Claude)  │
│  - Sistema de pagos (Stripe)        │
└─────────────────────────────────────┘
                 │
     ┌───────────┼───────────┐
     ▼           ▼           ▼
┌─────────┐ ┌─────────┐ ┌─────────┐
│PostgreSQL│ │  Redis  │ │   S3    │
└─────────┘ └─────────┘ └─────────┘
```

## [?] Backend (100% Python)

### Framework Principal: **FastAPI**

**Por qué FastAPI:**
- [OK] Alto rendimiento (comparable a Node/Go)
- [OK] Type hints nativos con Pydantic
- [OK] Documentación automática (OpenAPI/Swagger)
- [OK] Async/await nativo
- [OK] Validación automática de datos
- [OK] Ampliamente usado en producción
- [OK] Excelente integración con OpenAI SDK

```bash
pip install fastapi[all]
```

### ORM: **SQLAlchemy 2.0 + Alembic**

**Por qué SQLAlchemy:**
- [OK] ORM más maduro de Python
- [OK] Type hints con SQLAlchemy 2.0
- [OK] Async support completo
- [OK] Migraciones con Alembic
- [OK] Probado en producción por años

```bash
pip install sqlalchemy[asyncio] alembic psycopg[binary]
```

### Validación: **Pydantic v2**

```python
from pydantic import BaseModel, EmailStr, Field

class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8)
    name: str
    role: AdminRole
```

### Autenticación: **python-jose + passlib**

```bash
pip install python-jose[cryptography] passlib[bcrypt]
```

**Características:**
- JWT con RS256 o HS256
- Bcrypt para passwords
- Refresh tokens con Redis
- Rate limiting con slowapi

### Tareas Asíncronas: **Celery + Redis**

```bash
pip install celery[redis] flower
```

**Workers:**
- Procesamiento de PDFs
- Generación de embeddings
- Envío de emails
- Webhooks de Stripe
- Limpieza de datos

### AI SDKs: **OpenAI + Anthropic**

```bash
pip install openai anthropic
```

**Características:**
- SDK oficial de OpenAI para GPT-5, Realtime API
- SDK oficial de Anthropic para Claude
- Streaming de respuestas
- Function calling
- Manejo de errores y retries

### Pagos: **stripe-python**

```bash
pip install stripe
```

### Storage: **boto3** (AWS S3)

```bash
pip install boto3
```

### Email: **sendgrid** o **resend-python**

```bash
pip install sendgrid
# o
pip install resend
```

### Caché: **redis-py**

```bash
pip install redis hiredis
```

### Testing: **pytest + httpx**

```bash
pip install pytest pytest-asyncio httpx
```

## [P] Dependencias Completas del Backend

**requirements.txt:**
```txt
# Framework
fastapi[all]==0.109.0
uvicorn[standard]==0.27.0
gunicorn==21.2.0

# Database
sqlalchemy[asyncio]==2.0.25
alembic==1.13.1
psycopg[binary,pool]==3.1.18

# Validation
pydantic[email]==2.5.3
pydantic-settings==2.1.0

# Auth
python-jose[cryptography]==3.3.0
passlib[bcrypt]==1.7.4
python-multipart==0.0.6

# Tasks
celery[redis]==5.3.6
flower==2.0.1

# Cache
redis[hiredis]==5.0.1

# AI SDKs
openai==1.10.0
anthropic==0.18.0

# Payments
stripe==8.2.0

# Storage
boto3==1.34.34

# Email
sendgrid==6.11.0

# Utils
python-dotenv==1.0.0
httpx==0.26.0
tenacity==8.2.3  # Retries

# Monitoring
prometheus-client==0.19.0
sentry-sdk[fastapi]==1.40.0

# Testing
pytest==7.4.4
pytest-asyncio==0.23.3
pytest-cov==4.1.0
faker==22.4.0

# Type checking
mypy==1.8.0
types-redis==4.6.0.20240106
```

## [?] Frontend (TypeScript)

Mantenemos **Next.js 14+** porque es la mejor herramienta para dashboards:

### Framework: **Next.js 14+ (App Router)**

```json
{
  "dependencies": {
    "next": "14.1.0",
    "react": "18.2.0",
    "react-dom": "18.2.0"
  }
}
```

**Por qué Next.js:**
- [OK] Mejor experiencia de desarrollo para dashboards
- [OK] Server-side rendering
- [OK] TypeScript nativo
- [OK] Componentes modernos
- [OK] Routing automático

### UI: **shadcn/ui + Tailwind CSS**

```bash
npx shadcn-ui@latest init
```

### Estado: **Zustand** (mínimo)

```bash
npm install zustand
```

### Formularios: **React Hook Form + Zod**

```bash
npm install react-hook-form zod @hookform/resolvers
```

### Gráficos: **Recharts**

```bash
npm install recharts
```

### HTTP Client: **axios** o **fetch nativo**

```bash
npm install axios
```

## [*] Deployment (Sin Node.js en Backend)

### Application Server: **Gunicorn + Uvicorn**

```bash
# Producción
gunicorn app.main:app \
  --workers 4 \
  --worker-class uvicorn.workers.UvicornWorker \
  --bind 0.0.0.0:8000
```

### Process Manager: **Systemd** (nativo Linux)

**NO usamos PM2** (es Node.js), usamos systemd que es nativo:

```ini
# /etc/systemd/system/aipanel-api.service
[Unit]
Description=AIPanel FastAPI Backend
After=network.target postgresql.service redis.service

[Service]
Type=notify
User=aipanel
Group=aipanel
WorkingDirectory=/var/www/aipanel/backend
Environment="PATH=/var/www/aipanel/backend/venv/bin"
ExecStart=/var/www/aipanel/backend/venv/bin/gunicorn \
  --workers 4 \
  --worker-class uvicorn.workers.UvicornWorker \
  --bind 127.0.0.1:8000 \
  app.main:app

Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

### Celery Worker (Systemd)

```ini
# /etc/systemd/system/aipanel-worker.service
[Unit]
Description=AIPanel Celery Worker
After=network.target redis.service

[Service]
Type=forking
User=aipanel
Group=aipanel
WorkingDirectory=/var/www/aipanel/backend
Environment="PATH=/var/www/aipanel/backend/venv/bin"
ExecStart=/var/www/aipanel/backend/venv/bin/celery \
  -A app.celery worker \
  --loglevel=info \
  --concurrency=2

Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

### Frontend (Next.js Standalone)

```bash
# Build
cd frontend
npm run build

# Start con systemd
# /etc/systemd/system/aipanel-frontend.service
[Unit]
Description=AIPanel Frontend
After=network.target

[Service]
Type=simple
User=aipanel
Group=aipanel
WorkingDirectory=/var/www/aipanel/frontend
Environment="NODE_ENV=production"
Environment="PORT=3000"
ExecStart=/usr/bin/node /var/www/aipanel/frontend/.next/standalone/server.js

Restart=always

[Install]
WantedBy=multi-user.target
```

## [?] Base de Datos

### PostgreSQL 15+

```bash
sudo apt install postgresql-15 postgresql-contrib
```

### Redis 7+

```bash
sudo apt install redis-server
```

### Migraciones: **Alembic**

```bash
# Crear migración
alembic revision --autogenerate -m "descripcion"

# Aplicar migraciones
alembic upgrade head

# Rollback
alembic downgrade -1
```

## [?] Estructura del Proyecto Python

```
backend/
├── app/
│   ├── __init__.py
│   ├── main.py              # FastAPI app
│   ├── config.py            # Settings con pydantic-settings
│   ├── database.py          # SQLAlchemy setup
│   ├── celery.py            # Celery app
│   │
│   ├── models/              # SQLAlchemy models
│   │   ├── __init__.py
│   │   ├── user.py
│   │   ├── tenant.py
│   │   ├── server.py
│   │   └── agent.py
│   │
│   ├── schemas/             # Pydantic schemas (DTOs)
│   │   ├── __init__.py
│   │   ├── auth.py
│   │   ├── user.py
│   │   └── agent.py
│   │
│   ├── api/                 # Routers
│   │   ├── __init__.py
│   │   ├── deps.py          # Dependencies
│   │   ├── v1/
│   │   │   ├── __init__.py
│   │   │   ├── auth.py
│   │   │   ├── servers.py
│   │   │   ├── tenants.py
│   │   │   └── agents.py
│   │
│   ├── services/            # Business logic
│   │   ├── __init__.py
│   │   ├── auth.py
│   │   ├── agent.py
│   │   └── payment.py
│   │
│   ├── core/                # Core functionality
│   │   ├── __init__.py
│   │   ├── security.py      # JWT, password hashing
│   │   ├── config.py        # Settings
│   │   └── exceptions.py
│   │
│   ├── tasks/               # Celery tasks
│   │   ├── __init__.py
│   │   ├── email.py
│   │   └── ai.py
│   │
│   └── utils/               # Utilities
│       ├── __init__.py
│       ├── ai_client.py     # OpenAI/Anthropic wrappers
│       └── s3.py
│
├── alembic/                 # Database migrations
│   ├── versions/
│   └── env.py
│
├── tests/
│   ├── __init__.py
│   ├── conftest.py
│   └── test_auth.py
│
├── requirements.txt
├── requirements-dev.txt
├── pyproject.toml           # Poetry o setuptools
├── alembic.ini
└── .env.example
```

## [>] Herramientas de Desarrollo

### Virtual Environment: **venv** (nativo Python)

```bash
python3.11 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### Type Checking: **mypy**

```bash
mypy app/ --strict
```

### Linting: **ruff** (más rápido que flake8)

```bash
pip install ruff
ruff check app/
ruff format app/
```

### Testing: **pytest**

```bash
pytest tests/ -v --cov=app
```

## [!] Seguridad

### Secrets Management: **python-dotenv**

```python
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    database_url: str
    redis_url: str
    jwt_secret: str

    class Config:
        env_file = ".env"
```

### Rate Limiting: **slowapi**

```bash
pip install slowapi
```

```python
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)

@app.post("/api/auth/login")
@limiter.limit("5/minute")
async def login(...):
    ...
```

## [=] Monitoring

### Logs: **structlog**

```bash
pip install structlog
```

### Metrics: **prometheus-client**

```bash
pip install prometheus-client
```

### Errors: **Sentry**

```bash
pip install sentry-sdk[fastapi]
```

## [+] Comparativa: Node.js vs Python

| Característica | Node.js (Antes) | Python (Ahora) |
|----------------|-----------------|----------------|
| **Backend Framework** | NestJS | FastAPI |
| **ORM** | Prisma | SQLAlchemy 2.0 |
| **Validación** | class-validator | Pydantic |
| **Auth** | Passport + JWT | python-jose |
| **Tasks** | Bull (Redis) | Celery (Redis) |
| **Process Manager** | PM2 | Systemd |
| **App Server** | Node | Gunicorn + Uvicorn |
| **Type Safety** | TypeScript | Type hints + mypy |
| **AI SDKs** | @anthropic-ai/sdk | anthropic (oficial) |
| **Performance** | Bueno | Excelente (async) |
| **Madurez** | Medio | Alto |
| **Recursos** | ~300MB/worker | ~200MB/worker |

## [*] Comandos de Deployment

### Instalación Completa

```bash
# 1. Instalar Python 3.11
sudo apt install python3.11 python3.11-venv python3.11-dev

# 2. Crear virtual environment
cd /var/www/aipanel/backend
python3.11 -m venv venv
source venv/bin/activate

# 3. Instalar dependencias
pip install -r requirements.txt

# 4. Ejecutar migraciones
alembic upgrade head

# 5. Crear servicios systemd
sudo cp deploy/aipanel-api.service /etc/systemd/system/
sudo cp deploy/aipanel-worker.service /etc/systemd/system/
sudo cp deploy/aipanel-celery-beat.service /etc/systemd/system/

# 6. Iniciar servicios
sudo systemctl daemon-reload
sudo systemctl enable aipanel-api aipanel-worker
sudo systemctl start aipanel-api aipanel-worker

# 7. Verificar estado
sudo systemctl status aipanel-api
sudo systemctl status aipanel-worker
```

### Logs

```bash
# API logs
sudo journalctl -u aipanel-api -f

# Worker logs
sudo journalctl -u aipanel-worker -f

# Celery flower (monitoring UI)
celery -A app.celery flower --port=5555
```

## [?] Frontend Build

```bash
cd /var/www/aipanel/frontend

# Instalar dependencias (una sola vez, Node es necesario SOLO para el frontend)
npm install

# Build
npm run build

# El output será standalone, no necesita Node para correr
# Se inicia con systemd como se mostró arriba
```

## [OK] Ventajas del Stack Python-First

1. **Menor Fragmentación**: Todo el backend en un solo lenguaje
2. **Mejor para AI/ML**: Python es el lenguaje nativo de AI
3. **Más Maduro**: Librerías con años de producción
4. **Type-Safe**: Pydantic + mypy = excelente validación
5. **Recursos**: Systemd es más eficiente que PM2
6. **Debugging**: Más fácil debuggear un solo stack
7. **Hiring**: Más fácil encontrar devs Python
8. **Ecosistema**: Mejores librerías para data science, AI, procesamiento

## [?] Documentación API Automática

FastAPI genera automáticamente:

- **Swagger UI**: `http://api.aipanel.com/docs`
- **ReDoc**: `http://api.aipanel.com/redoc`
- **OpenAPI JSON**: `http://api.aipanel.com/openapi.json`

---

**Resultado**: Backend 100% Python con herramientas confiables, frontend moderno con Next.js, deployment con herramientas nativas de Linux (systemd).
