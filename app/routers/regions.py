from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
from app.database import get_db
from app.models import Region, District, Pricing
from app.schemas import RegionResponse, RegionCreate, DistrictResponse, DistrictCreate, PricingResponse

router = APIRouter(prefix="/api/regions", tags=["Regions"])


@router.get("/", response_model=List[RegionResponse])
def get_regions(db: Session = Depends(get_db)):
    """Get all active regions with their districts"""
    regions = db.query(Region).filter(Region.is_active == True).all()
    return regions


@router.get("/{region_id}/districts", response_model=List[DistrictResponse])
def get_districts_by_region(region_id: int, db: Session = Depends(get_db)):
    """Get all districts for a specific region"""
    districts = db.query(District).filter(
        District.region_id == region_id,
        District.is_active == True
    ).all()
    return districts


@router.get("/pricing", response_model=List[PricingResponse])
def get_pricing(
    from_region_id: Optional[int] = None,
    to_region_id: Optional[int] = None,
    service_type: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """Get pricing for routes. Clients can view all prices or filter by route and service type."""
    query = db.query(Pricing).filter(Pricing.is_active == True)
    
    if from_region_id:
        query = query.filter(Pricing.from_region_id == from_region_id)
    
    if to_region_id:
        query = query.filter(Pricing.to_region_id == to_region_id)
    
    if service_type:
        if service_type not in ["taxi", "delivery"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid service_type. Must be 'taxi' or 'delivery'"
            )
        query = query.filter(Pricing.service_type == service_type)
    
    pricing = query.all()
    return pricing


@router.get("/pricing/calculate")
def calculate_price(
    from_region_id: int,
    to_region_id: int,
    service_type: str,
    passengers: Optional[int] = None,
    db: Session = Depends(get_db)
):
    """Calculate price for a specific route"""
    if service_type not in ["taxi", "delivery"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid service_type. Must be 'taxi' or 'delivery'"
        )
    
    pricing = db.query(Pricing).filter(
        Pricing.from_region_id == from_region_id,
        Pricing.to_region_id == to_region_id,
        Pricing.service_type == service_type,
        Pricing.is_active == True
    ).first()
    
    if not pricing:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Pricing not found for this route"
        )
    
    base_price = pricing.base_price
    
    # Apply discount for taxi service based on passengers
    if service_type == "taxi" and passengers:
        if passengers == 1:
            discount = pricing.discount_1_passenger
        elif passengers == 2:
            discount = pricing.discount_2_passengers
        elif passengers == 3:
            discount = pricing.discount_3_passengers
        elif passengers == 4:
            discount = pricing.discount_full_car
        else:
            discount = 0
        
        # Calculate price per person after discount
        price_per_person = base_price * (1 - discount / 100)
        # Total price for all passengers
        total_price = price_per_person * passengers
        
        return {
            "from_region_id": from_region_id,
            "to_region_id": to_region_id,
            "service_type": service_type,
            "base_price": str(base_price),
            "passengers": passengers,
            "discount_percentage": str(discount),
            "price_per_person": str(price_per_person),
            "total_price": str(total_price)
        }
    else:
        # For delivery, no passenger count
        return {
            "from_region_id": from_region_id,
            "to_region_id": to_region_id,
            "service_type": service_type,
            "base_price": str(base_price),
            "passengers": passengers,
            "total_price": str(base_price)
        }
