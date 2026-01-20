# ===========================================
# AuraTask - User Schemas
# ===========================================

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, EmailStr, Field, ConfigDict


class UserBase(BaseModel):
    """Base user fields shared across schemas."""
    email: EmailStr
    timezone: str = Field(default="UTC", description="User's timezone (e.g., 'Asia/Kolkata')")


class UserCreate(UserBase):
    """Schema for user registration."""
    password: str = Field(
        ..., 
        min_length=8, 
        description="Password (min 8 characters)"
    )


class UserLogin(BaseModel):
    """Schema for user login."""
    email: EmailStr
    password: str = Field(..., min_length=1)


class UserUpdate(BaseModel):
    """Schema for updating user profile."""
    timezone: Optional[str] = Field(None, description="Update timezone")
    password: Optional[str] = Field(None, min_length=8, description="New password")


class UserResponse(UserBase):
    """Schema for user data in API responses."""
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    created_at: datetime
    updated_at: datetime


class UserInDB(UserResponse):
    """Schema with hashed password (internal use only)."""
    hashed_password: str
