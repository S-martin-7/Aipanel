"""
Celery application configuration.
"""
from celery import Celery
from celery.schedules import crontab
from app.core.config import settings

# Create Celery app
celery_app = Celery(
    "aipanel",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
    include=[
        "app.tasks.document_tasks",
        "app.tasks.email_tasks",
        "app.tasks.billing_tasks",
        "app.tasks.usage_tasks",
        "app.tasks.webhook_tasks",
    ]
)

# Celery configuration
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="America/Santiago",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=600,  # 10 minutes max
    task_soft_time_limit=300,  # 5 minutes soft limit
    worker_prefetch_multiplier=1,
    task_acks_late=True,
    task_reject_on_worker_lost=True,
)

# Scheduled tasks (Celery Beat)
celery_app.conf.beat_schedule = {
    # Check trial expirations daily at 9 AM
    "check-trial-expirations": {
        "task": "app.tasks.billing_tasks.check_trial_expirations",
        "schedule": crontab(hour=9, minute=0),
    },
    # Generate invoices at 1st of month
    "generate-monthly-invoices": {
        "task": "app.tasks.billing_tasks.generate_monthly_invoices",
        "schedule": crontab(day_of_month=1, hour=6, minute=0),
    },
    # Aggregate daily usage at midnight
    "aggregate-daily-usage": {
        "task": "app.tasks.usage_tasks.aggregate_daily_usage",
        "schedule": crontab(hour=0, minute=5),
    },
    # Check usage thresholds every hour
    "check-usage-thresholds": {
        "task": "app.tasks.usage_tasks.check_all_thresholds",
        "schedule": crontab(minute=0),
    },
    # Retry failed webhooks every 5 minutes
    "retry-failed-webhooks": {
        "task": "app.tasks.webhook_tasks.retry_failed_deliveries",
        "schedule": crontab(minute="*/5"),
    },
    # Clean old data weekly
    "cleanup-old-data": {
        "task": "app.tasks.usage_tasks.cleanup_old_data",
        "schedule": crontab(day_of_week=0, hour=3, minute=0),
    },
}
