"""Memory model for long-term context storage"""

from datetime import datetime
from sqlalchemy import Column, String, DateTime, Boolean, ForeignKey, Integer, Float, Text
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from pgvector.sqlalchemy import Vector
import uuid

from app.core.database import Base


class Memory(Base):
    """Memory model for semantic, episodic, and factual user information"""

    __tablename__ = "memories"

    memory_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.user_id"), nullable=False)

    # Memory classification
    memory_type = Column(
        String(50), nullable=False
    )  # 'semantic', 'episodic', 'fact'

    # Content and embedding
    content = Column(Text, nullable=False)
    embedding = Column(Vector(1536), nullable=True)

    # Importance and access tracking
    importance_score = Column(Float, default=0.5, nullable=False)
    access_count = Column(Integer, default=0, nullable=False)
    last_accessed_at = Column(DateTime(timezone=True), nullable=True)

    # Source tracking
    source_conversation_id = Column(
        UUID(as_uuid=True), ForeignKey("conversations.conversation_id"), nullable=True
    )
    source_message_id = Column(
        UUID(as_uuid=True), ForeignKey("messages.message_id"), nullable=True
    )

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

    # Soft delete
    is_deleted = Column(Boolean, default=False, nullable=False)

    # Relationships
    user = relationship("User", foreign_keys=[user_id])
    source_conversation = relationship("Conversation", foreign_keys=[source_conversation_id])
    source_message = relationship("Message", foreign_keys=[source_message_id])

    def __repr__(self) -> str:
        return f"<Memory(id={self.memory_id}, type={self.memory_type}, importance={self.importance_score})>"

    def update_access(self):
        """Update access tracking"""
        self.access_count += 1
        self.last_accessed_at = datetime.utcnow()
