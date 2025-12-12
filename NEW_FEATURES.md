# New Features Implementation

This document describes all the new features that have been added to the Taxi Service API.

## 1. Region and District Management with Pricing

### Endpoints

#### Create Region (Admin Only)
```
POST /api/admin/regions/
Authorization: Bearer <admin_token>

Body:
{
    "name_uz_latin": "Toshkent",
    "name_uz_cyrillic": "Тошкент",
    "name_russian": "Ташкент"
}
```

#### Update Region (Admin Only)
```
PUT /api/admin/regions/{region_id}
Authorization: Bearer <admin_token>

Body:
{
    "name_uz_latin": "Toshkent Shahri",
    "name_uz_cyrillic": "Тошкент Шаҳри",
    "name_russian": "Город Ташкент"
}
```

#### Delete Region (Admin Only)
```
DELETE /api/admin/regions/{region_id}
Authorization: Bearer <admin_token>
```

#### Create District (Admin Only)
```
POST /api/admin/regions/districts
Authorization: Bearer <admin_token>

Body:
{
    "region_id": 1,
    "name_uz_latin": "Yunusobod",
    "name_uz_cyrillic": "Юнусобод",
    "name_russian": "Юнусабад"
}
```

#### Update District (Admin Only)
```
PUT /api/admin/regions/districts/{district_id}
Authorization: Bearer <admin_token>

Body:
{
    "region_id": 1,
    "name_uz_latin": "Yunusobod tumani",
    "name_uz_cyrillic": "Юнусобод тумани",
    "name_russian": "Юнусабадский район"
}
```

#### Delete District (Admin Only)
```
DELETE /api/admin/regions/districts/{district_id}
Authorization: Bearer <admin_token>
```

### District-Level Pricing

#### Create District Pricing (Admin Only)
```
POST /api/admin/regions/district-pricing
Authorization: Bearer <admin_token>

Body:
{
    "from_district_id": 1,
    "to_district_id": 2,
    "service_type": "taxi",  // or "delivery"
    "base_price": "15000.00",
    "front_seat_price": "14000.00",
    "back_seat_price": "16000.00",
    "discount_1_passenger": "10.00",
    "discount_2_passengers": "15.00",
    "discount_3_passengers": "20.00",
    "discount_full_car": "25.00"
}
```

#### Update District Pricing (Admin Only)
```
PUT /api/admin/regions/district-pricing/{pricing_id}
Authorization: Bearer <admin_token>

Body:
{
    "base_price": "18000.00",
    "discount_1_passenger": "12.00"
}
```

#### Get All District Pricing (Admin Only)
```
GET /api/admin/regions/district-pricing
Authorization: Bearer <admin_token>
```

#### Delete District Pricing (Admin Only)
```
DELETE /api/admin/regions/district-pricing/{pricing_id}
Authorization: Bearer <admin_token>
```

### Pricing Priority
When creating orders, the system follows this priority:
1. **District-level pricing** (if both from_district_id and to_district_id are provided)
2. **Region-level pricing** (fallback if no district pricing exists)
3. **Default pricing** (if no pricing configuration exists)

## 2. Full CRUD for Taxi Orders (Admin Only)

### View All Taxi Orders
```
GET /api/admin/orders/taxi
Authorization: Bearer <admin_token>

Query Parameters:
- status: Optional filter by OrderStatus (pending, accepted, completed, cancelled)
- limit: Number of orders to return (default: 100)
- offset: Offset for pagination (default: 0)
```

### View Specific Taxi Order
```
GET /api/admin/orders/taxi/{order_id}
Authorization: Bearer <admin_token>
```

Returns all order details including:
- User information
- Driver information (if assigned)
- Route (regions and districts)
- Pricing breakdown (price, service_fee, driver_earnings)
- Pickup coordinates and address
- Passenger details (count, gender, seat_type)
- Schedule (date, time_start, time_end, scheduled_datetime)
- Status and timestamps
- Notes and cancellation reason

### Update Taxi Order
```
PUT /api/admin/orders/taxi/{order_id}
Authorization: Bearer <admin_token>

Body (all fields optional):
{
    "username": "Updated Name",
    "telephone": "998901234567",
    "passengers": 3,
    "price": "60000.00",
    "status": "completed",
    "note": "Updated by admin"
}
```

### Cancel Taxi Order
```
POST /api/admin/orders/taxi/{order_id}/cancel
Authorization: Bearer <admin_token>

Body:
{
    "order_id": 1,
    "order_type": "taxi",
    "cancellation_reason": "Customer request"
}
```

### Delete Taxi Order
```
DELETE /api/admin/orders/taxi/{order_id}
Authorization: Bearer <admin_token>
```

**Note:** Can only delete orders with status `CANCELLED` or `PENDING`

## 3. Full CRUD for Delivery Orders (Admin Only)

### View All Delivery Orders
```
GET /api/admin/orders/delivery
Authorization: Bearer <admin_token>

Query Parameters:
- status: Optional filter by OrderStatus
- limit: Number of orders to return (default: 100)
- offset: Offset for pagination (default: 0)
```

### View Specific Delivery Order
```
GET /api/admin/orders/delivery/{order_id}
Authorization: Bearer <admin_token>
```

Returns all order details including:
- User information
- Driver information (if assigned)
- Sender and receiver phone numbers
- Route (regions and districts)
- Pickup and dropoff coordinates/addresses
- Item type
- Pricing breakdown
- Schedule
- Status and timestamps

