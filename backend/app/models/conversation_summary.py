"""Conversation summary model for token efficiency"""

from datetime import datetime
from sqlalchemy import Column, String, DateTime, ForeignKey, Integer, Float, Text
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from pgvector.sqlalchemy import Vector
import uuid

from app.core.database import Base


class ConversationSummary(Base):
    """AI-generated conversation summaries for token optimization"""

    __tablename__ = "conversation_summaries"

    summary_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    conversation_id = Column(
        UUID(as_uuid=True),
        ForeignKey("conversations.conversation_id"),
        nullable=False,
    )

    # Summary content
    summary_text = Column(Text, nullable=False)
    summary_type = Column(
        String(50), default="auto", nullable=False
    )  # 'auto', 'manual', 'periodic'

    # Efficiency metrics
    tokens_saved = Column(Integer, default=0, nullable=False)
    original_message_count = Column(Integer, nullable=True)
    compression_ratio = Column(Float, nullable=True)

    # Summary metadata
    key_topics = Column(JSONB, nullable=True)  # Array of main topics
    sentiment_score = Column(Float, nullable=True)  # -1 to 1

    # Embedding for semantic search
    embedding = Column(Vector(1536), nullable=True)

    # Metadata
    metadata = Column(JSONB, default={}, nullable=False)

    # Timestamps
    created_at = Column(
        DateTime(timezone=True), default=datetime.utcnow, nullable=False
    )

    # Relationships
    conversation = relationship("Conversation", back_populates="summaries")

    def __repr__(self) -> str:
        return f"<ConversationSummary(id={self.summary_id}, type={self.summary_type}, tokens_saved={self.tokens_saved})>"

    def calculate_compression_ratio(self, original_tokens: int):
        """Calculate compression efficiency"""
        if original_tokens > 0:
            self.compression_ratio = self.tokens_saved / original_tokens
        else:
            self.compression_ratio = 0.0
