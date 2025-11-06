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


# ============================================================================
# New schemas for user profile management API
# ============================================================================

class UserProfileResponse(BaseModel):
    """Schema for detailed user profile response"""

    id: UUID4
    email: Optional[str] = None
    is_anonymous: bool
    consent_given: bool
    consent_timestamp: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
    last_active: datetime

    # Metadata fields
    age: Optional[int] = None
    display_name: Optional[str] = None
    preferences: Optional[dict] = None

    class Config:
        from_attributes = True


class UserProfileUpdateRequest(BaseModel):
    """Schema for updating user profile"""

    age: Optional[int] = Field(None, ge=13, le=120, description="User age (13-120)")
    display_name: Optional[str] = Field(None, max_length=100, description="Display name")
    preferences: Optional[dict] = Field(None, description="User preferences (notifications, theme, etc.)")


class UserStatisticsResponse(BaseModel):
    """Schema for user statistics"""

    user_id: UUID4
    total_conversations: int
    total_messages: int
    total_sessions: int
    crisis_events_count: int
    average_crisis_level: float
    first_session_date: Optional[datetime]
    last_session_date: Optional[datetime]
    most_common_emotion: Optional[str] = None
    current_cbt_stage: Optional[str] = None
    days_active: int

    # Emotion distribution
    emotion_distribution: Optional[dict] = None

    # Crisis level history
    crisis_level_trend: Optional[List[dict]] = None
