# ===========================================
# AuraTask - CRUD Package
# ===========================================

from app.crud.user import (
    get_user_by_email,
    get_user_by_id,
    create_user,
    update_user_timezone,
    authenticate_user,
    hash_password,
    verify_password,
)
from app.crud.task import (
    create_task,
    get_task_by_id,
    get_tasks_multi,
    update_task,
    complete_task,
    snooze_task,
    delete_task,
    get_tasks_due_soon,
)
from app.crud.subtasks import (
    create_subtask,
    get_subtask_by_id,
    toggle_subtask,
    check_auto_complete_task,
)

__all__ = [
    # User
    "get_user_by_email",
    "get_user_by_id",
    "create_user",
    "update_user_timezone",
    "authenticate_user",
    "hash_password",
    "verify_password",
    # Task
    "create_task",
    "get_task_by_id",
    "get_tasks_multi",
    "update_task",
    "complete_task",
    "snooze_task",
    "delete_task",
    "get_tasks_due_soon",
    # Subtask
    "create_subtask",
    "get_subtask_by_id",
    "toggle_subtask",
    "check_auto_complete_task",
]
