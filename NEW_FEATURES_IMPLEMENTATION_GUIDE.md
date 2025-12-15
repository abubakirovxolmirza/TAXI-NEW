# New Features Implementation Guide

## Overview

This document describes the newly implemented features and how to use them.

## Features Implemented

### 1. Order Acceptance History
Tracks which drivers received pending orders but did not accept them.

**Endpoints:**
- `POST /api/order-history/track/{order_type}/{order_id}` - Track driver actions (received/ignored/declined)
- `GET /api/order-acceptance-history/driver/{driver_id}` - Get history for a driver (Admin only)
- `GET /api/order-acceptance-history/order/taxi/{order_id}` - Get history for a taxi order (Admin only)
- `GET /api/order-acceptance-history/order/delivery/{order_id}` - Get history for a delivery order (Admin only)

### 2. Gender Choices Update
The `gender` field now only accepts `male` and `female`. The `other` option has been removed.

### 3. Pending Time CRUD
Full CRUD operations for managing `pending_time` on orders.

**Endpoints:**
- `GET /api/pending-time/` - Get global pending time setting
- `PUT /api/pending-time/` - Update global pending time setting (Admin only)
- `PUT /api/pending-time/taxi/{order_id}` - Update pending time for specific taxi order (Admin only)
- `PUT /api/pending-time/delivery/{order_id}` - Update pending time for specific delivery order (Admin only)

### 4. Bonus System
A complete bonus system that rewards users when orders are completed.

**Models:**
- `Bonus` - Configuration for bonus percentage
- User model now has `bonus_ball` field to track bonus balance

**Fields Added to Orders:**
- `bonus_user_id` (optional) - User who will receive the bonus

**How it works:**
1. When creating an order, optionally specify `bonus_user_id`
2. When the order is completed, the system:
   - Gets the active bonus configuration
   - Calculates bonus: `order_price * bonus_percent / 100`
   - Adds the bonus to the `bonus_ball` of the bonus user
   - Sends a notification to the bonus user

**Endpoints:**
- `POST /api/bonuses/` - Create bonus configuration (Admin only)
- `GET /api/bonuses/` - Get all bonus configurations (Admin only)
- `GET /api/bonuses/active` - Get active bonus configuration (Public)
- `GET /api/bonuses/{bonus_id}` - Get specific bonus configuration (Admin only)
- `PUT /api/bonuses/{bonus_id}` - Update bonus configuration (Admin only)
- `DELETE /api/bonuses/{bonus_id}` - Delete bonus configuration (Admin only)

### 5. Public Orders Logic
Orders can become publicly visible to all drivers after a configurable timeout.

**Fields Added to Orders:**
- `public_order` (boolean) - Whether order is visible to all drivers
- `pending_time` (integer) - Seconds before order becomes public

**How it works:**
1. Order is created with `public_order=false` and `pending_time` (default: 15 seconds)
2. A background task checks every 5 seconds for orders where:
   - Status is PENDING
   - `public_order` is false
   - No driver assigned
   - Time elapsed since creation >= `pending_time`
3. When conditions are met, the order is made public
4. All drivers are notified via WebSocket

**Endpoints:**
- `GET /api/public-orders/taxi` - Get all public taxi orders (Drivers only)
- `GET /api/public-orders/delivery` - Get all public delivery orders (Drivers only)
- `POST /api/public-orders/taxi/{order_id}/make-public` - Manually make taxi order public (Admin only)
- `POST /api/public-orders/delivery/{order_id}/make-public` - Manually make delivery order public (Admin only)

## Database Migration

### Running Migrations

1. **Apply the migration:**
```powershell
alembic upgrade head
```

2. **Verify migration status:**
```powershell
alembic current
```

3. **View migration history:**
```powershell
alembic history
```

### Rollback Migration (if needed)

To rollback the new features migration:
```powershell
alembic downgrade -1
```

### What the Migration Does

The migration `add_new_features_2025.py` performs the following:

1. **Updates Gender enum** - Removes 'other' option, keeps only 'male' and 'female'
2. **Adds to users table:**
   - `bonus_ball` (Numeric) - Bonus balance, default 0.00

3. **Adds to taxi_orders table:**
   - `bonus_user_id` (Integer, nullable) - Foreign key to users
   - `public_order` (Boolean) - Default false
   - `pending_time` (Integer, nullable) - Time in seconds

4. **Adds to delivery_orders table:**
   - `bonus_user_id` (Integer, nullable) - Foreign key to users
   - `public_order` (Boolean) - Default false
   - `pending_time` (Integer, nullable) - Time in seconds

5. **Creates bonuses table:**
   - `id` (Primary key)
   - `bonus_percent` (Numeric) - Percentage for bonus calculation
   - `description` (Text, nullable)
   - `is_active` (Boolean) - Default true
   - `created_at`, `updated_at` timestamps

6. **Creates order_acceptance_history table:**
   - `id` (Primary key)
   - `driver_id` (Foreign key to drivers)
   - `taxi_order_id` (Foreign key to taxi_orders, nullable)
   - `delivery_order_id` (Foreign key to delivery_orders, nullable)
   - `received_at` (DateTime with timezone)
   - `action` (String) - 'received', 'ignored', or 'declined'
   - `created_at` timestamp

7. **System Settings:**
   - Inserts default `public_order_pending_time` setting (15 seconds)
   - Inserts default bonus configuration (5%)

## Running Tests

### Prerequisites