### Update Delivery Order
```
PUT /api/admin/orders/delivery/{order_id}
Authorization: Bearer <admin_token>

Body (all fields optional):
{
    "receiver_telephone": "998909999999",
    "item_type": "document",
    "price": "35000.00",
    "note": "Updated delivery details"
}
```

### Cancel Delivery Order
```
POST /api/admin/orders/delivery/{order_id}/cancel
Authorization: Bearer <admin_token>

Body:
{
    "order_id": 1,
    "order_type": "delivery",
    "cancellation_reason": "Item not available"
}
```

### Delete Delivery Order
```
DELETE /api/admin/orders/delivery/{order_id}
Authorization: Bearer <admin_token>
```

**Note:** Can only delete orders with status `CANCELLED` or `PENDING`

## 4. Balance History Tracking

### View Balance Transaction History
```
GET /api/admin/drivers/balance/history
Authorization: Bearer <admin_token>

Query Parameters:
- driver_id: Optional filter by specific driver
- transaction_type: Optional filter by type (credit, debit, refund)
- limit: Number of transactions to return (default: 100)
- offset: Offset for pagination (default: 0)
```

Response includes:
- Transaction ID
- Driver ID and name
- Amount
- Transaction type
- Description
- Admin ID and name (who added the balance)
- Timestamp (when it was added)

Example Response:
```json
{
    "total": 25,
    "transactions": [
        {
            "id": 1,
            "driver_id": 5,
            "driver_name": "John Driver",
            "amount": "50000.00",
            "transaction_type": "credit",
            "description": "Bonus payment",
            "admin_id": 2,
            "admin_name": "Admin User",
            "created_at": "2025-12-12T10:30:00Z"
        }
    ]
}
```

## 5. Updated Pricing Logic

### Taxi Orders
When creating a taxi order, pricing is now calculated with district-level support:

```python
# If district IDs are provided, use district pricing
# Otherwise, fall back to region pricing
price = calculate_taxi_price(
    db=db,
    from_region_id=order_data.from_region_id,
    to_region_id=order_data.to_region_id,
    passengers=order_data.passengers,
    seat_type=seat_type,
    from_district_id=order_data.from_district_id,  # Optional
    to_district_id=order_data.to_district_id        # Optional
)
```

### Delivery Orders
Similar logic for delivery orders:

```python
price = calculate_delivery_price(
    db=db,
    from_region_id=order_data.from_region_id,
    to_region_id=order_data.to_region_id,
    from_district_id=order_data.from_district_id,  # Optional
    to_district_id=order_data.to_district_id        # Optional
)
```

### Calculate Price Endpoint
Updated to support district pricing:

```
GET /api/regions/pricing/calculate
Query Parameters:
- from_region_id: Required
- to_region_id: Required
- from_district_id: Optional
- to_district_id: Optional
- service_type: taxi or delivery
- passengers: For taxi orders

Response includes pricing_level: "district", "region", or "default"
```

## 6. Database Migrations

A new Alembic migration has been created to add the `district_pricing` table:

```bash
# Run migration
alembic upgrade head
```

Migration file: `alembic/versions/add_district_pricing.py`

## 7. Testing

Comprehensive test suites have been created:

### Run All Tests
```bash
pytest tests/test_new_features.py -v
pytest tests/test_admin_orders.py -v
```

### Test Coverage
- Region CRUD operations
- District CRUD operations
- District pricing CRUD operations
- Taxi order CRUD (admin)
- Delivery order CRUD (admin)
- Balance history tracking
- Pricing logic with district support
- Order visibility and detail completeness

## 8. Models Added/Updated

### New Models
- `DistrictPricing`: District-level pricing configuration

### Updated Models
- `BalanceTransaction`: Added better admin relationship

### New Schemas
- `DistrictPricingCreate`
- `DistrictPricingUpdate`
- `DistrictPricingResponse`
- `RegionCreateWithPricing`
- `DistrictCreateWithPricing`
- `TaxiOrderUpdate`
- `DeliveryOrderUpdate`
- `BalanceHistoryDetail`

## 9. Security

All new endpoints require admin authentication:
- `get_current_admin` dependency ensures only users with `ADMIN` or `SUPERADMIN` role can access
- JWT token-based authentication
- Proper error handling for unauthorized access

## 10. Notifications

The system automatically sends notifications when:
- Admin updates an order (notifies both user and driver)
- Admin cancels an order (notifies both user and driver)
- Admin adds balance to driver account

## 11. API Documentation

All new endpoints are automatically documented in:
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

## 12. Best Practices

### Order Management
- Always check order status before deletion
- Only delete cancelled or pending orders
- Use soft deletion (status update) instead of hard deletion when possible
- Document cancellation reasons

### Pricing
- Set district pricing for more granular control
- Region pricing acts as fallback
- Keep pricing consistent across related routes
- Document pricing changes

### Balance Management
- Always provide description when adding balance
- Monitor balance history regularly
- Filter by driver or transaction type for auditing

## Summary

All requested features have been implemented:
✅ Region and district CRUD with pricing support
✅ Full CRUD for taxi orders (admin)
✅ Full CRUD for delivery orders (admin)
✅ District-level pricing with fallback to region pricing
✅ Balance history endpoint with admin tracking
✅ Comprehensive test suite
✅ Full API documentation
