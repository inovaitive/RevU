from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from uuid import UUID
from datetime import datetime
from decimal import Decimal


class FeedbackBase(BaseModel):
    source: str = Field(..., description="Source of feedback (csv, manual, g2, capterra)")
    content: str = Field(..., description="Feedback content text")
    author_name: Optional[str] = None
    author_email: Optional[str] = None
    rating: Optional[Decimal] = Field(None, ge=0, le=5, description="Rating from 0 to 5")
    feedback_date: Optional[datetime] = None
    raw_metadata: Optional[Dict[str, Any]] = None


class FeedbackCreate(FeedbackBase):
    pass


class FeedbackUpdate(BaseModel):
    source: Optional[str] = None
    content: Optional[str] = None
    author_name: Optional[str] = None
    author_email: Optional[str] = None
    rating: Optional[Decimal] = Field(None, ge=0, le=5)
    feedback_date: Optional[datetime] = None
    raw_metadata: Optional[Dict[str, Any]] = None


class FeedbackResponse(FeedbackBase):
    id: UUID
    organization_id: UUID
    ingested_at: datetime
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class FeedbackWithAnalysis(FeedbackResponse):
    """Feedback response with analysis data included"""
    analysis: Optional[Any] = None  # Will be AnalysisResponse

    class Config:
        from_attributes = True


class FeedbackListResponse(BaseModel):
    """Paginated list of feedback items"""
    items: List[FeedbackResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


class FeedbackBatchUploadResult(BaseModel):
    """Result of batch CSV upload"""
    success_count: int
    error_count: int
    total: int
    errors: List[Dict[str, Any]] = []
