"""
Create a superadmin user
Usage: python scripts/create_superadmin.py
"""
from app.database import SessionLocal
from app.models import User, UserRole
from app.auth import get_password_hash
import getpass


def create_superadmin():
    """Create a superadmin user interactively"""
    
    print("=" * 50)
    print("Create Superadmin User")
    print("=" * 50)
    
    # Get user input
    telephone = input("Enter telephone number (e.g., +998901234567): ")
    name = input("Enter name: ")
    password = getpass.getpass("Enter password: ")
    confirm_password = getpass.getpass("Confirm password: ")
    
    # Validate
    if password != confirm_password:
        print("❌ Passwords do not match!")
        return
    
    if len(password) < 6:
        print("❌ Password must be at least 6 characters!")
        return
    
    db = SessionLocal()
    
    try:
        # Check if user already exists
        existing_user = db.query(User).filter(User.telephone == telephone).first()
        
        if existing_user:
            print(f"❌ User with telephone {telephone} already exists!")
            return
        
        # Create superadmin
        superadmin = User(
            telephone=telephone,
            name=name,
            hashed_password=get_password_hash(password),
            role=UserRole.SUPERADMIN,
            is_active=True
        )
        
        db.add(superadmin)
        db.commit()
        
        print("\n✅ Superadmin created successfully!")
        print(f"📱 Telephone: {telephone}")
        print(f"👤 Name: {name}")
        print(f"🔑 Role: SUPERADMIN")
        
    except Exception as e:
        print(f"\n❌ Error creating superadmin: {e}")
        db.rollback()
    finally:
        db.close()


if __name__ == "__main__":
    create_superadmin()
