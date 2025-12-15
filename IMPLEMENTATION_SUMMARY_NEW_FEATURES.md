  # Implementation Summary: New Features for Taxi Service API

## Overview
This document summarizes the implementation of 5 major features with comprehensive testing as requested.

## 🚀 Quick Start: How to Migrate and Test

### Step 1: Install Dependencies
Make sure all dependencies are installed:
```powershell
pip install -r requirements.txt
```

### Step 2: Database Migration

#### Option A: Using Alembic (Recommended)
```powershell
# Run the migration
alembic upgrade head
```

If you encounter issues with the Gender enum migration, you may need to manually adjust it for your database system.

#### Option B: Fresh Database (Development Only)
If you're starting fresh or in development:
```powershell
# This will drop all tables and recreate them
# WARNING: This deletes all data!
python -c "from app.database import engine, Base; from app.models import *; Base.metadata.drop_all(bind=engine); Base.metadata.create_all(bind=engine)"
```

### Step 3: Verify Database Changes

Check that new tables and columns exist:
```powershell
# Using SQLite (if that's your database)
sqlite3 your_database.db ".schema bonus"
sqlite3 your_database.db ".schema order_acceptance_history"

# Or check via Python
python -c "from app.database import SessionLocal; from app.models import Bonus, OrderAcceptanceHistory; db = SessionLocal(); print('Tables exist!' if db.query(Bonus).first() is not None or True else 'Error')"
```

### Step 4: Create Initial Data (Optional)

Create an initial bonus percentage:
```powershell
# Start Python shell
python

# Then run:
from app.database import SessionLocal
from app.models import Bonus
from decimal import Decimal

db = SessionLocal()
bonus = Bonus(bonus_percent=Decimal("5.00"), description="Default 5% bonus", is_active=True)
db.add(bonus)
db.commit()
print(f"Created bonus with ID: {bonus.id}")
db.close()
```

Set the public order timeout (default is 15 seconds if not set):
```powershell
python

from app.database import SessionLocal
from app.models import SystemSettings

db = SessionLocal()
setting = SystemSettings(
    setting_key="public_order_timeout",
    setting_value="15",
    description="Timeout in seconds before order becomes public"
)
db.add(setting)
db.commit()
print("Public order timeout set to 15 seconds")
db.close()
```

### Step 5: Run Tests

#### Run All New Feature Tests
```powershell
# Run the comprehensive test suite
pytest tests/test_new_features_complete.py -v

# Run with coverage report
pytest tests/test_new_features_complete.py -v --cov=app --cov-report=html
```

#### Run Specific Test Categories
```powershell
# Test only gender validation
pytest tests/test_new_features_complete.py -v -k "gender"

# Test only bonus system
pytest tests/test_new_features_complete.py -v -k "bonus"

# Test only pending time
pytest tests/test_new_features_complete.py -v -k "pending_time"

# Test only public orders
pytest tests/test_new_features_complete.py -v -k "public"

# Test only acceptance history
pytest tests/test_new_features_complete.py -v -k "acceptance"
```

#### Run All Tests (Including Existing)
```powershell
# Run entire test suite
pytest tests/ -v

# Run with detailed output
pytest tests/ -v -s
```

### Step 6: Start the Application

```powershell
# Development mode
python main.py

# Or using uvicorn directly
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

The application will:
- Start the API server
- Initialize Redis connection
- Start background tasks (including public order timeout checker)

### Step 7: Manual API Testing

#### Test Bonus System
```powershell
# Create admin token first
curl -X POST "http://localhost:8000/api/auth/login" -H "Content-Type: application/json" -d '{\"telephone\": \"+998901234567\", \"password\": \"your_password\"}'

# Create a bonus
curl -X POST "http://localhost:8000/api/bonus/" -H "Authorization: Bearer YOUR_TOKEN" -H "Content-Type: application/json" -d '{\"bonus_percent\": 5.0, \"description\": \"5% referral bonus\"}'

# Get all bonuses
curl -X GET "http://localhost:8000/api/bonus/" -H "Authorization: Bearer YOUR_TOKEN"

# Get active bonus
curl -X GET "http://localhost:8000/api/bonus/active" -H "Authorization: Bearer YOUR_TOKEN"
```

#### Test Public Orders
```powershell
# Get public taxi orders (as driver)
curl -X GET "http://localhost:8000/api/taxi-orders/public" -H "Authorization: Bearer DRIVER_TOKEN"

# Get public delivery orders
curl -X GET "http://localhost:8000/api/delivery-orders/public" -H "Authorization: Bearer DRIVER_TOKEN"

