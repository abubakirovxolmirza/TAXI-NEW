"""
Script to delete pricing records by specific criteria
"""
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from sqlalchemy.orm import Session
from app.database import SessionLocal
from app.models import Pricing, Region


def list_all_pricing(db: Session):
    """List all pricing records"""
    pricing_records = db.query(Pricing).all()
    
    if not pricing_records:
        print("\n📋 No pricing records found.")
        return []
    
    print("\n📋 Current Pricing Records:")
    print("-" * 100)
    print(f"{'ID':<5} {'From Region':<25} {'To Region':<25} {'Type':<10} {'Base Price':<12} {'Active':<8}")
    print("-" * 100)
    
    for p in pricing_records:
        from_region = db.query(Region).filter(Region.id == p.from_region_id).first()
        to_region = db.query(Region).filter(Region.id == p.to_region_id).first()
        
        from_name = from_region.name_uz_latin if from_region else f"ID:{p.from_region_id}"
        to_name = to_region.name_uz_latin if to_region else f"ID:{p.to_region_id}"
        
        print(f"{p.id:<5} {from_name:<25} {to_name:<25} {p.service_type:<10} {float(p.base_price):<12.2f} {'Yes' if p.is_active else 'No':<8}")
    
    print("-" * 100)
    print(f"\nTotal: {len(pricing_records)} record(s)\n")
    
    return pricing_records


def delete_by_id(db: Session):
    """Delete pricing by ID"""
    list_all_pricing(db)
    
    try:
        pricing_id = int(input("\nEnter Pricing ID to delete (0 to cancel): "))
        
        if pricing_id == 0:
            print("❌ Cancelled.")
            return
        
        pricing = db.query(Pricing).filter(Pricing.id == pricing_id).first()
        
        if not pricing:
            print(f"❌ Pricing with ID {pricing_id} not found.")
            return
        
        # Show details
        from_region = db.query(Region).filter(Region.id == pricing.from_region_id).first()
        to_region = db.query(Region).filter(Region.id == pricing.to_region_id).first()
        
        print(f"\n📌 Pricing Details:")
        print(f"   ID: {pricing.id}")
        print(f"   From: {from_region.name_uz_latin if from_region else 'Unknown'}")
        print(f"   To: {to_region.name_uz_latin if to_region else 'Unknown'}")
        print(f"   Type: {pricing.service_type}")
        print(f"   Base Price: {float(pricing.base_price)}")
        
        confirm = input("\n🔴 Delete this pricing? (yes/no): ")
        
        if confirm.lower() != 'yes':
            print("❌ Cancelled.")
            return
        
        db.delete(pricing)
        db.commit()
        
        print(f"✅ Pricing ID {pricing_id} deleted successfully!")
        
    except ValueError:
        print("❌ Invalid input. Please enter a number.")
    except Exception as e:
        print(f"❌ Error: {e}")
        db.rollback()


def delete_by_service_type(db: Session):
    """Delete pricing by service type"""
    print("\nService Types:")
    print("1. taxi")
    print("2. delivery")
    
    choice = input("\nSelect service type (1 or 2, 0 to cancel): ")
    
    if choice == "0":
        print("❌ Cancelled.")
        return
    
    service_type = "taxi" if choice == "1" else "delivery" if choice == "2" else None
    
    if not service_type:
        print("❌ Invalid choice.")
        return
    
    # Count records
    count = db.query(Pricing).filter(Pricing.service_type == service_type).count()
    
    if count == 0:
        print(f"\n📋 No pricing records found for service type '{service_type}'.")
        return
    
    print(f"\n⚠️  Found {count} pricing record(s) for service type '{service_type}'.")
    
    # List them
    pricing_records = db.query(Pricing).filter(Pricing.service_type == service_type).all()
    print("\nRecords to be deleted:")
    print("-" * 100)
    print(f"{'ID':<5} {'From Region':<25} {'To Region':<25} {'Base Price':<12}")
    print("-" * 100)
    
    for p in pricing_records:
        from_region = db.query(Region).filter(Region.id == p.from_region_id).first()
        to_region = db.query(Region).filter(Region.id == p.to_region_id).first()
        
        from_name = from_region.name_uz_latin if from_region else f"ID:{p.from_region_id}"
        to_name = to_region.name_uz_latin if to_region else f"ID:{p.to_region_id}"
        
        print(f"{p.id:<5} {from_name:<25} {to_name:<25} {float(p.base_price):<12.2f}")
    
    print("-" * 100)
    
    confirm = input(f"\n🔴 Delete ALL {count} pricing record(s) for '{service_type}'? (yes/no): ")
    
    if confirm.lower() != 'yes':
        print("❌ Cancelled.")
        return
    
    try:
        deleted = db.query(Pricing).filter(Pricing.service_type == service_type).delete()
        db.commit()
        print(f"✅ Successfully deleted {deleted} pricing record(s) for '{service_type}'!")
    except Exception as e:
        print(f"❌ Error: {e}")
        db.rollback()