Make sure pytest is installed:
```powershell
pip install pytest pytest-asyncio httpx
```

### Run All Tests

```powershell
pytest
```

### Run Specific Test File

```powershell
pytest tests/test_new_features_implementation.py
```

### Run Tests with Verbose Output

```powershell
pytest -v
```

### Run Tests with Coverage

```powershell
pytest --cov=app --cov-report=html
```

### Run Specific Test Function

```powershell
pytest tests/test_new_features_implementation.py::test_bonus_calculation -v
```

### Test Categories

The new features tests (`test_new_features_implementation.py`) include:

1. **Bonus System Tests:**
   - `test_create_bonus` - Creating bonus configurations
   - `test_get_active_bonus` - Getting active bonus
   - `test_update_bonus` - Updating bonus configurations
   - `test_bonus_calculation` - Bonus calculation logic
   - `test_order_with_bonus_user_id` - Orders with bonus users
   - `test_bonus_not_applied_without_bonus_user_id` - Bonus not applied when no bonus_user_id

2. **Order Acceptance History Tests:**
   - `test_order_acceptance_history_tracking` - Tracking driver actions

3. **Pending Time Tests:**
   - `test_get_pending_time_setting` - Getting pending time setting
   - `test_update_pending_time_setting` - Updating global pending time
   - `test_update_order_pending_time` - Updating order-specific pending time
   - `test_order_with_default_pending_time` - Default pending time on order creation

4. **Public Orders Tests:**
   - `test_public_orders_endpoint` - Getting public orders
   - `test_make_order_public` - Manually making orders public

5. **Gender Enum Tests:**
   - `test_gender_enum_no_other` - Verifying 'other' option is removed

### Test Fixtures

The tests use the following fixtures (defined in `conftest.py`):
- `client` - FastAPI test client
- `db` - Database session
- `user_token` - Authentication token for regular user
- `driver_token` - Authentication token for driver
- `admin_token` - Authentication token for admin

## Usage Examples

### Example 1: Creating an Order with Bonus

```python
import requests

# Create order with bonus user
response = requests.post(
    "http://localhost:8000/api/taxi-orders/",
    headers={"Authorization": f"Bearer {token}"},
    json={
        "username": "John Doe",
        "telephone": "998901234567",
        "bonus_user_id": 42,  # User ID who will receive bonus
        "from_region_id": 1,
        "from_district_id": 1,
        "to_region_id": 2,
        "to_district_id": 2,
        "passengers": 2,
        "client_gender": "male",
        "date": "16.12.2025",
        "time_start": "10:00",
        "time_end": "11:00"
    }
)
```

When this order is completed, user #42 will receive a bonus based on the order price and active bonus percentage.

### Example 2: Setting Up Bonus Configuration

```python
import requests

# Create bonus configuration
response = requests.post(
    "http://localhost:8000/api/bonuses/",
    headers={"Authorization": f"Bearer {admin_token}"},
    json={
        "bonus_percent": 10.0,  # 10% bonus
        "description": "Referral bonus",
        "is_active": True
    }
)
```

### Example 3: Tracking Order Acceptance History

```python
import requests

# When driver receives an order (called from driver app)
response = requests.post(
    "http://localhost:8000/api/order-history/track/taxi/123?action=received",
    headers={"Authorization": f"Bearer {driver_token}"}
)

# When driver ignores an order
response = requests.post(
    "http://localhost:8000/api/order-history/track/taxi/123?action=ignored",
    headers={"Authorization": f"Bearer {driver_token}"}
)
```

### Example 4: Configuring Pending Time

```python
import requests

# Set global pending time to 20 seconds
response = requests.put(
    "http://localhost:8000/api/pending-time/",
    headers={"Authorization": f"Bearer {admin_token}"},
    json={"pending_time": 20}
)

# Set pending time for specific order
response = requests.put(
    "http://localhost:8000/api/pending-time/taxi/123",
    headers={"Authorization": f"Bearer {admin_token}"},
    json={"pending_time": 30}
)
```

### Example 5: Getting Public Orders

```python
import requests

# Drivers can get all public taxi orders
response = requests.get(
    "http://localhost:8000/api/public-orders/taxi",
    headers={"Authorization": f"Bearer {driver_token}"}
)

public_orders = response.json()
```

## Background Tasks

The system runs two background tasks:

1. **check_unconfirmed_orders()** - Runs every 60 seconds
   - Checks for orders accepted but not confirmed within 15 minutes
   - Returns them to pending state

2. **check_pending_orders_for_public()** - Runs every 5 seconds
   - Checks for pending orders with expired pending_time
   - Makes them public and notifies all drivers

## API Documentation

After starting the server, you can access:
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

## Troubleshooting

### Migration Issues

If you encounter migration errors:

1. Check current migration state:
```powershell
alembic current
```

2. Check for pending migrations:
```powershell
alembic heads
```

3. If database is out of sync, you may need to stamp:
```powershell
alembic stamp head
```

### Test Failures

If tests fail:

1. Ensure database is clean:
```powershell
# Drop and recreate test database
```

2. Check that all dependencies are installed:
```powershell
pip install -r requirements.txt
```

3. Run tests with verbose output to see details:
```powershell
pytest -v -s
```

## Notes

- The `pending_time` is in seconds
- Default `pending_time` is 15 seconds (configurable via system settings)
- Bonus calculations use 2 decimal places
- Background tasks start automatically when the server starts
- Public orders are automatically broadcast to all connected drivers via WebSocket
