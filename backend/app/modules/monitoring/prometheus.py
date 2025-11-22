"""
Prometheus metrics for AIPanel.

Provides application metrics for monitoring and alerting.
"""

from prometheus_client import Counter, Histogram, Gauge, Info, generate_latest, CONTENT_TYPE_LATEST
from fastapi import APIRouter, Response
from functools import wraps
import time

from app.core.config import settings

router = APIRouter()

# Application Info
app_info = Info("aipanel", "AIPanel application information")
app_info.info({
    "version": settings.VERSION,
    "environment": settings.ENVIRONMENT,
})

# Request metrics
http_requests_total = Counter(
    "http_requests_total",
    "Total HTTP requests",
    ["method", "endpoint", "status_code"],
)

http_request_duration_seconds = Histogram(
    "http_request_duration_seconds",
    "HTTP request duration in seconds",
    ["method", "endpoint"],
    buckets=[0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0],
)

http_requests_in_progress = Gauge(
    "http_requests_in_progress",
    "HTTP requests currently being processed",
    ["method", "endpoint"],
)

# Business metrics
tenants_total = Gauge(
    "aipanel_tenants_total",
    "Total number of tenants",
    ["status"],
)

agents_total = Gauge(
    "aipanel_agents_total",
    "Total number of agents",
    ["status"],
)

conversations_total = Counter(
    "aipanel_conversations_total",
    "Total number of conversations",
    ["tenant_id"],
)

messages_total = Counter(
    "aipanel_messages_total",
    "Total number of messages",
    ["tenant_id", "role"],
)

# AI metrics
ai_requests_total = Counter(
    "aipanel_ai_requests_total",
    "Total AI API requests",
    ["provider", "model", "status"],
)

ai_request_duration_seconds = Histogram(
    "aipanel_ai_request_duration_seconds",
    "AI API request duration in seconds",
    ["provider", "model"],
    buckets=[0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0, 60.0],
)

tokens_used_total = Counter(
    "aipanel_tokens_used_total",
    "Total tokens used",
    ["tenant_id", "model", "type"],  # type: input, output, reasoning
)

ai_cost_total = Counter(
    "aipanel_ai_cost_total",
    "Total AI cost in USD",
    ["tenant_id", "model"],
)

# Billing metrics
mrr_total = Gauge(
    "aipanel_mrr_total",
    "Monthly Recurring Revenue in CLP",
)

payments_total = Counter(
    "aipanel_payments_total",
    "Total payments processed",
    ["status", "method"],
)

payment_amount_total = Counter(
    "aipanel_payment_amount_total",
    "Total payment amount in CLP",
    ["status"],
)

# Document processing metrics
documents_processed_total = Counter(
    "aipanel_documents_processed_total",
    "Total documents processed",
    ["status"],
)

document_processing_duration_seconds = Histogram(
    "aipanel_document_processing_duration_seconds",
    "Document processing duration in seconds",
    buckets=[1.0, 5.0, 10.0, 30.0, 60.0, 120.0, 300.0],
)

# Queue metrics
celery_tasks_total = Counter(
    "aipanel_celery_tasks_total",
    "Total Celery tasks",
    ["task_name", "status"],
)

celery_task_duration_seconds = Histogram(
    "aipanel_celery_task_duration_seconds",
    "Celery task duration in seconds",
    ["task_name"],
)

# Error metrics
errors_total = Counter(
    "aipanel_errors_total",
    "Total errors",
    ["type", "endpoint"],
)


# Decorator for tracking AI requests
def track_ai_request(provider: str, model: str):
    """Decorator to track AI request metrics."""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            start_time = time.time()
            status = "success"
            try:
                result = await func(*args, **kwargs)
                return result
            except Exception as e:
                status = "error"
                raise
            finally:
                duration = time.time() - start_time
                ai_requests_total.labels(
                    provider=provider,
                    model=model,
                    status=status,
                ).inc()
                ai_request_duration_seconds.labels(
                    provider=provider,
                    model=model,
                ).observe(duration)
        return wrapper
    return decorator


# Helper functions for recording metrics
def record_tokens_used(tenant_id: str, model: str, input_tokens: int, output_tokens: int, reasoning_tokens: int = 0):
    """Record token usage metrics."""
    tokens_used_total.labels(tenant_id=tenant_id, model=model, type="input").inc(input_tokens)
    tokens_used_total.labels(tenant_id=tenant_id, model=model, type="output").inc(output_tokens)
    if reasoning_tokens > 0:
        tokens_used_total.labels(tenant_id=tenant_id, model=model, type="reasoning").inc(reasoning_tokens)


def record_ai_cost(tenant_id: str, model: str, cost_usd: float):
    """Record AI cost metrics."""
    ai_cost_total.labels(tenant_id=tenant_id, model=model).inc(cost_usd)


def record_payment(status: str, method: str, amount: int):
    """Record payment metrics."""
    payments_total.labels(status=status, method=method).inc()
    payment_amount_total.labels(status=status).inc(amount)


def record_error(error_type: str, endpoint: str):
    """Record error metrics."""
    errors_total.labels(type=error_type, endpoint=endpoint).inc()


def update_business_metrics(
    active_tenants: int = 0,
    trial_tenants: int = 0,
    suspended_tenants: int = 0,
    active_agents: int = 0,
    paused_agents: int = 0,
    current_mrr: int = 0,
):
    """Update gauge metrics with current values."""
    tenants_total.labels(status="active").set(active_tenants)
    tenants_total.labels(status="trial").set(trial_tenants)
    tenants_total.labels(status="suspended").set(suspended_tenants)
    agents_total.labels(status="active").set(active_agents)
    agents_total.labels(status="paused").set(paused_agents)
    mrr_total.set(current_mrr)


@router.get("/prometheus")
async def prometheus_metrics():
    """
    Prometheus metrics endpoint.

    Returns metrics in Prometheus text format.
    """
    return Response(
        content=generate_latest(),
        media_type=CONTENT_TYPE_LATEST,
    )
