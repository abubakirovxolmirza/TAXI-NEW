"""
Reset database - Clear all data except regions and districts, then create superadmin
Usage: python scripts/reset_database.py
"""
import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app.database import SessionLocal
from app.models import (
    User, Driver, TaxiOrder, DeliveryOrder, Rating, 
    DriverApplication, BalanceTransaction, Notification,
    Feedback, SystemSettings, UserRole
)
from app.auth import get_password_hash


def reset_database():
    """Clear all data except regions and districts, then create superadmin"""
    
    print("=" * 60)
    print("DATABASE RESET")
    print("=" * 60)
    print("\n⚠️  WARNING: This will delete ALL data except regions and districts!")
    print("\nThe following will be deleted:")
    print("  - All users (including drivers and admins)")
    print("  - All taxi orders")
    print("  - All delivery orders")
    print("  - All ratings")
    print("  - All driver applications")
    print("  - All balance transactions")
    print("  - All notifications")
    print("  - All feedback")
    print("  - All system settings")
    print("\nThe following will be KEPT:")
    print("  - Regions")
    print("  - Districts")
    
    confirm = input("\nType 'RESET' to confirm: ")
    
    if confirm != "RESET":
        print("❌ Operation cancelled.")
        return
    
    db = SessionLocal()
    
    try:
        print("\n🗑️  Deleting data...")
        
        # Delete in order to respect foreign key constraints
        deleted_counts = {}
        
        # Delete notifications
        count = db.query(Notification).delete()
        deleted_counts['Notifications'] = count
        
        # Delete feedback
        count = db.query(Feedback).delete()
        deleted_counts['Feedback'] = count
        
        # Delete ratings
        count = db.query(Rating).delete()
        deleted_counts['Ratings'] = count
        
        # Delete balance transactions
        count = db.query(BalanceTransaction).delete()
        deleted_counts['Balance Transactions'] = count
        
        # Delete delivery orders
        count = db.query(DeliveryOrder).delete()
        deleted_counts['Delivery Orders'] = count
        
        # Delete taxi orders
        count = db.query(TaxiOrder).delete()
        deleted_counts['Taxi Orders'] = count
        
        # Delete driver applications
        count = db.query(DriverApplication).delete()
        deleted_counts['Driver Applications'] = count
        
        # Delete drivers
        count = db.query(Driver).delete()
        deleted_counts['Drivers'] = count
        
        # Delete system settings
        count = db.query(SystemSettings).delete()
        deleted_counts['System Settings'] = count
        
        # Delete all users
        count = db.query(User).delete()
        deleted_counts['Users'] = count
        
        db.commit()
        
        print("\n✅ Data deleted successfully:")
        for entity, count in deleted_counts.items():
            print(f"   {entity}: {count}")
        
        # Create superadmin
        print("\n👤 Creating superadmin account...")
        
        telephone = "+998917449994"
        name = "Super Admin"
        password = "admin123"
        
        superadmin = User(
            telephone=telephone,
            name=name,
            hashed_password=get_password_hash(password),
            role=UserRole.SUPERADMIN,
            is_active=True
        )
        
        db.add(superadmin)
        db.commit()
        db.refresh(superadmin)
        
        print("\n✅ Superadmin created successfully!")
        print(f"📱 Telephone: {telephone}")
        print(f"👤 Name: {name}")
        print(f"🔑 Password: {password}")
        print(f"🔑 Role: SUPERADMIN")
        print(f"🆔 User ID: {superadmin.id}")
        
        print("\n" + "=" * 60)
        print("DATABASE RESET COMPLETE")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    reset_database()
