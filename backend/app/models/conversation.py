"""Conversation and Message models with vector embeddings"""

from datetime import datetime
from sqlalchemy import Column, String, DateTime, Boolean, ForeignKey, Integer, Text, JSON
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from pgvector.sqlalchemy import Vector
import uuid

from app.core.database import Base


class Conversation(Base):
    """Conversation session model"""

    __tablename__ = "conversations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)

    # Conversation metadata
    title = Column(String(255), nullable=True)
    summary = Column(Text, nullable=True)

    # Crisis detection
    crisis_detected = Column(Boolean, default=False)
    crisis_severity = Column(Integer, default=0)  # 0-10 scale
    crisis_keywords_found = Column(JSON, nullable=True)  # List of detected keywords
    crisis_timestamp = Column(DateTime, nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )
    last_message_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Soft delete
    is_deleted = Column(Boolean, default=False)
    deleted_at = Column(DateTime, nullable=True)

    # Relationships
    user = relationship("User", back_populates="conversations")
    messages = relationship(
        "Message",
        back_populates="conversation",
        cascade="all, delete-orphan",
        order_by="Message.created_at",
    )

    def __repr__(self) -> str:
        return f"<Conversation(id={self.id}, user_id={self.user_id}, crisis={self.crisis_detected})>"


class Message(Base):
    """Message model with vector embeddings for semantic search"""

    __tablename__ = "messages"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    conversation_id = Column(
        UUID(as_uuid=True), ForeignKey("conversations.id"), nullable=False
    )

    # Message content
    role = Column(String(50), nullable=False)  # 'user' or 'assistant'
    content = Column(Text, nullable=False)

    # Vector embedding for semantic search (OpenAI ada-002: 1536 dimensions)
    embedding = Column(Vector(1536), nullable=True)

    # Metadata
    token_count = Column(Integer, nullable=True)
    model_used = Column(String(100), nullable=True)

    # Crisis detection for this specific message
    contains_crisis_keywords = Column(Boolean, default=False)
    detected_keywords = Column(JSON, nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Soft delete
    is_deleted = Column(Boolean, default=False)

    # Relationships
    conversation = relationship("Conversation", back_populates="messages")

    def __repr__(self) -> str:
        return f"<Message(id={self.id}, role={self.role}, crisis={self.contains_crisis_keywords})>"
