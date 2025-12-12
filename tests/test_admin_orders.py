import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from decimal import Decimal
from datetime import datetime, timezone

from app.database import Base, get_db
from app.models import (
    User, UserRole, Region, District, TaxiOrder, 
    DeliveryOrder, OrderStatus, Driver, ItemType, SeatType
)
from app.auth import get_password_hash
from main import app

# Test database setup
SQLALCHEMY_TEST_DATABASE_URL = "sqlite:///./test_orders.db"
engine = create_engine(SQLALCHEMY_TEST_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base.metadata.create_all(bind=engine)


def override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db

client = TestClient(app)


@pytest.fixture(scope="function")
def db_session():
    """Create a fresh database session for each test"""
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    yield db
    db.close()
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def admin_user(db_session):
    """Create an admin user"""
    admin = User(
        telephone="998901234567",
        name="Admin User",
        hashed_password=get_password_hash("admin123"),
        role=UserRole.ADMIN,
        is_active=True
    )
    db_session.add(admin)
    db_session.commit()
    db_session.refresh(admin)
    return admin


@pytest.fixture
def admin_token(admin_user):
    """Get admin authentication token"""
    response = client.post("/api/auth/login", json={
        "telephone": "998901234567",
        "password": "admin123"
    })
    return response.json()["access_token"]


@pytest.fixture
def test_user(db_session):
    """Create a regular user"""
    user = User(
        telephone="998901111111",
        name="Test User",
        hashed_password=get_password_hash("user123"),
        role=UserRole.USER,
        is_active=True
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def test_driver(db_session):
    """Create a test driver"""
    user = User(
        telephone="998902222222",
        name="Test Driver",
        hashed_password=get_password_hash("driver123"),
        role=UserRole.DRIVER,
        is_active=True
    )
    db_session.add(user)
    db_session.commit()
    
    driver = Driver(
        user_id=user.id,
        full_name="Test Driver",
        car_model="Toyota Camry",
        car_number="01A111AA",
        license_photo="/uploads/license.jpg",
        balance=Decimal("100000.00"),
        is_blocked=False
    )
    db_session.add(driver)
    db_session.commit()
    db_session.refresh(driver)
    return driver


@pytest.fixture
def test_regions(db_session):
    """Create test regions"""
    region1 = Region(
        name_uz_latin="Toshkent",
        name_uz_cyrillic="Тошкент",
        name_russian="Ташкент",
        is_active=True
    )
    region2 = Region(
        name_uz_latin="Samarqand",
        name_uz_cyrillic="Самарқанд",
        name_russian="Самарканд",
        is_active=True
    )
    db_session.add_all([region1, region2])
    db_session.commit()
    return region1, region2


@pytest.fixture
def test_districts(db_session, test_regions):
    """Create test districts"""
    region1, region2 = test_regions
    
    district1 = District(
        region_id=region1.id,
        name_uz_latin="Yunusobod",
        name_uz_cyrillic="Юнусобод",
        name_russian="Юнусабад",
        is_active=True
    )
    district2 = District(
        region_id=region2.id,
        name_uz_latin="Registon",
        name_uz_cyrillic="Регистон",
        name_russian="Регистан",
        is_active=True
    )
    db_session.add_all([district1, district2])
    db_session.commit()
    return district1, district2


@pytest.fixture
def test_taxi_order(db_session, test_user, test_regions, test_districts):
    """Create a test taxi order"""
    region1, region2 = test_regions
    district1, district2 = test_districts
    
    order = TaxiOrder(
        user_id=test_user.id,
        username=test_user.name,
        telephone=test_user.telephone,
        from_region_id=region1.id,
        from_district_id=district1.id,
        to_region_id=region2.id,
        to_district_id=district2.id,
        passengers=2,
        seat_type=SeatType.BACK,
        date="15.12.2025",
        time_start="10:00",
        time_end="12:00",
        price=Decimal("50000.00"),
        service_fee=Decimal("5000.00"),
        driver_earnings=Decimal("45000.00"),
        status=OrderStatus.PENDING,
        note="Test order"
    )
    db_session.add(order)
    db_session.commit()
    db_session.refresh(order)
    return order


@pytest.fixture
def test_delivery_order(db_session, test_user, test_regions, test_districts):
    """Create a test delivery order"""
    region1, region2 = test_regions
    district1, district2 = test_districts
    
    order = DeliveryOrder(
        user_id=test_user.id,
        username=test_user.name,
        sender_telephone=test_user.telephone,
        receiver_telephone="998903333333",
        from_region_id=region1.id,
        from_district_id=district1.id,
        to_region_id=region2.id,
        to_district_id=district2.id,
        item_type=ItemType.BOX,
        date="15.12.2025",
        time_start="14:00",
        time_end="16:00",
        price=Decimal("30000.00"),
        service_fee=Decimal("3000.00"),
        driver_earnings=Decimal("27000.00"),
        status=OrderStatus.PENDING,
        note="Test delivery"
    )
    db_session.add(order)
    db_session.commit()
    db_session.refresh(order)
    return order


# Test Taxi Order Management
class TestTaxiOrderManagement:
    """Test admin CRUD operations for taxi orders"""
    
    def test_get_all_taxi_orders(self, admin_token, test_taxi_order):
        """Test getting all taxi orders"""
        response = client.get(
            "/api/admin/orders/taxi",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 1
        assert data[0]["id"] == test_taxi_order.id
    
    def test_get_taxi_order_by_id(self, admin_token, test_taxi_order):
        """Test getting a specific taxi order"""
        response = client.get(
            f"/api/admin/orders/taxi/{test_taxi_order.id}",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == test_taxi_order.id
        assert data["username"] == test_taxi_order.username
        assert float(data["price"]) == float(test_taxi_order.price)
    
    def test_filter_taxi_orders_by_status(self, admin_token, test_taxi_order):
        """Test filtering taxi orders by status"""
        response = client.get(
            f"/api/admin/orders/taxi?status={OrderStatus.PENDING.value}",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        for order in data:
            assert order["status"] == OrderStatus.PENDING.value
    
    def test_update_taxi_order(self, admin_token, test_taxi_order):
        """Test updating a taxi order"""
        response = client.put(
            f"/api/admin/orders/taxi/{test_taxi_order.id}",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={
                "passengers": 3,
                "price": "60000.00",
                "note": "Updated by admin"
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert data["passengers"] == 3
        assert float(data["price"]) == 60000.00
        assert data["note"] == "Updated by admin"
    
    def test_cancel_taxi_order(self, admin_token, test_taxi_order):
        """Test cancelling a taxi order"""
        response = client.post(
            f"/api/admin/orders/taxi/{test_taxi_order.id}/cancel",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={
                "order_id": test_taxi_order.id,
                "order_type": "taxi",
                "cancellation_reason": "Customer request"
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] == True
        
        # Verify order is cancelled
        order_response = client.get(
            f"/api/admin/orders/taxi/{test_taxi_order.id}",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert order_response.json()["status"] == OrderStatus.CANCELLED.value
    
    def test_delete_taxi_order(self, admin_token, test_taxi_order, db_session):
        """Test deleting a taxi order"""
        # First cancel the order (required before deletion)
        test_taxi_order.status = OrderStatus.CANCELLED
        db_session.commit()
        
        response = client.delete(
            f"/api/admin/orders/taxi/{test_taxi_order.id}",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] == True
        
        # Verify order is deleted
        order_response = client.get(
            f"/api/admin/orders/taxi/{test_taxi_order.id}",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert order_response.status_code == 404
    
    def test_cannot_delete_active_order(self, admin_token, test_taxi_order):
        """Test that active orders cannot be deleted"""
        response = client.delete(
            f"/api/admin/orders/taxi/{test_taxi_order.id}",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 400
        assert "cancel" in response.json()["detail"].lower()


# Test Delivery Order Management
class TestDeliveryOrderManagement:
    """Test admin CRUD operations for delivery orders"""
    
    def test_get_all_delivery_orders(self, admin_token, test_delivery_order):
        """Test getting all delivery orders"""
        response = client.get(
            "/api/admin/orders/delivery",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 1
        assert data[0]["id"] == test_delivery_order.id
    
    def test_get_delivery_order_by_id(self, admin_token, test_delivery_order):
        """Test getting a specific delivery order"""
        response = client.get(
            f"/api/admin/orders/delivery/{test_delivery_order.id}",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == test_delivery_order.id
        assert data["item_type"] == test_delivery_order.item_type.value
    
    def test_update_delivery_order(self, admin_token, test_delivery_order):
        """Test updating a delivery order"""
        response = client.put(
            f"/api/admin/orders/delivery/{test_delivery_order.id}",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={
                "item_type": "document",
                "price": "35000.00",
                "note": "Updated delivery"
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert data["item_type"] == "document"
        assert float(data["price"]) == 35000.00
    
    def test_cancel_delivery_order(self, admin_token, test_delivery_order):
        """Test cancelling a delivery order"""
        response = client.post(
            f"/api/admin/orders/delivery/{test_delivery_order.id}/cancel",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={
                "order_id": test_delivery_order.id,
                "order_type": "delivery",
                "cancellation_reason": "Item not available"
            }
        )
        assert response.status_code == 200
        assert response.json()["success"] == True
    
    def test_delete_delivery_order(self, admin_token, test_delivery_order, db_session):
        """Test deleting a delivery order"""
        # First cancel the order
        test_delivery_order.status = OrderStatus.CANCELLED
        db_session.commit()
        
        response = client.delete(
            f"/api/admin/orders/delivery/{test_delivery_order.id}",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200
        
        # Verify order is deleted
        order_response = client.get(
            f"/api/admin/orders/delivery/{test_delivery_order.id}",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert order_response.status_code == 404


# Test Order Visibility and Details
class TestOrderVisibility:
    """Test that all order details are visible in admin panel"""
    
    def test_taxi_order_full_details_visible(self, admin_token, test_taxi_order):
        """Test that all taxi order details are returned"""
        response = client.get(
            f"/api/admin/orders/taxi/{test_taxi_order.id}",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        data = response.json()
        
        # Verify all important fields are present
        required_fields = [
            "id", "user_id", "username", "telephone",
            "from_region_id", "from_district_id",
            "to_region_id", "to_district_id",
            "passengers", "date", "time_start", "time_end",
            "price", "service_fee", "driver_earnings",
            "status", "created_at"
        ]
        
        for field in required_fields:
            assert field in data, f"Field {field} missing from response"
    
    def test_delivery_order_full_details_visible(self, admin_token, test_delivery_order):
        """Test that all delivery order details are returned"""
        response = client.get(
            f"/api/admin/orders/delivery/{test_delivery_order.id}",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        data = response.json()
        
        # Verify all important fields are present
        required_fields = [
            "id", "user_id", "username",
            "sender_telephone", "receiver_telephone",
            "from_region_id", "from_district_id",
            "to_region_id", "to_district_id",
            "item_type", "date", "time_start", "time_end",
            "price", "service_fee", "driver_earnings",
            "status", "created_at"
        ]
        
        for field in required_fields:
            assert field in data, f"Field {field} missing from response"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
