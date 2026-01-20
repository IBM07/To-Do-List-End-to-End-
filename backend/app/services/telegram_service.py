"""
===========================================
AuraTask - Telegram Service
===========================================
Direct Telegram Bot API messaging
"""

import requests
from typing import Optional, Tuple
import logging

from app.config import settings

logger = logging.getLogger(__name__)

TELEGRAM_API_BASE = "https://api.telegram.org"


def send_telegram_message(
    chat_id: str,
    message: str,
    parse_mode: str = "HTML"
) -> Tuple[bool, Optional[str]]:
    """
    Send a message via Telegram Bot API.
    
    Args:
        chat_id: Telegram chat ID of recipient
        message: Message text (supports HTML formatting)
        parse_mode: "HTML" or "Markdown"
        
    Returns:
        Tuple of (success: bool, error_message: Optional[str])
    """
    if not settings.TELEGRAM_BOT_TOKEN:
        return False, "TELEGRAM_BOT_TOKEN not configured in .env"
    
    if not chat_id:
        return False, "Chat ID is required"
    
    try:
        url = f"{TELEGRAM_API_BASE}/bot{settings.TELEGRAM_BOT_TOKEN}/sendMessage"
        
        payload = {
            "chat_id": chat_id,
            "text": message,
            "parse_mode": parse_mode,
        }
        
        print(f"[TELEGRAM] Sending to chat_id: {chat_id}")
        logger.info(f"Sending Telegram message to chat_id: {chat_id}")
        
        response = requests.post(url, json=payload, timeout=10)
        
        if response.status_code == 200:
            result = response.json()
            if result.get("ok"):
                print(f"[TELEGRAM] ✅ Message sent successfully")
                logger.info("Telegram message sent successfully")
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
        error_msg = "Request timed out"
        print(f"[TELEGRAM] ❌ {error_msg}")
        return False, error_msg
        
    except Exception as e:
        error_msg = f"Telegram error: {str(e)}"
        print(f"[TELEGRAM] ❌ {error_msg}")
        logger.error(error_msg)
        return False, error_msg


def send_task_reminder_telegram(
    chat_id: str,
    task_title: str,
    task_description: Optional[str],
    due_date_str: str,
    priority: str,
    time_left: str
) -> Tuple[bool, Optional[str]]:
    """
    Send a task reminder via Telegram.
    """
    message = f"""
⏰ <b>Task Due in {time_left}</b>

📋 <b>Task:</b> {task_title}
📅 <b>Due:</b> {due_date_str}
🔥 <b>Priority:</b> {priority}

{task_description or 'No description provided.'}

---
<i>AuraTask Reminder</i>
    """.strip()
    
    return send_telegram_message(chat_id, message)


def verify_bot_token() -> Tuple[bool, Optional[str]]:
    """
    Verify that the Telegram bot token is valid.
    """
    if not settings.TELEGRAM_BOT_TOKEN:
        return False, "TELEGRAM_BOT_TOKEN not configured"
    
    try:
        url = f"{TELEGRAM_API_BASE}/bot{settings.TELEGRAM_BOT_TOKEN}/getMe"
        response = requests.get(url, timeout=5)
        
        if response.status_code == 200 and response.json().get("ok"):
            bot_info = response.json().get("result", {})
            bot_name = bot_info.get("username", "Unknown")
            return True, f"Bot verified: @{bot_name}"
        else:
            return False, "Invalid bot token"
            
    except Exception as e:
        return False, str(e)
