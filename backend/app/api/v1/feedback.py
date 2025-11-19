from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from sqlalchemy import desc, asc
from typing import Optional, List
from uuid import UUID
import pandas as pd
import io
from datetime import datetime
import uuid

from app.database import get_db
from app.models.user import User
from app.models.feedback import Feedback
from app.schemas.feedback import (
    FeedbackCreate,
    FeedbackUpdate,
    FeedbackResponse,
    FeedbackWithAnalysis,
    FeedbackListResponse,
    FeedbackBatchUploadResult
)
from app.middleware.auth import get_current_user
import math

router = APIRouter()


@router.get("", response_model=FeedbackListResponse)
async def list_feedback(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    source: Optional[str] = Query(None, description="Filter by source"),
    search: Optional[str] = Query(None, description="Search in content and author"),
    date_from: Optional[datetime] = Query(None, description="Filter feedback from date"),
    date_to: Optional[datetime] = Query(None, description="Filter feedback to date"),
    sort_by: str = Query("created_at", description="Sort by field"),
    sort_order: str = Query("desc", description="Sort order (asc/desc)"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    List all feedback items with pagination and filters.
    """
    # Base query filtered by organization
    query = db.query(Feedback).filter(Feedback.organization_id == current_user.organization_id)

    # Apply filters
    if source:
        query = query.filter(Feedback.source == source)

    if search:
        search_term = f"%{search}%"
        query = query.filter(
            (Feedback.content.ilike(search_term)) |
            (Feedback.author_name.ilike(search_term)) |
            (Feedback.author_email.ilike(search_term))
        )

    if date_from:
        query = query.filter(Feedback.feedback_date >= date_from)

    if date_to:
        query = query.filter(Feedback.feedback_date <= date_to)

    # Get total count
    total = query.count()

    # Apply sorting
    sort_column = getattr(Feedback, sort_by, Feedback.created_at)
    if sort_order == "asc":
        query = query.order_by(asc(sort_column))
    else:
        query = query.order_by(desc(sort_column))

    # Apply pagination
    offset = (page - 1) * page_size
    items = query.offset(offset).limit(page_size).all()

    total_pages = math.ceil(total / page_size) if total > 0 else 0

    return FeedbackListResponse(
        items=[FeedbackResponse.from_orm(item) for item in items],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages
    )


@router.post("", response_model=FeedbackResponse, status_code=status.HTTP_201_CREATED)
async def create_feedback(
    feedback_data: FeedbackCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Create a new feedback item.
    """
    new_feedback = Feedback(
        id=uuid.uuid4(),
        organization_id=current_user.organization_id,
        source=feedback_data.source,
        content=feedback_data.content,
        author_name=feedback_data.author_name,
        author_email=feedback_data.author_email,
        rating=feedback_data.rating,
        feedback_date=feedback_data.feedback_date or datetime.utcnow(),
        raw_metadata=feedback_data.raw_metadata
    )

    db.add(new_feedback)
    db.commit()
    db.refresh(new_feedback)

    return FeedbackResponse.from_orm(new_feedback)


@router.get("/{feedback_id}", response_model=FeedbackWithAnalysis)
async def get_feedback(
    feedback_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get a single feedback item by ID with analysis.
    """
    feedback = db.query(Feedback).filter(
        Feedback.id == feedback_id,
        Feedback.organization_id == current_user.organization_id
    ).first()

    if not feedback:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Feedback not found"
        )

    return FeedbackWithAnalysis.from_orm(feedback)


@router.put("/{feedback_id}", response_model=FeedbackResponse)
async def update_feedback(
    feedback_id: UUID,
    feedback_data: FeedbackUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Update a feedback item.
    """
    feedback = db.query(Feedback).filter(
        Feedback.id == feedback_id,
        Feedback.organization_id == current_user.organization_id
    ).first()

    if not feedback:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Feedback not found"
        )

    # Update only provided fields
    update_data = feedback_data.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(feedback, field, value)

    feedback.updated_at = datetime.utcnow()

    db.commit()
    db.refresh(feedback)

    return FeedbackResponse.from_orm(feedback)


@router.delete("/{feedback_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_feedback(
    feedback_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Delete a feedback item.
    """
    feedback = db.query(Feedback).filter(
        Feedback.id == feedback_id,
        Feedback.organization_id == current_user.organization_id
    ).first()

    if not feedback:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Feedback not found"
        )

    db.delete(feedback)
    db.commit()

    return None


@router.post("/batch", response_model=FeedbackBatchUploadResult)
async def upload_csv(
    file: UploadFile = File(..., description="CSV file with feedback data"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Upload multiple feedback items from CSV file.

    Expected CSV columns:
    - content (required)
    - author_name (optional)
    - author_email (optional)
    - rating (optional, 0-5)
    - feedback_date (optional, ISO format)
    - source (optional, defaults to 'csv')
    """
    if not file.filename.endswith('.csv'):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File must be a CSV"
        )

    try:
        # Read CSV file
        contents = await file.read()
        df = pd.read_csv(io.BytesIO(contents))

        # Validate required columns
        if 'content' not in df.columns:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="CSV must have 'content' column"
            )

        success_count = 0
        error_count = 0
        errors = []

        for index, row in df.iterrows():
            try:
                # Validate content is not empty
                if pd.isna(row['content']) or str(row['content']).strip() == '':
                    error_count += 1
                    errors.append({
                        "row": index + 2,  # +2 for header and 0-indexing
                        "error": "Content is required"
                    })
                    continue

                # Parse feedback_date if present
                feedback_date = None
                if 'feedback_date' in df.columns and not pd.isna(row['feedback_date']):
                    try:
                        feedback_date = pd.to_datetime(row['feedback_date'])
                    except:
                        pass

                # Parse rating if present
                rating = None
                if 'rating' in df.columns and not pd.isna(row['rating']):
                    try:
                        rating = float(row['rating'])
                        if rating < 0 or rating > 5:
                            rating = None
                    except:
                        pass

                # Create feedback
                new_feedback = Feedback(
                    id=uuid.uuid4(),
                    organization_id=current_user.organization_id,
                    source=row.get('source', 'csv') if 'source' in df.columns and not pd.isna(row.get('source')) else 'csv',
                    content=str(row['content']),
                    author_name=str(row['author_name']) if 'author_name' in df.columns and not pd.isna(row['author_name']) else None,
                    author_email=str(row['author_email']) if 'author_email' in df.columns and not pd.isna(row['author_email']) else None,
                    rating=rating,
                    feedback_date=feedback_date or datetime.utcnow()
                )

                db.add(new_feedback)
                success_count += 1

            except Exception as e:
                error_count += 1
                errors.append({
                    "row": index + 2,
                    "error": str(e)
                })

        # Commit all successful inserts
        db.commit()

        return FeedbackBatchUploadResult(
            success_count=success_count,
            error_count=error_count,
            total=len(df),
            errors=errors[:10]  # Return max 10 errors
        )

    except pd.errors.EmptyDataError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="CSV file is empty"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Error processing CSV: {str(e)}"
        )


@router.get("/template/download")
async def download_template():
    """
    Download a sample CSV template for feedback upload.
    """
    # Create sample CSV
    sample_data = {
        'content': ['Great product, very helpful!', 'Having issues with performance'],
        'author_name': ['John Doe', 'Jane Smith'],
        'author_email': ['john@example.com', 'jane@example.com'],
        'rating': [5.0, 3.5],
        'feedback_date': ['2025-11-01T10:00:00', '2025-11-15T14:30:00'],
        'source': ['g2', 'capterra']
    }

    df = pd.DataFrame(sample_data)
    stream = io.StringIO()
    df.to_csv(stream, index=False)
    stream.seek(0)

    return StreamingResponse(
        iter([stream.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=feedback_template.csv"}
    )