# Update public order timeout (as admin)
curl -X PUT "http://localhost:8000/api/admin/settings/public-order-timeout" -H "Authorization: Bearer ADMIN_TOKEN" -H "Content-Type: application/json" -d '{\"public_order_timeout\": 20}'
```

#### Test Pending Time
```powershell
# Update pending time for taxi order (as admin)
curl -X PUT "http://localhost:8000/api/taxi-orders/123/pending-time" -H "Authorization: Bearer ADMIN_TOKEN" -H "Content-Type: application/json" -d '{\"pending_time\": 300}'
```

#### Test Order with Bonus
```powershell
# Create order with bonus_user_id
curl -X POST "http://localhost:8000/api/taxi-orders/" -H "Authorization: Bearer USER_TOKEN" -H "Content-Type: application/json" -d '{
  \"username\": \"John Doe\",
  \"telephone\": \"+998901234567\",
  \"from_region_id\": 1,
  \"from_district_id\": 1,
  \"to_region_id\": 2,
  \"to_district_id\": 2,
  \"passengers\": 2,
  \"client_gender\": \"male\",
  \"date\": \"15.12.2025\",
  \"time_start\": \"10:00\",
  \"time_end\": \"11:00\",
  \"bonus_user_id\": 5
}'
```

### Step 8: Verify Background Tasks

Check that the public order timeout task is running:
```powershell
# Monitor application logs, you should see:
# [TASKS] Background tasks started
# [TASK] Taxi order #123 is now public (no acceptance within 15s)
```

### Troubleshooting

#### Migration Issues
If migration fails:
```powershell
# Check current revision
alembic current

# Check migration history
alembic history

# Rollback one revision
alembic downgrade -1

# Try upgrade again
alembic upgrade head
```

#### Gender Enum Issue
If you get errors about the Gender enum:
```powershell
# For PostgreSQL, manually run:
# ALTER TYPE gender DROP VALUE IF EXISTS 'other';

# For SQLite, the enum is not enforced at DB level, so the migration should work

