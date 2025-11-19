from pydantic import BaseModel
from typing import Dict, List, Any
from datetime import datetime


class SentimentBreakdown(BaseModel):
    """Breakdown of sentiment counts"""
    positive: int = 0
    negative: int = 0
    neutral: int = 0
    mixed: int = 0


class FeedbackSummary(BaseModel):
    """Summary of a single feedback item for dashboard"""
    id: str
    content_snippet: str
    sentiment: str
    priority_score: int
    urgency: str
    created_at: datetime


class DashboardStats(BaseModel):
    """Dashboard statistics response"""
    # Overall counts
    total_feedback: int
    total_analyzed: int
    pending_analysis: int

    # Sentiment
    sentiment_breakdown: SentimentBreakdown
    average_sentiment_score: float

    # Priority
    average_priority_score: float
    high_priority_count: int
    critical_priority_count: int

    # Risks and insights
    churn_risk_count: int
    competitor_mentions_count: int

    # Review
    pending_review_count: int

    # Top themes
    top_themes: List[Dict[str, Any]]

    # Recent feedback
    recent_feedback: List[FeedbackSummary]

    # Trend data (optional for charts)
    sentiment_trend: List[Dict[str, Any]] = []


class ThemeStats(BaseModel):
    """Statistics for a specific theme"""
    theme: str
    count: int
    sentiment_distribution: Dict[str, int]
