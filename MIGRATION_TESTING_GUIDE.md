# Quick Start: Migration and Testing

## Automated Migration & Testing (Easiest)

### Option 1: Using PowerShell Script
```powershell
.\migrate_and_test.ps1
```

### Option 2: Using Python Script
```powershell
python migrate_and_test.py
```

Both scripts will:
- ✅ Install dependencies
- ✅ Run database migration
- ✅ Set up initial data (bonus, settings)
- ✅ Run comprehensive tests
- ✅ Verify all models are working

---

## Manual Migration & Testing

### Step 1: Install Dependencies
```powershell
pip install -r requirements.txt
```

### Step 2: Run Migration
```powershell
alembic upgrade head
```

### Step 3: Run Tests
```powershell
# All new feature tests
pytest tests/test_new_features_complete.py -v

# Specific feature tests
pytest tests/test_new_features_complete.py -v -k "bonus"
pytest tests/test_new_features_complete.py -v -k "gender"
pytest tests/test_new_features_complete.py -v -k "pending_time"
pytest tests/test_new_features_complete.py -v -k "public"
pytest tests/test_new_features_complete.py -v -k "acceptance"
```

### Step 4: Start Application
```powershell
python main.py
```

---

## What Was Implemented

✅ **Order Acceptance History**
- Track which drivers received but didn't accept orders
- API: `GET /api/taxi-orders/{id}/acceptance-history`

✅ **Gender Field Update**
- Only 'male' and 'female' accepted
- 'other' option removed

✅ **Pending Time CRUD**
- Fully manageable pending_time field
- API: `PUT /api/taxi-orders/{id}/pending-time`

✅ **Bonus System**
- Create/manage bonus percentages
- Automatic bonus calculation on order completion
- API: `/api/bonus/` endpoints

✅ **Public Orders**
- Orders become public after timeout (default 15 seconds)
- Configurable timeout via admin settings
- API: `GET /api/taxi-orders/public`

---

## Testing Endpoints

### View API Documentation
```
http://localhost:8000/docs
```

### Test Bonus System
```bash
# Create bonus (admin required)
POST /api/bonus/
{
  "bonus_percent": 5.0,
  "description": "5% referral bonus"
}

# Get all bonuses
GET /api/bonus/
```

### Test Public Orders
```bash
# Get public orders (driver required)
GET /api/taxi-orders/public
GET /api/delivery-orders/public

# Update timeout (admin required)
PUT /api/admin/settings/public-order-timeout
{
  "public_order_timeout": 20
}
```

### Test Order with Bonus
```bash
POST /api/taxi-orders/
{
  "username": "John Doe",
  "telephone": "+998901234567",
  "from_region_id": 1,
  "from_district_id": 1,
  "to_region_id": 2,
  "to_district_id": 2,
  "passengers": 2,
  "client_gender": "male",
  "date": "15.12.2025",
  "time_start": "10:00",
  "time_end": "11:00",
  "bonus_user_id": 5
}
```

---

## Troubleshooting

### Migration Failed
```powershell
# Check current version
alembic current

# Rollback and retry
alembic downgrade -1
alembic upgrade head
```

### Tests Failed
```powershell
# Remove test database
Remove-Item test_new_features.db -ErrorAction SilentlyContinue

# Run tests again
pytest tests/test_new_features_complete.py -v
```

### Gender Enum Issue
For PostgreSQL:
```sql
ALTER TYPE gender DROP VALUE IF EXISTS 'other';
```

---

## Documentation

📚 **Full Documentation**: `IMPLEMENTATION_SUMMARY_NEW_FEATURES.md`

📝 **Test File**: `tests/test_new_features_complete.py`

🗄️ **Migration**: `alembic/versions/add_new_features_2025.py`

---

## Support

If you encounter issues:
1. Check the full documentation in `IMPLEMENTATION_SUMMARY_NEW_FEATURES.md`
2. Review test examples in `tests/test_new_features_complete.py`
3. Check logs for error messages
4. Verify database connection and Redis availability

---

**All features are production-ready with comprehensive test coverage! 🎉**
