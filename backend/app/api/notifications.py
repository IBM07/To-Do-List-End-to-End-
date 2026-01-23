# ===========================================
# AuraTask - Notification Settings API
# ===========================================
# Manage user notification preferences

from typing import Optional

import apprise
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_db
from app.models.user import User
from app.models.notification import NotificationSettings, NotificationChannel
from app.schemas.notification import (
    NotificationSettingsUpdate,
    NotificationSettingsResponse,
    NotificationTest,
)
from app.api.auth import get_current_user
from app.utils.encryption import encrypt_field, decrypt_field


router = APIRouter()


# ===========================================
# Helper Functions
# ===========================================

async def get_or_create_settings(
    db: AsyncSession,
    user_id: int
) -> NotificationSettings:
    """Get user's notification settings, creating if not exists."""
    result = await db.execute(
        select(NotificationSettings).where(NotificationSettings.user_id == user_id)
    )
    settings = result.scalar_one_or_none()
    
    if not settings:
        settings = NotificationSettings(
            user_id=user_id,
            email_enabled=True,
        )
        db.add(settings)
        await db.flush()
        await db.refresh(settings)
    
    return settings


# ===========================================
# Notification Settings Endpoints
# ===========================================

@router.get("/settings", response_model=NotificationSettingsResponse)
async def get_notification_settings(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get current user's notification settings.
    """
    notification_settings = await get_or_create_settings(db, current_user.id)
    
    # Decrypt sensitive fields before sending to client
    response = NotificationSettingsResponse.model_validate(notification_settings)
    response.telegram_chat_id = decrypt_field(notification_settings.telegram_chat_id)
    response.discord_webhook_url = decrypt_field(notification_settings.discord_webhook_url)
    
    return response


@router.put("/settings", response_model=NotificationSettingsResponse)
async def update_notification_settings(
    updates: NotificationSettingsUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Update notification settings.
    
    Only provided fields are updated.
    """
    notification_settings = await get_or_create_settings(db, current_user.id)
    
    update_data = updates.model_dump(exclude_unset=True)
    
    # Encrypt sensitive fields before saving
    if 'telegram_chat_id' in update_data and update_data['telegram_chat_id']:
        update_data['telegram_chat_id'] = encrypt_field(update_data['telegram_chat_id'])
    if 'discord_webhook_url' in update_data and update_data['discord_webhook_url']:
        update_data['discord_webhook_url'] = encrypt_field(update_data['discord_webhook_url'])
    
    for field, value in update_data.items():
        setattr(notification_settings, field, value)
    
    await db.flush()
    await db.refresh(notification_settings)
    
    # Decrypt for response
    response = NotificationSettingsResponse.model_validate(notification_settings)
    response.telegram_chat_id = decrypt_field(notification_settings.telegram_chat_id)
    response.discord_webhook_url = decrypt_field(notification_settings.discord_webhook_url)
    
    return response


# ===========================================
# Test Notification Endpoints
# ===========================================

class TestResult(BaseModel):
    """Result of notification test."""
    success: bool
    channel: str
    message: str
    sent_to: str = None  # Recipient info


@router.post("/test", response_model=TestResult)
async def test_notification(
    test_data: NotificationTest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Send a test notification to verify channel connectivity.
    
    Use this to confirm Email/Telegram/Discord is properly configured.
    """
    notification_settings = await get_or_create_settings(db, current_user.id)
    
    channel = test_data.channel
    message = test_data.message or "🎉 Hello from AuraTask! Your notifications are working."
    
    apobj = apprise.Apprise()
    success = False
    error_msg = ""
    
    try:
        if channel == NotificationChannel.EMAIL:
            if not notification_settings.email_enabled:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Email notifications not enabled"
                )
            
            email = notification_settings.email_address or current_user.email
            
            if not settings.SMTP_USER or not settings.SMTP_PASSWORD:
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail="SMTP not configured on server"
                )
            
            # Use direct smtplib email service
            from app.services.email_service import send_email
            
            success, error_msg = send_email(
                to_email=email,
                subject="AuraTask Test Notification",
                body=message
            )
            
            if error_msg:
                error_msg = error_msg  # Will be used in response
        
        elif channel == NotificationChannel.TELEGRAM:
            if not notification_settings.telegram_enabled:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Telegram notifications not enabled"
                )
            
            if not notification_settings.telegram_chat_id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Telegram chat ID not configured"
                )
            
            if not settings.TELEGRAM_BOT_TOKEN:
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail="Telegram bot not configured on server"
                )
            
            # Use direct Telegram API service
            from app.services.telegram_service import send_telegram_message
            
            # Decrypt chat ID before use
            telegram_chat_id = decrypt_field(notification_settings.telegram_chat_id)
            success, error_msg = send_telegram_message(
                chat_id=telegram_chat_id,
                message=f"<b>🎉 AuraTask Test</b>\n\n{message}"
            )
            
            if error_msg:
                error_msg = error_msg
        
        elif channel == NotificationChannel.DISCORD:
            if not notification_settings.discord_enabled:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Discord notifications not enabled"
                )
            
            if not notification_settings.discord_webhook_url:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Discord webhook URL not configured"
                )
            
            # Decrypt webhook URL before use
            discord_webhook_url = decrypt_field(notification_settings.discord_webhook_url)
            apobj.add(discord_webhook_url)
            success = apobj.notify(
                title="AuraTask Test Notification",
                body=message,
                notify_type=apprise.NotifyType.INFO,
            )
        
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unknown channel: {channel}"
            )
    
    except HTTPException:
        raise
    except Exception as e:
        error_msg = str(e)
        success = False
    
    # Track recipient for response
    recipient = ""
    if channel == NotificationChannel.EMAIL:
        recipient = notification_settings.email_address or current_user.email
    elif channel == NotificationChannel.TELEGRAM:
        recipient = notification_settings.telegram_chat_id or ""
    elif channel == NotificationChannel.DISCORD:
        recipient = "Discord Webhook"
    
    if success:
        return TestResult(
            success=True,
            channel=channel.value,
            message="Test notification sent successfully!",
            sent_to=recipient
        )
    else:
        return TestResult(
            success=False,
            channel=channel.value,
            message=f"Failed to send: {error_msg or 'Check channel configuration'}"
        )


@router.get("/channels")
async def get_available_channels(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get list of configured and available notification channels.
    """
    notification_settings = await get_or_create_settings(db, current_user.id)
    
    return {
        "channels": [
            {
                "name": "EMAIL",
                "enabled": notification_settings.email_enabled,
                "configured": bool(notification_settings.email_address or current_user.email),
                "server_ready": bool(settings.SMTP_USER),
            },
            {
                "name": "TELEGRAM",
                "enabled": notification_settings.telegram_enabled,
                "configured": bool(notification_settings.telegram_chat_id),
                "server_ready": bool(settings.TELEGRAM_BOT_TOKEN),
            },
            {
                "name": "DISCORD",
                "enabled": notification_settings.discord_enabled,
                "configured": bool(notification_settings.discord_webhook_url),
                "server_ready": True,  # No server config needed for webhooks
            },
        ]
    }
