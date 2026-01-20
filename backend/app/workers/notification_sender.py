# ===========================================
# AuraTask - Notification Sender Worker
# ===========================================
# Celery task for sending notifications via Apprise

from datetime import datetime, timezone
from typing import Optional

import apprise
from celery import shared_task

from app.config import settings
from app.database import get_sync_session
from app.models.task import Task, TaskStatus
from app.models.notification import (
    NotificationLog,
    NotificationSettings,
    NotificationChannel,
    NotificationStatus,
)
from app.models.user import User


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def send_task_reminder(self, task_id: int, reminder_type: str):
    """
    Send a task reminder notification.
    
    This task is scheduled with an ETA by the NotificationScheduler.
    It re-verifies task status before sending to handle race conditions.
    
    Args:
        task_id: Database ID of the task
        reminder_type: "1_HOUR" or "24_HOUR"
        
    Returns:
        Dict with status and details
    """
    with get_sync_session() as db:
        try:
            # Step 1: Fetch the task and verify it's still valid
            task = db.query(Task).filter(Task.id == task_id).first()
            
            if not task:
                return {"status": "skipped", "reason": "task_not_found"}
            
            # Skip if task is completed or cancelled
            if task.status in [TaskStatus.COMPLETED, TaskStatus.CANCELLED]:
                return {"status": "skipped", "reason": "task_completed"}
            
            # Skip if task is snoozed
            if task.snoozed_until and task.snoozed_until > datetime.now(timezone.utc):
                return {"status": "skipped", "reason": "task_snoozed"}
            
            # Step 2: Get user and notification settings
            user = db.query(User).filter(User.id == task.user_id).first()
            if not user:
                return {"status": "skipped", "reason": "user_not_found"}
            
            notification_settings = db.query(NotificationSettings).filter(
                NotificationSettings.user_id == user.id
            ).first()
            
            if not notification_settings:
                return {"status": "skipped", "reason": "no_notification_settings"}
            
            # Step 3: Build notification message
            time_left = "1 hour" if reminder_type == "1_HOUR" else "24 hours"
            subject = f"⏰ Task Due in {time_left}: {task.title[:50]}"
            body = f"""
Task Reminder from AuraTask

📋 Task: {task.title}
⏰ Due: {task.due_date.strftime("%b %d, %Y at %I:%M %p")} UTC
🔥 Priority: {task.priority.value}

{task.description or 'No description provided.'}

---
Log in to AuraTask to manage your tasks.
            """.strip()
            
            # Step 4: Send via configured channels
            sent_channels = []
            errors = []
            
            # Email notification
            if notification_settings.email_enabled and notification_settings.email_address:
                success, error = _send_email(
                    notification_settings.email_address,
                    subject,
                    body
                )
                if success:
                    sent_channels.append(NotificationChannel.EMAIL)
                    _log_notification(db, task_id, NotificationChannel.EMAIL, NotificationStatus.SENT, reminder_type)
                else:
                    errors.append(f"EMAIL: {error}")
                    _log_notification(db, task_id, NotificationChannel.EMAIL, NotificationStatus.FAILED, reminder_type, error)
            
            # Telegram notification
            if notification_settings.telegram_enabled and notification_settings.telegram_chat_id:
                success, error = _send_telegram(
                    notification_settings.telegram_chat_id,
                    subject,
                    body
                )
                if success:
                    sent_channels.append(NotificationChannel.TELEGRAM)
                    _log_notification(db, task_id, NotificationChannel.TELEGRAM, NotificationStatus.SENT, reminder_type)
                else:
                    errors.append(f"TELEGRAM: {error}")
                    _log_notification(db, task_id, NotificationChannel.TELEGRAM, NotificationStatus.FAILED, reminder_type, error)
            
            # Discord notification
            if notification_settings.discord_enabled and notification_settings.discord_webhook_url:
                success, error = _send_discord(
                    notification_settings.discord_webhook_url,
                    subject,
                    body
                )
                if success:
                    sent_channels.append(NotificationChannel.DISCORD)
                    _log_notification(db, task_id, NotificationChannel.DISCORD, NotificationStatus.SENT, reminder_type)
                else:
                    errors.append(f"DISCORD: {error}")
                    _log_notification(db, task_id, NotificationChannel.DISCORD, NotificationStatus.FAILED, reminder_type, error)
            
            db.commit()
            
            return {
                "status": "sent" if sent_channels else "no_channels",
                "channels": [c.value for c in sent_channels],
                "errors": errors,
            }
            
        except Exception as e:
            db.rollback()
            # Retry on failure
            raise self.retry(exc=e)


