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


def test_create_bonus_model(db_session: Session):
    """Test creating a bonus configuration in database"""
    bonus = Bonus(
        bonus_percent=Decimal("10.00"),
        description="10% bonus for referrals",
        is_active=True
    )
    db_session.add(bonus)
    db_session.commit()
    db_session.refresh(bonus)
    
    assert bonus.id is not None
    assert bonus.bonus_percent == Decimal("10.00")
    assert bonus.description == "10% bonus for referrals"
    assert bonus.is_active is True


def test_get_active_bonus_model(db_session: Session):
    """Test getting active bonus configuration from database"""
    # Create an active bonus
    bonus = Bonus(
        bonus_percent=Decimal("5.00"),
        description="Default bonus",
        is_active=True
    )
    db_session.add(bonus)
    db_session.commit()
    
    # Query for active bonus
    active_bonus = db_session.query(Bonus).filter(Bonus.is_active == True).first()
    
    assert active_bonus is not None
    assert active_bonus.bonus_percent == Decimal("5.00")
    assert active_bonus.is_active is True


def test_update_bonus_model(db_session: Session):
    """Test updating a bonus configuration"""
    # Create a bonus
    bonus = Bonus(
        bonus_percent=Decimal("5.00"),
        description="Initial bonus",
        is_active=True
    )
    db_session.add(bonus)
    db_session.commit()
    db_session.refresh(bonus)
    
    # Update bonus
    bonus.bonus_percent = Decimal("15.00")
    bonus.description = "Updated bonus"
    bonus.is_active = False
    db_session.commit()
    db_session.refresh(bonus)
    
    assert bonus.bonus_percent == Decimal("15.00")
    assert bonus.description == "Updated bonus"
    assert bonus.is_active is False


def test_bonus_calculation(db_session: Session):
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
    db_session.add_all([order_user, bonus_user])
    db_session.commit()
    db_session.refresh(bonus_user)
    
    # Create active bonus
    bonus_config = Bonus(
        bonus_percent=Decimal("10.00"),
        is_active=True
    )
    db_session.add(bonus_config)
    db_session.commit()
    
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
    db_session.add(order)
    db_session.commit()
    db_session.refresh(order)
    
    # Calculate and apply bonus
    bonus_amount = calculate_and_apply_bonus(db_session, order)
    
    assert bonus_amount == Decimal("10.00")  # 10% of 100.00
    
    # Check bonus user's balance
    db_session.refresh(bonus_user)
    assert bonus_user.bonus_ball == Decimal("10.00")


def test_order_with_bonus_user_id_model(db_session: Session):
    """Test creating an order with bonus_user_id in database"""
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
    db_session.add_all([order_user, bonus_user])
    db_session.commit()
    db_session.refresh(bonus_user)
    
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
        status=OrderStatus.PENDING
    )
    db_session.add(order)
    db_session.commit()
    db_session.refresh(order)
    
    assert order.bonus_user_id == bonus_user.id
    assert order.id is not None


def test_order_acceptance_history_tracking(db_session: Session):
    """Test tracking order acceptance history"""
    # Create driver
    user = User(
        telephone="998901234567",
        name="Driver User",
        hashed_password="hashed"
    )
    db_session.add(user)
    db_session.commit()
    
    driver = Driver(
        user_id=user.id,
        full_name="Test Driver",
        car_model="Toyota",
        car_number="01A123BC",
        license_photo="photo.jpg"
    )
    db_session.add(driver)
    db_session.commit()
    
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
    db_session.add(order)
    db_session.commit()
    db_session.refresh(order)
    
    # Track that driver received the order
    history = OrderAcceptanceHistory(
        driver_id=driver.id,
        taxi_order_id=order.id,
        action="received"
    )
    db_session.add(history)
    db_session.commit()
    
    # Verify history entry
    saved_history = db_session.query(OrderAcceptanceHistory).filter(
        OrderAcceptanceHistory.driver_id == driver.id,
        OrderAcceptanceHistory.taxi_order_id == order.id
    ).first()
    
    assert saved_history is not None
    assert saved_history.action == "received"


def test_get_pending_time_setting(client: TestClient):
    """Test getting pending time setting via API"""
    response = client.get("/api/pending-time/")
    
    assert response.status_code == 200
    data = response.json()
    assert "setting_value" in data


def test_pending_time_system_setting(db_session: Session):
    """Test pending time system setting in database"""
    setting = SystemSettings(
        setting_key="public_order_pending_time",
        setting_value="20"
    )
    db_session.add(setting)
    db_session.commit()
    
    # Query setting
    saved_setting = db_session.query(SystemSettings).filter(
        SystemSettings.setting_key == "public_order_pending_time"
    ).first()
    
    assert saved_setting is not None
    assert saved_setting.setting_value == "20"


def test_update_order_pending_time_model(db_session: Session):
    """Test updating pending time for a specific order"""
    # Create user
    user = User(
        telephone="998901234567",
        name="Test User",
        hashed_password="hashed"
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    
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
    db_session.add(order)
    db_session.commit()
    db_session.refresh(order)
    
    # Update pending time
    order.pending_time = 30
    db_session.commit()
    db_session.refresh(order)
    
    assert order.pending_time == 30


def test_public_order_flag(db_session: Session):
    """Test public order flag in database"""
    # Create user
    user = User(
        telephone="998901234567",
        name="Test User",
        hashed_password="hashed"
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    
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
    db_session.add(order)
    db_session.commit()
    db_session.refresh(order)
    
    assert order.public_order is True
    assert order.id is not None


def test_make_order_public_model(db_session: Session):
    """Test manually making an order public"""
    # Create user
    user = User(
        telephone="998901234567",
        name="Test User",
        hashed_password="hashed"
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    
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
    db_session.add(order)
    db_session.commit()
    db_session.refresh(order)
    
    # Make order public
    order.public_order = True
    db_session.commit()
    db_session.refresh(order)
    
    assert order.public_order is True


def test_gender_enum_no_other(db_session: Session):
    """Test that Gender enum only has male and female"""
    from app.models import Gender
    
    gender_values = [g.value for g in Gender]
    assert "male" in gender_values
    assert "female" in gender_values
    assert "other" not in gender_values
    assert len(gender_values) == 2


def test_order_with_default_pending_time_model(db_session: Session):
    """Test that orders are created with default pending time"""
    # Create user
    user = User(
        telephone="998901234567",
        name="Test User",
        hashed_password="hashed"
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    
    # Set default pending time
    setting = SystemSettings(
        setting_key="public_order_pending_time",
        setting_value="15"
    )
    db_session.add(setting)
    db_session.commit()
    
    # Create order with default pending time
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
        pending_time=15,
        public_order=False
    )
    db_session.add(order)
    db_session.commit()
    db_session.refresh(order)
    
    assert order.pending_time == 15
    assert order.public_order is False


def test_bonus_not_applied_without_bonus_user_id(db_session: Session):
    """Test that bonus is not applied when bonus_user_id is None"""
    # Create user
    user = User(
        telephone="998901234567",
        name="Test User",
        hashed_password="hashed",
        bonus_ball=Decimal("0.00")
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    
    # Create active bonus
    bonus_config = Bonus(
        bonus_percent=Decimal("10.00"),
        is_active=True
    )
    db_session.add(bonus_config)
    db_session.commit()
    
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
    db_session.add(order)
    db_session.commit()
    db_session.refresh(order)
    
    # Calculate and apply bonus
    bonus_amount = calculate_and_apply_bonus(db_session, order)
    
    assert bonus_amount is None  # No bonus should be applied
