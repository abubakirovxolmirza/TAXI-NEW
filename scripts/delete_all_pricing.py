"""
Script to delete all pricing records from the database
"""
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from sqlalchemy.orm import Session
from app.database import SessionLocal, engine
from app.models import Pricing


def delete_all_pricing():
    """Delete all pricing records"""
    print("\n" + "="*60)
    print("DELETE ALL PRICING RECORDS")
    print("="*60)
    
    db = SessionLocal()
    
    try:
        # Count existing pricing records
        total_count = db.query(Pricing).count()
        
        if total_count == 0:
            print("\n✅ No pricing records found in database.")
            return
        
        print(f"\n⚠️  Found {total_count} pricing record(s) in database.")
        
        # Ask for confirmation
        confirmation = input("\n🔴 Are you sure you want to DELETE ALL pricing records? (yes/no): ")
        
        if confirmation.lower() != 'yes':
            print("\n❌ Operation cancelled.")
            return
        
        # Double confirmation for safety
        double_confirm = input("\n🔴 This action CANNOT be undone! Type 'DELETE ALL' to confirm: ")
        
        if double_confirm != 'DELETE ALL':
            print("\n❌ Operation cancelled.")
            return
        
        # Delete all pricing records
        deleted_count = db.query(Pricing).delete()
        db.commit()
        
        print(f"\n✅ Successfully deleted {deleted_count} pricing record(s)!")
        print("\n" + "="*60)
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        db.rollback()
    finally:
        db.close()


if __name__ == "__main__":
    delete_all_pricing()
