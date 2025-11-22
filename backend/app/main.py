"""
AIPanel - Main Application Entry Point

Este archivo es el ORQUESTADOR principal del sistema.
Solo debe:
1. Crear la aplicación FastAPI
2. Configurar middleware
3. Registrar routers de módulos
4. Configurar eventos de inicio/cierre

NO debe contener lógica de negocio.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware

from app.core.config import settings
from app.core.rate_limiter import RateLimitMiddleware, rate_limiter
from app.core.database import init_database, close_database
from app.core.request_context import RequestContextMiddleware
from app.core.startup_validation import run_startup_validation, run_all_validations
from app.utils.logger import setup_logging, get_logger

# Importar routers de módulos
from app.modules.auth.router import router as auth_router
from app.modules.tenants.router import router as tenants_router
from app.modules.agents.router import router as agents_router
from app.modules.chat.router import router as chat_router
from app.modules.documents.router import router as documents_router
from app.modules.search.router import router as search_router
from app.modules.payments.router import router as payments_router
from app.modules.usage.router import router as usage_router
from app.modules.monitoring.health import router as health_router
from app.modules.monitoring.prometheus import router as prometheus_router
from app.modules.settings.router import router as settings_router
from app.modules.plans.router import router as plans_router
from app.modules.billing.router import router as billing_router
from app.modules.ai_lab.router import router as ai_lab_router
from app.modules.widget.router import router as widget_router
from app.modules.webhooks.router import router as webhooks_router
from app.modules.dashboard.router import router as dashboard_router
from app.modules.audit.router import router as audit_router
from app.modules.email.router import router as email_router

logger = get_logger(__name__)


def create_app() -> FastAPI:
    """
    Factory para crear la aplicación FastAPI.

    Este orquestador:
    - Configura logging
    - Crea instancia de FastAPI
    - Configura middleware
    - Registra routers de módulos
    - Configura eventos de lifecycle

    Returns:
        FastAPI: Instancia configurada de la aplicación
    """

    # 1. Setup logging
    setup_logging()
    logger.info("Iniciando AIPanel Backend")

    # 2. Crear aplicación FastAPI
    app = FastAPI(
        title=settings.PROJECT_NAME,
        description="Sistema de gestion multi-tenant para agentes AI",
        version="1.0.0",
        docs_url="/api/docs" if settings.ENVIRONMENT != "production" else None,
        redoc_url="/api/redoc" if settings.ENVIRONMENT != "production" else None,
    )

    # 3. Configurar middleware
    _configure_middleware(app)

    # 4. Registrar routers de módulos
    _register_routers(app)

    # 5. Configurar eventos
    _configure_events(app)

    logger.info("Aplicacion configurada exitosamente")

    return app


def _configure_middleware(app: FastAPI) -> None:
    """Configurar middleware de la aplicación."""

    # Request Context (first - outer middleware runs last)
    # This sets up request_id, tenant_id, user_id for logging
    app.add_middleware(RequestContextMiddleware)

    # CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.get_cors_origins(),
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Compresión GZIP
    app.add_middleware(GZipMiddleware, minimum_size=1000)

    # Rate limiting (100 requests per minute per IP/API key)
    if settings.ENVIRONMENT != "test":
        app.add_middleware(
            RateLimitMiddleware,
            limiter=rate_limiter,
            default_limit=100,
            window_seconds=60,
        )

    logger.info("Middleware configurado")


def _register_routers(app: FastAPI) -> None:
    """Registrar routers de todos los módulos."""

    # Health check y monitoring (sin prefijo /api para simplificar health checks)
    app.include_router(
        health_router,
        tags=["health"]
    )

    app.include_router(
        prometheus_router,
        tags=["monitoring"]
    )

    # API v1 routers
    api_prefix = "/api/v1"

    app.include_router(
        auth_router,
        prefix=f"{api_prefix}/auth",
        tags=["authentication"]
    )

    app.include_router(
        tenants_router,
        prefix=f"{api_prefix}/tenants",
        tags=["tenants"]
    )

    app.include_router(
        agents_router,
        prefix=f"{api_prefix}/agents",
        tags=["agents"]
    )

    app.include_router(
        chat_router,
        prefix=f"{api_prefix}/chat",
        tags=["chat"]
    )

    app.include_router(
        documents_router,
        prefix=f"{api_prefix}/documents",
        tags=["documents"]
    )

    app.include_router(
        search_router,
        prefix=f"{api_prefix}/search",
        tags=["search"]
    )

    app.include_router(
        payments_router,
        prefix=f"{api_prefix}/payments",
        tags=["payments"]
    )

    app.include_router(
        usage_router,
        prefix=f"{api_prefix}/usage",
        tags=["usage"]
    )

    app.include_router(
        settings_router,
        prefix=f"{api_prefix}/settings",
        tags=["settings"]
    )

    app.include_router(
        plans_router,
        prefix=f"{api_prefix}/plans",
        tags=["plans"]
    )

    app.include_router(
        billing_router,
        prefix=f"{api_prefix}/billing",
        tags=["billing"]
    )

    app.include_router(
        ai_lab_router,
        prefix=f"{api_prefix}/ai-lab",
        tags=["ai-lab"]
    )

    app.include_router(
        widget_router,
        prefix=f"{api_prefix}/widget",
        tags=["widget"]
    )

    app.include_router(
        webhooks_router,
        prefix=f"{api_prefix}/webhooks",
        tags=["webhooks"]
    )

    app.include_router(
        dashboard_router,
        prefix=f"{api_prefix}/dashboard",
        tags=["dashboard"]
    )

    app.include_router(
        audit_router,
        prefix=f"{api_prefix}/audit",
        tags=["audit"]
    )

    app.include_router(
        email_router,
        prefix=f"{api_prefix}/email",
        tags=["email"]
    )

    logger.info("Routers de modulos registrados")


def _configure_events(app: FastAPI) -> None:
    """Configurar eventos de lifecycle de la aplicación."""

    @app.on_event("startup")
    async def startup_event():
        """Ejecutado al iniciar la aplicación."""
        logger.info("Ejecutando tareas de startup")

        # 1. Validate configuration (fail fast on critical errors)
        run_startup_validation(
            fail_on_error=(settings.ENVIRONMENT == "production")
        )

        # 2. Inicializar conexión a base de datos
        await init_database()

        # 3. Run async validations (database, redis, etc.)
        validation_results = await run_all_validations(
            fail_on_critical=(settings.ENVIRONMENT == "production")
        )
        logger.info(f"Validation results: {validation_results}")

        logger.info("Startup completado")

    @app.on_event("shutdown")
    async def shutdown_event():
        """Ejecutado al cerrar la aplicación."""
        logger.info("Ejecutando tareas de shutdown")

        # Cerrar conexiones
        await close_database()
        await rate_limiter.close()

        logger.info("Shutdown completado")


# Crear instancia global de la aplicación
app = create_app()


# Entry point para ejecución directa
if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=settings.PORT,
        reload=settings.ENVIRONMENT == "development",
        log_level="info"
    )
