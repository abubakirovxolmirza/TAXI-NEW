from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import User, Feedback
from app.schemas import FeedbackCreate, FeedbackResponse
from app.auth import get_current_user

router = APIRouter(prefix="/api/feedback", tags=["Feedback"])


@router.post("/", response_model=FeedbackResponse)
def submit_feedback(
    feedback_data: FeedbackCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Submit feedback or complaint"""
    new_feedback = Feedback(
        user_id=current_user.id,
        message=feedback_data.message
    )
    
    db.add(new_feedback)
    db.commit()
    db.refresh(new_feedback)
    
    # TODO: Send to Telegram admin group
    
    return new_feedback
