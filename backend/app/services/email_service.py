"""
===========================================
AuraTask - Email Service
===========================================
Direct SMTP email sending using Python's smtplib
"""

import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional, Tuple
import logging

from app.config import settings

logger = logging.getLogger(__name__)


def send_email(
    to_email: str,
    subject: str,
    body: str,
    html_body: Optional[str] = None
) -> Tuple[bool, Optional[str]]:
    """
    Send email via Gmail SMTP.
    
    Args:
        to_email: Recipient email address
        subject: Email subject
        body: Plain text email body
        html_body: Optional HTML body
        
    Returns:
        Tuple of (success: bool, error_message: Optional[str])
    """
    # Validate SMTP configuration
    if not settings.SMTP_USER:
        return False, "SMTP_USER not configured in .env"
    
    if not settings.SMTP_PASSWORD:
        return False, "SMTP_PASSWORD not configured in .env"
    
    try:
        # Create message
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = f"{settings.SMTP_FROM_NAME} <{settings.SMTP_FROM_EMAIL or settings.SMTP_USER}>"
        msg["To"] = to_email
        
        # Add plain text part
        part1 = MIMEText(body, "plain")
        msg.attach(part1)
        
        # Add HTML part if provided
        if html_body:
            part2 = MIMEText(html_body, "html")
            msg.attach(part2)
        
        # Connect to Gmail SMTP
        logger.info(f"Connecting to {settings.SMTP_HOST}:{settings.SMTP_PORT}")
        print(f"[EMAIL] Connecting to {settings.SMTP_HOST}:{settings.SMTP_PORT}")
        
        with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT) as server:
            # Start TLS encryption
            server.starttls()
            
            # Login with App Password
            print(f"[EMAIL] Logging in as {settings.SMTP_USER}")
            server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
            
            # Send email
            print(f"[EMAIL] Sending to {to_email}")
            server.sendmail(
                settings.SMTP_FROM_EMAIL or settings.SMTP_USER,
                to_email,
                msg.as_string()
            )
        
        logger.info(f"Email sent successfully to {to_email}")
        print(f"[EMAIL] ✅ Sent successfully to {to_email}")
        return True, None
        
    except smtplib.SMTPAuthenticationError as e:
        error_msg = f"Authentication failed: {str(e)} - Check your Gmail App Password"
        logger.error(error_msg)
        print(f"[EMAIL] ❌ {error_msg}")
        return False, error_msg
        
    except smtplib.SMTPConnectError as e:
        error_msg = f"Connection failed: {str(e)}"
        logger.error(error_msg)
        print(f"[EMAIL] ❌ {error_msg}")
        return False, error_msg
        
    except Exception as e:
        error_msg = f"Email error: {str(e)}"
        logger.error(error_msg)
        print(f"[EMAIL] ❌ {error_msg}")
        return False, error_msg


def send_task_reminder_email(
    to_email: str,
    task_title: str,
    task_description: Optional[str],
    due_date_str: str,
    priority: str,
    time_left: str
) -> Tuple[bool, Optional[str]]:
    """
    Send a task reminder email.
    
    Args:
        to_email: Recipient email
        task_title: Task title
        task_description: Task description
        due_date_str: Formatted due date string
        priority: Priority level
        time_left: Time remaining (e.g., "1 hour", "24 hours")
        
    Returns:
        Tuple of (success, error_message)
    """
    subject = f"⏰ Task Due in {time_left}: {task_title[:50]}"
    
    body = f"""
Task Reminder from AuraTask

📋 Task: {task_title}
⏰ Due: {due_date_str}
🔥 Priority: {priority}

{task_description or 'No description provided.'}

---
Log in to AuraTask to manage your tasks.
    """.strip()
    
    html_body = f"""
    <html>
    <body style="font-family: Arial, sans-serif; padding: 20px; background-color: #f5f5f5;">
        <div style="max-width: 600px; margin: 0 auto; background: white; padding: 30px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1);">
            <h2 style="color: #7c3aed;">⏰ Task Reminder</h2>
            <div style="background: #f8f4ff; padding: 20px; border-radius: 8px; margin: 20px 0;">
                <h3 style="margin: 0 0 10px 0; color: #1a1a2e;">{task_title}</h3>
                <p style="margin: 5px 0;"><strong>📅 Due:</strong> {due_date_str}</p>
                <p style="margin: 5px 0;"><strong>🔥 Priority:</strong> {priority}</p>
            </div>
            <p style="color: #666;">{task_description or 'No description provided.'}</p>
            <hr style="border: none; border-top: 1px solid #eee; margin: 20px 0;">
            <p style="color: #999; font-size: 12px;">Log in to AuraTask to manage your tasks.</p>
        </div>
    </body>
    </html>
    """
    
    return send_email(to_email, subject, body, html_body)
