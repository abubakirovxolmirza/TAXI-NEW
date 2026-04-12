from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.auth import get_current_admin, get_current_user
from app.database import get_db
from app.models import Car, User
from app.schemas import CarCreate, CarResponse, CarUpdate

router = APIRouter(prefix="/api/cars", tags=["Cars"])


@router.post("/", response_model=CarResponse, status_code=status.HTTP_201_CREATED)
def create_car(
    car_data: CarCreate,
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    del current_user
    name = car_data.name.strip()
    tariff = car_data.tariff.strip()

    existing = db.query(Car).filter(Car.name == name, Car.tariff == tariff).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Car with this name and tariff already exists",
        )

    new_car = Car(name=name, tariff=tariff)
    db.add(new_car)
    db.commit()
    db.refresh(new_car)
    return new_car


@router.get("/", response_model=List[CarResponse])
def get_all_cars(
    tariff: Optional[str] = Query(None, description="Filter by tariff"),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    del current_user
    query = db.query(Car)

    if tariff is not None and tariff.strip():
        query = query.filter(Car.tariff == tariff.strip())

    cars = (
        query
        .order_by(Car.created_at.desc(), Car.id.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )
    return cars


@router.get("/tariff/{tariff}", response_model=List[CarResponse])
def get_cars_by_tariff(
    tariff: str,
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    del current_user
    normalized_tariff = tariff.strip()
    if not normalized_tariff:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Tariff must not be empty",
        )

    cars = (
        db.query(Car)
        .filter(Car.tariff == normalized_tariff)
        .order_by(Car.created_at.desc(), Car.id.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )
    return cars


@router.get("/{car_id}", response_model=CarResponse)
def get_car(
    car_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    del current_user
    car = db.query(Car).filter(Car.id == car_id).first()
    if not car:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Car not found",
        )
    return car


@router.put("/{car_id}", response_model=CarResponse)
def update_car(
    car_id: int,
    car_data: CarUpdate,
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    del current_user
    car = db.query(Car).filter(Car.id == car_id).first()
    if not car:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Car not found",
        )

    update_data = car_data.dict(exclude_unset=True)
    if "name" in update_data:
        car.name = update_data["name"].strip()
    if "tariff" in update_data:
        car.tariff = update_data["tariff"].strip()

    duplicate = db.query(Car).filter(
        Car.id != car_id,
        Car.name == car.name,
        Car.tariff == car.tariff,
    ).first()
    if duplicate:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Car with this name and tariff already exists",
        )

    db.commit()
    db.refresh(car)
    return car


@router.delete("/{car_id}")
def delete_car(
    car_id: int,
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    del current_user
    car = db.query(Car).filter(Car.id == car_id).first()
    if not car:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Car not found",
        )

    db.delete(car)
    db.commit()
    return {"success": True, "message": "Car deleted successfully"}
