"""Session schemas for API validation"""

from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, UUID4, Field


class SessionNote(BaseModel):
    """Schema for session note"""

    content: str = Field(..., max_length=1000, description="Note content")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    author: str = Field(default="user", description="Note author")


class SessionStartRequest(BaseModel):
    """Schema for starting a new session"""

    conversation_id: Optional[UUID4] = Field(
        None, description="Existing conversation ID (optional - will create new if not provided)"
    )
    title: Optional[str] = Field(None, max_length=255, description="Session title")


class SessionEndRequest(BaseModel):
    """Schema for ending a session"""

    notes: Optional[str] = Field(None, max_length=1000, description="Session closing notes")


class SessionNoteRequest(BaseModel):
    """Schema for adding a note to a session"""

    content: str = Field(..., min_length=1, max_length=1000, description="Note content")


class SessionResponse(BaseModel):
    """Schema for session response"""

    id: UUID4
    conversation_id: UUID4
    user_id: UUID4
    started_at: datetime
    ended_at: Optional[datetime] = None
    duration_minutes: Optional[int] = None
    summary: Optional[str] = None
    notes: List[dict] = []
    message_count: int
    crisis_level: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class SessionSummaryResponse(BaseModel):
    """Schema for session summary (AI-generated)"""

    session_id: UUID4
    summary: str
    key_topics: List[str] = []
    emotions_detected: List[str] = []
    crisis_level: int
    progress_notes: Optional[str] = None
    recommendations: List[str] = []
    generated_at: datetime


class SessionListResponse(BaseModel):
    """Schema for paginated session list"""

    sessions: List[SessionResponse]
    total: int
    page: int
    page_size: int
    has_more: bool
