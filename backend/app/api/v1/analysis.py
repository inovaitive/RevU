from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from uuid import UUID
import uuid
import logging
from datetime import datetime

from app.database import get_db
from app.models.user import User
from app.models.feedback import Feedback
from app.models.analysis import Analysis
from app.schemas.analysis import (
    AnalysisResponse,
    AnalysisTriggerRequest,
    AnalysisBatchTriggerRequest,
    AnalysisBatchResult,
    AnalysisReviewRequest
)
from app.middleware.auth import get_current_user
from app.services.nlp_preprocessor import preprocess_text
from app.services.ai_analyzer import analyze_feedback_with_claude, AI_MODEL_VERSION
from app.services.prioritizer import (
    calculate_priority_score,
    categorize_urgency,
    requires_human_review
)

router = APIRouter()
logger = logging.getLogger(__name__)


async def perform_analysis(
    feedback: Feedback,
    db: Session,
    force_reanalysis: bool = False
) -> Analysis:
    """
    Perform complete analysis on a feedback item.

    This orchestrates:
    1. spaCy NLP preprocessing
    2. Claude AI analysis
    3. Priority scoring
    4. HITL flagging

    Args:
        feedback: Feedback object to analyze
        db: Database session
        force_reanalysis: Whether to re-analyze if analysis exists

    Returns:
        Analysis object

    Raises:
        Exception: If analysis fails
    """
    # Check if analysis already exists
    existing_analysis = db.query(Analysis).filter(
        Analysis.feedback_id == feedback.id
    ).first()

    if existing_analysis and not force_reanalysis:
        logger.info(f"Analysis already exists for feedback {feedback.id}")
        return existing_analysis

    try:
        # Step 1: spaCy preprocessing
        logger.info(f"Running spaCy preprocessing for feedback {feedback.id}")
        nlp_result = preprocess_text(feedback.content)

        # Step 2: Claude AI analysis
        logger.info(f"Analyzing feedback {feedback.id} with Claude AI")
        ai_result = await analyze_feedback_with_claude(
            feedback_text=feedback.content,
            author_name=feedback.author_name,
            source=feedback.source,
            rating=float(feedback.rating) if feedback.rating else None,
            entities=nlp_result
        )

        # Step 3: Calculate priority score
        logger.info(f"Calculating priority score for feedback {feedback.id}")
        priority_score = calculate_priority_score(
            sentiment_score=float(ai_result.get("sentiment_score", 0)),
            urgency_keywords=nlp_result.get("urgency_keywords", []),
            churn_risk=ai_result.get("insights", {}).get("churn_risk", False),
            competitor_mentions=ai_result.get("insights", {}).get("competitor_mentions", []),
            rating=float(feedback.rating) if feedback.rating else None,
            feedback_date=feedback.feedback_date,
            nlp_entities=nlp_result
        )

        urgency = categorize_urgency(priority_score)

        # Step 4: Determine if human review is needed
        needs_review = requires_human_review(
            confidence_score=float(ai_result.get("confidence", 0)),
            churn_risk=ai_result.get("insights", {}).get("churn_risk", False),
            priority_score=priority_score,
            sentiment=ai_result.get("sentiment", "neutral"),
            categories=ai_result.get("categories", [])
        )

        # Merge competitor mentions from both NLP and AI
        all_competitors = list(set(
            nlp_result.get("competitor_mentions", []) +
            ai_result.get("insights", {}).get("competitor_mentions", [])
        ))

        # Create or update analysis
        if existing_analysis:
            # Update existing analysis
            existing_analysis.sentiment = ai_result.get("sentiment")
            existing_analysis.sentiment_score = ai_result.get("sentiment_score")
            existing_analysis.categories = ai_result.get("categories", [])
            existing_analysis.themes = ai_result.get("themes", [])
            existing_analysis.priority_score = priority_score
            existing_analysis.urgency = urgency
            existing_analysis.insights = ai_result.get("insights", {})
            existing_analysis.churn_risk = ai_result.get("insights", {}).get("churn_risk", False)
            existing_analysis.competitor_mentions = all_competitors
            existing_analysis.extracted_entities = nlp_result.get("entities", {})
            existing_analysis.confidence_score = ai_result.get("confidence")
            existing_analysis.requires_review = needs_review
            existing_analysis.ai_model_version = AI_MODEL_VERSION
            existing_analysis.updated_at = datetime.utcnow()

            db.commit()
            db.refresh(existing_analysis)
            logger.info(f"Updated analysis for feedback {feedback.id}")
            return existing_analysis
        else:
            # Create new analysis
            new_analysis = Analysis(
                id=uuid.uuid4(),
                feedback_id=feedback.id,
                sentiment=ai_result.get("sentiment"),
                sentiment_score=ai_result.get("sentiment_score"),
                categories=ai_result.get("categories", []),
                themes=ai_result.get("themes", []),
                priority_score=priority_score,
                urgency=urgency,
                insights=ai_result.get("insights", {}),
                churn_risk=ai_result.get("insights", {}).get("churn_risk", False),
                competitor_mentions=all_competitors,
                extracted_entities=nlp_result.get("entities", {}),
                confidence_score=ai_result.get("confidence"),
                requires_review=needs_review,
                ai_model_version=AI_MODEL_VERSION
            )

            db.add(new_analysis)
            db.commit()
            db.refresh(new_analysis)
            logger.info(f"Created new analysis for feedback {feedback.id}")
            return new_analysis

    except Exception as e:
        logger.error(f"Error analyzing feedback {feedback.id}: {str(e)}")
        raise


