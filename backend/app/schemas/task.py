# ===========================================
# AuraTask - Task Schemas
# ===========================================

from datetime import datetime
from typing import Optional

import pytz
from pydantic import BaseModel, Field, ConfigDict, field_validator, computed_field

from app.models.task import Priority, TaskStatus


class TaskBase(BaseModel):
    """Base task fields shared across schemas."""
    title: str = Field(..., min_length=1, max_length=500, description="Task title")
    description: Optional[str] = Field(None, description="Detailed task description")
    priority: Priority = Field(default=Priority.MEDIUM, description="Task priority level")


class TaskCreate(BaseModel):
    """
    Schema for creating a task.
    
    Supports two modes:
    1. NLP Mode: Just provide 'nlp_input' string like "Fix bug #Urgent by Friday 5pm"
    2. Structured Mode: Provide individual fields (title, priority, due_date)
    """
    # NLP Mode - Natural language input
    nlp_input: Optional[str] = Field(
        None, 
        description="Natural language task input (e.g., 'Fix bug #Urgent by Friday 5pm')"
    )
    
    # Structured Mode - Individual fields
    title: Optional[str] = Field(None, min_length=1, max_length=500)
    description: Optional[str] = None
    priority: Optional[Priority] = Field(default=Priority.MEDIUM)
    due_date: Optional[datetime] = Field(
        None, 
        description="Due date in ISO format (assumed to be user's local time)"
    )
    
    @field_validator("nlp_input", "title", mode="before")
    @classmethod
    def strip_whitespace(cls, v):
        """Strip whitespace from string inputs."""
        if isinstance(v, str):
            return v.strip()
        return v
    
    def model_post_init(self, __context):
        """Validate that either nlp_input OR title+due_date is provided."""
        if not self.nlp_input and not self.title:
            raise ValueError("Either 'nlp_input' or 'title' must be provided")
        if self.title and not self.due_date and not self.nlp_input:
            raise ValueError("'due_date' is required when using structured mode")


class TaskUpdate(BaseModel):
    """Schema for updating an existing task."""
    title: Optional[str] = Field(None, min_length=1, max_length=500)
    description: Optional[str] = None
    priority: Optional[Priority] = None
    status: Optional[TaskStatus] = None
    due_date: Optional[datetime] = None


class TaskSnooze(BaseModel):
    """Schema for snoozing task notifications."""
    snooze_minutes: int = Field(
        ..., 
        ge=5, 
        le=1440,  # Max 24 hours
        description="Minutes to snooze (5-1440)"
    )


class TaskResponse(BaseModel):
    """
    Schema for task data in API responses.
    
    Includes computed fields for timezone-aware date formatting.
    """
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    user_id: int
    title: str
    description: Optional[str]
    priority: Priority
    status: TaskStatus
    due_date: datetime  # UTC
    snoozed_until: Optional[datetime]
    urgency_score: float
    created_at: datetime
    updated_at: datetime
    
    # User's timezone (set by API before response)
    _user_timezone: str = "UTC"
    
    def set_user_timezone(self, timezone: str) -> "TaskResponse":
        """Set user timezone for computed fields."""
        object.__setattr__(self, "_user_timezone", timezone)
        return self
    
    @computed_field
    @property
    def due_date_local(self) -> str:
        """
        Due date formatted in user's local timezone.
        
        Returns ISO format string for frontend parsing.
        """
        try:
            tz = pytz.timezone(self._user_timezone)
            local_dt = self.due_date.replace(tzinfo=pytz.UTC).astimezone(tz)
            return local_dt.isoformat()
        except Exception:
            return self.due_date.isoformat()
    
    @computed_field
    @property
    def due_date_human(self) -> str:
        """
        Human-readable due date in user's timezone.
        
        Returns: "Jan 20, 2026 at 5:00 PM"
        """
        try:
            tz = pytz.timezone(self._user_timezone)
            local_dt = self.due_date.replace(tzinfo=pytz.UTC).astimezone(tz)
            return local_dt.strftime("%b %d, %Y at %I:%M %p")
        except Exception:
            return self.due_date.strftime("%b %d, %Y at %I:%M %p")
    
    @computed_field
    @property
    def is_overdue(self) -> bool:
        """Check if task is past due date."""
        return datetime.utcnow() > self.due_date and self.status not in [
            TaskStatus.COMPLETED, 
            TaskStatus.CANCELLED
        ]
    
    @computed_field
    @property
    def is_snoozed(self) -> bool:
        """Check if task notifications are currently snoozed."""
        if not self.snoozed_until:
            return False
        return datetime.utcnow() < self.snoozed_until


class TaskListResponse(BaseModel):
    """Schema for paginated task list response."""
    tasks: list[TaskResponse]
    total: int
    page: int
    per_page: int
    total_pages: int
