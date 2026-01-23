# ===========================================
# AuraTask - Notification Scheduler Service
# ===========================================
# Event-driven notification scheduling using Celery ETA

from datetime import datetime, timedelta, timezone
from typing import List, Optional, Tuple

from app.models.task import Task
from app.models.notification import NotificationSettings
from app.workers.celery_app import celery_app, get_predictable_task_id


class NotificationScheduler:
    """
    Schedules Celery tasks with precise ETAs for task notifications.
    
    Uses event-driven approach: notifications are scheduled when tasks
    are created/updated, not by polling.
    """
    
    def schedule_task_notifications(
        self,
        task: Task,
        user_settings: NotificationSettings,
    ) -> List[Tuple[str, str]]:
        """
        Schedule 1-hour and 24-hour reminder notifications for a task.
        
        Args:
            task: Task to schedule notifications for
            user_settings: User's notification preferences
            
        Returns:
            List of (reminder_type, celery_task_id) tuples for scheduled tasks
        """
        # Import here to avoid circular imports
        from app.workers.notification_sender import send_task_reminder
        
        now = datetime.now(timezone.utc)
        scheduled_tasks = []
        
        # Ensure due_date is timezone-aware
        due_date = task.due_date
        if due_date.tzinfo is None:
            due_date = due_date.replace(tzinfo=timezone.utc)
        
        # Schedule 24-hour reminder
        if user_settings.notify_24hr_before:
            eta_24hr = due_date - timedelta(hours=24)
            if eta_24hr > now:
                task_id = get_predictable_task_id(task.id, "24hr")
                send_task_reminder.apply_async(
                    args=[task.id, "24_HOUR"],
                    eta=eta_24hr,
                    task_id=task_id,
                )
                scheduled_tasks.append(("24_HOUR", task_id))
        
        # Schedule 1-hour reminder
        if user_settings.notify_1hr_before:
            eta_1hr = due_date - timedelta(hours=1)
            if eta_1hr > now:
                task_id = get_predictable_task_id(task.id, "1hr")
                send_task_reminder.apply_async(
                    args=[task.id, "1_HOUR"],
                    eta=eta_1hr,
                    task_id=task_id,
                )
                scheduled_tasks.append(("1_HOUR", task_id))
        
        # Schedule AT_DUE reminder (exactly when task is due)
        # Always schedule this as it's the most important notification
        if due_date > now:
            task_id = get_predictable_task_id(task.id, "at_due")
            send_task_reminder.apply_async(
                args=[task.id, "AT_DUE"],
                eta=due_date,
                task_id=task_id,
            )
            scheduled_tasks.append(("AT_DUE", task_id))
        
        return scheduled_tasks
    
    def revoke_task_notifications(self, task_id: int) -> None:
        """
        Cancel all pending notifications for a task.
        
        Called when a task is completed, cancelled, or deleted.
        
        Args:
            task_id: Database ID of the task
        """
        # Revoke all reminder types using predictable IDs
        celery_task_id_1hr = get_predictable_task_id(task_id, "1hr")
        celery_task_id_24hr = get_predictable_task_id(task_id, "24hr")
        celery_task_id_at_due = get_predictable_task_id(task_id, "at_due")
        
        celery_app.control.revoke(celery_task_id_1hr, terminate=True)
        celery_app.control.revoke(celery_task_id_24hr, terminate=True)
        celery_app.control.revoke(celery_task_id_at_due, terminate=True)
    
    def reschedule_task_notifications(
        self,
        task: Task,
        user_settings: NotificationSettings,
    ) -> List[Tuple[str, str]]:
        """
        Reschedule notifications when a task's due date changes.
        
        Args:
            task: Task with updated due date
            user_settings: User's notification preferences
            
        Returns:
            List of newly scheduled (reminder_type, celery_task_id) tuples
        """
        # First, cancel existing notifications
        self.revoke_task_notifications(task.id)
        
        # Then schedule new ones
        return self.schedule_task_notifications(task, user_settings)


# Singleton instance
notification_scheduler = NotificationScheduler()


def schedule_notifications(task: Task, user_settings: NotificationSettings):
    """Convenience function to schedule notifications."""
    return notification_scheduler.schedule_task_notifications(task, user_settings)


def revoke_notifications(task_id: int):
    """Convenience function to revoke notifications."""
    notification_scheduler.revoke_task_notifications(task_id)


def reschedule_notifications(task: Task, user_settings: NotificationSettings):
    """Convenience function to reschedule notifications."""
    return notification_scheduler.reschedule_task_notifications(task, user_settings)
