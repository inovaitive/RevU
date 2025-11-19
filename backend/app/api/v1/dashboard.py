from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, desc
from typing import Optional
from datetime import datetime, timedelta
from collections import Counter
import logging

from app.database import get_db
from app.models.user import User
from app.models.feedback import Feedback
from app.models.analysis import Analysis
from app.schemas.dashboard import DashboardStats, SentimentBreakdown, FeedbackSummary
from app.middleware.auth import get_current_user

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/stats", response_model=DashboardStats)
async def get_dashboard_stats(
    days: int = Query(30, description="Number of days to include in stats", ge=1, le=365),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get comprehensive dashboard statistics.

    Includes:
    - Total feedback counts
    - Sentiment breakdown
    - Priority distribution
    - Churn risk alerts
    - Top themes
    - Recent feedback
    """
    org_id = current_user.organization_id

    # Date filter
    date_threshold = datetime.utcnow() - timedelta(days=days)

    # 1. Total feedback count
    total_feedback = db.query(Feedback).filter(
        Feedback.organization_id == org_id,
        Feedback.created_at >= date_threshold
    ).count()

    # 2. Total analyzed (has analysis)
    total_analyzed = db.query(Feedback).join(Analysis).filter(
        Feedback.organization_id == org_id,
        Feedback.created_at >= date_threshold
    ).count()

    pending_analysis = total_feedback - total_analyzed

    # 3. Sentiment breakdown
    sentiment_counts = db.query(
        Analysis.sentiment,
        func.count(Analysis.id)
    ).join(Feedback).filter(
        Feedback.organization_id == org_id,
        Feedback.created_at >= date_threshold
    ).group_by(Analysis.sentiment).all()

    sentiment_breakdown = SentimentBreakdown()
    for sentiment, count in sentiment_counts:
        if sentiment == "positive":
            sentiment_breakdown.positive = count
        elif sentiment == "negative":
            sentiment_breakdown.negative = count
        elif sentiment == "neutral":
            sentiment_breakdown.neutral = count
        elif sentiment == "mixed":
            sentiment_breakdown.mixed = count

    # 4. Average sentiment score
    avg_sentiment = db.query(
        func.avg(Analysis.sentiment_score)
    ).join(Feedback).filter(
        Feedback.organization_id == org_id,
        Feedback.created_at >= date_threshold,
        Analysis.sentiment_score.isnot(None)
    ).scalar()

    average_sentiment_score = float(avg_sentiment) if avg_sentiment else 0.0

    # 5. Average priority score
    avg_priority = db.query(
        func.avg(Analysis.priority_score)
    ).join(Feedback).filter(
        Feedback.organization_id == org_id,
        Feedback.created_at >= date_threshold,
        Analysis.priority_score.isnot(None)
    ).scalar()

    average_priority_score = float(avg_priority) if avg_priority else 0.0

    # 6. High and critical priority counts
    high_priority_count = db.query(Analysis).join(Feedback).filter(
        Feedback.organization_id == org_id,
        Feedback.created_at >= date_threshold,
        Analysis.priority_score >= 60
    ).count()

    critical_priority_count = db.query(Analysis).join(Feedback).filter(
        Feedback.organization_id == org_id,
        Feedback.created_at >= date_threshold,
        Analysis.priority_score >= 80
    ).count()

    # 7. Churn risk count
    churn_risk_count = db.query(Analysis).join(Feedback).filter(
        Feedback.organization_id == org_id,
        Feedback.created_at >= date_threshold,
        Analysis.churn_risk == True
    ).count()

    # 8. Competitor mentions count
    competitor_mentions_count = db.query(Analysis).join(Feedback).filter(
        Feedback.organization_id == org_id,
        Feedback.created_at >= date_threshold,
        Analysis.competitor_mentions.isnot(None),
        func.array_length(Analysis.competitor_mentions, 1) > 0
    ).count()

    # 9. Pending review count
    pending_review_count = db.query(Analysis).join(Feedback).filter(
        Feedback.organization_id == org_id,
        Feedback.created_at >= date_threshold,
        Analysis.requires_review == True,
        Analysis.reviewed_by.is_(None)
    ).count()

    # 10. Top themes
    # Get all themes from analyses
    analyses_with_themes = db.query(Analysis.themes).join(Feedback).filter(
        Feedback.organization_id == org_id,
        Feedback.created_at >= date_threshold,
        Analysis.themes.isnot(None)
    ).all()

    # Flatten themes and count
    all_themes = []
    for (themes,) in analyses_with_themes:
        if themes:
            all_themes.extend(themes)

    theme_counts = Counter(all_themes)
    top_themes = [
        {"theme": theme, "count": count}
        for theme, count in theme_counts.most_common(10)
    ]

    # 11. Recent feedback (last 10)
    recent_feedback_items = db.query(Feedback, Analysis).outerjoin(Analysis).filter(
        Feedback.organization_id == org_id
    ).order_by(desc(Feedback.created_at)).limit(10).all()

    recent_feedback = []
    for feedback, analysis in recent_feedback_items:
        # Truncate content for snippet
        content_snippet = feedback.content[:100] + "..." if len(feedback.content) > 100 else feedback.content

        recent_feedback.append(FeedbackSummary(
            id=str(feedback.id),
            content_snippet=content_snippet,
            sentiment=analysis.sentiment if analysis else "unanalyzed",
            priority_score=analysis.priority_score if analysis else 0,
            urgency=analysis.urgency if analysis else "unknown",
            created_at=feedback.created_at
        ))

    # 12. Sentiment trend (last 7 days)
    sentiment_trend = []
    for i in range(7):
        day = datetime.utcnow() - timedelta(days=6-i)
        day_start = day.replace(hour=0, minute=0, second=0, microsecond=0)
        day_end = day_start + timedelta(days=1)

        day_sentiment = db.query(
            func.avg(Analysis.sentiment_score)
        ).join(Feedback).filter(
            Feedback.organization_id == org_id,
            Feedback.created_at >= day_start,
            Feedback.created_at < day_end,
            Analysis.sentiment_score.isnot(None)
        ).scalar()

        sentiment_trend.append({
            "date": day_start.strftime("%Y-%m-%d"),
            "average_sentiment": float(day_sentiment) if day_sentiment else 0.0
        })

    return DashboardStats(
        total_feedback=total_feedback,
        total_analyzed=total_analyzed,
        pending_analysis=pending_analysis,
        sentiment_breakdown=sentiment_breakdown,
        average_sentiment_score=round(average_sentiment_score, 2),
        average_priority_score=round(average_priority_score, 1),
        high_priority_count=high_priority_count,
        critical_priority_count=critical_priority_count,
        churn_risk_count=churn_risk_count,
        competitor_mentions_count=competitor_mentions_count,
        pending_review_count=pending_review_count,
        top_themes=top_themes,
        recent_feedback=recent_feedback,
        sentiment_trend=sentiment_trend
    )


@router.get("/themes")
async def get_theme_stats(
    days: int = Query(30, ge=1, le=365),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get detailed statistics for each theme.
    """
    org_id = current_user.organization_id
    date_threshold = datetime.utcnow() - timedelta(days=days)

    # Get all analyses with themes
    analyses = db.query(Analysis.themes, Analysis.sentiment).join(Feedback).filter(
        Feedback.organization_id == org_id,
        Feedback.created_at >= date_threshold,
        Analysis.themes.isnot(None)
    ).all()

    # Build theme statistics
    theme_stats = {}

    for themes, sentiment in analyses:
        if not themes:
            continue

        for theme in themes:
            if theme not in theme_stats:
                theme_stats[theme] = {
                    "theme": theme,
                    "count": 0,
                    "sentiment_distribution": {
                        "positive": 0,
                        "negative": 0,
                        "neutral": 0,
                        "mixed": 0
                    }
                }

            theme_stats[theme]["count"] += 1
            if sentiment in theme_stats[theme]["sentiment_distribution"]:
                theme_stats[theme]["sentiment_distribution"][sentiment] += 1

    # Sort by count
    sorted_themes = sorted(theme_stats.values(), key=lambda x: x["count"], reverse=True)

    return {"themes": sorted_themes[:20]}  # Top 20 themes


@router.get("/urgent-items")
async def get_urgent_items(
    limit: int = Query(10, ge=1, le=50),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get urgent feedback items that need immediate attention.

    Returns items with:
    - Critical or high urgency
    - Churn risk
    - High priority score
    """
    org_id = current_user.organization_id

    urgent_items = db.query(Feedback, Analysis).join(Analysis).filter(
        Feedback.organization_id == org_id,
        (
            (Analysis.urgency.in_(["critical", "high"])) |
            (Analysis.churn_risk == True) |
            (Analysis.priority_score >= 70)
        )
    ).order_by(desc(Analysis.priority_score)).limit(limit).all()

    results = []
    for feedback, analysis in urgent_items:
        results.append({
            "feedback_id": str(feedback.id),
            "content_snippet": feedback.content[:150] + "..." if len(feedback.content) > 150 else feedback.content,
            "author_name": feedback.author_name,
            "source": feedback.source,
            "sentiment": analysis.sentiment,
            "priority_score": analysis.priority_score,
            "urgency": analysis.urgency,
            "churn_risk": analysis.churn_risk,
            "requires_review": analysis.requires_review,
            "created_at": feedback.created_at
        })

    return {"urgent_items": results}
