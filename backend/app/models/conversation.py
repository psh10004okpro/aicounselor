"""Conversation and Message models with vector embeddings"""

from datetime import datetime
from sqlalchemy import Column, String, DateTime, Boolean, ForeignKey, Integer, Text
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from pgvector.sqlalchemy import Vector
import uuid

from app.core.database import Base


class Conversation(Base):
    """Conversation session model"""

    __tablename__ = "conversations"

    conversation_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.user_id"), nullable=False)

    # Conversation metadata
    title = Column(String(255), nullable=True)
    summary = Column(Text, nullable=True)

    # Status tracking
    status = Column(String(50), default="active", nullable=False)

    # Crisis detection
    crisis_detected = Column(Boolean, default=False, nullable=False)
    crisis_severity = Column(Integer, default=0, nullable=False)  # 0-10 scale
    crisis_keywords_found = Column(JSONB, nullable=True)
    crisis_timestamp = Column(DateTime(timezone=True), nullable=True)

    # Metadata
    metadata = Column(JSONB, default={}, nullable=False)

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
    last_message_at = Column(
        DateTime(timezone=True), default=datetime.utcnow, nullable=False
    )

    # Soft delete
    is_deleted = Column(Boolean, default=False, nullable=False)
    deleted_at = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    user = relationship("User", back_populates="conversations")
    messages = relationship(
        "Message",
        back_populates="conversation",
        cascade="all, delete-orphan",
        order_by="Message.created_at",
    )
    summaries = relationship(
        "ConversationSummary",
        back_populates="conversation",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<Conversation(id={self.conversation_id}, user_id={self.user_id}, status={self.status}, crisis={self.crisis_detected})>"


class Message(Base):
    """Message model with vector embeddings for semantic search"""

    __tablename__ = "messages"

    message_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    conversation_id = Column(
        UUID(as_uuid=True), ForeignKey("conversations.conversation_id"), nullable=False
    )

    # Message content
    role = Column(String(50), nullable=False)  # 'user', 'assistant', or 'system'
    content = Column(Text, nullable=False)

    # Optional encryption
    content_encrypted = Column(Text, nullable=True)
    is_encrypted = Column(Boolean, default=False, nullable=False)

    # Vector embedding for semantic search (OpenAI ada-002: 1536 dimensions)
    embedding = Column(Vector(1536), nullable=True)

    # Metadata
    tokens_used = Column(Integer, nullable=True)
    model_used = Column(String(100), nullable=True)

    # Crisis detection for this specific message
    contains_crisis_keywords = Column(Boolean, default=False, nullable=False)
    detected_keywords = Column(JSONB, nullable=True)

    # Metadata
    metadata = Column(JSONB, default={}, nullable=False)

    # Timestamps
    created_at = Column(
        DateTime(timezone=True), default=datetime.utcnow, nullable=False
    )

    # Soft delete
    is_deleted = Column(Boolean, default=False, nullable=False)

    # Relationships
    conversation = relationship("Conversation", back_populates="messages")

    def __repr__(self) -> str:
        return f"<Message(id={self.message_id}, role={self.role}, crisis={self.contains_crisis_keywords})>"
