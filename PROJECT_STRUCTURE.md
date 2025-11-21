# Estructura del Proyecto AIPanel

Sistema modular de gestión multi-tenant para agentes AI.

## Principios de Arquitectura

### 1. Modularidad
- Cada módulo es independiente y auto-contenido
- Módulos se comunican a través de interfaces bien definidas
- Un módulo puede ser reemplazado sin afectar otros

### 2. Separación de Responsabilidades
- Testing separado del código de producción
- Logs y errores en directorios dedicados
- Documentación separada del código
- Configuración centralizada

### 3. Sin Emojis
- Todos los archivos usan solo texto ASCII
- Compatibilidad garantizada con Windows/Linux/Mac
- Logs y mensajes sin caracteres especiales

## Estructura de Directorios

```
aipanel/
├── backend/                      # Backend Python (FastAPI)
│   ├── app/                      # Código de la aplicación
│   │   ├── main.py              # ORQUESTADOR PRINCIPAL - solo importa y ejecuta
│   │   │
│   │   ├── core/                # Núcleo del sistema
│   │   │   ├── __init__.py
│   │   │   ├── config.py        # Configuración centralizada
│   │   │   ├── database.py      # Conexión a BD
│   │   │   ├── security.py      # JWT, hashing, encriptación
│   │   │   ├── dependencies.py  # Dependencies de FastAPI
│   │   │   └── exceptions.py    # Excepciones personalizadas
│   │   │
│   │   ├── modules/             # MÓDULOS INDEPENDIENTES
│   │   │   ├── __init__.py
│   │   │   │
│   │   │   ├── auth/            # Módulo de Autenticación
│   │   │   │   ├── __init__.py
│   │   │   │   ├── router.py    # Endpoints REST
│   │   │   │   ├── service.py   # Lógica de negocio
│   │   │   │   ├── models.py    # Modelos SQLAlchemy
│   │   │   │   ├── schemas.py   # Schemas Pydantic
│   │   │   │   └── utils.py     # Utilidades del módulo
│   │   │   │
│   │   │   ├── tenants/         # Módulo de Tenants
│   │   │   │   ├── __init__.py
│   │   │   │   ├── router.py
│   │   │   │   ├── service.py
│   │   │   │   ├── models.py
│   │   │   │   └── schemas.py
│   │   │   │
│   │   │   ├── agents/          # Módulo de Agentes AI
│   │   │   │   ├── __init__.py
│   │   │   │   ├── router.py
│   │   │   │   ├── service.py
│   │   │   │   ├── models.py
│   │   │   │   └── schemas.py
│   │   │   │
│   │   │   ├── chat/            # Módulo de Chat
│   │   │   │   ├── __init__.py
│   │   │   │   ├── router.py
│   │   │   │   ├── service.py
│   │   │   │   ├── streaming.py
│   │   │   │   └── schemas.py
│   │   │   │
│   │   │   ├── documents/       # Módulo de Documentos
│   │   │   │   ├── __init__.py
│   │   │   │   ├── router.py
│   │   │   │   ├── service.py
│   │   │   │   ├── models.py
│   │   │   │   ├── schemas.py
│   │   │   │   ├── processor.py  # Procesamiento de documentos
│   │   │   │   ├── chunking.py   # División inteligente
│   │   │   │   └── summarizer.py # Generación de resúmenes
│   │   │   │
│   │   │   ├── search/          # Módulo de Búsqueda
│   │   │   │   ├── __init__.py
│   │   │   │   ├── router.py
│   │   │   │   ├── service.py
│   │   │   │   └── fulltext.py  # Full-text search
│   │   │   │
│   │   │   ├── payments/        # Módulo de Pagos (Transbank)
│   │   │   │   ├── __init__.py
│   │   │   │   ├── router.py
│   │   │   │   ├── service.py
│   │   │   │   ├── transbank.py # Cliente Transbank
│   │   │   │   ├── webhooks.py  # Webhooks de pago
│   │   │   │   └── schemas.py
│   │   │   │
│   │   │   ├── usage/           # Módulo de Uso y Tokens
│   │   │   │   ├── __init__.py
│   │   │   │   ├── router.py
│   │   │   │   ├── service.py
│   │   │   │   ├── tracker.py   # Token tracking
│   │   │   │   ├── thresholds.py # Umbrales
│   │   │   │   ├── models.py
│   │   │   │   └── schemas.py
│   │   │   │
│   │   │   └── monitoring/      # Módulo de Monitoreo
│   │   │       ├── __init__.py
│   │   │       ├── health.py    # Health checks
│   │   │       ├── metrics.py   # Prometheus metrics
│   │   │       └── sentry.py    # Sentry integration
│   │   │
│   │   ├── integrations/        # Integraciones Externas
│   │   │   ├── __init__.py
│   │   │   ├── openai_client.py
│   │   │   ├── anthropic_client.py
│   │   │   ├── s3_client.py
│   │   │   └── email_client.py
│   │   │
│   │   ├── tasks/               # Tareas Asíncronas (Celery)
│   │   │   ├── __init__.py
│   │   │   ├── celery.py        # Configuración Celery
│   │   │   ├── document_tasks.py
│   │   │   ├── billing_tasks.py
│   │   │   └── email_tasks.py
│   │   │
│   │   └── utils/               # Utilidades Globales
│   │       ├── __init__.py
│   │       ├── logger.py        # Logger configurado
│   │       ├── validators.py
│   │       ├── formatters.py
│   │       └── helpers.py
│   │
│   ├── testing/                 # DIRECTORIO DE TESTING
│   │   ├── __init__.py
│   │   ├── conftest.py         # Fixtures de pytest
│   │   ├── test_auth.py
│   │   ├── test_tenants.py
│   │   ├── test_agents.py
│   │   ├── test_documents.py
│   │   ├── test_payments.py
│   │   ├── test_usage.py
│   │   └── fixtures/
│   │       ├── users.json
│   │       ├── tenants.json
│   │       └── sample.pdf
│   │
│   ├── debugging/               # DIRECTORIO DE DEBUGGING
│   │   ├── debug_database.py   # Scripts de debug de BD
│   │   ├── debug_openai.py     # Test manual de OpenAI
│   │   ├── debug_transbank.py  # Test manual de Transbank
│   │   └── debug_summarizer.py # Test de resúmenes
│   │
│   ├── logs/                    # DIRECTORIO DE LOGS
│   │   ├── .gitignore          # Ignorar logs en git
│   │   ├── app.log
│   │   ├── error.log
│   │   ├── access.log
│   │   └── celery.log
│   │
│   ├── errors/                  # DIRECTORIO DE ERRORES
│   │   ├── .gitignore
│   │   ├── exceptions/          # Stack traces
│   │   └── sentry/              # Reportes de Sentry
│   │
│   ├── migrations/              # Migraciones de Base de Datos
│   │   ├── versions/
│   │   └── env.py
│   │
│   ├── scripts/                 # Scripts de Utilidad
│   │   ├── create_admin.py
│   │   ├── seed_database.py
│   │   └── migrate_data.py
│   │
│   ├── requirements.txt         # Dependencias Python
│   ├── requirements-dev.txt     # Dependencias de desarrollo
│   └── pytest.ini              # Configuración de pytest
│
├── frontend/                    # Frontend Next.js
│   ├── src/
│   │   ├── app/                # App Router
│   │   │   ├── layout.tsx
│   │   │   ├── page.tsx
│   │   │   │
│   │   │   ├── (auth)/         # Grupo de autenticación
│   │   │   │   ├── login/
│   │   │   │   └── register/
│   │   │   │
│   │   │   ├── (admin)/        # Panel Admin (Nivel 1)
│   │   │   │   ├── dashboard/
│   │   │   │   ├── servers/
│   │   │   │   ├── tenants/
│   │   │   │   └── analytics/
│   │   │   │
│   │   │   └── (tenant)/       # Panel Tenant (Nivel 2)
│   │   │       ├── dashboard/
│   │   │       ├── agents/
│   │   │       ├── documents/
│   │   │       ├── playground/
│   │   │       ├── usage/
│   │   │       └── billing/
│   │   │
│   │   ├── components/         # Componentes React
│   │   │   ├── ui/            # Componentes UI base (shadcn)
│   │   │   ├── layout/        # Layouts
│   │   │   ├── forms/         # Formularios
│   │   │   ├── charts/        # Gráficos
│   │   │   └── modules/       # Componentes por módulo
│   │   │       ├── auth/
│   │   │       ├── agents/
│   │   │       ├── documents/
│   │   │       └── chat/
│   │   │
│   │   ├── lib/               # Librerías y utilidades
│   │   │   ├── api.ts         # Cliente HTTP
│   │   │   ├── auth.ts        # Auth helpers
│   │   │   └── utils.ts       # Utilidades
│   │   │
│   │   ├── stores/            # State management (Zustand)
│   │   │   ├── auth-store.ts
│   │   │   ├── agents-store.ts
│   │   │   └── ui-store.ts
│   │   │
│   │   └── types/             # TypeScript types
│   │       ├── api.ts
│   │       ├── models.ts
│   │       └── schemas.ts
│   │
│   ├── public/                # Assets estáticos
│   ├── testing/               # Tests del frontend
│   │   ├── test_components.tsx
│   │   └── test_api.ts
│   │
│   ├── package.json
│   └── next.config.js
│
├── shared/                     # Código Compartido
│   ├── types/                 # Types compartidos
│   │   └── index.ts
│   └── constants/             # Constantes
│       └── index.ts
│
├── documentation/              # DOCUMENTACIÓN SEPARADA
│   ├── README.md              # Índice de documentación
│   │
│   ├── architecture/          # Arquitectura
│   │   ├── overview.md
│   │   ├── authentication.md
│   │   ├── payments.md
│   │   ├── memory_strategy.md
│   │   ├── token_tracking.md
│   │   └── tech_stack.md
│   │
│   ├── api/                   # Documentación de API
│   │   ├── overview.md
│   │   ├── authentication.md
│   │   ├── tenants.md
│   │   ├── agents.md
│   │   ├── chat.md
│   │   └── payments.md
│   │
│   ├── guides/                # Guías
│   │   ├── getting_started.md
│   │   ├── deployment.md
│   │   ├── development.md
│   │   ├── testing.md
│   │   └── troubleshooting.md
│   │
│   ├── modules/               # Documentación por módulo
│   │   ├── auth_module.md
│   │   ├── tenants_module.md
│   │   ├── agents_module.md
│   │   ├── documents_module.md
│   │   ├── payments_module.md
│   │   └── usage_module.md
│   │
│   └── diagrams/              # Diagramas
│       ├── architecture.png
│       ├── auth_flow.png
│       └── payment_flow.png
│
├── deployment/                # Scripts de Deployment
│   ├── systemd/              # Servicios systemd
│   │   ├── aipanel-api.service
│   │   ├── aipanel-worker.service
│   │   └── aipanel-beat.service
│   │
│   ├── nginx/                # Configuración Nginx
│   │   └── aipanel.conf
│   │
│   ├── scripts/              # Scripts de deployment
│   │   ├── install.sh
│   │   ├── deploy.sh
│   │   └── backup.sh
│   │
│   └── monitoring/           # Monitoring configs
│       ├── prometheus.yml
│       └── grafana-dashboard.json
│
├── database/                  # Base de Datos
│   ├── schema.prisma         # Prisma schema
│   ├── migrations/           # Migraciones SQL
│   └── seeds/                # Datos iniciales
│       ├── admin_users.sql
│       └── default_plans.sql
│
├── .env.example              # Variables de entorno
├── .gitignore
├── LICENSE
└── README.md                 # README principal

```

