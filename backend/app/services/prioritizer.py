from typing import Dict, Any, List, Optional
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


def calculate_priority_score(
    sentiment_score: float,
    urgency_keywords: List[str],
    churn_risk: bool,
    competitor_mentions: List[str],
    rating: Optional[float] = None,
    feedback_date: Optional[datetime] = None,
    nlp_entities: Optional[Dict[str, Any]] = None
) -> int:
    """
    Calculate priority score for feedback based on multiple factors.

    Score ranges from 0-100, with higher scores indicating higher priority.

    Scoring breakdown:
    - Sentiment (0-30 points): Negative feedback gets higher priority
    - Urgency keywords (0-30 points): Keywords like "critical", "urgent"
    - Churn risk (0-25 points): High priority if customer might leave
    - Competitor mentions (0-15 points): Important competitive intelligence
    - Low rating (0-10 points): Low ratings need attention
    - Recency (0-10 points): Recent feedback is more relevant

    Args:
        sentiment_score: Score from -1.0 (negative) to 1.0 (positive)
        urgency_keywords: List of urgency-related keywords found
        churn_risk: Boolean indicating if customer might churn
        competitor_mentions: List of competitor names mentioned
        rating: Numerical rating (0-5) if available
        feedback_date: When feedback was submitted
        nlp_entities: Additional entities from NLP processing

    Returns:
        Priority score (0-100)
    """
    score = 0

    # 1. Sentiment component (0-30 points)
    # More negative sentiment = higher priority
    if sentiment_score <= -0.7:
        score += 30  # Very negative
    elif sentiment_score <= -0.4:
        score += 25  # Negative
    elif sentiment_score <= -0.1:
        score += 15  # Slightly negative
    elif sentiment_score <= 0.1:
        score += 10  # Neutral (still worth reviewing)
    # Positive feedback gets lower priority (0-5 points)
    elif sentiment_score > 0.1:
        score += 5

    # 2. Urgency keywords (0-30 points)
    # Each urgency keyword adds points, capped at 30
    urgency_points = min(len(urgency_keywords) * 10, 30)
    score += urgency_points

    # 3. Churn risk (0-25 points)
    # Customer at risk of leaving gets very high priority
    if churn_risk:
        score += 25

    # 4. Competitor mentions (0-15 points)
    # Competitive intelligence is valuable
    if competitor_mentions and len(competitor_mentions) > 0:
        score += 15

    # 5. Low rating (0-10 points)
    # Ratings below 3.0 indicate dissatisfaction
    if rating is not None:
        if rating < 2.0:
            score += 10
        elif rating < 3.0:
            score += 7
        elif rating < 3.5:
            score += 4

    # 6. Recency (0-10 points)
    # Recent feedback is more actionable
    if feedback_date:
        days_old = (datetime.utcnow() - feedback_date).days
        if days_old < 1:
            score += 10  # Today
        elif days_old < 7:
            score += 8   # This week
        elif days_old < 30:
            score += 5   # This month
        elif days_old < 90:
            score += 2   # This quarter

    # 7. Additional boost for critical combinations
    # Very negative + churn risk = extra boost
    if sentiment_score < -0.5 and churn_risk:
        score += 10

    # Multiple urgency keywords = critical
    if len(urgency_keywords) >= 3:
        score += 5

    # Cap score at 100
    final_score = min(score, 100)

    logger.debug(f"Priority score calculated: {final_score} (sentiment: {sentiment_score}, urgency: {len(urgency_keywords)}, churn: {churn_risk})")

    return final_score


def categorize_urgency(priority_score: int) -> str:
    """
    Categorize urgency level based on priority score.

    Args:
        priority_score: Calculated priority score (0-100)

    Returns:
        Urgency level: "critical", "high", "medium", or "low"
    """
    if priority_score >= 80:
        return "critical"
    elif priority_score >= 60:
        return "high"
    elif priority_score >= 30:
        return "medium"
    else:
        return "low"


def requires_human_review(
    confidence_score: float,
    churn_risk: bool,
    priority_score: int,
    sentiment: str,
    categories: List[str]
) -> bool:
    """
    Determine if feedback requires human review (HITL - Human In The Loop).

    Flags for review if:
    - AI confidence is low (<0.7)
    - Churn risk detected
    - Very high priority (>80)
    - Sentiment is "mixed" (ambiguous)
    - Contains both complaint and praise (conflicting signals)

    Args:
        confidence_score: AI's confidence in analysis (0.0-1.0)
        churn_risk: Boolean indicating churn risk
        priority_score: Calculated priority (0-100)
        sentiment: Detected sentiment ("positive", "negative", "neutral", "mixed")
        categories: List of feedback categories

    Returns:
        Boolean indicating if human review is needed
    """
    # Low confidence = needs review
    if confidence_score < 0.7:
        logger.debug(f"Flagged for review: Low confidence ({confidence_score})")
        return True

    # Churn risk = always review
    if churn_risk:
        logger.debug("Flagged for review: Churn risk detected")
        return True

    # Very high priority = review
    if priority_score > 80:
        logger.debug(f"Flagged for review: High priority ({priority_score})")
        return True

    # Mixed sentiment = ambiguous, needs review
    if sentiment == "mixed":
        logger.debug("Flagged for review: Mixed sentiment")
        return True

    # Conflicting categories (both complaint and praise)
    if "complaint" in categories and "praise" in categories:
        logger.debug("Flagged for review: Conflicting categories")
        return True

    # Bug reports with low confidence
    if "bug" in categories and confidence_score < 0.8:
        logger.debug("Flagged for review: Bug report with medium confidence")
        return True

    return False


def calculate_sentiment_score_from_rating(rating: Optional[float]) -> float:
    """
    Convert a numerical rating (0-5) to a sentiment score (-1 to 1).

    This can be used as a fallback or to validate AI sentiment analysis.

    Args:
        rating: Numerical rating from 0 to 5

    Returns:
        Sentiment score from -1.0 to 1.0
    """
    if rating is None:
        return 0.0

    # Map 0-5 rating to -1 to 1 scale
    # 0 -> -1.0, 2.5 -> 0.0, 5 -> 1.0
    return (rating - 2.5) / 2.5


def get_priority_label(priority_score: int) -> str:
    """
    Get a human-readable priority label.

    Args:
        priority_score: Priority score (0-100)

    Returns:
        Priority label with emoji
    """
    urgency = categorize_urgency(priority_score)

    labels = {
        "critical": f"🔴 Critical (P0)",
        "high": f"🟠 High (P1)",
        "medium": f"🟡 Medium (P2)",
        "low": f"🟢 Low (P3)"
    }

    return labels.get(urgency, "⚪ Unknown")
