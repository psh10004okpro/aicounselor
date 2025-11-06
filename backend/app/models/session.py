"""Session model for tracking counseling sessions"""

from datetime import datetime
from sqlalchemy import Column, String, DateTime, Boolean, ForeignKey, Integer, Text
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
import uuid

from app.core.database import Base


class Session(Base):
    """
    Counseling session model

    Tracks individual counseling sessions within conversations.
    Sessions have start/end times and AI-generated summaries.
    """

    __tablename__ = "sessions"

    session_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    conversation_id = Column(
        UUID(as_uuid=True), ForeignKey("conversations.conversation_id"), nullable=False
    )
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.user_id"), nullable=False)

    # Session timing
    started_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    ended_at = Column(DateTime(timezone=True), nullable=True)
    duration_minutes = Column(Integer, nullable=True)

    # Session content
    summary = Column(Text, nullable=True)  # AI-generated summary
    notes = Column(JSONB, default=[], nullable=False)  # User/therapist notes

    # Session metrics
    message_count = Column(Integer, default=0, nullable=False)
    crisis_level = Column(Integer, default=0, nullable=False)  # Highest crisis level during session

    # Metadata
    session_metadata = Column("metadata", JSONB, default={}, nullable=False)

    # Timestamps
    created_at = Column(
        DateTime(timezone=True), default=datetime.utcnow, nullable=False
    )
    updated_at = Column(
        DateTime(timezone=True),
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
    )

    # Soft delete
    is_deleted = Column(Boolean, default=False, nullable=False)
    deleted_at = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    conversation = relationship("Conversation")
    user = relationship("User")

    def __repr__(self) -> str:
        return f"<Session(id={self.session_id}, conversation_id={self.conversation_id}, started={self.started_at})>"
