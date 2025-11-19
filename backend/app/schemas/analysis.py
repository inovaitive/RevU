from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from uuid import UUID
from datetime import datetime
from decimal import Decimal


class AnalysisBase(BaseModel):
    sentiment: Optional[str] = None
    sentiment_score: Optional[Decimal] = None
    categories: Optional[List[str]] = None
    themes: Optional[List[str]] = None
    priority_score: Optional[int] = Field(None, ge=0, le=100)
    urgency: Optional[str] = None
    insights: Optional[Dict[str, Any]] = None
    churn_risk: bool = False
    competitor_mentions: Optional[List[str]] = None
    extracted_entities: Optional[Dict[str, Any]] = None
    confidence_score: Optional[Decimal] = Field(None, ge=0, le=1)
    requires_review: bool = False


class AnalysisCreate(AnalysisBase):
    feedback_id: UUID
    ai_model_version: Optional[str] = None


class AnalysisResponse(AnalysisBase):
    id: UUID
    feedback_id: UUID
    ai_model_version: Optional[str] = None
    reviewed_by: Optional[UUID] = None
    reviewed_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class AnalysisTriggerRequest(BaseModel):
    """Request to trigger analysis for a single feedback"""
    feedback_id: UUID
    force_reanalysis: bool = Field(False, description="Re-analyze even if analysis exists")


class AnalysisBatchTriggerRequest(BaseModel):
    """Request to trigger analysis for multiple feedback items"""
    feedback_ids: List[UUID]
    force_reanalysis: bool = Field(False, description="Re-analyze even if analysis exists")


class AnalysisBatchResult(BaseModel):
    """Result of batch analysis operation"""
    success_count: int
    error_count: int
    total: int
    errors: List[Dict[str, Any]] = []


class AnalysisReviewRequest(BaseModel):
    """Request to review and update an analysis (HITL)"""
    approved: bool
    sentiment: Optional[str] = None
    categories: Optional[List[str]] = None
    themes: Optional[List[str]] = None
    priority_score: Optional[int] = Field(None, ge=0, le=100)
    urgency: Optional[str] = None
    notes: Optional[str] = None