def delete_inactive_pricing(db: Session):
    """Delete all inactive pricing records"""
    count = db.query(Pricing).filter(Pricing.is_active == False).count()
    
    if count == 0:
        print("\n📋 No inactive pricing records found.")
        return
    
    print(f"\n⚠️  Found {count} inactive pricing record(s).")
    
    # List them
    pricing_records = db.query(Pricing).filter(Pricing.is_active == False).all()
    print("\nInactive records to be deleted:")
    print("-" * 100)
    print(f"{'ID':<5} {'From Region':<25} {'To Region':<25} {'Type':<10} {'Base Price':<12}")
    print("-" * 100)
    
    for p in pricing_records:
        from_region = db.query(Region).filter(Region.id == p.from_region_id).first()
        to_region = db.query(Region).filter(Region.id == p.to_region_id).first()
        
        from_name = from_region.name_uz_latin if from_region else f"ID:{p.from_region_id}"
        to_name = to_region.name_uz_latin if to_region else f"ID:{p.to_region_id}"
        
        print(f"{p.id:<5} {from_name:<25} {to_name:<25} {p.service_type:<10} {float(p.base_price):<12.2f}")
    
    print("-" * 100)
    
    confirm = input(f"\n🔴 Delete ALL {count} inactive pricing record(s)? (yes/no): ")
    
    if confirm.lower() != 'yes':
        print("❌ Cancelled.")
        return
    
    try:
        deleted = db.query(Pricing).filter(Pricing.is_active == False).delete()
        db.commit()
        print(f"✅ Successfully deleted {deleted} inactive pricing record(s)!")
    except Exception as e:
        print(f"❌ Error: {e}")
        db.rollback()


def delete_all_pricing(db: Session):
    """Delete all pricing records"""
    count = db.query(Pricing).count()
    
    if count == 0:
        print("\n📋 No pricing records found.")
        return
    
    print(f"\n⚠️  Found {count} pricing record(s) in total.")
    
    confirm = input("\n🔴 Delete ALL pricing records? (yes/no): ")
    
    if confirm.lower() != 'yes':
        print("❌ Cancelled.")
        return
    
    # Double confirmation
    double_confirm = input("\n🔴 This action CANNOT be undone! Type 'DELETE ALL' to confirm: ")
    
    if double_confirm != 'DELETE ALL':
        print("❌ Cancelled.")
        return
    
    try:
        deleted = db.query(Pricing).delete()
        db.commit()
        print(f"✅ Successfully deleted {deleted} pricing record(s)!")
    except Exception as e:
        print(f"❌ Error: {e}")
        db.rollback()


def main():
    """Main menu"""
    print("\n" + "="*60)
    print("DELETE PRICING RECORDS - INTERACTIVE TOOL")
    print("="*60)
    
    db = SessionLocal()
    
    try:
        while True:
            print("\n📋 Options:")
            print("1. List all pricing records")
            print("2. Delete pricing by ID")
            print("3. Delete pricing by service type (taxi/delivery)")
            print("4. Delete all inactive pricing")
            print("5. Delete ALL pricing records")
            print("0. Exit")
            
            choice = input("\nSelect option: ")
            
            if choice == "0":
                print("\n👋 Goodbye!")
                break
            elif choice == "1":
                list_all_pricing(db)
            elif choice == "2":
                delete_by_id(db)
            elif choice == "3":
                delete_by_service_type(db)
            elif choice == "4":
                delete_inactive_pricing(db)
            elif choice == "5":
                delete_all_pricing(db)
            else:
                print("❌ Invalid option. Please try again.")
    
    except KeyboardInterrupt:
        print("\n\n⚠️  Operation interrupted by user.")
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
