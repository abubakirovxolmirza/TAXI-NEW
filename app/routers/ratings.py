from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from app.database import get_db
from app.models import User, Rating, TaxiOrder, DeliveryOrder
from app.schemas import RatingCreate, RatingResponse
from app.auth import get_current_user
from app.utils import update_driver_rating, create_notification

router = APIRouter(prefix="/api/ratings", tags=["Ratings"])


@router.post("/", response_model=RatingResponse, status_code=status.HTTP_201_CREATED)
def create_rating(
    rating_data: RatingCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create a rating for a completed order"""
    # Get order based on type
    if rating_data.order_type == "taxi":
        order = db.query(TaxiOrder).filter(TaxiOrder.id == rating_data.order_id).first()
    elif rating_data.order_type == "delivery":
        order = db.query(DeliveryOrder).filter(DeliveryOrder.id == rating_data.order_id).first()
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid order type"
        )
    
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order not found"
        )
    
    # Check if user owns the order
    if order.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to rate this order"
        )
    
    # Check if order is completed
    from app.models import OrderStatus
    if order.status != OrderStatus.COMPLETED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only completed orders can be rated"
        )
    
    # Check if rating already exists
    existing_rating = db.query(Rating).filter(
        Rating.user_id == current_user.id,
        Rating.driver_id == rating_data.driver_id,
        (Rating.taxi_order_id == rating_data.order_id) if rating_data.order_type == "taxi" 
        else (Rating.delivery_order_id == rating_data.order_id)
    ).first()
    
    if existing_rating:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You have already rated this order"
        )
    
    # Create rating
    new_rating = Rating(
        user_id=current_user.id,
        driver_id=rating_data.driver_id,
        rating=rating_data.rating,
        comment=rating_data.comment
    )
    
    if rating_data.order_type == "taxi":
        new_rating.taxi_order_id = rating_data.order_id
    else:
        new_rating.delivery_order_id = rating_data.order_id
    
    db.add(new_rating)
    db.commit()
    db.refresh(new_rating)
    
    # Update driver's average rating
    update_driver_rating(db, rating_data.driver_id)
    
    # Notify driver
    create_notification(
        db=db,
        title="New Rating",
        message=f"You received a {rating_data.rating}-star rating from a customer.",
        notification_type="rating_received",
        driver_id=rating_data.driver_id
    )
    
    return new_rating


@router.get("/driver/{driver_id}", response_model=List[RatingResponse])
def get_driver_ratings(
    driver_id: int,
    db: Session = Depends(get_db)
):
    """Get all ratings for a driver"""
    ratings = db.query(Rating).filter(Rating.driver_id == driver_id).order_by(Rating.created_at.desc()).all()
    return ratings
