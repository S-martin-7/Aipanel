"""
Request Context Management.

Provides request-scoped context variables for tenant_id, user_id, and request_id.
These values are automatically included in all log messages.
"""

import uuid
from contextvars import ContextVar
from typing import Optional
from dataclasses import dataclass

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

from app.utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class RequestContext:
    """Container for request-scoped context data."""
    request_id: str
    tenant_id: Optional[str] = None
    user_id: Optional[str] = None
    api_key_id: Optional[str] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    path: Optional[str] = None
    method: Optional[str] = None


# Context variable to store request context
_request_context: ContextVar[Optional[RequestContext]] = ContextVar(
    "request_context", default=None
)


def get_request_context() -> Optional[RequestContext]:
    """Get the current request context."""
    return _request_context.get()


def get_request_id() -> Optional[str]:
    """Get the current request ID."""
    ctx = _request_context.get()
    return ctx.request_id if ctx else None


def get_tenant_id() -> Optional[str]:
    """Get the current tenant ID from context."""
    ctx = _request_context.get()
    return ctx.tenant_id if ctx else None


def get_user_id() -> Optional[str]:
    """Get the current user ID from context."""
    ctx = _request_context.get()
    return ctx.user_id if ctx else None


def set_tenant_id(tenant_id: str) -> None:
    """Set the tenant ID in the current context."""
    ctx = _request_context.get()
    if ctx:
        ctx.tenant_id = tenant_id


def set_user_id(user_id: str) -> None:
    """Set the user ID in the current context."""
    ctx = _request_context.get()
    if ctx:
        ctx.user_id = user_id


def set_api_key_id(api_key_id: str) -> None:
    """Set the API key ID in the current context."""
    ctx = _request_context.get()
    if ctx:
        ctx.api_key_id = api_key_id


class RequestContextMiddleware(BaseHTTPMiddleware):
    """
    Middleware that sets up request context for logging and tracing.

    Extracts:
    - request_id from X-Request-ID header or generates one
    - Client IP from X-Forwarded-For or client.host
    - User-Agent header

    Tenant and user IDs are set later by auth dependencies.
    """

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        # Get or generate request ID
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())

        # Get client IP
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            ip_address = forwarded_for.split(",")[0].strip()
        else:
            ip_address = request.client.host if request.client else None

        # Create context
        context = RequestContext(
            request_id=request_id,
            ip_address=ip_address,
            user_agent=request.headers.get("User-Agent"),
            path=str(request.url.path),
            method=request.method,
        )

        # Set context for this request
        token = _request_context.set(context)

        # Store request_id in request state for easy access
        request.state.request_id = request_id

        try:
            # Log request start
            logger.info(
                f"Request started: {request.method} {request.url.path}",
                extra={
                    "request_id": request_id,
                    "method": request.method,
                    "path": str(request.url.path),
                    "ip": ip_address,
                }
            )

            response = await call_next(request)

            # Add request ID to response headers
            response.headers["X-Request-ID"] = request_id

            # Log request end
            logger.info(
                f"Request completed: {response.status_code}",
                extra={
                    "request_id": request_id,
                    "status_code": response.status_code,
                    "tenant_id": context.tenant_id,
                    "user_id": context.user_id,
                }
            )

            return response

        except Exception as e:
            logger.error(
                f"Request failed: {type(e).__name__}: {str(e)}",
                extra={
                    "request_id": request_id,
                    "tenant_id": context.tenant_id,
                    "user_id": context.user_id,
                    "error": str(e),
                },
                exc_info=True,
            )
            raise

        finally:
            # Reset context
            _request_context.reset(token)


class ContextualLoggerAdapter:
    """
    Logger adapter that automatically includes request context.

    Usage:
        logger = ContextualLoggerAdapter(get_logger(__name__))
        logger.info("Something happened")  # Includes request_id, tenant_id, etc.
    """

    def __init__(self, logger):
        self._logger = logger

    def _get_extra(self, extra: Optional[dict] = None) -> dict:
        """Build extra dict with context values."""
        ctx = get_request_context()
        result = {}

        if ctx:
            result["request_id"] = ctx.request_id
            if ctx.tenant_id:
                result["tenant_id"] = ctx.tenant_id
            if ctx.user_id:
                result["user_id"] = ctx.user_id
            if ctx.api_key_id:
                result["api_key_id"] = ctx.api_key_id

        if extra:
            result.update(extra)

        return result

    def debug(self, msg: str, extra: Optional[dict] = None, **kwargs):
        self._logger.debug(msg, extra=self._get_extra(extra), **kwargs)

    def info(self, msg: str, extra: Optional[dict] = None, **kwargs):
        self._logger.info(msg, extra=self._get_extra(extra), **kwargs)

    def warning(self, msg: str, extra: Optional[dict] = None, **kwargs):
        self._logger.warning(msg, extra=self._get_extra(extra), **kwargs)

    def error(self, msg: str, extra: Optional[dict] = None, **kwargs):
        self._logger.error(msg, extra=self._get_extra(extra), **kwargs)

    def critical(self, msg: str, extra: Optional[dict] = None, **kwargs):
        self._logger.critical(msg, extra=self._get_extra(extra), **kwargs)

    def exception(self, msg: str, extra: Optional[dict] = None, **kwargs):
        self._logger.exception(msg, extra=self._get_extra(extra), **kwargs)


def get_contextual_logger(name: str) -> ContextualLoggerAdapter:
    """Get a logger that automatically includes request context."""
    return ContextualLoggerAdapter(get_logger(name))
