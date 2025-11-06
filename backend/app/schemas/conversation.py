"""Conversation and message schemas for API validation"""

from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, UUID4, Field


class MessageCreate(BaseModel):
    """Schema for creating a new message"""

    content: str = Field(..., min_length=1, max_length=10000)
    role: str = Field(..., pattern="^(user|assistant)$")


class MessageResponse(BaseModel):
    """Schema for message response"""

    id: UUID4
    conversation_id: UUID4
    role: str
    content: str
    contains_crisis_keywords: bool
    detected_keywords: Optional[List[str]] = None
    created_at: datetime

    class Config:
        from_attributes = True


class ConversationCreate(BaseModel):
    """Schema for creating a new conversation"""

    title: Optional[str] = Field(None, max_length=255)


class ConversationResponse(BaseModel):
    """Schema for conversation response"""

    id: UUID4
    user_id: UUID4
    title: Optional[str] = None
    summary: Optional[str] = None
    crisis_detected: bool
    crisis_severity: int
    created_at: datetime
    updated_at: datetime
    last_message_at: datetime
    messages: List[MessageResponse] = []

    class Config:
        from_attributes = True


class ChatRequest(BaseModel):
    """Schema for chat completion request"""

    message: str = Field(..., min_length=1, max_length=10000)
    conversation_id: Optional[UUID4] = None
    stream: bool = Field(default=True)


class ChatResponse(BaseModel):
    """Schema for chat completion response"""

    conversation_id: UUID4
    message: MessageResponse
    crisis_detected: bool
    crisis_severity: int
    cached: bool = False


class StreamChunk(BaseModel):
    """Schema for streaming response chunk"""

    content: str
    done: bool = False
    conversation_id: Optional[UUID4] = None
    crisis_detected: bool = False


# ============================================================================
# New schemas for conversation management API
# ============================================================================

class ConversationListItem(BaseModel):
    """Schema for conversation list item (summary view)"""

    id: UUID4
    title: Optional[str] = None
    summary: Optional[str] = None
    status: str
    crisis_detected: bool
    crisis_severity: int
    message_count: int = 0
    last_message_preview: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    last_message_at: datetime

    class Config:
        from_attributes = True


class ConversationListResponse(BaseModel):
    """Schema for paginated conversation list response"""

    conversations: List[ConversationListItem]
    total: int
    page: int
    page_size: int
    has_more: bool


class ConversationDetailResponse(BaseModel):
    """Schema for detailed conversation view"""

    id: UUID4
    user_id: UUID4
    title: Optional[str] = None
    summary: Optional[str] = None
    status: str
    crisis_detected: bool
    crisis_severity: int
    crisis_keywords_found: Optional[List[str]] = None
    created_at: datetime
    updated_at: datetime
    last_message_at: datetime
    messages: List[MessageResponse] = []
    message_count: int

    class Config:
        from_attributes = True


class ConversationUpdateRequest(BaseModel):
    """Schema for updating conversation"""

    title: Optional[str] = Field(None, max_length=255)
    summary: Optional[str] = Field(None, max_length=1000)
    status: Optional[str] = Field(None, pattern="^(active|archived|deleted)$")


class MessageListResponse(BaseModel):
    """Schema for paginated message list"""

    messages: List[MessageResponse]
    total: int
    page: int
    page_size: int
    has_more: bool
    conversation_id: UUID4
