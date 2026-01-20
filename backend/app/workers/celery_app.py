# ===========================================
# AuraTask - Celery Application Configuration
# ===========================================
# Event-driven task queue for notifications

from celery import Celery
from celery.schedules import crontab

from app.config import settings


# Initialize Celery with Redis as broker
celery_app = Celery(
    "auratask",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
    include=[
        "app.workers.notification_sender",
        "app.workers.urgency_updater",
    ],
)

# Celery Configuration
celery_app.conf.update(
    # Task execution settings
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    
    # Task tracking for revocation
    task_track_started=True,
    result_expires=86400,  # Results expire after 1 day
    
    # Task naming convention for predictable IDs
    task_create_missing_queues=True,
    
    # Worker settings
    worker_prefetch_multiplier=1,
    task_acks_late=True,
    
    # Retry settings
    task_default_retry_delay=60,
    task_max_retries=3,
)

# Beat schedule for periodic tasks
celery_app.conf.beat_schedule = {
    # Recalculate urgency scores every 5 minutes
    "update-urgency-scores": {
        "task": "app.workers.urgency_updater.update_all_urgency_scores",
        "schedule": 300.0,  # Every 5 minutes
    },
    # Clean up old notification logs daily at 2 AM
    "cleanup-notification-logs": {
        "task": "app.workers.notification_sender.cleanup_old_logs",
        "schedule": crontab(hour=2, minute=0),
    },
}


def get_predictable_task_id(task_id: int, reminder_type: str) -> str:
    """
    Generate a predictable Celery task ID for notification revocation.
    
    Args:
        task_id: Database task ID
        reminder_type: Type of reminder ('1hr' or '24hr')
        
    Returns:
        Predictable task ID string
    """
    return f"notify_{reminder_type}_{task_id}"
