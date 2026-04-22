"""
Celery app for distributed OSINT task processing.
Uses Redis as broker. Configure via CELERY_BROKER_URL / REDIS_URL.
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from celery import Celery

broker_url = os.getenv("CELERY_BROKER_URL") or os.getenv("REDIS_URL", "redis://localhost:6379/0")
result_backend = os.getenv("CELERY_RESULT_BACKEND") or broker_url

celery_app = Celery(
    "osint_platform",
    broker=broker_url,
    backend=result_backend,
    include=["backend.tasks"],
)
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    result_expires=3600,
)
