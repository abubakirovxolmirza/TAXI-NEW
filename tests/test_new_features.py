import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from decimal import Decimal

from app.database import Base, get_db
from app.models import (
    User, UserRole, Region, District, Pricing, 
    DistrictPricing, Driver, BalanceTransaction
)
from app.auth import get_password_hash
from main import app

# Test database setup
SQLALCHEMY_TEST_DATABASE_URL = "sqlite:///./test.db"
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
    """Create an admin user for testing"""
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
    """Get authentication token for admin"""
    response = client.post("/api/auth/login", json={
        "telephone": "998901234567",
        "password": "admin123"
    })
    return response.json()["access_token"]


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
    db_session.refresh(region1)
    db_session.refresh(region2)
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
        region_id=region1.id,
        name_uz_latin="Chilonzor",
        name_uz_cyrillic="Чилонзор",
        name_russian="Чиланзар",
        is_active=True
    )
    district3 = District(
        region_id=region2.id,
        name_uz_latin="Registon",
        name_uz_cyrillic="Регистон",
        name_russian="Регистан",
        is_active=True
    )
    
    db_session.add_all([district1, district2, district3])
    db_session.commit()
    return district1, district2, district3


@pytest.fixture
def test_driver(db_session):
    """Create a test driver"""
    user = User(
        telephone="998901111111",
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
        balance=Decimal("0.00"),
        is_blocked=False
    )
    db_session.add(driver)
    db_session.commit()
    db_session.refresh(driver)
    return driver


