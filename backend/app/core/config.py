"""
Configuración centralizada del sistema.

Todas las variables de entorno y configuraciones se gestionan aquí.
"""

from typing import List
from pydantic import field_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Configuración global de la aplicación."""

    # Application
    PROJECT_NAME: str = "AIPanel"
    VERSION: str = "1.0.0"
    ENVIRONMENT: str = "development"  # development, staging, production
    PORT: int = 8000

    # Database
    DATABASE_URL: str
    DATABASE_ECHO: bool = False  # Log de queries SQL

    # Redis
    REDIS_URL: str

    # JWT
    JWT_SECRET: str
    JWT_REFRESH_SECRET: str
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRES_IN: int = 900  # 15 minutos en segundos
    JWT_REFRESH_EXPIRES_IN: int = 604800  # 7 días en segundos

    # CORS
    CORS_ORIGINS: List[str] = ["http://localhost:3000"]

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def parse_cors_origins(cls, v):
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",")]
        return v

    # OpenAI
    OPENAI_API_KEY: str
    OPENAI_ORG_ID: str | None = None

    # Anthropic
    ANTHROPIC_API_KEY: str

    # Transbank
    TRANSBANK_ENV: str = "integration"  # integration o production
    TRANSBANK_COMMERCE_CODE: str
    TRANSBANK_API_KEY: str

    # AWS S3 (opcional)
    AWS_ACCESS_KEY_ID: str | None = None
    AWS_SECRET_ACCESS_KEY: str | None = None
    AWS_REGION: str = "us-east-1"
    AWS_S3_BUCKET: str | None = None

    # Email
    SENDGRID_API_KEY: str | None = None
    EMAIL_FROM: str = "noreply@aipanel.com"
    EMAIL_FROM_NAME: str = "AIPanel"

    # Frontend URL
    FRONTEND_URL: str = "http://localhost:3000"

    # Rate Limiting
    RATE_LIMIT_TTL: int = 60  # segundos
    RATE_LIMIT_MAX: int = 100  # requests por TTL

    # Logs
    LOG_LEVEL: str = "INFO"
    LOG_FILE_PATH: str = "backend/logs"

    # Billing
    DEFAULT_CURRENCY: str = "CLP"
    GRACE_PERIOD_DAYS: int = 14

    # Sentry (opcional)
    SENTRY_DSN: str | None = None

    class Config:
        env_file = ".env"
        case_sensitive = True


# Instancia global de configuración
settings = Settings()
