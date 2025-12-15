# Quick Start Guide - Running Migrations and Tests

## Running Database Migrations

### 1. Apply All Migrations
```powershell
alembic upgrade head
```

This will:
- Update the Gender enum (remove 'other' option)
- Add bonus_ball field to users table
- Add bonus_user_id, public_order, pending_time to orders
- Create bonuses table
- Create order_acceptance_history table
- Insert default system settings

### 2. Check Current Migration Status
```powershell
alembic current
```

### 3. View Migration History
```powershell
alembic history
```

### 4. Rollback Migration (if needed)
```powershell
alembic downgrade -1
```

## Running Tests

### 1. Install Test Dependencies (if not already installed)
```powershell
pip install pytest pytest-asyncio httpx
```

### 2. Run All Tests
```powershell
pytest
```

### 3. Run Only New Features Tests
```powershell
pytest tests/test_new_features_implementation.py
```

### 4. Run Tests with Verbose Output
```powershell
pytest -v
```

### 5. Run Tests with Coverage Report
```powershell
pytest --cov=app --cov-report=html
```

### 6. Run Specific Test
```powershell
pytest tests/test_new_features_implementation.py::test_bonus_calculation -v
```

## Starting the Application

### Option 1: Using Python
```powershell
python main.py
```

### Option 2: Using Uvicorn
```powershell
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

## Accessing API Documentation

Once the server is running:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## Testing the New Features

### Test Bonus System
```powershell
# Create bonus configuration (requires admin token)
curl -X POST http://localhost:8000/api/bonuses/ \
  -H "Authorization: Bearer YOUR_ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"bonus_percent": 10.0, "description": "Test bonus", "is_active": true}'

# Get active bonus (public endpoint)
curl http://localhost:8000/api/bonuses/active
```

### Test Pending Time
```powershell
# Get current pending time setting
curl http://localhost:8000/api/pending-time/

# Update pending time (requires admin token)
curl -X PUT http://localhost:8000/api/pending-time/ \
  -H "Authorization: Bearer YOUR_ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"pending_time": 20}'
```

### Test Public Orders
```powershell
# Get public taxi orders (requires driver token)
curl http://localhost:8000/api/public-orders/taxi \
  -H "Authorization: Bearer YOUR_DRIVER_TOKEN"

# Get public delivery orders (requires driver token)
curl http://localhost:8000/api/public-orders/delivery \
  -H "Authorization: Bearer YOUR_DRIVER_TOKEN"
```

## Troubleshooting

### If Migration Fails
1. Check database connection in `app/config.py`
2. Ensure PostgreSQL is running
3. Check migration file for syntax errors
4. View detailed error: `alembic upgrade head --sql` (shows SQL without executing)

### If Tests Fail
1. Ensure test database is properly configured
2. Check that all dependencies are installed: `pip install -r requirements.txt`
3. Clear pytest cache: `pytest --cache-clear`
4. Run with more details: `pytest -v -s`

### Common Issues

**Issue: "Import errors" in IDE**
- This is normal - imports work at runtime
- Install packages: `pip install -r requirements.txt`

**Issue: "Alembic can't locate revision"**
- Check: `alembic heads`
- May need: `alembic stamp head`

**Issue: "Database already has these changes"**
- Check current state: `alembic current`
- May need to manually stamp: `alembic stamp add_new_features_2025`

## Verification Checklist

After running migrations and tests, verify:

- [ ] Migration applied successfully (`alembic current` shows latest)
- [ ] All tests pass (`pytest` returns 0 failures)
- [ ] Server starts without errors
- [ ] API docs accessible at `/docs`
- [ ] Bonus endpoints work (check `/api/bonuses/active`)
- [ ] Pending time endpoints work (check `/api/pending-time/`)
- [ ] Public orders endpoints exist (check `/api/public-orders/taxi`)

## Success Indicators

✅ **Migration successful** if:
- `alembic current` shows `add_new_features_2025`
- No error messages during upgrade
- Database tables have new columns

✅ **Tests successful** if:
- All test functions pass
- No import errors
- Coverage report generated (if using --cov)

✅ **Application running** if:
- Server starts on port 8000
- `/docs` shows all new endpoints
- No errors in console log
- Background tasks message appears

## Need Help?

1. Check logs for detailed error messages
2. Review `NEW_FEATURES_IMPLEMENTATION_GUIDE.md` for detailed documentation
3. Check `IMPLEMENTATION_SUMMARY.md` for overview of changes
4. Ensure all files are saved and no syntax errors exist
