from sqlalchemy import Column, String, Integer, Boolean, DateTime, ForeignKey, DECIMAL, ARRAY
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid
from app.database import Base


class Analysis(Base):
    __tablename__ = "analysis"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    feedback_id = Column(UUID(as_uuid=True), ForeignKey("feedback.id", ondelete="CASCADE"), nullable=False, unique=True, index=True)

    # Sentiment
    sentiment = Column(String(50), nullable=True, index=True)  # positive, negative, neutral, mixed
    sentiment_score = Column(DECIMAL(4, 3), nullable=True)  # -1.000 to 1.000

    # Categories and themes
    categories = Column(ARRAY(String), nullable=True)  # bug, feature_request, complaint, praise, question, etc.
    themes = Column(ARRAY(String), nullable=True)  # UI, performance, support, pricing, etc.

    # Priority
    priority_score = Column(Integer, nullable=True, index=True)  # 0-100
    urgency = Column(String(50), nullable=True, index=True)  # low, medium, high, critical

    # Insights
    insights = Column(JSONB, nullable=True)  # Structured insights from AI

    # Risk and intelligence
    churn_risk = Column(Boolean, default=False, index=True)
    competitor_mentions = Column(ARRAY(String), nullable=True)

    # Entities from spaCy
    extracted_entities = Column(JSONB, nullable=True)

    # Confidence and review
    confidence_score = Column(DECIMAL(4, 3), nullable=True)  # 0.000 to 1.000
    requires_review = Column(Boolean, default=False)
    reviewed_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    reviewed_at = Column(DateTime(timezone=True), nullable=True)

    # Metadata
    ai_model_version = Column(String(100), nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    feedback = relationship("Feedback", back_populates="analysis")
    reviewer = relationship("User", back_populates="reviewed_analyses", foreign_keys=[reviewed_by])
