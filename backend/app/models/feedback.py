from sqlalchemy import Column, String, Text, DateTime, ForeignKey, DECIMAL
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid
from app.database import Base


class Feedback(Base):
    __tablename__ = "feedback"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    source = Column(String(100), nullable=False, index=True)  # csv, manual, g2, capterra, etc.
    content = Column(Text, nullable=False)
    author_name = Column(String(255), nullable=True)
    author_email = Column(String(255), nullable=True)
    rating = Column(DECIMAL(3, 2), nullable=True)  # 0.00 to 5.00
    feedback_date = Column(DateTime(timezone=True), nullable=True, index=True)
    raw_metadata = Column(JSONB, nullable=True)  # Store original platform-specific data
    ingested_at = Column(DateTime(timezone=True), server_default=func.now())
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    organization = relationship("Organization", back_populates="feedback")
    analysis = relationship("Analysis", back_populates="feedback", uselist=False, cascade="all, delete-orphan")
