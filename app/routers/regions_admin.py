from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session, aliased
from typing import List
from app.database import get_db
from app.models import Region, District, DistrictPricing, Tariff, User
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
@router.post("/district-pricing", response_model=List[DistrictPricingResponse], status_code=status.HTTP_201_CREATED)
def create_district_pricing(
    pricing_data: DistrictPricingCreate,
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """Create or update district-level pricing for one or many routes (Admin only).

    Enhancements:
    - `tariff_pricings`: send multiple tariff prices in one request; each is upserted.
    - `both_directions`: also creates/upserts reverse (to→from) pairs in addition to forward pairs.
    Legacy one-way, single-tariff behaviour stays unchanged when these fields are not provided.
    """
    from_ids = set(pricing_data.from_district_ids or [])
    to_ids = set(pricing_data.to_district_ids or [])
    if pricing_data.from_district_id is not None:
        from_ids.add(pricing_data.from_district_id)
    if pricing_data.to_district_id is not None:
        to_ids.add(pricing_data.to_district_id)

    all_district_ids = from_ids | to_ids
    existing_district_ids = {
        district_id
        for (district_id,) in db.query(District.id)
        .filter(District.id.in_(all_district_ids), District.is_active == True)
        .all()
    }
    missing_ids = sorted(all_district_ids - existing_district_ids)
    if missing_ids:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"District(s) not found or inactive: {', '.join(str(x) for x in missing_ids)}",
        )

    # Build district pairs (optionally both directions)
    pairs = set()
    for from_district_id in from_ids:
        for to_district_id in to_ids:
            pairs.add((from_district_id, to_district_id))
            if pricing_data.both_directions:
                pairs.add((to_district_id, from_district_id))

    # Build tariff payloads (single tariff legacy or multi-tariff mode)
    if pricing_data.tariff_pricings:
        pricing_payloads = [
            {
                "service_type": pricing_data.service_type,
                "tariff": tp.tariff,
                "base_price": tp.base_price,
                "front_seat_price": tp.front_seat_price,
                "back_seat_price": tp.back_seat_price,
                "discount_1_passenger": tp.discount_1_passenger,
                "discount_2_passengers": tp.discount_2_passengers,
                "discount_3_passengers": tp.discount_3_passengers,
                "discount_full_car": tp.discount_full_car,
            }
            for tp in pricing_data.tariff_pricings
        ]
    else:
        pricing_payloads = [
            {
                "service_type": pricing_data.service_type,
                "tariff": pricing_data.tariff,
                "base_price": pricing_data.base_price,
                "front_seat_price": pricing_data.front_seat_price,
                "back_seat_price": pricing_data.back_seat_price,
                "discount_1_passenger": pricing_data.discount_1_passenger,
                "discount_2_passengers": pricing_data.discount_2_passengers,
                "discount_3_passengers": pricing_data.discount_3_passengers,
                "discount_full_car": pricing_data.discount_full_car,
            }
        ]

    upserted: List[DistrictPricing] = []

    for from_district_id, to_district_id in sorted(pairs):
        for payload in pricing_payloads:
            existing = db.query(DistrictPricing).filter(
                DistrictPricing.from_district_id == from_district_id,
                DistrictPricing.to_district_id == to_district_id,
                DistrictPricing.service_type == payload["service_type"],
                DistrictPricing.tariff == payload["tariff"],
            ).first()

            if existing:
                for key, value in payload.items():
                    setattr(existing, key, value)
                existing.is_active = True
                upserted.append(existing)
                continue

            new_pricing = DistrictPricing(
                from_district_id=from_district_id,
                to_district_id=to_district_id,
                **payload,
            )
            db.add(new_pricing)
            upserted.append(new_pricing)

    db.commit()
    for item in upserted:
        db.refresh(item)

    return upserted


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
    if pricing.service_type == "delivery" and update_data.get("tariff") not in (None, Tariff.STANDARD):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Delivery pricing supports only standard tariff"
        )
    for key, value in update_data.items():
        setattr(pricing, key, value)
    
    db.commit()
    db.refresh(pricing)
    
    return pricing


@router.get("/district-pricing", response_model=List[DistrictPricingResponse])
def get_all_district_pricing(
    service_type: str = Query("taxi", pattern="^(taxi|delivery)$"),
    tariff: Tariff | None = None,
    from_region_id: int | None = None,
    to_region_id: int | None = None,
    from_district_id: int | None = None,
    to_district_id: int | None = None,
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """Get district-level pricing configurations with pagination (Admin only)."""
    from_district = aliased(District)
    to_district = aliased(District)

    query = db.query(DistrictPricing).filter(
        DistrictPricing.is_active == True,
        DistrictPricing.service_type == service_type,
    )

    if tariff is not None:
        query = query.filter(DistrictPricing.tariff == tariff)
    if from_region_id is not None:
        query = query.join(
            from_district,
            from_district.id == DistrictPricing.from_district_id,
        ).filter(from_district.region_id == from_region_id)
    if to_region_id is not None:
        query = query.join(
            to_district,
            to_district.id == DistrictPricing.to_district_id,
        ).filter(to_district.region_id == to_region_id)
    if from_district_id is not None:
        query = query.filter(DistrictPricing.from_district_id == from_district_id)
    if to_district_id is not None:
        query = query.filter(DistrictPricing.to_district_id == to_district_id)

    pricing = (
        query.order_by(DistrictPricing.id.asc())
        .offset(offset)
        .limit(limit)
        .all()
    )
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
