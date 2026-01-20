# ===========================================
# AuraTask - Notification Models
# ===========================================

from datetime import datetime
from enum import Enum as PyEnum
from typing import TYPE_CHECKING, Optional

from sqlalchemy import String, Text, DateTime, Boolean, ForeignKey, Enum, func, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.user import User
    from app.models.task import Task


class NotificationChannel(str, PyEnum):
    """Supported notification channels."""
    EMAIL = "EMAIL"
    TELEGRAM = "TELEGRAM"
    DISCORD = "DISCORD"


class NotificationStatus(str, PyEnum):
    """Notification delivery status."""
    PENDING = "PENDING"
    SENT = "SENT"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


class NotificationSettings(Base):
    """
    User's notification preferences.
    
    Each user has one settings record controlling which channels
    are enabled and when to receive alerts.
    """
    __tablename__ = "notification_settings"
    
    # Primary Key
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    
    # Foreign Key (One-to-One with User)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        unique=True,
        nullable=False
    )
    
    # Email Settings
    email_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    email_address: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    
    # Telegram Settings
    telegram_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    telegram_chat_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    
    # Discord Settings
    discord_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    discord_webhook_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    
    # Notification Timing
    notify_1hr_before: Mapped[bool] = mapped_column(Boolean, default=True)
    notify_24hr_before: Mapped[bool] = mapped_column(Boolean, default=True)
    
    # Relationship
    user: Mapped["User"] = relationship("User", back_populates="notification_settings")
    
    def __repr__(self) -> str:
        channels = []
        if self.email_enabled:
            channels.append("EMAIL")
        if self.telegram_enabled:
            channels.append("TELEGRAM")
        if self.discord_enabled:
            channels.append("DISCORD")
        return f"<NotificationSettings(user_id={self.user_id}, channels={channels})>"


class NotificationLog(Base):
    """
    Log of all notification attempts.
    
    Tracks every notification sent (or attempted) for auditing
    and debugging purposes.
    """
    __tablename__ = "notification_logs"
    
    # Primary Key
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    
    # Foreign Key
    task_id: Mapped[int] = mapped_column(
        ForeignKey("tasks.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    
    # Notification Details
    channel: Mapped[NotificationChannel] = mapped_column(
        Enum(NotificationChannel),
        nullable=False
    )
    status: Mapped[NotificationStatus] = mapped_column(
        Enum(NotificationStatus),
        default=NotificationStatus.PENDING,
        nullable=False,
        index=True
    )
    
    # Timing (timezone-aware for proper UTC handling)
    scheduled_for: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    sent_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    
    # Error Tracking
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Celery Task ID (for revocation)
    celery_task_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    
    # Relationship
    task: Mapped["Task"] = relationship("Task", back_populates="notification_logs")
    
    # Indexes
    __table_args__ = (
        Index("idx_scheduled_for", "scheduled_for"),
        Index("idx_task_status", "task_id", "status"),
    )
    
    def __repr__(self) -> str:
        return f"<NotificationLog(task_id={self.task_id}, channel={self.channel}, status={self.status})>"
