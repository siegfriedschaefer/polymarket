"""Celery application configuration."""

from celery import Celery
from celery.schedules import crontab

from polymarket_bot.config import settings
from polymarket_bot.utils.logging import setup_logging

setup_logging()

celery_app = Celery(
    "polymarket_bot",
    broker=settings.celery_broker,
    backend=settings.celery_backend,
    include=["polymarket_bot.tasks.trading_tasks"]
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=300,
    task_soft_time_limit=270,
    worker_prefetch_multiplier=1,
    worker_max_tasks_per_child=1000,
)

celery_app.conf.beat_schedule = {
    "run-strategy-every-5-minutes": {
        "task": "polymarket_bot.tasks.trading_tasks.run_strategy",
        "schedule": 300.0,
    },
    "update-positions-every-minute": {
        "task": "polymarket_bot.tasks.trading_tasks.update_positions",
        "schedule": 60.0,
    },
}
