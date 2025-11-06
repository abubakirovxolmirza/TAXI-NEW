from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from app.database import get_db
from app.models import Region, District
from app.schemas import RegionResponse, RegionCreate, DistrictResponse, DistrictCreate

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
