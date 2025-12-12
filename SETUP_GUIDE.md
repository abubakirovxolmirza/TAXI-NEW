# Quick Setup Guide for New Features

## Prerequisites
- Python 3.8+
- PostgreSQL or SQLite database
- Existing Taxi Service API installation

## Installation Steps

### 1. Update Dependencies
```bash
pip install -r requirements.txt
```

### 2. Run Database Migration
```bash
# Apply the new district_pricing table migration
alembic upgrade head
```

This will create the `district_pricing` table in your database.

### 3. Verify Imports
The new routers are automatically included in `main.py`:
- `app.routers.admin_orders` - Admin order management
- `app.routers.regions_admin` - Admin regions/districts/pricing

### 4. Start the Server
```bash
# Development mode
python main.py

# Or with uvicorn
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### 5. Access API Documentation
Open your browser:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## Testing the New Features

### 1. Run Tests
```bash
# Run all new feature tests
pytest tests/test_new_features.py -v

# Run admin order management tests
pytest tests/test_admin_orders.py -v

# Run all tests
pytest tests/ -v
```

### 2. Manual Testing

#### Login as Admin
```bash
curl -X POST "http://localhost:8000/api/auth/login" \
  -H "Content-Type: application/json" \
  -d '{
    "telephone": "YOUR_ADMIN_PHONE",
    "password": "YOUR_ADMIN_PASSWORD"
  }'
```

Save the `access_token` from the response.

#### Create a Region
```bash
curl -X POST "http://localhost:8000/api/admin/regions/" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name_uz_latin": "Toshkent",
    "name_uz_cyrillic": "Тошкент",
    "name_russian": "Ташкент"
  }'
```

#### Create a District
```bash
curl -X POST "http://localhost:8000/api/admin/regions/districts" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "region_id": 1,
    "name_uz_latin": "Yunusobod",
    "name_uz_cyrillic": "Юнусобод",
    "name_russian": "Юнусабад"
  }'
```

#### Create District Pricing
```bash
curl -X POST "http://localhost:8000/api/admin/regions/district-pricing" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "from_district_id": 1,
    "to_district_id": 2,
    "service_type": "taxi",
    "base_price": "15000.00",
    "front_seat_price": "14000.00",
    "back_seat_price": "16000.00",
    "discount_1_passenger": "10.00",
    "discount_2_passengers": "15.00",
    "discount_3_passengers": "20.00",
    "discount_full_car": "25.00"
  }'
```

#### View Balance History
```bash
curl -X GET "http://localhost:8000/api/admin/drivers/balance/history" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

#### Get All Taxi Orders
```bash
curl -X GET "http://localhost:8000/api/admin/orders/taxi" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

#### Update a Taxi Order
```bash
curl -X PUT "http://localhost:8000/api/admin/orders/taxi/1" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "passengers": 3,
    "note": "Updated by admin"
  }'
```

## Common Issues and Solutions

### Issue: Migration fails
**Solution:** Make sure you have the latest code and your database connection is properly configured in `app/config.py`

### Issue: 401 Unauthorized
**Solution:** Ensure you're using a valid admin token and the user has ADMIN or SUPERADMIN role

### Issue: District pricing not being used
**Solution:** Make sure both `from_district_id` and `to_district_id` are provided when creating orders. The system will fall back to region pricing if districts are not specified.

### Issue: Cannot delete order
**Solution:** Orders must be in CANCELLED or PENDING status before deletion. Cancel the order first, then delete.

## New Database Schema

### district_pricing Table
```sql
CREATE TABLE district_pricing (
    id SERIAL PRIMARY KEY,
    from_district_id INTEGER NOT NULL REFERENCES districts(id),
    to_district_id INTEGER NOT NULL REFERENCES districts(id),
    service_type VARCHAR(20) NOT NULL,
    base_price NUMERIC(10, 2) NOT NULL,
    front_seat_price NUMERIC(10, 2),
    back_seat_price NUMERIC(10, 2),
    discount_1_passenger NUMERIC(5, 2) DEFAULT 0.00,
    discount_2_passengers NUMERIC(5, 2) DEFAULT 0.00,
    discount_3_passengers NUMERIC(5, 2) DEFAULT 0.00,
    discount_full_car NUMERIC(5, 2) DEFAULT 0.00,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE
);
```

## API Endpoints Summary

### Regions & Districts
- `POST /api/admin/regions/` - Create region
- `PUT /api/admin/regions/{id}` - Update region
- `DELETE /api/admin/regions/{id}` - Delete region
- `POST /api/admin/regions/districts` - Create district
- `PUT /api/admin/regions/districts/{id}` - Update district
- `DELETE /api/admin/regions/districts/{id}` - Delete district

### District Pricing
- `POST /api/admin/regions/district-pricing` - Create
- `PUT /api/admin/regions/district-pricing/{id}` - Update
- `GET /api/admin/regions/district-pricing` - Get all
- `DELETE /api/admin/regions/district-pricing/{id}` - Delete

### Taxi Orders (Admin)
- `GET /api/admin/orders/taxi` - List all
- `GET /api/admin/orders/taxi/{id}` - Get one
- `PUT /api/admin/orders/taxi/{id}` - Update
- `POST /api/admin/orders/taxi/{id}/cancel` - Cancel
- `DELETE /api/admin/orders/taxi/{id}` - Delete

### Delivery Orders (Admin)
- `GET /api/admin/orders/delivery` - List all
- `GET /api/admin/orders/delivery/{id}` - Get one
- `PUT /api/admin/orders/delivery/{id}` - Update
- `POST /api/admin/orders/delivery/{id}/cancel` - Cancel
- `DELETE /api/admin/orders/delivery/{id}` - Delete

### Balance History
- `GET /api/admin/drivers/balance/history` - Get transaction history

## Next Steps

1. Review the full documentation in `NEW_FEATURES.md`
2. Run the test suite to ensure everything works
3. Test the API endpoints using Swagger UI or Postman
4. Set up proper region, district, and pricing configurations for your service area
5. Train your admin users on the new features

## Support

For issues or questions:
1. Check the `NEW_FEATURES.md` documentation
2. Review test files for usage examples
3. Check API documentation at `/docs`
4. Review error messages in server logs
