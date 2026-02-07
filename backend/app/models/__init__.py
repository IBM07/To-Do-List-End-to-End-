# ===========================================
# AuraTask - Models Package
# ===========================================
# Import all models here so Alembic can discover them

from app.database import Base
from app.models.user import User
from app.models.task import Task, Priority, TaskStatus
from app.models.notification import (
    NotificationSettings,
    NotificationLog,
    NotificationChannel,
    NotificationStatus,
)
from app.models.subtask import Subtask

# Export all models for easy imports
__all__ = [
    # User
    "User",
    # Task
    "Task",
    "Priority",
    "TaskStatus",
    # Notification
    "NotificationSettings",
    "NotificationLog",
    "NotificationChannel",
    "NotificationStatus",
    # Subtask
    "Subtask",
]
