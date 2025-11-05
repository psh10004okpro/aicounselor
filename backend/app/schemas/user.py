"""User schemas for API validation"""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, EmailStr, UUID4


class UserCreate(BaseModel):
    """Schema for creating a new user"""

    email: Optional[EmailStr] = None
    is_anonymous: bool = True
    consent_given: bool = False


class UserResponse(BaseModel):
    """Schema for user response"""

    id: UUID4
    email: Optional[str] = None
    is_anonymous: bool
    session_token: str
    consent_given: bool
    created_at: datetime
    last_active: datetime

    class Config:
        from_attributes = True
