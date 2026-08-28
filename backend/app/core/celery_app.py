from celery import Celery

from app.core.config import get_settings

settings = get_settings()

# https://docs.celeryq.dev — broker = Redis (see app.core.cache)
celery_app = Celery(
    "cryptoexchange",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=["app.tasks"],
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,
    broker_connection_retry_on_startup=True,
    task_always_eager=settings.CELERY_TASK_ALWAYS_EAGER,
    beat_schedule={
        "refresh-market-stats": {
            "task": "app.tasks.refresh_market_stats",
            "schedule": 60.0,
        },
        "cleanup-stale-transactions": {
            "task": "app.tasks.cleanup_stale_transactions",
            "schedule": 86400.0,
        },
    },
)