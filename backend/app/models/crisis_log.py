"""Crisis log model for safety monitoring"""

from datetime import datetime
from sqlalchemy import Column, String, DateTime, Boolean, ForeignKey, Integer, Text
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
import uuid

from app.core.database import Base


class CrisisLog(Base):
    """Crisis detection and intervention logging"""

    __tablename__ = "crisis_logs"

    log_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.user_id"), nullable=False)
    conversation_id = Column(
        UUID(as_uuid=True), ForeignKey("conversations.conversation_id"), nullable=True
    )
    message_id = Column(
        UUID(as_uuid=True), ForeignKey("messages.message_id"), nullable=True
    )

    # Risk assessment
    risk_level = Column(
        String(50), nullable=False
    )  # 'none', 'low', 'medium', 'high', 'critical'
    risk_score = Column(Integer, nullable=True)  # 0-10 scale

    # Crisis details
    message_content = Column(Text, nullable=True)  # Snapshot of concerning content
    detected_keywords = Column(JSONB, nullable=True)
    detection_method = Column(
        String(100), nullable=True
    )  # 'keyword', 'pattern', 'ml_model', 'combined'

    # Action taken
    action_taken = Column(String(255), nullable=True)
    resources_provided = Column(JSONB, nullable=True)
    alert_sent = Column(Boolean, default=False, nullable=False)
    alert_sent_to = Column(String(255), nullable=True)

    # Follow-up tracking
    follow_up_required = Column(Boolean, default=False, nullable=False)
    follow_up_completed = Column(Boolean, default=False, nullable=False)
    follow_up_notes = Column(Text, nullable=True)

    # Metadata
    metadata = Column(JSONB, default={}, nullable=False)

    # Timestamps
    created_at = Column(
        DateTime(timezone=True), default=datetime.utcnow, nullable=False
    )
    resolved_at = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    user = relationship("User", back_populates="crisis_logs")
    conversation = relationship("Conversation", foreign_keys=[conversation_id])
    message = relationship("Message", foreign_keys=[message_id])

    def __repr__(self) -> str:
        return f"<CrisisLog(id={self.log_id}, risk={self.risk_level}, resolved={self.resolved_at is not None})>"

    def mark_resolved(self, notes: str = None):
        """Mark crisis as resolved"""
        self.resolved_at = datetime.utcnow()
        if notes:
            self.follow_up_notes = notes
        self.follow_up_completed = True