# For MySQL, you may need to alter the column:
# ALTER TABLE taxi_orders MODIFY COLUMN client_gender ENUM('male', 'female');
```

#### Test Database Issues
If tests fail with database errors:
```powershell
# Delete test database and retry
Remove-Item -Path "test_new_features.db" -ErrorAction SilentlyContinue
pytest tests/test_new_features_complete.py -v
```

#### Background Task Not Running
If public orders don't become public:
- Check that Redis is running
- Verify the background task started (check logs)
- Check the `public_order_timeout` system setting

### Monitoring

After deployment, monitor:
1. **Bonus calculations**: Check user `bonus_ball` values are updating correctly
2. **Public orders**: Verify orders become public after timeout
3. **Acceptance history**: Check that history records are being created
4. **Gender validation**: Ensure only 'male' and 'female' are accepted

## Features Implemented

### 1. Order Acceptance History (Taxi & Delivery)
**Purpose**: Track which drivers received pending orders but did not accept them.

**Implementation**:
- **New Model**: `OrderAcceptanceHistory` in `app/models.py`
  - Fields: `id`, `driver_id`, `taxi_order_id`, `delivery_order_id`, `action`, `created_at`
  - Actions tracked: "received_pending", "not_accepted", "accepted"
  
- **Database Changes**:
  - New table: `order_acceptance_history`
  - Foreign keys to `drivers`, `taxi_orders`, and `delivery_orders`
  - Indexes on driver_id, taxi_order_id, delivery_order_id

- **API Endpoints**:
  - `GET /api/taxi-orders/{order_id}/acceptance-history` - View acceptance history for taxi order (Admin only)
  - `GET /api/delivery-orders/{order_id}/acceptance-history` - View acceptance history for delivery order (Admin only)

- **Logic**:
  - When a driver accepts an order, a record with action="accepted" is created
  - History is automatically recorded in the accept order endpoint

### 2. Gender Choices Update
**Purpose**: Remove "other" option, keeping only "male" and "female".

**Implementation**:
- **Model Change**: Updated `Gender` enum in `app/models.py`
  - Removed `OTHER = "other"`
  - Kept only `MALE = "male"` and `FEMALE = "female"`

- **Database Changes**:
  - Migration removes 'other' value from gender enum
  
- **Validation**:
  - Pydantic schemas automatically validate to only accept "male" or "female"
  - Returns 422 validation error for invalid gender values

### 3. Pending Time CRUD
**Purpose**: Make pending_time fully manageable via CRUD operations.

**Implementation**:
- **Model Changes**:
  - Added `pending_time` field (Integer) to both `TaxiOrder` and `DeliveryOrder` models
  - Stores time in seconds

- **Schema Changes**:
  - New schema: `PendingTimeUpdate` in `app/schemas.py`
  - Validates that pending_time >= 0

- **API Endpoints**:
  - `PUT /api/taxi-orders/{order_id}/pending-time` - Update pending time for taxi order (Admin only)
  - `PUT /api/delivery-orders/{order_id}/pending-time` - Update pending time for delivery order (Admin only)

- **Features**:
  - Create: Set pending_time when creating order
  - Read: View pending_time in order response
  - Update: Change pending_time manually via endpoint
  - Validation: Prevents negative values

### 4. Bonus System
**Purpose**: Calculate and award bonuses to users when orders are completed.

**Implementation**:
- **New Model**: `Bonus` in `app/models.py`
  - Fields: `id`, `bonus_percent`, `description`, `is_active`, `created_at`, `updated_at`
  - Stores percentage (0-100) for bonus calculation

- **Model Changes**:
  - Added `bonus_ball` field to `User` model (Numeric 10,2)
  - Added `bonus_user_id` field to both `TaxiOrder` and `DeliveryOrder` models

- **API Endpoints** (all in `/api/bonus/`):
  - `POST /` - Create bonus percentage record (Admin only)
  - `GET /` - Get all bonus records (Admin only)
  - `GET /active` - Get active bonus percentage (Admin only)
  - `GET /{bonus_id}` - Get specific bonus record (Admin only)
  - `PUT /{bonus_id}` - Update bonus record (Admin only)
  - `DELETE /{bonus_id}` - Delete bonus record (Admin only)

- **Bonus Calculation Logic** (in `app/routers/driver.py`):
  1. When order is completed, check if `bonus_user_id` is provided
  2. If yes, get active bonus percentage
  3. Calculate: `bonus_amount = (order.price * bonus_percent) / 100`
  4. Add `bonus_amount` to `bonus_user.bonus_ball`
  5. Send notification to bonus user

- **Validation**:
  - Bonus percentage must be between 0 and 100
  - Returns validation error for invalid percentages

### 5. Public Orders Logic (Taxi & Delivery)
**Purpose**: If no driver accepts within timeout, make order public to all drivers.

**Implementation**:
- **Model Changes**:
  - Added `public_order` field (Boolean, default False) to orders
  - Added `public_order_activated_at` field (DateTime) to track when order became public

- **System Settings**:
  - New setting: `public_order_timeout` (default: 15 seconds)
  - Configurable via admin endpoints

- **Background Task** (in `app/tasks.py`):
  - New function: `check_public_order_timeout()`
  - Runs every 5 seconds
  - Checks for orders that:
    - Are PENDING status
    - Have public_order = False
    - Have no driver assigned
    - Created more than timeout seconds ago
  - Sets `public_order = True` and broadcasts to all drivers

- **API Endpoints**:
  - `GET /api/taxi-orders/public` - Get public taxi orders (Driver only)
  - `GET /api/delivery-orders/public` - Get public delivery orders (Driver only)
  - `GET /api/admin/settings/public-order-timeout` - Get timeout setting (Admin only)
  - `PUT /api/admin/settings/public-order-timeout` - Update timeout setting (Admin only)

- **Logic Flow**:
  1. Order created with `public_order = False`
  2. Order broadcasted to eligible drivers
  3. If no acceptance within timeout, background task sets `public_order = True`
  4. Order becomes visible in public endpoint
  5. All drivers can now see and accept the order

## Database Migration

**File**: `alembic/versions/add_new_features_2025.py`

**Changes**:
- Add `bonus_ball` column to `users` table
- Add `pending_time`, `bonus_user_id`, `public_order`, `public_order_activated_at` to `taxi_orders`
- Add same fields to `delivery_orders`
- Create `bonus` table
- Create `order_acceptance_history` table
- Add foreign keys and indexes
- Remove 'other' from Gender enum

**To Apply**:
```bash
alembic upgrade head
```

## Testing

**Test File**: `tests/test_new_features_complete.py`

**Test Coverage**:

### Gender Validation Tests
- ✅ Test 'male' gender is accepted
- ✅ Test 'female' gender is accepted
- ✅ Test 'other' gender is rejected with 422 error

### Bonus System Tests
- ✅ Create bonus percentage record
- ✅ Retrieve all bonus records
- ✅ Update bonus record
- ✅ Delete bonus record
- ✅ Bonus calculation on order completion
- ✅ No bonus when bonus_user_id not provided
- ✅ Bonus percentage validation (0-100 range)
- ✅ Multiple orders accumulating bonuses

### Pending Time CRUD Tests
- ✅ Update pending_time for taxi order
- ✅ Update pending_time for delivery order
- ✅ Retrieve updated pending_time
- ✅ Validation: reject negative values

### Public Order Tests
- ✅ Order becomes public after timeout
- ✅ Get public orders endpoint
- ✅ Update public order timeout setting
- ✅ Get public order timeout setting
- ✅ Accepted orders never become public

### Order Acceptance History Tests
- ✅ Acceptance recorded when driver accepts
- ✅ Retrieve acceptance history for order
- ✅ Multiple drivers recorded correctly
- ✅ History for both taxi and delivery orders

### Edge Case Tests
- ✅ Order with zero price (bonus = 0)
- ✅ Zero percent bonus (valid)
- ✅ Bonus percentage > 100% (rejected)
- ✅ Bonus percentage < 0% (rejected)
- ✅ Order accepted at timeout boundary

**Running Tests**:
```bash
pytest tests/test_new_features_complete.py -v
```

## Updated Files

### Models & Schemas
- `app/models.py` - Added new models and fields
- `app/schemas.py` - Added new request/response schemas

### Routers
- `app/routers/bonus.py` - NEW: Bonus CRUD endpoints
- `app/routers/taxi_orders.py` - Added public orders, pending time, acceptance history endpoints
- `app/routers/delivery_orders.py` - Added public orders, pending time, acceptance history endpoints
- `app/routers/driver.py` - Added bonus calculation in complete order, acceptance history tracking
- `app/routers/admin.py` - Added public order timeout settings

### Core
- `app/tasks.py` - Added public order timeout background task
- `main.py` - Registered bonus router

### Database
- `alembic/versions/add_new_features_2025.py` - Migration for all changes

### Tests
- `tests/test_new_features_complete.py` - Comprehensive test suite

## API Summary

### New Endpoints

#### Bonus Management
- `POST /api/bonus/` - Create bonus
- `GET /api/bonus/` - List bonuses
- `GET /api/bonus/active` - Get active bonus
- `GET /api/bonus/{id}` - Get bonus
- `PUT /api/bonus/{id}` - Update bonus
- `DELETE /api/bonus/{id}` - Delete bonus

#### Order Management
- `GET /api/taxi-orders/public` - Public taxi orders
- `GET /api/delivery-orders/public` - Public delivery orders
- `PUT /api/taxi-orders/{id}/pending-time` - Update pending time
- `PUT /api/delivery-orders/{id}/pending-time` - Update pending time
- `GET /api/taxi-orders/{id}/acceptance-history` - View history
- `GET /api/delivery-orders/{id}/acceptance-history` - View history

#### System Settings
- `GET /api/admin/settings/public-order-timeout` - Get timeout
- `PUT /api/admin/settings/public-order-timeout` - Update timeout

## Usage Examples

### 1. Creating an Order with Bonus User

```json
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