@router.post("/trigger", response_model=AnalysisResponse)
async def trigger_analysis(
    request: AnalysisTriggerRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Trigger AI analysis for a single feedback item.
    """
    # Fetch feedback
    feedback = db.query(Feedback).filter(
        Feedback.id == request.feedback_id,
        Feedback.organization_id == current_user.organization_id
    ).first()

    if not feedback:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Feedback not found"
        )

    # Perform analysis
    analysis = await perform_analysis(feedback, db, request.force_reanalysis)

    return AnalysisResponse.from_orm(analysis)


@router.post("/batch", response_model=AnalysisBatchResult)
async def trigger_batch_analysis(
    request: AnalysisBatchTriggerRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Trigger AI analysis for multiple feedback items.

    Note: In MVP, this runs synchronously. In production, use Celery for async processing.
    """
    success_count = 0
    error_count = 0
    errors = []

    for feedback_id in request.feedback_ids:
        try:
            # Fetch feedback
            feedback = db.query(Feedback).filter(
                Feedback.id == feedback_id,
                Feedback.organization_id == current_user.organization_id
            ).first()

            if not feedback:
                error_count += 1
                errors.append({
                    "feedback_id": str(feedback_id),
                    "error": "Feedback not found"
                })
                continue

            # Perform analysis
            await perform_analysis(feedback, db, request.force_reanalysis)
            success_count += 1

        except Exception as e:
            error_count += 1
            errors.append({
                "feedback_id": str(feedback_id),
                "error": str(e)
            })
            logger.error(f"Error analyzing feedback {feedback_id}: {str(e)}")

    return AnalysisBatchResult(
        success_count=success_count,
        error_count=error_count,
        total=len(request.feedback_ids),
        errors=errors[:10]  # Return max 10 errors
    )


@router.get("/{feedback_id}", response_model=AnalysisResponse)
async def get_analysis(
    feedback_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get analysis for a specific feedback item.
    """
    # Verify feedback belongs to user's organization
    feedback = db.query(Feedback).filter(
        Feedback.id == feedback_id,
        Feedback.organization_id == current_user.organization_id
    ).first()

    if not feedback:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Feedback not found"
        )

    # Fetch analysis
    analysis = db.query(Analysis).filter(
        Analysis.feedback_id == feedback_id
    ).first()

    if not analysis:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Analysis not found. Trigger analysis first."
        )

    return AnalysisResponse.from_orm(analysis)


@router.get("/pending-review", response_model=List[AnalysisResponse])
async def get_pending_reviews(
    limit: int = 20,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get all analyses requiring human review (HITL).
    """
    # Query analyses that need review
    analyses = db.query(Analysis).join(Feedback).filter(
        Feedback.organization_id == current_user.organization_id,
        Analysis.requires_review == True,
        Analysis.reviewed_by == None
    ).order_by(Analysis.priority_score.desc()).limit(limit).all()

    return [AnalysisResponse.from_orm(a) for a in analyses]


@router.put("/{feedback_id}/review", response_model=AnalysisResponse)
async def review_analysis(
    feedback_id: UUID,
    review: AnalysisReviewRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Review and update an analysis (Human-in-the-Loop).
    """
    # Verify feedback belongs to user's organization
    feedback = db.query(Feedback).filter(
        Feedback.id == feedback_id,
        Feedback.organization_id == current_user.organization_id
    ).first()

    if not feedback:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Feedback not found"
        )

    # Fetch analysis
    analysis = db.query(Analysis).filter(
        Analysis.feedback_id == feedback_id
    ).first()

    if not analysis:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Analysis not found"
        )

    # Update analysis with human review
    if review.sentiment:
        analysis.sentiment = review.sentiment
    if review.categories:
        analysis.categories = review.categories
    if review.themes:
        analysis.themes = review.themes
    if review.priority_score is not None:
        analysis.priority_score = review.priority_score
        analysis.urgency = categorize_urgency(review.priority_score)
    if review.urgency:
        analysis.urgency = review.urgency

    # Mark as reviewed
    analysis.reviewed_by = current_user.id
    analysis.reviewed_at = datetime.utcnow()
    analysis.requires_review = False if review.approved else True

    # Add review notes to insights
    if review.notes:
        if not analysis.insights:
            analysis.insights = {}
        analysis.insights["review_notes"] = review.notes

    analysis.updated_at = datetime.utcnow()

    db.commit()
    db.refresh(analysis)

    return AnalysisResponse.from_orm(analysis)
