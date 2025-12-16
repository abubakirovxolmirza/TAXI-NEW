#!/usr/bin/env python
"""Add 'both' value to gender enum"""
from app.database import SessionLocal
from sqlalchemy import text

db = SessionLocal()
try:
    db.execute(text("ALTER TYPE gender ADD VALUE IF NOT EXISTS 'both'"))
    db.commit()
    print("✅ Successfully added 'both' to gender enum")
    
    # Verify
    result = db.execute(text("SELECT unnest(enum_range(NULL::gender))")).fetchall()
    values = [r[0] for r in result]
    print(f"Gender enum values: {values}")
except Exception as e:
    print(f"❌ Error: {e}")
    db.rollback()
finally:
    db.close()
