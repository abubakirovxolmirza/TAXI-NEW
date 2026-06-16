"""
Seed initial data for the taxi service database
Run this script after database migrations
"""
import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from sqlalchemy.orm import Session
from app.database import SessionLocal, engine, Base
from app.models import Region, District, Pricing, User, UserRole
from app.auth import get_password_hash
from decimal import Decimal

def seed_regions_districts(db: Session):
    """Seed regions and districts of Uzbekistan"""
    
    regions_data = [
        {
            "name_uz_latin": "Toshkent shahri",
            "name_uz_cyrillic": "Тошкент шаҳри",
            "name_russian": "город Ташкент",
            "districts": [
                {"uz_latin": "Bektemir", "uz_cyrillic": "Бектемир", "russian": "Бектемир"},
                {"uz_latin": "Mirzo Ulug'bek", "uz_cyrillic": "Мирзо Улуғбек", "russian": "Мирзо Улугбек"},
                {"uz_latin": "Mirobod", "uz_cyrillic": "Миробод", "russian": "Мирабад"},
                {"uz_latin": "Olmazor", "uz_cyrillic": "Олмазор", "russian": "Алмазар"},
                {"uz_latin": "Sergeli", "uz_cyrillic": "Сергели", "russian": "Сергели"},
                {"uz_latin": "Shayxontoxur", "uz_cyrillic": "Шайхонтохур", "russian": "Шайхантахур"},
                {"uz_latin": "Yashnobod", "uz_cyrillic": "Яшнобод", "russian": "Яшнабад"},
                {"uz_latin": "Yunusobod", "uz_cyrillic": "Юнусобод", "russian": "Юнусабад"},
            ]
        },
        {
            "name_uz_latin": "Toshkent viloyati",
            "name_uz_cyrillic": "Тошкент вилояти",
            "name_russian": "Ташкентская область",
            "districts": [
                {"uz_latin": "Angren", "uz_cyrillic": "Ангрен", "russian": "Ангрен"},
                {"uz_latin": "Bekobod", "uz_cyrillic": "Бекобод", "russian": "Бекабад"},
                {"uz_latin": "Chirchiq", "uz_cyrillic": "Чирчиқ", "russian": "Чирчик"},
                {"uz_latin": "Olmaliq", "uz_cyrillic": "Олмалиқ", "russian": "Алмалык"},
            ]
        },
        {
            "name_uz_latin": "Samarqand",
            "name_uz_cyrillic": "Самарқанд",
            "name_russian": "Самарканд",
            "districts": [
                {"uz_latin": "Samarqand shahri", "uz_cyrillic": "Самарқанд шаҳри", "russian": "город Самарканд"},
                {"uz_latin": "Bulung'ur", "uz_cyrillic": "Булунғур", "russian": "Булунгур"},
                {"uz_latin": "Jomboy", "uz_cyrillic": "Жомбой", "russian": "Джамбай"},
            ]
        },
        {
            "name_uz_latin": "Buxoro",
            "name_uz_cyrillic": "Бухоро",
            "name_russian": "Бухара",
            "districts": [
                {"uz_latin": "Buxoro shahri", "uz_cyrillic": "Бухоро шаҳри", "russian": "город Бухара"},
                {"uz_latin": "Kogon", "uz_cyrillic": "Когон", "russian": "Каган"},
            ]
        },
        {
            "name_uz_latin": "Namangan",
            "name_uz_cyrillic": "Наманган",
            "name_russian": "Наманган",
            "districts": [
                {"uz_latin": "Namangan shahri", "uz_cyrillic": "Наманган шаҳри", "russian": "город Наманган"},
                {"uz_latin": "Chortoq", "uz_cyrillic": "Чортоқ", "russian": "Чартак"},
            ]
        }
    ]
    
    for region_data in regions_data:
        # Create region
        region = Region(
            name_uz_latin=region_data["name_uz_latin"],
            name_uz_cyrillic=region_data["name_uz_cyrillic"],
            name_russian=region_data["name_russian"],
            is_active=True
        )
        db.add(region)
        db.flush()
        
        # Create districts
        for district_data in region_data["districts"]:
            district = District(
                region_id=region.id,
                name_uz_latin=district_data["uz_latin"],
                name_uz_cyrillic=district_data["uz_cyrillic"],
                name_russian=district_data["russian"],
                is_active=True
            )
            db.add(district)
    
    db.commit()
    print("✅ Regions and districts seeded successfully")


def seed_pricing(db: Session):
    """Seed initial pricing data"""
    
    # Get regions
    regions = db.query(Region).all()
    
    if len(regions) < 2:
        print("⚠️ Not enough regions to create pricing")
        return
    
    # Create sample pricing between first few regions
    pricing_data = [
        {
            "from_region": 1,
            "to_region": 2,
            "service_type": "taxi",
            "base_price": Decimal("50000.00"),
            "discount_1": Decimal("5000.00"),
            "discount_2": Decimal("10000.00"),
            "discount_3": Decimal("15000.00"),
            "discount_full": Decimal("20000.00")
        },
        {
            "from_region": 1,
            "to_region": 2,
            "service_type": "delivery",
            "base_price": Decimal("30000.00"),
            "discount_1": Decimal("0.00"),
            "discount_2": Decimal("0.00"),
            "discount_3": Decimal("0.00"),
            "discount_full": Decimal("0.00")
        },
        {
            "from_region": 2,
            "to_region": 1,
            "service_type": "taxi",
            "base_price": Decimal("50000.00"),
            "discount_1": Decimal("5000.00"),
            "discount_2": Decimal("10000.00"),
            "discount_3": Decimal("15000.00"),
            "discount_full": Decimal("20000.00")
        }
    ]
    
    for price_data in pricing_data:
        pricing = Pricing(
            from_region_id=price_data["from_region"],
            to_region_id=price_data["to_region"],
            service_type=price_data["service_type"],
            base_price=price_data["base_price"],
            discount_1_passenger=price_data["discount_1"],
            discount_2_passengers=price_data["discount_2"],
            discount_3_passengers=price_data["discount_3"],
            discount_full_car=price_data["discount_full"],
            is_active=True
        )
        db.add(pricing)
    
    db.commit()
    print("✅ Pricing data seeded successfully")


def create_superadmin(db: Session):
    """Create initial superadmin user"""
    
    # Check if superadmin already exists
    existing_superadmin = db.query(User).filter(
        User.role == UserRole.SUPERADMIN
    ).first()
    
    if existing_superadmin:
        print("⚠️ Superadmin already exists")
        return
    
    # Create superadmin
    superadmin = User(
        telephone="+998901234567",
        name="Super Admin",
        hashed_password=get_password_hash("admin123"),
        role=UserRole.SUPERADMIN,
        is_active=True
    )
    
    db.add(superadmin)
    db.commit()
    
    print("✅ Superadmin created successfully")
    print("📱 Telephone: +998901234567")
    print("🔑 Password: admin123")
    print("⚠️ PLEASE CHANGE THE PASSWORD IMMEDIATELY!")


def main():
    """Run all seed functions"""
    print("🌱 Seeding database...")
    
    # Create tables if not exist
    Base.metadata.create_all(bind=engine)
    
    db = SessionLocal()
    
    try:
        # Seed data
        seed_regions_districts(db)
        seed_pricing(db)
        create_superadmin(db)
        
        print("\n✅ Database seeding completed successfully!")
        
    except Exception as e:
        print(f"\n❌ Error seeding database: {e}")
        db.rollback()
    finally:
        db.close()


if __name__ == "__main__":
    main()
