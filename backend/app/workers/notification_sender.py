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
from app.utils.encryption import decrypt_field


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
            
            # Step 3: Build notification message based on reminder type
            if reminder_type == "AT_DUE":
                subject = f"🚨 Task Due NOW: {task.title[:50]}"
                time_info = "Your task is due NOW!"
            elif reminder_type == "1_HOUR":
                subject = f"⏰ Task Due in 1 Hour: {task.title[:50]}"
                time_info = "Your task is due in 1 hour."
            else:  # 24_HOUR
                subject = f"📅 Task Due in 24 Hours: {task.title[:50]}"
                time_info = "Your task is due in 24 hours."
            
            body = f"""
Task Reminder from AuraTask

📋 Task: {task.title}
⏰ {time_info}
📆 Due: {task.due_date.strftime("%b %d, %Y at %I:%M %p")} UTC
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
                # Decrypt the chat ID before use
                telegram_chat_id = decrypt_field(notification_settings.telegram_chat_id)
                success, error = _send_telegram(
                    telegram_chat_id,
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
                # Decrypt the webhook URL before use
                discord_webhook_url = decrypt_field(notification_settings.discord_webhook_url)
                success, error = _send_discord(
                    discord_webhook_url,
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
    """Send message via Telegram bot using direct HTTP API."""
    try:
        if not settings.TELEGRAM_BOT_TOKEN:
            return False, "Telegram bot not configured"
        
        if not chat_id:
            return False, "Chat ID is required"
        
        import requests
        
        url = f"https://api.telegram.org/bot{settings.TELEGRAM_BOT_TOKEN}/sendMessage"
        
        # Format message with HTML
        message = f"""
<b>⏰ {subject}</b>

{body}

---
<i>AuraTask Reminder</i>
        """.strip()
        
        payload = {
            "chat_id": chat_id,
            "text": message,
            "parse_mode": "HTML",
        }
        
        print(f"[TELEGRAM] Sending to chat_id: {chat_id}")
        
        response = requests.post(url, json=payload, timeout=10)
        
        if response.status_code == 200:
            result = response.json()
            if result.get("ok"):
                print(f"[TELEGRAM] ✅ Message sent successfully")
                return True, None
            else:
                error = result.get("description", "Unknown error")
                print(f"[TELEGRAM] ❌ API error: {error}")
                return False, f"Telegram API error: {error}"
        else:
            error_msg = f"HTTP {response.status_code}: {response.text}"
            print(f"[TELEGRAM] ❌ {error_msg}")
            return False, error_msg
            
    except requests.Timeout:
        return False, "Request timed out"
    except Exception as e:
        return False, str(e)


def _send_discord(webhook_url: str, subject: str, body: str) -> tuple[bool, Optional[str]]:
    """Send message via Discord webhook using direct HTTP API."""
    try:
        if not webhook_url:
            return False, "Discord webhook URL is required"
        
        import requests
        
        # Discord webhook expects JSON with content or embeds
        # Using embed for better formatting
        embed = {
            "title": f"⏰ {subject}",
            "description": body,
            "color": 5814783,  # Purple color
            "footer": {
                "text": "AuraTask Reminder"
            }
        }
        
        payload = {
            "embeds": [embed]
        }
        
        print(f"[DISCORD] Sending to webhook...")
        
        response = requests.post(webhook_url, json=payload, timeout=10)
        
        # Discord returns 204 No Content on success
        if response.status_code in [200, 204]:
            print(f"[DISCORD] ✅ Message sent successfully")
            return True, None
        else:
            error_msg = f"HTTP {response.status_code}: {response.text}"
            print(f"[DISCORD] ❌ {error_msg}")
            return False, error_msg
            
    except requests.Timeout:
        return False, "Request timed out"
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