### 2. Setting Bonus Percentage

```json
POST /api/bonus/
{
  "bonus_percent": 5.0,
  "description": "5% bonus for referrals"
}
```

### 3. Updating Pending Time

```json
PUT /api/taxi-orders/123/pending-time
{
  "pending_time": 300
}
```

### 4. Setting Public Order Timeout

```json
PUT /api/admin/settings/public-order-timeout
{
  "public_order_timeout": 20
}
```

### 5. Getting Public Orders (Driver)

```
GET /api/taxi-orders/public
```

## Notes & Considerations

1. **Gender Enum**: The database migration attempts to remove 'other' from the enum. This is database-specific and may need manual intervention on some databases.

2. **Background Tasks**: The public order timeout task runs automatically when the app starts. Make sure Redis is configured for optimal performance.

3. **Bonus Calculation**: Bonuses are only calculated when an order is COMPLETED and if a `bonus_user_id` is provided.

4. **Order Acceptance History**: Currently tracks "accepted" action. Can be extended to track "received_pending" and "not_accepted" by adding logic in order broadcasting.

5. **Public Orders**: Orders only become public if they remain PENDING without driver acceptance. Once accepted, they never become public.

6. **Testing**: All tests use SQLite in-memory database. For production testing, use the actual database system.

7. **Permissions**: Most admin endpoints require ADMIN or SUPERADMIN role. Bonus operations are restricted to admins only.

## Future Enhancements

1. **Order Acceptance History**: Add tracking when orders are broadcasted to drivers (received_pending action)
2. **Bonus History**: Track bonus transactions separately for audit purposes
3. **Public Order Notifications**: Push notifications when order becomes public
4. **Dynamic Timeout**: Allow different timeout values per region or time of day
5. **Bonus Tiers**: Support multiple bonus percentages based on order value or user level

## Deployment Checklist

- [ ] Run database migration: `alembic upgrade head`
- [ ] Set initial public order timeout: Default 15 seconds
- [ ] Create initial bonus percentage record if needed
- [ ] Run test suite to verify all features: `pytest tests/test_new_features_complete.py -v`
- [ ] Update API documentation with new endpoints
- [ ] Configure background tasks to start on application startup (already done in main.py)
- [ ] Monitor public order timeout task logs
- [ ] Test bonus calculation in production with small orders first

## Support

For issues or questions:
- Check test file for usage examples
- Review API endpoints in router files
- Check model definitions for field constraints
- Review migration file for database schema changes
