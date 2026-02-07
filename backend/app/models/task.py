# ===========================================
# AuraTask - Task Model
# ===========================================

from datetime import datetime
from enum import Enum as PyEnum
from typing import TYPE_CHECKING, List, Optional

from sqlalchemy import String, Text, DateTime, Float, ForeignKey, Enum, func, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.user import User
    from app.models.notification import NotificationLog
    from app.models.subtask import Subtask


class Priority(str, PyEnum):
    """Task priority levels."""
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    URGENT = "URGENT"


class TaskStatus(str, PyEnum):
    """Task completion status."""
    PENDING = "PENDING"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"


class Task(Base):
    """
    Task model representing a user's task with priority and deadline.
    
    Attributes:
        id: Primary key
        user_id: Foreign key to User
        title: Task title (max 500 chars)
        description: Optional detailed description
        priority: LOW, MEDIUM, HIGH, or URGENT
        status: PENDING, IN_PROGRESS, COMPLETED, or CANCELLED
        due_date: Deadline in UTC
        snoozed_until: If snoozed, notifications paused until this time
        urgency_score: Computed score for dashboard sorting
        created_at: Creation timestamp
        updated_at: Last update timestamp
    """
    __tablename__ = "tasks"
    
    # Primary Key
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    
    # Foreign Key
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    
    # Task Content
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Priority & Status
    priority: Mapped[Priority] = mapped_column(
        Enum(Priority),
        default=Priority.MEDIUM,
        nullable=False
    )
    status: Mapped[TaskStatus] = mapped_column(
        Enum(TaskStatus),
        default=TaskStatus.PENDING,
        nullable=False,
        index=True
    )
    
    # Time Management (timezone-aware for proper UTC handling)
    due_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    snoozed_until: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    
    # Computed Score (updated by Celery Beat)
    urgency_score: Mapped[float] = mapped_column(Float, default=0.0)
    
    # Timestamps (timezone-aware)
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
    user: Mapped["User"] = relationship("User", back_populates="tasks")
    notification_logs: Mapped[List["NotificationLog"]] = relationship(
        "NotificationLog",
        back_populates="task",
        cascade="all, delete-orphan"
    )
    
    subtasks: Mapped[List["Subtask"]] = relationship(
        "Subtask",
        back_populates="task",
        cascade="all, delete-orphan",
        order_by="Subtask.order"
    )
    
    # Indexes for query optimization
    __table_args__ = (
        Index("idx_due_date", "due_date"),
        Index("idx_urgency_score", "urgency_score", postgresql_using="btree"),
        Index("idx_user_status", "user_id", "status"),
    )
    
    def __repr__(self) -> str:
        return f"<Task(id={self.id}, title='{self.title[:30]}...', priority={self.priority})>"
