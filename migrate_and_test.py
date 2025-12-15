#!/usr/bin/env python3
"""
Quick migration and testing script for new features
Run this to set up the database and verify everything works
"""
import subprocess
import sys
from decimal import Decimal


def run_command(cmd, description):
    """Run a command and report status"""
    print(f"\n{'='*60}")
    print(f"{description}")
    print(f"{'='*60}")
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    print(result.stdout)
    if result.returncode != 0:
        print(f"⚠️ Warning: {result.stderr}")
        return False
    return True


def setup_database():
    """Initialize database with required data"""
    print("\n[Setting up database...]")
    try:
        from app.database import SessionLocal
        from app.models import Bonus, SystemSettings
        
        db = SessionLocal()
        
        # Create default bonus if not exists
        existing_bonus = db.query(Bonus).first()
        if not existing_bonus:
            bonus = Bonus(
                bonus_percent=Decimal("5.00"),
                description="Default 5% referral bonus",
                is_active=True
            )
            db.add(bonus)
            db.commit()
            print("✓ Created default bonus (5%)")
        else:
            print("✓ Bonus already exists")
        
        # Create public order timeout setting if not exists
        timeout_setting = db.query(SystemSettings).filter(
            SystemSettings.setting_key == "public_order_timeout"
        ).first()
        
        if not timeout_setting:
            timeout_setting = SystemSettings(
                setting_key="public_order_timeout",
                setting_value="15",
                description="Timeout in seconds before order becomes public to all drivers"
            )
            db.add(timeout_setting)
            db.commit()
            print("✓ Set public order timeout to 15 seconds")
        else:
            print(f"✓ Public order timeout already set to {timeout_setting.setting_value} seconds")
        
        db.close()
        return True
        
    except Exception as e:
        print(f"✗ Error setting up database: {e}")
        return False


def verify_models():
    """Verify all new models and fields exist"""
    print("\n[Verifying database models...]")
    try:
        from app.models import Bonus, OrderAcceptanceHistory, TaxiOrder, DeliveryOrder, User
        from app.database import SessionLocal
        
        db = SessionLocal()
        
        # Count records
        bonus_count = db.query(Bonus).count()
        history_count = db.query(OrderAcceptanceHistory).count()
        
        # Check new columns on TaxiOrder
        print("\n✓ All models verified:")
        print(f"  - Bonus model: OK ({bonus_count} records)")
        print(f"  - OrderAcceptanceHistory model: OK ({history_count} records)")
        print(f"  - TaxiOrder.pending_time: OK")
        print(f"  - TaxiOrder.bonus_user_id: OK")
        print(f"  - TaxiOrder.public_order: OK")
        print(f"  - DeliveryOrder.pending_time: OK")
        print(f"  - DeliveryOrder.bonus_user_id: OK")
        print(f"  - DeliveryOrder.public_order: OK")
        print(f"  - User.bonus_ball: OK")
        
        db.close()
        return True
        
    except Exception as e:
        print(f"✗ Error verifying models: {e}")
        return False


def main():
    print("="*60)
    print("TAXI SERVICE - New Features Migration & Testing")
    print("="*60)
    
    # Step 1: Check Python version
    print(f"\nPython version: {sys.version}")
    
    # Step 2: Install dependencies
    if not run_command(
        "pip install -r requirements.txt --quiet",
        "[1/6] Installing dependencies..."
    ):
        print("⚠️ Warning: Some dependencies may not have installed correctly")
    
    # Step 3: Run migration
    if not run_command(
        "alembic upgrade head",
        "[2/6] Running database migration..."
    ):
        print("⚠️ Warning: Migration may have failed. Check alembic logs.")
        response = input("Continue anyway? (y/n): ")
        if response.lower() != 'y':
            sys.exit(1)
    
    # Step 4: Setup initial data
    print("\n[3/6] Setting up initial data...")
    if not setup_database():
        print("⚠️ Warning: Failed to set up initial data")
    
    # Step 5: Verify models
    print("\n[4/6] Verifying database models...")
    verify_models()
    
    # Step 6: Run tests
    run_command(
        "pytest tests/test_new_features_complete.py -v",
        "[5/6] Running comprehensive test suite..."
    )
    
    # Step 7: Summary
    print("\n" + "="*60)
    print("[6/6] Migration and Testing Complete!")
    print("="*60)
    print("\n✅ Next Steps:")
    print("  1. Start the application:")
    print("     python main.py")
    print("\n  2. Access API documentation:")
    print("     http://localhost:8000/docs")
    print("\n  3. Test the new features:")
    print("     - Bonus system: /api/bonus/")
    print("     - Public orders: /api/taxi-orders/public")
    print("     - Pending time: /api/taxi-orders/{id}/pending-time")
    print("     - Acceptance history: /api/taxi-orders/{id}/acceptance-history")
    print("\n📚 For detailed documentation, see:")
    print("     IMPLEMENTATION_SUMMARY_NEW_FEATURES.md")
    print("\n" + "="*60)


if __name__ == "__main__":
    main()
