from celery import Celery

from vivido.core import get_settings

settings = get_settings()

celery_app = Celery(
    "vivido",
    broker=settings.redis_url,
    backend=settings.redis_url,
    include=["vivido.celery_worker.tasks"],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=300,
    worker_prefetch_multiplier=1,
)
