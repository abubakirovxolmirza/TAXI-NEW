"""
Tests for new features: Bonus system, Order acceptance history, 
Pending time management, and Public orders
"""
import pytest
from decimal import Decimal
from datetime import datetime, timedelta, timezone
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models import (
    User, Driver, Bonus, TaxiOrder, DeliveryOrder, 
    OrderAcceptanceHistory, OrderStatus, SystemSettings,
    UserRole, Gender, ItemType
)
from app.utils import calculate_and_apply_bonus


def test_create_bonus(client: TestClient, admin_token: str):
    """Test creating a bonus configuration"""
    response = client.post(
        "/api/bonuses/",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={
            "bonus_percent": 10.0,
            "description": "10% bonus for referrals",
            "is_active": True
        }
    )
    
    assert response.status_code == 201
    data = response.json()
    assert data["bonus_percent"] == "10.00"
    assert data["description"] == "10% bonus for referrals"
    assert data["is_active"] is True


def test_get_active_bonus(client: TestClient, db: Session):
    """Test getting active bonus configuration"""
    # Create an active bonus
    bonus = Bonus(
        bonus_percent=Decimal("5.00"),
        description="Default bonus",
        is_active=True
    )
    db.add(bonus)
    db.commit()
    
    response = client.get("/api/bonuses/active")
    
    assert response.status_code == 200
    data = response.json()
    assert data["bonus_percent"] == "5.00"
    assert data["is_active"] is True


