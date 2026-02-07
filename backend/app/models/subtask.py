# ===========================================
# AuraTask - Subtask Model
# ===========================================

from datetime import datetime
from sqlalchemy import String, Integer, DateTime, Boolean, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Subtask(Base):
    """
    Subtask model representing a smaller unit of work within a parent Task.
    
    Attributes:
        id: Primary key
        task_id: Foreign key to parent Task
        title: Subtask title (max 500 chars)
        is_completed: Completion status
        order: Order for display/sorting (drag-drop support)
        created_at: Creation timestamp
    """
    __tablename__ = "subtasks"
    
    # Primary Key
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    
    # Foreign Key
    task_id: Mapped[int] = mapped_column(
        ForeignKey("tasks.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    
    # Content
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    is_completed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), 
        server_default=func.now()
    )
    
    # Relationship
    task: Mapped["Task"] = relationship("Task", back_populates="subtasks")

    def __repr__(self) -> str:
        return f"<Subtask(id={self.id}, title='{self.title[:30]}...', completed={self.is_completed})>"
