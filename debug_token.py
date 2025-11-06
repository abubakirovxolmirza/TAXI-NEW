#!/usr/bin/env python3
import sys
sys.path.insert(0, '/var/www/taxi-service/TAXI-NEW')

from jose import jwt
from app.config import settings

# Test token from the script
token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOjEsImV4cCI6MTc2NTA1MDQ2NX0.aP5XKGMpY9LsnYbKg4wDt9NpeCmJ54NweNdEKvw3z7Q"

print("=" * 60)
print("JWT TOKEN DEBUGGING")
print("=" * 60)
print(f"\nToken: {token[:50]}...")
print(f"\nSECRET_KEY: {settings.SECRET_KEY}")
print(f"ALGORITHM: {settings.ALGORITHM}")

try:
    payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
    print("\n✓ Token decoded successfully!")
    print(f"Payload: {payload}")
    
    user_id = payload.get("sub")
    print(f"\nUser ID from token: {user_id}")
    
    # Test database query
    from app.database import SessionLocal
    from app.models import User
    
    db = SessionLocal()
    user = db.query(User).filter(User.id == user_id).first()
    
    if user:
        print(f"\n✓ User found in database!")
        print(f"  ID: {user.id}")
        print(f"  Name: {user.name}")
        print(f"  Role: {user.role}")
        print(f"  Is Active: {user.is_active}")
    else:
        print(f"\n✗ User ID {user_id} not found in database!")
    
    db.close()
    
except Exception as e:
    print(f"\n✗ Error: {e}")
    print(f"Error type: {type(e).__name__}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 60)
