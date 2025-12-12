from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from app.database import get_db
from app.models import Region, District, DistrictPricing, User
from app.schemas import (
    RegionResponse, DistrictResponse,
    RegionCreateWithPricing, DistrictCreateWithPricing,
    DistrictPricingCreate, DistrictPricingUpdate, DistrictPricingResponse
)
from app.auth import get_current_admin

router = APIRouter(prefix="/api/admin/regions", tags=["Admin - Regions & Districts"])


# Region Management
@router.post("/", response_model=RegionResponse, status_code=status.HTTP_201_CREATED)
def create_region(
    region_data: RegionCreateWithPricing,
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """Create a new region (Admin only)"""
    # Check if region with same name already exists
    existing = db.query(Region).filter(
        Region.name_uz_latin == region_data.name_uz_latin
    ).first()
    
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Region with this name already exists"
        )
    
    new_region = Region(
        name_uz_latin=region_data.name_uz_latin,
        name_uz_cyrillic=region_data.name_uz_cyrillic,
        name_russian=region_data.name_russian
    )
    
    db.add(new_region)
    db.commit()
    db.refresh(new_region)
    
    return new_region


@router.put("/{region_id}", response_model=RegionResponse)
def update_region(
    region_id: int,
    region_data: RegionCreateWithPricing,
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """Update a region (Admin only)"""
    region = db.query(Region).filter(Region.id == region_id).first()
    
    if not region:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Region not found"
        )
    
    region.name_uz_latin = region_data.name_uz_latin
    region.name_uz_cyrillic = region_data.name_uz_cyrillic
    region.name_russian = region_data.name_russian
    
    db.commit()
    db.refresh(region)
    
    return region


@router.delete("/{region_id}")
def delete_region(
    region_id: int,
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """Soft delete a region (Admin only)"""
    region = db.query(Region).filter(Region.id == region_id).first()
    
    if not region:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Region not found"
        )
    
    region.is_active = False
    db.commit()
    
    return {"success": True, "message": "Region deleted successfully"}


# District Management
@router.post("/districts", response_model=DistrictResponse, status_code=status.HTTP_201_CREATED)
def create_district(
    district_data: DistrictCreateWithPricing,
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """Create a new district (Admin only)"""
    # Verify region exists
    region = db.query(Region).filter(Region.id == district_data.region_id).first()
    if not region:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Region not found"
        )
    
    new_district = District(
        region_id=district_data.region_id,
        name_uz_latin=district_data.name_uz_latin,
        name_uz_cyrillic=district_data.name_uz_cyrillic,
        name_russian=district_data.name_russian
    )
    
    db.add(new_district)
    db.commit()
    db.refresh(new_district)
    
    return new_district


@router.put("/districts/{district_id}", response_model=DistrictResponse)
def update_district(
    district_id: int,
    district_data: DistrictCreateWithPricing,
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """Update a district (Admin only)"""
    district = db.query(District).filter(District.id == district_id).first()
    
    if not district:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="District not found"
        )
    
    district.region_id = district_data.region_id
    district.name_uz_latin = district_data.name_uz_latin
    district.name_uz_cyrillic = district_data.name_uz_cyrillic
    district.name_russian = district_data.name_russian
    
    db.commit()
    db.refresh(district)
    
    return district


@router.delete("/districts/{district_id}")
def delete_district(
    district_id: int,
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """Soft delete a district (Admin only)"""
    district = db.query(District).filter(District.id == district_id).first()
    
    if not district:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="District not found"
        )
    
    district.is_active = False
    db.commit()
    
    return {"success": True, "message": "District deleted successfully"}


# District Pricing Management
@router.post("/district-pricing", response_model=DistrictPricingResponse, status_code=status.HTTP_201_CREATED)
def create_district_pricing(
    pricing_data: DistrictPricingCreate,
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """Create district-level pricing (Admin only)"""
    # Check if pricing already exists
    existing = db.query(DistrictPricing).filter(
        DistrictPricing.from_district_id == pricing_data.from_district_id,
        DistrictPricing.to_district_id == pricing_data.to_district_id,
        DistrictPricing.service_type == pricing_data.service_type,
        DistrictPricing.is_active == True
    ).first()
    
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="District pricing for this route already exists"
        )
    
    new_pricing = DistrictPricing(**pricing_data.dict())
    db.add(new_pricing)
    db.commit()
    db.refresh(new_pricing)
    
    return new_pricing


@router.put("/district-pricing/{pricing_id}", response_model=DistrictPricingResponse)
def update_district_pricing(
    pricing_id: int,
    pricing_data: DistrictPricingUpdate,
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """Update district-level pricing (Admin only)"""
    pricing = db.query(DistrictPricing).filter(DistrictPricing.id == pricing_id).first()
    
    if not pricing:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="District pricing not found"
        )
    
    update_data = pricing_data.dict(exclude_unset=True)
    for key, value in update_data.items():
        setattr(pricing, key, value)
    
    db.commit()
    db.refresh(pricing)
    
    return pricing


@router.get("/district-pricing", response_model=List[DistrictPricingResponse])
def get_all_district_pricing(
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """Get all district-level pricing configurations (Admin only)"""
    pricing = db.query(DistrictPricing).filter(DistrictPricing.is_active == True).all()
    return pricing


@router.delete("/district-pricing/{pricing_id}")
def delete_district_pricing(
    pricing_id: int,
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """Delete district-level pricing (Admin only)"""
    pricing = db.query(DistrictPricing).filter(DistrictPricing.id == pricing_id).first()
    
    if not pricing:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="District pricing not found"
        )
    
    db.delete(pricing)
    db.commit()
    
    return {"success": True, "message": "District pricing deleted successfully"}