## Flujo de Ejecución

### Backend Main (main.py)

El archivo principal es un simple orquestador:

```python
# backend/app/main.py
from fastapi import FastAPI
from app.core.config import settings
from app.core.database import init_database
from app.utils.logger import setup_logging

# Importar routers de módulos
from app.modules.auth.router import router as auth_router
from app.modules.tenants.router import router as tenants_router
from app.modules.agents.router import router as agents_router
# ... otros routers

def create_app() -> FastAPI:
    """Orquestador principal - solo crea y configura la app"""

    # Setup logging
    setup_logging()

    # Crear app
    app = FastAPI(title=settings.PROJECT_NAME)

    # Incluir routers de módulos
    app.include_router(auth_router, prefix="/api/v1/auth", tags=["auth"])
    app.include_router(tenants_router, prefix="/api/v1/tenants", tags=["tenants"])
    app.include_router(agents_router, prefix="/api/v1/agents", tags=["agents"])
    # ... otros routers

    return app

# Crear instancia de la app
app = create_app()

# Evento de inicio
@app.on_event("startup")
async def startup():
    await init_database()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
```

## Estructura de un Módulo

Cada módulo sigue la misma estructura:

```
modules/example_module/
├── __init__.py          # Exporta las interfaces públicas
├── router.py            # Endpoints REST (FastAPI router)
├── service.py           # Lógica de negocio
├── models.py            # Modelos de base de datos (SQLAlchemy)
├── schemas.py           # Schemas de validación (Pydantic)
├── utils.py             # Utilidades específicas del módulo
└── exceptions.py        # Excepciones del módulo
```

