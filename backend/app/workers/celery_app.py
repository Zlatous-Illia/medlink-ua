from celery import Celery
from app.core.config import settings

celery_app = Celery(
    "medlink",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=["app.workers.email_tasks"],
)
celery_app.conf.timezone = "Europe/Kiev"