def test_update_bonus(client: TestClient, admin_token: str, db: Session):
    """Test updating a bonus configuration"""
    # Create a bonus
    bonus = Bonus(
        bonus_percent=Decimal("5.00"),
        description="Initial bonus",
        is_active=True
    )
    db.add(bonus)
    db.commit()
    db.refresh(bonus)
    
    response = client.put(
        f"/api/bonuses/{bonus.id}",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={
            "bonus_percent": 15.0,
            "description": "Updated bonus",
            "is_active": False
        }
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["bonus_percent"] == "15.00"
    assert data["description"] == "Updated bonus"
    assert data["is_active"] is False


def test_bonus_calculation(db: Session):
    """Test bonus calculation and application"""
    # Create users
    order_user = User(
        telephone="998901234567",
        name="Order User",
        hashed_password="hashed",
        bonus_ball=Decimal("0.00")
    )
    bonus_user = User(
        telephone="998907654321",
        name="Bonus User",
        hashed_password="hashed",
        bonus_ball=Decimal("0.00")
    )
    db.add_all([order_user, bonus_user])
    db.commit()
    db.refresh(bonus_user)
    
    # Create active bonus
    bonus_config = Bonus(
        bonus_percent=Decimal("10.00"),
        is_active=True
    )
    db.add(bonus_config)
    db.commit()
    
    # Create order with bonus_user_id
    order = TaxiOrder(
        user_id=order_user.id,
        bonus_user_id=bonus_user.id,
        username="Test User",
        telephone="998901234567",
        from_region_id=1,
        from_district_id=1,
        to_region_id=2,
        to_district_id=2,
        passengers=2,
        date="16.12.2025",
        time_start="10:00",
        time_end="11:00",
        price=Decimal("100.00"),
        service_fee=Decimal("10.00"),
        driver_earnings=Decimal("90.00"),
        status=OrderStatus.COMPLETED
    )
    db.add(order)
    db.commit()
    db.refresh(order)
    
    # Calculate and apply bonus
    bonus_amount = calculate_and_apply_bonus(db, order)
    
    assert bonus_amount == Decimal("10.00")  # 10% of 100.00
    
    # Check bonus user's balance
    db.refresh(bonus_user)
    assert bonus_user.bonus_ball == Decimal("10.00")


def test_order_with_bonus_user_id(client: TestClient, user_token: str, db: Session):
    """Test creating an order with bonus_user_id"""
    # Create bonus user
    bonus_user = User(
        telephone="998907654321",
        name="Bonus User",
        hashed_password="hashed",
        bonus_ball=Decimal("0.00")
    )
    db.add(bonus_user)
    db.commit()
    db.refresh(bonus_user)
    
    response = client.post(
        "/api/taxi-orders/",
        headers={"Authorization": f"Bearer {user_token}"},
        json={
            "username": "Test User",
            "telephone": "998901234567",
            "bonus_user_id": bonus_user.id,
            "from_region_id": 1,
            "from_district_id": 1,
            "to_region_id": 2,
            "to_district_id": 2,
            "passengers": 2,
            "client_gender": "male",
            "date": "16.12.2025",
            "time_start": "10:00",
            "time_end": "11:00"
        }
    )
    
    assert response.status_code == 201
    data = response.json()
    assert data["bonus_user_id"] == bonus_user.id


def test_order_acceptance_history_tracking(db: Session):
    """Test tracking order acceptance history"""
    # Create driver
    user = User(
        telephone="998901234567",
        name="Driver User",
        hashed_password="hashed"
    )
    db.add(user)
    db.commit()
    
    driver = Driver(
        user_id=user.id,
        full_name="Test Driver",
        car_model="Toyota",
        car_number="01A123BC",
        license_photo="photo.jpg"
    )
    db.add(driver)
    db.commit()
    
    # Create order
    order = TaxiOrder(
        user_id=user.id,
        username="Test User",
        telephone="998901234567",
        from_region_id=1,
        from_district_id=1,
        to_region_id=2,
        to_district_id=2,
        passengers=2,
        date="16.12.2025",
        time_start="10:00",
        time_end="11:00",
        price=Decimal("100.00"),
        service_fee=Decimal("10.00"),
        driver_earnings=Decimal("90.00"),
        status=OrderStatus.PENDING
    )
    db.add(order)
    db.commit()
    db.refresh(order)
    
    # Track that driver received the order
    history = OrderAcceptanceHistory(
        driver_id=driver.id,
        taxi_order_id=order.id,
        action="received"
    )
    db.add(history)
    db.commit()
    
    # Verify history entry
    saved_history = db.query(OrderAcceptanceHistory).filter(
        OrderAcceptanceHistory.driver_id == driver.id,
        OrderAcceptanceHistory.taxi_order_id == order.id
    ).first()
    
    assert saved_history is not None
    assert saved_history.action == "received"


def test_get_pending_time_setting(client: TestClient):
    """Test getting pending time setting"""
    response = client.get("/api/pending-time/")
    
    assert response.status_code == 200
    data = response.json()
    assert "setting_value" in data


def test_update_pending_time_setting(client: TestClient, admin_token: str):
    """Test updating global pending time setting"""
    response = client.put(
        "/api/pending-time/",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"pending_time": 20}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["setting_value"] == "20"


def test_update_order_pending_time(client: TestClient, admin_token: str, db: Session):
    """Test updating pending time for a specific order"""
    # Create user
    user = User(
        telephone="998901234567",
        name="Test User",
        hashed_password="hashed"
    )
    db.add(user)
    db.commit()
    
    # Create order
    order = TaxiOrder(
        user_id=user.id,
        username="Test User",
        telephone="998901234567",
        from_region_id=1,
        from_district_id=1,
        to_region_id=2,
        to_district_id=2,
        passengers=2,
        date="16.12.2025",
        time_start="10:00",
        time_end="11:00",
        price=Decimal("100.00"),
        service_fee=Decimal("10.00"),
        driver_earnings=Decimal("90.00"),
        status=OrderStatus.PENDING,
        pending_time=15
    )
    db.add(order)
    db.commit()
    db.refresh(order)
    
    response = client.put(
        f"/api/pending-time/taxi/{order.id}",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"pending_time": 30}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["pending_time"] == 30


def test_public_orders_endpoint(client: TestClient, driver_token: str, db: Session):
    """Test getting public orders"""
    # Create user
    user = User(
        telephone="998901234567",
        name="Test User",
        hashed_password="hashed"
    )
    db.add(user)
    db.commit()
    
    # Create public order
    order = TaxiOrder(
        user_id=user.id,
        username="Test User",
        telephone="998901234567",
        from_region_id=1,
        from_district_id=1,
        to_region_id=2,
        to_district_id=2,
        passengers=2,
        date="16.12.2025",
        time_start="10:00",
        time_end="11:00",
        price=Decimal("100.00"),
        service_fee=Decimal("10.00"),
        driver_earnings=Decimal("90.00"),
        status=OrderStatus.PENDING,
        public_order=True
    )
    db.add(order)
    db.commit()
    
    response = client.get(
        "/api/public-orders/taxi",
        headers={"Authorization": f"Bearer {driver_token}"}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 1
    assert any(o["id"] == order.id for o in data)


def test_make_order_public(client: TestClient, admin_token: str, db: Session):
    """Test manually making an order public"""
    # Create user
    user = User(
        telephone="998901234567",
        name="Test User",
        hashed_password="hashed"
    )
    db.add(user)
    db.commit()
    
    # Create order
    order = TaxiOrder(
        user_id=user.id,
        username="Test User",
        telephone="998901234567",
        from_region_id=1,
        from_district_id=1,
        to_region_id=2,
        to_district_id=2,
        passengers=2,
        date="16.12.2025",
        time_start="10:00",
        time_end="11:00",
        price=Decimal("100.00"),
        service_fee=Decimal("10.00"),
        driver_earnings=Decimal("90.00"),
        status=OrderStatus.PENDING,
        public_order=False
    )
    db.add(order)
    db.commit()
    db.refresh(order)
    
    response = client.post(
        f"/api/public-orders/taxi/{order.id}/make-public",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["public_order"] is True


def test_gender_enum_no_other(db: Session):
    """Test that Gender enum only has male and female"""
    from app.models import Gender
    
    gender_values = [g.value for g in Gender]
    assert "male" in gender_values
    assert "female" in gender_values
    assert "other" not in gender_values
    assert len(gender_values) == 2


def test_order_with_default_pending_time(client: TestClient, user_token: str, db: Session):
    """Test that orders are created with default pending time"""
    # Set default pending time
    setting = SystemSettings(
        setting_key="public_order_pending_time",
        setting_value="15"
    )
    db.add(setting)
    db.commit()
    
    response = client.post(
        "/api/taxi-orders/",
        headers={"Authorization": f"Bearer {user_token}"},
        json={
            "username": "Test User",
            "telephone": "998901234567",
            "from_region_id": 1,
            "from_district_id": 1,
            "to_region_id": 2,
            "to_district_id": 2,
            "passengers": 2,
            "date": "16.12.2025",
            "time_start": "10:00",
            "time_end": "11:00"
        }
    )
    
    assert response.status_code == 201
    data = response.json()
    assert data["pending_time"] == 15
    assert data["public_order"] is False


def test_bonus_not_applied_without_bonus_user_id(db: Session):
    """Test that bonus is not applied when bonus_user_id is None"""
    # Create user
    user = User(
        telephone="998901234567",
        name="Test User",
        hashed_password="hashed",
        bonus_ball=Decimal("0.00")
    )
    db.add(user)
    db.commit()
    
    # Create active bonus
    bonus_config = Bonus(
        bonus_percent=Decimal("10.00"),
        is_active=True
    )
    db.add(bonus_config)
    db.commit()
    
    # Create order without bonus_user_id
    order = TaxiOrder(
        user_id=user.id,
        bonus_user_id=None,  # No bonus user
        username="Test User",
        telephone="998901234567",
        from_region_id=1,
        from_district_id=1,
        to_region_id=2,
        to_district_id=2,
        passengers=2,
        date="16.12.2025",
        time_start="10:00",
        time_end="11:00",
        price=Decimal("100.00"),
        service_fee=Decimal("10.00"),
        driver_earnings=Decimal("90.00"),
        status=OrderStatus.COMPLETED
    )
    db.add(order)
    db.commit()
    
    # Calculate and apply bonus
    bonus_amount = calculate_and_apply_bonus(db, order)
    
    assert bonus_amount is None  # No bonus should be applied