### Ejemplo: Módulo de Autenticación

```python
# modules/auth/__init__.py
from .router import router
from .service import AuthService

__all__ = ["router", "AuthService"]


# modules/auth/router.py
from fastapi import APIRouter, Depends
from .service import AuthService
from .schemas import LoginRequest, AuthResponse

router = APIRouter()

@router.post("/login", response_model=AuthResponse)
async def login(request: LoginRequest, service: AuthService = Depends()):
    return await service.login(request)


# modules/auth/service.py
class AuthService:
    def __init__(self, db: Database):
        self.db = db

    async def login(self, request: LoginRequest) -> AuthResponse:
        # Lógica de negocio aquí
        pass


# modules/auth/schemas.py
from pydantic import BaseModel

class LoginRequest(BaseModel):
    email: str
    password: str

class AuthResponse(BaseModel):
    access_token: str
    refresh_token: str
```

## Convenciones de Nomenclatura

### Archivos de Testing
- Prefijo: `test_`
- Ubicación: `/backend/testing/`
- Ejemplo: `test_auth.py`, `test_payments.py`

### Archivos de Debugging
- Prefijo: `debug_`
- Ubicación: `/backend/debugging/`
- Ejemplo: `debug_database.py`, `debug_openai.py`

### Logs
- Ubicación: `/backend/logs/`
- Nombres: `app.log`, `error.log`, `access.log`, `celery.log`
- Rotación automática configurada