# Test Region Management
class TestRegionManagement:
    """Test region CRUD operations"""
    
    def test_create_region(self, admin_token):
        """Test creating a new region"""
        response = client.post(
            "/api/admin/regions/",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={
                "name_uz_latin": "Buxoro",
                "name_uz_cyrillic": "Бухоро",
                "name_russian": "Бухара"
            }
        )
        assert response.status_code == 201
        data = response.json()
        assert data["name_uz_latin"] == "Buxoro"
        assert data["is_active"] == True
    
    def test_update_region(self, admin_token, test_regions):
        """Test updating a region"""
        region1, _ = test_regions
        
        response = client.put(
            f"/api/admin/regions/{region1.id}",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={
                "name_uz_latin": "Toshkent Shahri",
                "name_uz_cyrillic": "Тошкент Шаҳри",
                "name_russian": "Город Ташкент"
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert data["name_uz_latin"] == "Toshkent Shahri"
    
    def test_delete_region(self, admin_token, test_regions):
        """Test soft-deleting a region"""
        region1, _ = test_regions
        
        response = client.delete(
            f"/api/admin/regions/{region1.id}",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200
        assert response.json()["success"] == True


# Test District Management
class TestDistrictManagement:
    """Test district CRUD operations"""
    
    def test_create_district(self, admin_token, test_regions):
        """Test creating a new district"""
        region1, _ = test_regions
        
        response = client.post(
            "/api/admin/regions/districts",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={
                "region_id": region1.id,
                "name_uz_latin": "Mirobod",
                "name_uz_cyrillic": "Мироб од",
                "name_russian": "Мирабад"
            }
        )
        assert response.status_code == 201
        data = response.json()
        assert data["name_uz_latin"] == "Mirobod"
        assert data["region_id"] == region1.id
    
    def test_update_district(self, admin_token, test_districts):
        """Test updating a district"""
        district1, _, _ = test_districts
        
        response = client.put(
            f"/api/admin/regions/districts/{district1.id}",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={
                "region_id": district1.region_id,
                "name_uz_latin": "Yunusobod tumani",
                "name_uz_cyrillic": "Юнусобод тумани",
                "name_russian": "Юнусабадский район"
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert data["name_uz_latin"] == "Yunusobod tumani"
    
    def test_delete_district(self, admin_token, test_districts):
        """Test soft-deleting a district"""
        district1, _, _ = test_districts
        
        response = client.delete(
            f"/api/admin/regions/districts/{district1.id}",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200
        assert response.json()["success"] == True


# Test District Pricing
class TestDistrictPricing:
    """Test district-level pricing management"""
    
    def test_create_district_pricing(self, admin_token, test_districts):
        """Test creating district-level pricing"""
        district1, district2, _ = test_districts
        
        response = client.post(
            "/api/admin/regions/district-pricing",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={
                "from_district_id": district1.id,
                "to_district_id": district2.id,
                "service_type": "taxi",
                "base_price": "15000.00",
                "front_seat_price": "14000.00",
                "back_seat_price": "16000.00",
                "discount_1_passenger": "10.00",
                "discount_2_passengers": "15.00",
                "discount_3_passengers": "20.00",
                "discount_full_car": "25.00"
            }
        )
        assert response.status_code == 201
        data = response.json()
        assert data["service_type"] == "taxi"
        assert float(data["base_price"]) == 15000.00
    
    def test_update_district_pricing(self, admin_token, test_districts, db_session):
        """Test updating district-level pricing"""
        district1, district2, _ = test_districts
        
        # Create pricing first
        pricing = DistrictPricing(
            from_district_id=district1.id,
            to_district_id=district2.id,
            service_type="taxi",
            base_price=Decimal("15000.00"),
            is_active=True
        )
        db_session.add(pricing)
        db_session.commit()
        db_session.refresh(pricing)
        
        response = client.put(
            f"/api/admin/regions/district-pricing/{pricing.id}",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={
                "base_price": "18000.00",
                "discount_1_passenger": "12.00"
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert float(data["base_price"]) == 18000.00
    
    def test_get_all_district_pricing(self, admin_token, test_districts, db_session):
        """Test getting all district pricing"""
        district1, district2, _ = test_districts
        
        # Create some pricing
        pricing1 = DistrictPricing(
            from_district_id=district1.id,
            to_district_id=district2.id,
            service_type="taxi",
            base_price=Decimal("15000.00"),
            is_active=True
        )
        pricing2 = DistrictPricing(
            from_district_id=district1.id,
            to_district_id=district2.id,
            service_type="delivery",
            base_price=Decimal("10000.00"),
            is_active=True
        )
        db_session.add_all([pricing1, pricing2])
        db_session.commit()
        
        response = client.get(
            "/api/admin/regions/district-pricing",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 2


# Test Balance History
class TestBalanceHistory:
    """Test balance transaction history"""
    
    def test_add_balance_and_check_history(self, admin_token, test_driver, db_session):
        """Test adding balance and retrieving history"""
        # Add balance
        response = client.post(
            "/api/admin/drivers/balance/add",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={
                "driver_id": test_driver.id,
                "amount": "50000.00",
                "description": "Bonus payment"
            }
        )
        assert response.status_code == 200
        
        # Check balance history
        response = client.get(
            "/api/admin/drivers/balance/history",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["total"] >= 1
        assert data["transactions"][0]["driver_id"] == test_driver.id
        assert float(data["transactions"][0]["amount"]) == 50000.00
        assert data["transactions"][0]["admin_name"] == "Admin User"
    
    def test_filter_balance_history_by_driver(self, admin_token, test_driver):
        """Test filtering balance history by driver"""
        response = client.get(
            f"/api/admin/drivers/balance/history?driver_id={test_driver.id}",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        for transaction in data["transactions"]:
            assert transaction["driver_id"] == test_driver.id
    
    def test_filter_balance_history_by_type(self, admin_token, test_driver):
        """Test filtering balance history by transaction type"""
        # Add balance (credit transaction)
        client.post(
            "/api/admin/drivers/balance/add",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={
                "driver_id": test_driver.id,
                "amount": "25000.00",
                "description": "Test credit"
            }
        )
        
        response = client.get(
            "/api/admin/drivers/balance/history?transaction_type=credit",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        for transaction in data["transactions"]:
            assert transaction["transaction_type"] == "credit"


# Test Pricing Logic with Districts
class TestPricingLogic:
    """Test pricing calculation with district-level support"""
    
    def test_district_pricing_priority(self, test_regions, test_districts, db_session):
        """Test that district pricing takes priority over region pricing"""
        region1, region2 = test_regions
        district1, _, district3 = test_districts
        
        # Create region-level pricing
        region_pricing = Pricing(
            from_region_id=region1.id,
            to_region_id=region2.id,
            service_type="taxi",
            base_price=Decimal("100000.00"),
            is_active=True
        )
        db_session.add(region_pricing)
        
        # Create district-level pricing (should override region pricing)
        district_pricing = DistrictPricing(
            from_district_id=district1.id,
            to_district_id=district3.id,
            service_type="taxi",
            base_price=Decimal("80000.00"),
            is_active=True
        )
        db_session.add(district_pricing)
        db_session.commit()
        
        # Calculate price with districts - should use district pricing
        response = client.get(
            f"/api/regions/pricing/calculate?from_region_id={region1.id}&to_region_id={region2.id}"
            f"&from_district_id={district1.id}&to_district_id={district3.id}&service_type=taxi&passengers=1"
        )
        assert response.status_code == 200
        data = response.json()
        assert data["pricing_level"] == "district"
        assert float(data["base_price"]) == 80000.00
    
    def test_fallback_to_region_pricing(self, test_regions, db_session):
        """Test fallback to region pricing when no district pricing exists"""
        region1, region2 = test_regions
        
        # Create only region-level pricing
        region_pricing = Pricing(
            from_region_id=region1.id,
            to_region_id=region2.id,
            service_type="delivery",
            base_price=Decimal("50000.00"),
            is_active=True
        )
        db_session.add(region_pricing)
        db_session.commit()
        
        # Calculate price without districts - should use region pricing
        response = client.get(
            f"/api/regions/pricing/calculate?from_region_id={region1.id}&to_region_id={region2.id}"
            f"&service_type=delivery"
        )
        assert response.status_code == 200
        data = response.json()
        assert data["pricing_level"] == "region"
        assert float(data["base_price"]) == 50000.00


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
