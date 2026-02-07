# ===========================================
# AuraTask - Schemas Package
# ===========================================

from app.schemas.user import (
    UserCreate,
    UserLogin,
    UserUpdate,
    UserResponse,
    UserInDB,
)
from app.schemas.task import (
    TaskCreate,
    TaskUpdate,
    TaskSnooze,
    TaskResponse,
    TaskListResponse,
)
from app.schemas.notification import (
    NotificationSettingsUpdate,
    NotificationSettingsResponse,
    NotificationLogResponse,
    NotificationTest,
)
from app.schemas.subtask import (
    SubtaskCreate,
    SubtaskUpdate,
    SubtaskResponse,
)

__all__ = [
    # User
    "UserCreate",
    "UserUpdate",
    "UserResponse",
    "UserInDB",
    # Task
    "TaskCreate",
    "TaskUpdate",
    "TaskSnooze",
    "TaskResponse",
    "TaskListResponse",
    # Notification
    "NotificationSettingsUpdate",
    "NotificationSettingsResponse",
    "NotificationLogResponse",
    "NotificationTest",
    # Subtask
    "SubtaskCreate",
    "SubtaskUpdate",
    "SubtaskResponse",
]