### Errores
- Ubicación: `/backend/errors/`
- Stack traces guardados con timestamp
- Integración con Sentry para producción

## Beneficios de Esta Estructura

### 1. Modularidad
- Cada módulo puede desarrollarse independientemente
- Fácil de escalar agregando nuevos módulos
- Testing más simple (cada módulo se testea por separado)

### 2. Mantenibilidad
- Código organizado y fácil de encontrar
- Responsabilidades claras
- Fácil de refactorizar

### 3. Compatibilidad
- Sin emojis = sin problemas de encoding
- Funciona en Windows, Linux, Mac
- CI/CD más confiable

### 4. Testing y Debugging
- Tests completamente separados del código de producción
- Scripts de debugging no contaminan el código
- Fácil de ejecutar tests: `pytest backend/testing/`

### 5. Claridad
- Estructura predecible
- Nuevos desarrolladores encuentran código rápidamente
- Documentación separada del código

## Comandos Útiles

### Testing
```bash
# Ejecutar todos los tests
pytest backend/testing/

# Test específico
pytest backend/testing/test_auth.py

# Con coverage
pytest backend/testing/ --cov=backend/app --cov-report=html
```

### Debugging
```bash
# Ejecutar script de debug
python backend/debugging/debug_database.py

# Debug de OpenAI
python backend/debugging/debug_openai.py
```

### Logs
```bash
# Ver logs en tiempo real
tail -f backend/logs/app.log

# Ver solo errores
tail -f backend/logs/error.log

# Buscar en logs
grep "ERROR" backend/logs/app.log
```

### Desarrollo
```bash
# Ejecutar backend
cd backend && python -m app.main

# Ejecutar con auto-reload
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Ejecutar worker de Celery
celery -A app.tasks.celery worker --loglevel=info

# Ejecutar beat (tareas programadas)
celery -A app.tasks.celery beat --loglevel=info
```

## Migración desde Estructura Anterior

Si ya tienes código en estructura antigua, migrar es simple:

1. Crear nuevos directorios
2. Mover archivos a sus módulos correspondientes
3. Actualizar imports
4. Actualizar tests
5. Verificar que todo funciona

La documentación actual en `docs/` se debe mover a `documentation/`.
