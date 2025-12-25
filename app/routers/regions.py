from decimal import Decimal
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
from app.database import get_db
from app.models import Region, District, Pricing, DistrictPricing, SeatType, User
from app.schemas import (
    RegionResponse, RegionCreate, DistrictResponse, DistrictCreate, PricingResponse,
    RegionCreateWithPricing, DistrictCreateWithPricing,
    DistrictPricingCreate, DistrictPricingUpdate, DistrictPricingResponse
)
from app.auth import get_current_admin

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
    seat_type: Optional[str] = None,
    from_district_id: Optional[int] = None,
    to_district_id: Optional[int] = None,
    db: Session = Depends(get_db)
):
    """Calculate price for a specific route (supports district-level pricing)"""
    if service_type not in ["taxi", "delivery"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid service_type. Must be 'taxi' or 'delivery'"
        )
    
    pricing = None
    pricing_level = "default"
    
    # Try district-level pricing first
    if from_district_id and to_district_id:
        pricing = db.query(DistrictPricing).filter(
            DistrictPricing.from_district_id == from_district_id,
            DistrictPricing.to_district_id == to_district_id,
            DistrictPricing.service_type == service_type,
            DistrictPricing.is_active == True
        ).first()
        if pricing:
            pricing_level = "district"
    
    # Fallback to region-level pricing
    if not pricing:
        pricing = db.query(Pricing).filter(
            Pricing.from_region_id == from_region_id,
            Pricing.to_region_id == to_region_id,
            Pricing.service_type == service_type,
            Pricing.is_active == True
        ).first()
        if pricing:
            pricing_level = "region"
    
    if not pricing:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Pricing not found for this route"
        )
    
    base_price = pricing.base_price
    selected_seat: Optional[SeatType] = None
    
    # Resolve seat type for taxi pricing
    if service_type == "taxi":
        total_passengers = passengers if passengers and passengers > 0 else 1
        if seat_type:
            try:
                selected_seat = SeatType(seat_type.lower())
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid seat_type. Must be 'front' or 'back'"
                )
        else:
            # Default to BACK (rear) seat for all cases, including single passenger
            # Front seat should only be used when explicitly requested
            selected_seat = SeatType.BACK
        
        # Apply seat-specific pricing when available
        if selected_seat == SeatType.FRONT and pricing.front_seat_price:
            base_price = pricing.front_seat_price
        elif selected_seat == SeatType.BACK and pricing.back_seat_price:
            base_price = pricing.back_seat_price
    
    # Apply discount for taxi service based on passengers
    if service_type == "taxi":
        total_passengers = passengers if passengers and passengers > 0 else 1
        if total_passengers == 1:
            discount = pricing.discount_1_passenger or Decimal("0")
        elif total_passengers == 2:
            discount = pricing.discount_2_passengers or Decimal("0")
        elif total_passengers == 3:
            discount = pricing.discount_3_passengers or Decimal("0")
        elif total_passengers == 4:
            discount = pricing.discount_full_car or Decimal("0")
        else:
            discount = Decimal("0")
        
        discount_multiplier = Decimal("1") - (Decimal(discount) / Decimal("100"))
        
        # Calculate price per person after discount
        price_per_person = base_price * discount_multiplier
        # Total price for all passengers
        total_price = price_per_person * total_passengers
        
        return {
            "pricing_level": pricing_level,
            "from_region_id": from_region_id,
            "to_region_id": to_region_id,
            "from_district_id": from_district_id,
            "to_district_id": to_district_id,
            "service_type": service_type,
            "base_price": str(base_price),
            "passengers": total_passengers,
            "discount_percentage": str(discount),
            "price_per_person": str(price_per_person),
            "total_price": str(total_price),
            "seat_type": selected_seat.value if selected_seat else None
        }
    else:
        # For delivery, no passenger count
        return {
            "pricing_level": pricing_level,
            "from_region_id": from_region_id,
            "to_region_id": to_region_id,
            "from_district_id": from_district_id,
            "to_district_id": to_district_id,
            "service_type": service_type,
            "base_price": str(base_price),
            "passengers": passengers,
            "seat_type": selected_seat.value if selected_seat else None,
            "total_price": str(base_price)
        }
