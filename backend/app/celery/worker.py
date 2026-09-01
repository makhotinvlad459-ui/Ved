# backend/app/celery/worker.py
from celery import Celery
import os

# Настройка Celery
REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379/0")

celery_app = Celery(
    "ved_worker",
    broker=REDIS_URL,
    backend=REDIS_URL,
    include=["app.celery.tasks"]
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=3600,
    task_soft_time_limit=3000,
)


@celery_app.task(name="ping")
def ping():
    """Тестовая задача"""
    return "pong"
# ============================================
# Настройка периодических задач (Celery Beat)
# ============================================
from celery.schedules import crontab

celery_app.conf.beat_schedule = {
    'cleanup-old-files-daily': {
        'task': 'cleanup_old_files',
        'schedule': crontab(hour=3, minute=0),  # каждый день в 3:00
        'args': (),
    },
}
