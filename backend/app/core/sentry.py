"""
Sentry integration for error tracking and performance monitoring.

Provides centralized error tracking, alerting, and performance insights.
"""

import sentry_sdk
from sentry_sdk.integrations.fastapi import FastApiIntegration
from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration
from sentry_sdk.integrations.celery import CeleryIntegration
from sentry_sdk.integrations.redis import RedisIntegration
from sentry_sdk.integrations.httpx import HttpxIntegration
from typing import Optional, Dict, Any

from app.core.config import settings
from app.utils.logger import get_logger

logger = get_logger(__name__)


def init_sentry():
    """
    Initialize Sentry SDK with all integrations.

    Should be called early in application startup.
    """
    if not settings.SENTRY_DSN:
        logger.warning("Sentry DSN not configured, error tracking disabled")
        return

    sentry_sdk.init(
        dsn=settings.SENTRY_DSN,
        environment=settings.ENVIRONMENT,
        release=f"aipanel@{settings.VERSION}",

        # Performance monitoring
        traces_sample_rate=0.1 if settings.ENVIRONMENT == "production" else 1.0,
        profiles_sample_rate=0.1 if settings.ENVIRONMENT == "production" else 1.0,

        # Integrations
        integrations=[
            FastApiIntegration(transaction_style="endpoint"),
            SqlalchemyIntegration(),
            CeleryIntegration(),
            RedisIntegration(),
            HttpxIntegration(),
        ],

        # Data scrubbing
        send_default_pii=False,
        before_send=before_send,
        before_send_transaction=before_send_transaction,

        # Additional options
        attach_stacktrace=True,
        max_breadcrumbs=50,
        debug=settings.ENVIRONMENT == "development",
    )

    logger.info(f"Sentry initialized for environment: {settings.ENVIRONMENT}")


def before_send(event: Dict[str, Any], hint: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Process event before sending to Sentry.

    Filter out sensitive data and unnecessary errors.
    """
    # Filter out expected exceptions
    if "exc_info" in hint:
        exc_type, exc_value, _ = hint["exc_info"]
        exc_name = exc_type.__name__

        # Don't report common expected errors
        ignored_exceptions = [
            "HTTPException",
            "RequestValidationError",
            "AuthenticationError",
            "RateLimitExceeded",
        ]

        if exc_name in ignored_exceptions:
            return None

    # Remove sensitive data from request
    if "request" in event:
        request = event["request"]

        # Remove sensitive headers
        if "headers" in request:
            sensitive_headers = ["authorization", "x-api-key", "cookie"]
            request["headers"] = {
                k: "[Filtered]" if k.lower() in sensitive_headers else v
                for k, v in request.get("headers", {}).items()
            }

        # Remove sensitive body fields
        if "data" in request:
            sensitive_fields = ["password", "token", "api_key", "secret"]
            if isinstance(request["data"], dict):
                request["data"] = {
                    k: "[Filtered]" if any(s in k.lower() for s in sensitive_fields) else v
                    for k, v in request["data"].items()
                }

    # Add custom tags
    event.setdefault("tags", {})
    event["tags"]["app"] = "aipanel"

    return event


def before_send_transaction(event: Dict[str, Any], hint: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Process transaction before sending to Sentry.

    Filter out noisy transactions.
    """
    # Don't track health check endpoints
    transaction_name = event.get("transaction", "")
    ignored_transactions = [
        "/health",
        "/ready",
        "/live",
        "/metrics",
        "/prometheus",
    ]

    if any(transaction_name.endswith(t) for t in ignored_transactions):
        return None

    return event


def capture_exception(
    exception: Exception,
    context: Optional[Dict[str, Any]] = None,
    user_id: Optional[str] = None,
    tenant_id: Optional[str] = None,
):
    """
    Capture an exception and send to Sentry with context.

    Args:
        exception: The exception to capture
        context: Additional context data
        user_id: Optional user ID
        tenant_id: Optional tenant ID
    """
    with sentry_sdk.push_scope() as scope:
        # Add user context
        if user_id:
            scope.set_user({"id": user_id})

        # Add tenant context
        if tenant_id:
            scope.set_tag("tenant_id", tenant_id)

        # Add custom context
        if context:
            scope.set_context("custom", context)

        sentry_sdk.capture_exception(exception)


def capture_message(
    message: str,
    level: str = "info",
    context: Optional[Dict[str, Any]] = None,
    tenant_id: Optional[str] = None,
):
    """
    Capture a message and send to Sentry.

    Args:
        message: The message to capture
        level: Log level (debug, info, warning, error, fatal)
        context: Additional context data
        tenant_id: Optional tenant ID
    """
    with sentry_sdk.push_scope() as scope:
        if tenant_id:
            scope.set_tag("tenant_id", tenant_id)

        if context:
            scope.set_context("custom", context)

        sentry_sdk.capture_message(message, level=level)


def set_user_context(user_id: str, email: Optional[str] = None, tenant_id: Optional[str] = None):
    """
    Set the current user context for Sentry.

    Should be called after authentication.
    """
    sentry_sdk.set_user({
        "id": user_id,
        "email": email,
    })

    if tenant_id:
        sentry_sdk.set_tag("tenant_id", tenant_id)


def add_breadcrumb(
    message: str,
    category: str = "custom",
    level: str = "info",
    data: Optional[Dict[str, Any]] = None,
):
    """
    Add a breadcrumb to the current scope.

    Breadcrumbs are used to understand the sequence of events leading to an error.
    """
    sentry_sdk.add_breadcrumb(
        message=message,
        category=category,
        level=level,
        data=data,
    )


def start_transaction(name: str, op: str = "task"):
    """
    Start a new transaction for performance monitoring.

    Returns a context manager.
    """
    return sentry_sdk.start_transaction(name=name, op=op)


# Decorator for capturing errors in async functions
def capture_errors(func):
    """Decorator to capture errors and send to Sentry."""
    async def wrapper(*args, **kwargs):
        try:
            return await func(*args, **kwargs)
        except Exception as e:
            capture_exception(e)
            raise
    return wrapper
