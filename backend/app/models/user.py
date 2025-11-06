"""User model for authentication and tracking"""

from datetime import datetime
from sqlalchemy import Column, String, DateTime, Boolean
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
import uuid

from app.core.database import Base


class User(Base):
    """User model with HIPAA/GDPR compliance fields"""

    __tablename__ = "users"

    user_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Encrypted email for privacy
    email_encrypted = Column(String, nullable=True)
    email_hash = Column(String(64), unique=True, nullable=True)

    # Anonymous session support
    is_anonymous = Column(Boolean, default=True, nullable=False)
    session_token = Column(String(255), unique=True, nullable=False)

    # Compliance
    consent_given = Column(Boolean, default=False, nullable=False)
    consent_timestamp = Column(DateTime(timezone=True), nullable=True)
    data_retention_until = Column(DateTime(timezone=True), nullable=True)

    # Metadata (user preferences, settings)
    # Using user_metadata to avoid SQLAlchemy reserved keyword 'metadata'
    user_metadata = Column("metadata", JSONB, default={}, nullable=False)

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
    last_active = Column(
        DateTime(timezone=True), default=datetime.utcnow, nullable=False
    )

    # Privacy flags
    deleted_at = Column(DateTime(timezone=True), nullable=True)
    is_deleted = Column(Boolean, default=False, nullable=False)

    # Relationships
    conversations = relationship(
        "Conversation", back_populates="user", cascade="all, delete-orphan"
    )
    crisis_logs = relationship(
        "CrisisLog", back_populates="user", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<User(id={self.user_id}, anonymous={self.is_anonymous})>"
