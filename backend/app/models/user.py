# ===========================================
# AuraTask - User Model
# ===========================================

from datetime import datetime
from typing import TYPE_CHECKING, List

from sqlalchemy import String, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.task import Task
    from app.models.notification import NotificationSettings


class User(Base):
    """
    User model for authentication and task ownership.
    
    Attributes:
        id: Primary key
        email: Unique email address (indexed)
        hashed_password: Bcrypt hashed password
        timezone: User's timezone for due date display (e.g., 'Asia/Kolkata')
        created_at: Account creation timestamp
        updated_at: Last update timestamp
    """
    __tablename__ = "users"
    
    # Primary Key
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    
    # Authentication
    email: Mapped[str] = mapped_column(
        String(255), 
        unique=True, 
        index=True, 
        nullable=False
    )
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    
    # User Preferences
    timezone: Mapped[str] = mapped_column(String(50), default="UTC")
    
    # Timestamps (timezone-aware to prevent naive datetime bugs)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), 
        server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), 
        server_default=func.now(), 
        onupdate=func.now()
    )
    
    # Relationships
    tasks: Mapped[List["Task"]] = relationship(
        "Task", 
        back_populates="user", 
        cascade="all, delete-orphan"
    )
    notification_settings: Mapped["NotificationSettings"] = relationship(
        "NotificationSettings",
        back_populates="user",
        uselist=False,
        cascade="all, delete-orphan"
    )
    
    def __repr__(self) -> str:
        return f"<User(id={self.id}, email='{self.email}')>"
