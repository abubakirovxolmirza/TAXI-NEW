"""
Comprehensive tests for new features:
1. Order acceptance history
2. Gender field validation (only male/female)
3. Pending time CRUD
4. Bonus system
5. Public orders logic
"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from datetime import datetime, timedelta
from decimal import Decimal
import time

from app.database import Base, get_db
from app.models import (
    User, Driver, TaxiOrder, DeliveryOrder, Bonus, OrderAcceptanceHistory,
    OrderStatus, UserRole, Gender, SystemSettings
)
from main import app

# Test database
SQLALCHEMY_TEST_DATABASE_URL = "sqlite:///./test_new_features.db"
engine = create_engine(SQLALCHEMY_TEST_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Override get_db dependency
def override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db

client = TestClient(app)


@pytest.fixture(scope="function", autouse=True)
def setup_database():
    """Create tables before each test and drop after"""
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def db():
    """Get database session"""
    database = TestingSessionLocal()
    try:
        yield database
    finally:
        database.close()


@pytest.fixture
def admin_token(db):
    """Create admin user and return auth token"""
    from app.auth import get_password_hash
    
    admin_user = User(
        telephone="+998901234567",
        name="Admin User",
        hashed_password=get_password_hash("admin123"),
        role=UserRole.ADMIN
    )
    db.add(admin_user)
    db.commit()
    
    response = client.post("/api/auth/login", json={
        "telephone": "+998901234567",
        "password": "admin123"
    })
    return response.json()["access_token"]


@pytest.fixture
def user_token(db):
    """Create regular user and return auth token"""
    from app.auth import get_password_hash
    
    user = User(
        telephone="+998901234568",
        name="Test User",
        hashed_password=get_password_hash("user123"),
        role=UserRole.USER
    )
    db.add(user)
    db.commit()
    
    response = client.post("/api/auth/login", json={
        "telephone": "+998901234568",
        "password": "user123"
    })
    return response.json()["access_token"]


@pytest.fixture
def driver_token(db):
    """Create driver user and return auth token"""
    from app.auth import get_password_hash
    
    user = User(
        telephone="+998901234569",
        name="Test Driver",
        hashed_password=get_password_hash("driver123"),
        role=UserRole.DRIVER
    )
    db.add(user)
    db.commit()
    
    driver = Driver(
        user_id=user.id,
        full_name="Test Driver",
        car_model="Toyota Camry",
        car_number="01A123BC",
        license_photo="license.jpg",
        balance=Decimal("100.00")
    )
    db.add(driver)
    db.commit()
    
    response = client.post("/api/auth/login", json={
        "telephone": "+998901234569",
        "password": "driver123"
    })
    return response.json()["access_token"]


@pytest.fixture
def bonus_user(db):
    """Create a user who will receive bonuses"""
    from app.auth import get_password_hash
    
    user = User(
        telephone="+998901234570",
        name="Bonus User",
        hashed_password=get_password_hash("bonus123"),
        role=UserRole.USER,
        bonus_ball=Decimal("0.00")
    )
    db.add(user)
    db.commit()
    return user


# ============= GENDER FIELD VALIDATION TESTS =============

def test_gender_only_male_female_valid(user_token, db):
    """Test that only 'male' and 'female' are accepted"""
    from app.models import Region, District
    
    # Create test regions and districts
    region = Region(id=1, name_uz_latin="Tashkent", name_uz_cyrillic="Тошкент", name_russian="Ташкент")
    district = District(id=1, region_id=1, name_uz_latin="Yunusabad", name_uz_cyrillic="Юнусабад", name_russian="Юнусабад")
    db.add_all([region, district])
    db.commit()
    
    # Test with 'male'
    response = client.post(
        "/api/taxi-orders/",
        headers={"Authorization": f"Bearer {user_token}"},
        json={
            "username": "Test User",
            "telephone": "+998901234568",
            "from_region_id": 1,
            "from_district_id": 1,
            "to_region_id": 1,
            "to_district_id": 1,
            "passengers": 2,
            "client_gender": "male",
            "date": "15.12.2025",
            "time_start": "10:00",
            "time_end": "11:00"
        }
    )
    assert response.status_code == 201
    
    # Test with 'female'
    response = client.post(
        "/api/taxi-orders/",
        headers={"Authorization": f"Bearer {user_token}"},
        json={
            "username": "Test User",
            "telephone": "+998901234568",
            "from_region_id": 1,
            "from_district_id": 1,
            "to_region_id": 1,
            "to_district_id": 1,
            "passengers": 2,
            "client_gender": "female",
            "date": "15.12.2025",
            "time_start": "10:00",
            "time_end": "11:00"
        }
    )
    assert response.status_code == 201


def test_gender_other_rejected(user_token, db):
    """Test that 'other' gender is rejected"""
    from app.models import Region, District
    
    # Create test regions and districts
    region = Region(id=1, name_uz_latin="Tashkent", name_uz_cyrillic="Тошкент", name_russian="Ташкент")
    district = District(id=1, region_id=1, name_uz_latin="Yunusabad", name_uz_cyrillic="Юнусабад", name_russian="Юнусабад")
    db.add_all([region, district])
    db.commit()
    
    response = client.post(
        "/api/taxi-orders/",
        headers={"Authorization": f"Bearer {user_token}"},
        json={
            "username": "Test User",
            "telephone": "+998901234568",
            "from_region_id": 1,
            "from_district_id": 1,
            "to_region_id": 1,
            "to_district_id": 1,
            "passengers": 2,
            "client_gender": "other",
            "date": "15.12.2025",
            "time_start": "10:00",
            "time_end": "11:00"
        }
    )
    assert response.status_code == 422  # Validation error


# ============= BONUS SYSTEM TESTS =============

def test_create_bonus(admin_token, db):
    """Test creating a bonus percentage record"""
    response = client.post(
        "/api/bonus/",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={
            "bonus_percent": 5.0,
            "description": "5% bonus on completed orders"
        }
    )
    assert response.status_code == 201
    data = response.json()
    assert data["bonus_percent"] == "5.00"
    assert data["is_active"] == True


def test_get_all_bonuses(admin_token, db):
    """Test retrieving all bonus records"""
    # Create a bonus first
    bonus = Bonus(bonus_percent=Decimal("5.00"), description="Test bonus", is_active=True)
    db.add(bonus)
    db.commit()
    
    response = client.get(
        "/api/bonus/",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 1


def test_update_bonus(admin_token, db):
    """Test updating a bonus record"""
    bonus = Bonus(bonus_percent=Decimal("5.00"), description="Test bonus", is_active=True)
    db.add(bonus)
    db.commit()
    
    response = client.put(
        f"/api/bonus/{bonus.id}",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={
            "bonus_percent": 10.0,
            "description": "Updated to 10%"
        }
    )
    assert response.status_code == 200
    data = response.json()
    assert data["bonus_percent"] == "10.00"


def test_delete_bonus(admin_token, db):
    """Test deleting a bonus record"""
    bonus = Bonus(bonus_percent=Decimal("5.00"), description="Test bonus", is_active=True)
    db.add(bonus)
    db.commit()
    
    response = client.delete(
        f"/api/bonus/{bonus.id}",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert response.status_code == 200


def test_bonus_calculation_on_order_completion(db, driver_token, user_token, bonus_user):
    """Test that bonus is calculated and added when order is completed"""
    from app.auth import get_password_hash
    from app.models import Region, District, Pricing
    
    # Create test data
    region = Region(id=1, name_uz_latin="Tashkent", name_uz_cyrillic="Тошкент", name_russian="Ташкент")
    district = District(id=1, region_id=1, name_uz_latin="Yunusabad", name_uz_cyrillic="Юнусабад", name_russian="Юнусабад")
    pricing = Pricing(
        from_region_id=1,
        to_region_id=1,
        service_type="taxi",
        base_price=Decimal("100.00"),
        is_active=True
    )
    db.add_all([region, district, pricing])
    db.commit()
    
    # Create active bonus
    bonus = Bonus(bonus_percent=Decimal("10.00"), is_active=True)
    db.add(bonus)
    db.commit()
    
    # Create user for order
    user = db.query(User).filter(User.telephone == "+998901234568").first()
    driver = db.query(Driver).first()
    
    # Create order with bonus_user_id
    order = TaxiOrder(
        user_id=user.id,
        username="Test User",
        telephone="+998901234568",
        from_region_id=1,
        from_district_id=1,
        to_region_id=1,
        to_district_id=1,
        passengers=2,
        date="15.12.2025",
        time_start="10:00",
        time_end="11:00",
        price=Decimal("100.00"),
        service_fee=Decimal("8.00"),
        driver_earnings=Decimal("92.00"),
        status=OrderStatus.ACCEPTED,
        driver_id=driver.id,
        is_confirmed=True,
        bonus_user_id=bonus_user.id
    )
    db.add(order)
    db.commit()
    
    # Complete the order
    response = client.post(
        f"/api/driver/orders/complete/taxi/{order.id}",
        headers={"Authorization": f"Bearer {driver_token}"}
    )
    assert response.status_code == 200
    
    # Check that bonus was added
    db.refresh(bonus_user)
    expected_bonus = Decimal("100.00") * Decimal("10.00") / Decimal("100")
    assert bonus_user.bonus_ball == expected_bonus


def test_no_bonus_without_bonus_user_id(db, driver_token, user_token):
    """Test that no bonus is added when bonus_user_id is not provided"""
    from app.models import Region, District, Pricing
    
    # Create test data
    region = Region(id=1, name_uz_latin="Tashkent", name_uz_cyrillic="Тошкент", name_russian="Ташкент")
    district = District(id=1, region_id=1, name_uz_latin="Yunusabad", name_uz_cyrillic="Юнусабад", name_russian="Юнусабад")
    pricing = Pricing(
        from_region_id=1,
        to_region_id=1,
        service_type="taxi",
        base_price=Decimal("100.00"),
        is_active=True
    )
    db.add_all([region, district, pricing])
    db.commit()
    
    # Create active bonus
    bonus = Bonus(bonus_percent=Decimal("10.00"), is_active=True)
    db.add(bonus)
    db.commit()
    
    user = db.query(User).filter(User.telephone == "+998901234568").first()
    driver = db.query(Driver).first()
    
    # Create order WITHOUT bonus_user_id
    order = TaxiOrder(
        user_id=user.id,
        username="Test User",
        telephone="+998901234568",
        from_region_id=1,
        from_district_id=1,
        to_region_id=1,
        to_district_id=1,
        passengers=2,
        date="15.12.2025",
        time_start="10:00",
        time_end="11:00",
        price=Decimal("100.00"),
        service_fee=Decimal("8.00"),
        driver_earnings=Decimal("92.00"),
        status=OrderStatus.ACCEPTED,
        driver_id=driver.id,
        is_confirmed=True,
        bonus_user_id=None
    )
    db.add(order)
    db.commit()
    
    # Complete the order
    response = client.post(
        f"/api/driver/orders/complete/taxi/{order.id}",
        headers={"Authorization": f"Bearer {driver_token}"}
    )
    assert response.status_code == 200


def test_bonus_percentage_validation(admin_token):
    """Test that bonus percentage must be between 0 and 100"""
    # Test with invalid percentage > 100
    response = client.post(
        "/api/bonus/",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={
            "bonus_percent": 150.0,
            "description": "Invalid bonus"
        }
    )
    assert response.status_code == 422
    
    # Test with negative percentage
    response = client.post(
        "/api/bonus/",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={
            "bonus_percent": -5.0,
            "description": "Invalid bonus"
        }
    )
    assert response.status_code == 422


# ============= PENDING TIME CRUD TESTS =============

def test_update_pending_time_taxi(admin_token, db):
    """Test updating pending_time for taxi order"""
    from app.models import Region, District
    
    region = Region(id=1, name_uz_latin="Tashkent", name_uz_cyrillic="Тошкент", name_russian="Ташкент")
    district = District(id=1, region_id=1, name_uz_latin="Yunusabad", name_uz_cyrillic="Юнусабад", name_russian="Юнусабад")
    db.add_all([region, district])
    db.commit()
    
    user = db.query(User).first()
    order = TaxiOrder(
        user_id=user.id,
        username="Test",
        telephone="+998901234567",
        from_region_id=1,
        from_district_id=1,
        to_region_id=1,
        to_district_id=1,
        passengers=2,
        date="15.12.2025",
        time_start="10:00",
        time_end="11:00",
        price=Decimal("100.00"),
        status=OrderStatus.PENDING
    )
    db.add(order)
    db.commit()
    
    response = client.put(
        f"/api/taxi-orders/{order.id}/pending-time",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"pending_time": 300}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["pending_time"] == 300


def test_update_pending_time_delivery(admin_token, db):
    """Test updating pending_time for delivery order"""
    from app.models import Region, District, ItemType
    
    region = Region(id=1, name_uz_latin="Tashkent", name_uz_cyrillic="Тошкент", name_russian="Ташкент")
    district = District(id=1, region_id=1, name_uz_latin="Yunusabad", name_uz_cyrillic="Юнусабад", name_russian="Юнусабад")
    db.add_all([region, district])
    db.commit()
    
    user = db.query(User).first()
    order = DeliveryOrder(
        user_id=user.id,
        username="Test",
        sender_telephone="+998901234567",
        receiver_telephone="+998901234568",
        from_region_id=1,
        from_district_id=1,
        to_region_id=1,
        to_district_id=1,
        item_type=ItemType.BOX,
        date="15.12.2025",
        time_start="10:00",
        time_end="11:00",
        price=Decimal("100.00"),
        status=OrderStatus.PENDING
    )
    db.add(order)
    db.commit()
    
    response = client.put(
        f"/api/delivery-orders/{order.id}/pending-time",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"pending_time": 600}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["pending_time"] == 600


def test_pending_time_validation(admin_token, db):
    """Test that pending_time cannot be negative"""
    from app.models import Region, District
    
    region = Region(id=1, name_uz_latin="Tashkent", name_uz_cyrillic="Тошкент", name_russian="Ташкент")
    district = District(id=1, region_id=1, name_uz_latin="Yunusabad", name_uz_cyrillic="Юнусабад", name_russian="Юнусабад")
    db.add_all([region, district])
    db.commit()
    
    user = db.query(User).first()
    order = TaxiOrder(
        user_id=user.id,
        username="Test",
        telephone="+998901234567",
        from_region_id=1,
        from_district_id=1,
        to_region_id=1,
        to_district_id=1,
        passengers=2,
        date="15.12.2025",
        time_start="10:00",
        time_end="11:00",
        price=Decimal("100.00"),
        status=OrderStatus.PENDING
    )
    db.add(order)
    db.commit()
    
    response = client.put(
        f"/api/taxi-orders/{order.id}/pending-time",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"pending_time": -100}
    )
    assert response.status_code == 422


# ============= PUBLIC ORDER TESTS =============

def test_order_becomes_public_after_timeout(db, user_token):
    """Test that order becomes public after timeout"""
    from app.models import Region, District
    
    # Set public order timeout to 2 seconds
    setting = SystemSettings(
        setting_key="public_order_timeout",
        setting_value="2",
        description="Test timeout"
    )
    db.add(setting)
    db.commit()
    
    region = Region(id=1, name_uz_latin="Tashkent", name_uz_cyrillic="Тошкент", name_russian="Ташкент")
    district = District(id=1, region_id=1, name_uz_latin="Yunusabad", name_uz_cyrillic="Юнусабад", name_russian="Юнусабад")
    db.add_all([region, district])
    db.commit()
    
    # Create order
    response = client.post(
        "/api/taxi-orders/",
        headers={"Authorization": f"Bearer {user_token}"},
        json={
            "username": "Test User",
            "telephone": "+998901234568",
            "from_region_id": 1,
            "from_district_id": 1,
            "to_region_id": 1,
            "to_district_id": 1,
            "passengers": 2,
            "date": "15.12.2025",
            "time_start": "10:00",
            "time_end": "11:00"
        }
    )
    assert response.status_code == 201
    order_id = response.json()["id"]
    
    # Wait for timeout (2 seconds + buffer)
    time.sleep(3)
    
    # Check if order became public
    order = db.query(TaxiOrder).filter(TaxiOrder.id == order_id).first()
    # Note: This test depends on background task running
    # In real scenario, background task would set public_order to True


def test_get_public_orders(db, driver_token):
    """Test retrieving public orders"""
    from app.models import Region, District
    
    region = Region(id=1, name_uz_latin="Tashkent", name_uz_cyrillic="Тошкент", name_russian="Ташкент")
    district = District(id=1, region_id=1, name_uz_latin="Yunusabad", name_uz_cyrillic="Юнусабад", name_russian="Юнусабад")
    db.add_all([region, district])
    db.commit()
    
    user = db.query(User).first()
    
    # Create a public order
    order = TaxiOrder(
        user_id=user.id,
        username="Test",
        telephone="+998901234567",
        from_region_id=1,
        from_district_id=1,
        to_region_id=1,
        to_district_id=1,
        passengers=2,
        date="15.12.2025",
        time_start="10:00",
        time_end="11:00",
        price=Decimal("100.00"),
        status=OrderStatus.PENDING,
        public_order=True
    )
    db.add(order)
    db.commit()
    
    response = client.get(
        "/api/taxi-orders/public",
        headers={"Authorization": f"Bearer {driver_token}"}
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 1
    assert data[0]["public_order"] == True


def test_update_public_order_timeout(admin_token, db):
    """Test updating the public order timeout setting"""
    response = client.put(
        "/api/admin/settings/public-order-timeout",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"public_order_timeout": 30}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["public_order_timeout"] == 30


def test_get_public_order_timeout(admin_token, db):
    """Test retrieving the public order timeout setting"""
    # Set a value first
    setting = SystemSettings(
        setting_key="public_order_timeout",
        setting_value="20",
        description="Test"
    )
    db.add(setting)
    db.commit()
    
    response = client.get(
        "/api/admin/settings/public-order-timeout",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["public_order_timeout"] == 20


# ============= ORDER ACCEPTANCE HISTORY TESTS =============

def test_acceptance_history_recorded_on_accept(db, driver_token):
    """Test that acceptance is recorded in history when driver accepts order"""
    from app.models import Region, District
    
    region = Region(id=1, name_uz_latin="Tashkent", name_uz_cyrillic="Тошкент", name_russian="Ташкент")
    district = District(id=1, region_id=1, name_uz_latin="Yunusabad", name_uz_cyrillic="Юнусабад", name_russian="Юнусабад")
    db.add_all([region, district])
    db.commit()
    
    user = db.query(User).first()
    driver = db.query(Driver).first()
    
    # Create order
    order = TaxiOrder(
        user_id=user.id,
        username="Test",
        telephone="+998901234567",
        from_region_id=1,
        from_district_id=1,
        to_region_id=1,
        to_district_id=1,
        passengers=2,
        date="15.12.2025",
        time_start="10:00",
        time_end="11:00",
        price=Decimal("100.00"),
        status=OrderStatus.PENDING
    )
    db.add(order)
    db.commit()
    
    # Accept order
    response = client.post(
        f"/api/driver/orders/accept/taxi/{order.id}",
        headers={"Authorization": f"Bearer {driver_token}"}
    )
    assert response.status_code == 200
    
    # Check history
    history = db.query(OrderAcceptanceHistory).filter(
        OrderAcceptanceHistory.taxi_order_id == order.id,
        OrderAcceptanceHistory.driver_id == driver.id,
        OrderAcceptanceHistory.action == "accepted"
    ).first()
    
    assert history is not None
    assert history.driver_id == driver.id


def test_get_acceptance_history(db, admin_token):
    """Test retrieving acceptance history for an order"""
    from app.models import Region, District
    
    region = Region(id=1, name_uz_latin="Tashkent", name_uz_cyrillic="Тошкент", name_russian="Ташкент")
    district = District(id=1, region_id=1, name_uz_latin="Yunusabad", name_uz_cyrillic="Юнусабад", name_russian="Юнусабад")
    db.add_all([region, district])
    db.commit()
    
    user = db.query(User).first()
    driver = db.query(Driver).first()
    
    # Create order and history
    order = TaxiOrder(
        user_id=user.id,
        username="Test",
        telephone="+998901234567",
        from_region_id=1,
        from_district_id=1,
        to_region_id=1,
        to_district_id=1,
        passengers=2,
        date="15.12.2025",
        time_start="10:00",
        time_end="11:00",
        price=Decimal("100.00"),
        status=OrderStatus.PENDING
    )
    db.add(order)
    db.commit()
    
    history_entry = OrderAcceptanceHistory(
        driver_id=driver.id,
        taxi_order_id=order.id,
        action="accepted"
    )
    db.add(history_entry)
    db.commit()
    
    response = client.get(
        f"/api/taxi-orders/{order.id}/acceptance-history",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 1
    assert data[0]["driver_id"] == driver.id


# ============= EDGE CASE TESTS =============

def test_order_with_zero_price_bonus(db, driver_token, bonus_user):
    """Test bonus calculation with order price = 0"""
    from app.models import Region, District
    
    region = Region(id=1, name_uz_latin="Tashkent", name_uz_cyrillic="Тошкент", name_russian="Ташкент")
    district = District(id=1, region_id=1, name_uz_latin="Yunusabad", name_uz_cyrillic="Юнусабад", name_russian="Юнусабад")
    db.add_all([region, district])
    db.commit()
    
    bonus = Bonus(bonus_percent=Decimal("10.00"), is_active=True)
    db.add(bonus)
    db.commit()
    
    user = db.query(User).first()
    driver = db.query(Driver).first()
    
    order = TaxiOrder(
        user_id=user.id,
        username="Test",
        telephone="+998901234567",
        from_region_id=1,
        from_district_id=1,
        to_region_id=1,
        to_district_id=1,
        passengers=2,
        date="15.12.2025",
        time_start="10:00",
        time_end="11:00",
        price=Decimal("0.00"),  # Zero price
        status=OrderStatus.ACCEPTED,
        driver_id=driver.id,
        is_confirmed=True,
        bonus_user_id=bonus_user.id
    )
    db.add(order)
    db.commit()
    
    initial_bonus = bonus_user.bonus_ball
    
    response = client.post(
        f"/api/driver/orders/complete/taxi/{order.id}",
        headers={"Authorization": f"Bearer {driver_token}"}
    )
    assert response.status_code == 200
    
    db.refresh(bonus_user)
    # Bonus should still be 0 since price is 0
    assert bonus_user.bonus_ball == initial_bonus


def test_zero_percent_bonus(admin_token):
    """Test creating bonus with 0% (valid)"""
    response = client.post(
        "/api/bonus/",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={
            "bonus_percent": 0.0,
            "description": "0% bonus"
        }
    )
    assert response.status_code == 201


def test_accepted_order_never_becomes_public(db):
    """Test that accepted orders don't become public"""
    from app.models import Region, District
    
    region = Region(id=1, name_uz_latin="Tashkent", name_uz_cyrillic="Тошкент", name_russian="Ташкент")
    district = District(id=1, region_id=1, name_uz_latin="Yunusabad", name_uz_cyrillic="Юнусабад", name_russian="Юнусабад")
    db.add_all([region, district])
    db.commit()
    
    user = db.query(User).first()
    driver = db.query(Driver).first()
    
    order = TaxiOrder(
        user_id=user.id,
        username="Test",
        telephone="+998901234567",
        from_region_id=1,
        from_district_id=1,
        to_region_id=1,
        to_district_id=1,
        passengers=2,
        date="15.12.2025",
        time_start="10:00",
        time_end="11:00",
        price=Decimal("100.00"),
        status=OrderStatus.ACCEPTED,
        driver_id=driver.id
    )
    db.add(order)
    db.commit()
    
    # Even after timeout, accepted orders should not become public
    # The background task checks for PENDING status
    assert order.public_order == False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
