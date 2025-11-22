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
    CORS_ORIGINS: str = "http://localhost:3000"

    def get_cors_origins(self) -> List[str]:
        """Get CORS origins as a list."""
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",")]

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

    # Email - SMTP
    SMTP_HOST: str | None = None
    SMTP_PORT: int = 587
    SMTP_USER: str | None = None
    SMTP_PASSWORD: str | None = None
    SMTP_FROM: str = "noreply@aipanel.com"

    # Email - SendGrid (alternativo)
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

    # Twilio SMS (opcional)
    TWILIO_ACCOUNT_SID: str | None = None
    TWILIO_AUTH_TOKEN: str | None = None
    TWILIO_FROM_NUMBER: str | None = None

    # Slack (opcional)
    SLACK_WEBHOOK_URL: str | None = None
    SLACK_BOT_TOKEN: str | None = None
    SLACK_DEFAULT_CHANNEL: str | None = None

    # OneSignal Push Notifications (opcional)
    ONESIGNAL_APP_ID: str | None = None
    ONESIGNAL_API_KEY: str | None = None

    class Config:
        env_file = ".env"
        case_sensitive = True
        extra = "ignore"  # Ignore extra fields in .env


# Instancia global de configuración
settings = Settings()