def _send_email(to_email: str, subject: str, body: str) -> tuple[bool, Optional[str]]:
    """Send email via Gmail SMTP using smtplib."""
    try:
        if not settings.SMTP_USER or not settings.SMTP_PASSWORD:
            return False, "SMTP not configured"
        
        # Use direct smtplib email service
        import smtplib
        from email.mime.text import MIMEText
        from email.mime.multipart import MIMEMultipart
        
        # Create message
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = f"{settings.SMTP_FROM_NAME} <{settings.SMTP_FROM_EMAIL or settings.SMTP_USER}>"
        msg["To"] = to_email
        
        part = MIMEText(body, "plain")
        msg.attach(part)
        
        # Send via SMTP
        with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT) as server:
            server.starttls()
            server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
            server.sendmail(
                settings.SMTP_FROM_EMAIL or settings.SMTP_USER,
                to_email,
                msg.as_string()
            )
        
        return True, None
    except Exception as e:
        return False, str(e)


def _send_telegram(chat_id: str, subject: str, body: str) -> tuple[bool, Optional[str]]:
    """Send message via Telegram bot."""
    try:
        if not settings.TELEGRAM_BOT_TOKEN:
            return False, "Telegram bot not configured"
        
        apobj = apprise.Apprise()
        telegram_url = f"tgram://{settings.TELEGRAM_BOT_TOKEN}/{chat_id}"
        apobj.add(telegram_url)
        
        message = f"*{subject}*\n\n{body}"
        result = apobj.notify(
            body=message,
            notify_type=apprise.NotifyType.INFO,
        )
        
        return result, None if result else "Telegram send failed"
    except Exception as e:
        return False, str(e)


def _send_discord(webhook_url: str, subject: str, body: str) -> tuple[bool, Optional[str]]:
    """Send message via Discord webhook."""
    try:
        apobj = apprise.Apprise()
        # Convert webhook URL to Apprise format
        # Discord webhook: https://discord.com/api/webhooks/{id}/{token}
        apobj.add(webhook_url)
        
        result = apobj.notify(
            title=subject,
            body=body,
            notify_type=apprise.NotifyType.INFO,
        )
        
        return result, None if result else "Discord send failed"
    except Exception as e:
        return False, str(e)


def _log_notification(
    db,
    task_id: int,
    channel: NotificationChannel,
    status: NotificationStatus,
    reminder_type: str,
    error_message: Optional[str] = None,
):
    """Log notification attempt to database."""
    log = NotificationLog(
        task_id=task_id,
        channel=channel,
        status=status,
        scheduled_for=datetime.now(timezone.utc),
        sent_at=datetime.now(timezone.utc) if status == NotificationStatus.SENT else None,
        error_message=error_message,
    )
    db.add(log)


@shared_task
def cleanup_old_logs():
    """
    Clean up notification logs older than 30 days.
    Runs daily via Celery Beat.
    """
    from datetime import timedelta
    
    with get_sync_session() as db:
        cutoff = datetime.now(timezone.utc) - timedelta(days=30)
        db.query(NotificationLog).filter(
            NotificationLog.scheduled_for < cutoff
        ).delete()
        db.commit()
    
    return {"status": "cleaned"}
