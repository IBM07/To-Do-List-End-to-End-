# ===========================================
# AuraTask - Subtask Schemas
# ===========================================

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field


class SubtaskCreate(BaseModel):
    """Schema for creating a subtask."""
    title: str = Field(..., min_length=1, max_length=500, description="Subtask title")


class SubtaskUpdate(BaseModel):
    """Schema for updating a subtask."""
    title: Optional[str] = Field(None, min_length=1, max_length=500)
    is_completed: Optional[bool] = None
    order: Optional[int] = None


class SubtaskResponse(BaseModel):
    """Schema for subtask in API responses."""
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    task_id: int
    title: str
    is_completed: bool
    order: int
    created_at: datetime
