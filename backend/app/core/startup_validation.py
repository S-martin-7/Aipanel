"""
Startup Validation.

Validates critical configuration and dependencies on application startup.
Fails fast if required settings are missing or invalid.
"""

import sys
from typing import List, Tuple

from app.core.config import settings
from app.utils.logger import get_logger

logger = get_logger(__name__)


class StartupValidationError(Exception):
    """Raised when critical startup validation fails."""
    pass


def validate_required_settings() -> List[Tuple[str, str]]:
    """
    Validate that all required settings are configured.

    Returns:
        List of (setting_name, error_message) tuples for failed validations
    """
    errors = []

    # Database
    if not settings.DATABASE_URL:
        errors.append(("DATABASE_URL", "Database URL is required"))

    # JWT secrets
    if not settings.JWT_SECRET or settings.JWT_SECRET == "change-this-in-production":
        if settings.ENVIRONMENT == "production":
            errors.append(("JWT_SECRET", "JWT secret must be set in production"))
        else:
            logger.warning("JWT_SECRET not configured - using default (not safe for production)")

    if not settings.JWT_REFRESH_SECRET or settings.JWT_REFRESH_SECRET == "change-this-refresh-secret":
        if settings.ENVIRONMENT == "production":
            errors.append(("JWT_REFRESH_SECRET", "JWT refresh secret must be set in production"))

    # Redis (optional but recommended)
    if not settings.REDIS_URL:
        logger.warning("REDIS_URL not configured - rate limiting and caching may be limited")

    return errors


def validate_ai_provider_keys() -> List[Tuple[str, str]]:
    """
    Validate AI provider API keys are configured.

    Returns:
        List of (provider, warning_message) tuples
    """
    warnings = []

    if not getattr(settings, 'OPENAI_API_KEY', None):
        warnings.append(("OPENAI", "OpenAI API key not configured"))

    if not getattr(settings, 'ANTHROPIC_API_KEY', None):
        warnings.append(("ANTHROPIC", "Anthropic API key not configured"))

    return warnings


def validate_payment_settings() -> List[Tuple[str, str]]:
    """
    Validate payment provider settings.

    Returns:
        List of (setting, warning_message) tuples
    """
    warnings = []

    if settings.ENVIRONMENT == "production":
        if not getattr(settings, 'TRANSBANK_API_KEY', None):
            warnings.append(("TRANSBANK_API_KEY", "Transbank API key not configured"))
        if not getattr(settings, 'TRANSBANK_COMMERCE_CODE', None):
            warnings.append(("TRANSBANK_COMMERCE_CODE", "Transbank commerce code not configured"))
    else:
        # Check test credentials
        if not getattr(settings, 'TRANSBANK_COMMERCE_CODE', None):
            logger.info("Transbank not configured - payment features will be limited")

    return warnings


def validate_security_settings() -> List[Tuple[str, str]]:
    """
    Validate security-related settings.

    Returns:
        List of (setting, error_message) tuples
    """
    errors = []

    # CORS origins
    cors_origins = settings.get_cors_origins()
    if settings.ENVIRONMENT == "production":
        if "*" in cors_origins:
            errors.append(("CORS_ORIGINS", "Wildcard CORS origin not allowed in production"))
        if any("localhost" in origin for origin in cors_origins):
            logger.warning("localhost in CORS origins - ensure this is intentional")

    return errors


def run_startup_validation(fail_on_error: bool = True) -> bool:
    """
    Run all startup validations.

    Args:
        fail_on_error: If True, raises exception on critical errors

    Returns:
        True if all validations passed

    Raises:
        StartupValidationError: If critical validation fails and fail_on_error is True
    """
    logger.info("Running startup validation...")

    all_errors = []
    all_warnings = []

    # Required settings (critical)
    errors = validate_required_settings()
    all_errors.extend(errors)

    # Security settings (critical in production)
    security_errors = validate_security_settings()
    if settings.ENVIRONMENT == "production":
        all_errors.extend(security_errors)
    else:
        all_warnings.extend(security_errors)

    # AI provider keys (warnings only)
    ai_warnings = validate_ai_provider_keys()
    all_warnings.extend(ai_warnings)

    # Payment settings (warnings)
    payment_warnings = validate_payment_settings()
    all_warnings.extend(payment_warnings)

    # Log warnings
    for setting, message in all_warnings:
        logger.warning(f"Configuration warning [{setting}]: {message}")

    # Handle errors
    if all_errors:
        for setting, message in all_errors:
            logger.error(f"Configuration error [{setting}]: {message}")

        if fail_on_error:
            error_msg = "; ".join([f"{s}: {m}" for s, m in all_errors])
            raise StartupValidationError(f"Startup validation failed: {error_msg}")

        return False

    logger.info("Startup validation completed successfully")
    return True


async def validate_database_connection() -> bool:
    """
    Validate database connection is working.

    Returns:
        True if database is accessible
    """
    try:
        from app.core.database import engine
        from sqlalchemy import text

        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
            logger.info("Database connection validated")
            return True

    except Exception as e:
        logger.error(f"Database connection failed: {e}")
        return False


async def validate_redis_connection() -> bool:
    """
    Validate Redis connection if configured.

    Returns:
        True if Redis is accessible or not configured
    """
    if not settings.REDIS_URL:
        logger.info("Redis not configured - skipping validation")
        return True

    try:
        import aioredis
        redis = await aioredis.from_url(settings.REDIS_URL)
        await redis.ping()
        await redis.close()
        logger.info("Redis connection validated")
        return True

    except ImportError:
        logger.warning("aioredis not installed - Redis validation skipped")
        return True

    except Exception as e:
        logger.warning(f"Redis connection failed: {e}")
        return False


async def run_all_validations(fail_on_critical: bool = True) -> dict:
    """
    Run all startup validations including async checks.

    Args:
        fail_on_critical: Fail if critical validations fail

    Returns:
        Dict with validation results
    """
    results = {
        "config": False,
        "database": False,
        "redis": False,
        "overall": False,
    }

    # Config validation
    try:
        results["config"] = run_startup_validation(fail_on_error=fail_on_critical)
    except StartupValidationError:
        if fail_on_critical:
            raise

    # Database validation
    results["database"] = await validate_database_connection()
    if not results["database"] and fail_on_critical:
        raise StartupValidationError("Database connection failed")

    # Redis validation (non-critical)
    results["redis"] = await validate_redis_connection()

    # Overall result
    results["overall"] = results["config"] and results["database"]

    return results
