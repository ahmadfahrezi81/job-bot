# app/celery_app.py
from celery import Celery
import os
from dotenv import load_dotenv

load_dotenv()

# Redis connection
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

celery_app = Celery(
    "job_bot",
    broker=REDIS_URL,
    backend=REDIS_URL,
    include=["app.tasks"],  # Import tasks module
)

# Celery config
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=1800,  # 30 min hard limit
    task_soft_time_limit=1500,  # 25 min soft limit
    result_expires=3600,  # Results expire after 1 hour
    worker_pool="solo",  # Use solo pool instead of prefork (fixes event loop issues)
)
