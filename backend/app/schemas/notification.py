# ===========================================
# AuraTask - Notification Schemas
# ===========================================

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field, ConfigDict

from app.models.notification import NotificationChannel, NotificationStatus


class NotificationSettingsBase(BaseModel):
    """Base notification settings fields."""
    email_enabled: bool = True
    email_address: Optional[str] = None
    telegram_enabled: bool = False
    telegram_chat_id: Optional[str] = None
    discord_enabled: bool = False
    discord_webhook_url: Optional[str] = None
    notify_1hr_before: bool = True
    notify_24hr_before: bool = True


class NotificationSettingsUpdate(BaseModel):
    """Schema for updating notification settings."""
    email_enabled: Optional[bool] = None
    email_address: Optional[str] = None
    telegram_enabled: Optional[bool] = None
    telegram_chat_id: Optional[str] = None
    discord_enabled: Optional[bool] = None
    discord_webhook_url: Optional[str] = None
    notify_1hr_before: Optional[bool] = None
    notify_24hr_before: Optional[bool] = None


class NotificationSettingsResponse(NotificationSettingsBase):
    """Schema for notification settings in API responses."""
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    user_id: int


class NotificationLogResponse(BaseModel):
    """Schema for notification log in API responses."""
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    task_id: int
    channel: NotificationChannel
    status: NotificationStatus
    scheduled_for: datetime
    sent_at: Optional[datetime]
    error_message: Optional[str]


class NotificationTest(BaseModel):
    """Schema for testing notification delivery."""
    channel: NotificationChannel = Field(
        default=NotificationChannel.EMAIL,
        description="Channel to test"
    )
    message: str = Field(
        default="This is a test notification from AuraTask!",
        description="Test message content"
    )
