"""User model for authentication and tracking"""

from datetime import datetime
from sqlalchemy import Column, String, DateTime, Boolean
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import uuid

from app.core.database import Base


class User(Base):
    """User model with HIPAA/GDPR compliance fields"""

    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String(255), unique=True, nullable=True, index=True)

    # Anonymous session support
    is_anonymous = Column(Boolean, default=True)
    session_token = Column(String(255), unique=True, index=True)

    # Compliance
    consent_given = Column(Boolean, default=False)
    consent_timestamp = Column(DateTime, nullable=True)
    data_retention_until = Column(DateTime, nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )
    last_active = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Privacy flags
    deleted_at = Column(DateTime, nullable=True)  # Soft delete
    is_deleted = Column(Boolean, default=False)

    # Relationships
    conversations = relationship(
        "Conversation", back_populates="user", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<User(id={self.id}, anonymous={self.is_anonymous})>"
