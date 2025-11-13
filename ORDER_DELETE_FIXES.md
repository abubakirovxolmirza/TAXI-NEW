# Order Deletion Fixes and Enhancements

## Summary
Fixed authorization issues with order deletion and added bulk delete functionality for both delivery orders and taxi orders.

## Changes Made

### 1. Fixed Authorization Issue
**Problem:** Only order owners could delete orders, even admin and superadmin users were blocked.

**Solution:** Updated authorization logic in both endpoints to allow:
- ✅ Order owners (users who created the order)
- ✅ Admin users
- ✅ Super admin users

### 2. Added Bulk Delete Functionality
Created new endpoints that accept a list of order IDs for bulk deletion operations.

### 3. Fixed Route Ordering Issue
**Problem:** The `/delete-all` endpoint was returning a 422 error because FastAPI was matching it with the `/{order_id}` route first.

**Solution:** Moved the `/delete-all` endpoint definition **before** the `/{order_id}` endpoint so specific routes are matched before path parameters. This is a critical FastAPI routing best practice.

**Route Order (Correct):**
1. `/delete-all` ✅ (specific route - matches first)
2. `/{order_id}` (path parameter - matches after)

---

## API Endpoints

### Delivery Orders

#### Delete Single Order (Updated)
**Endpoint:** `DELETE /api/delivery-orders/{order_id}`

**Authorization:** 
- Order owner, admin, or superadmin

**Restrictions:**
- Only cancelled or completed orders can be deleted

**Response:**
```json
{
  "message": "Order deleted successfully",
  "order_id": 123
}
```

#### Bulk Delete Orders (New)
**Endpoint:** `POST /api/delivery-orders/bulk-delete`

**Authorization:**
- Order owner (for their own orders), admin, or superadmin

**Request Body:**
```json
{
  "order_ids": [1, 2, 3, 4, 5]
}
```

**Response:**
```json
{
  "message": "Successfully deleted 3 order(s)",
  "deleted_orders": [1, 3, 5],
  "failed_orders": [
    {
      "order_id": 2,
      "reason": "Only cancelled or completed orders can be deleted"
    },
    {
      "order_id": 4,
      "reason": "Order not found"
    }
  ],
  "total_requested": 5,
  "total_deleted": 3,
  "total_failed": 2
}
```

#### Delete All Orders (New)
**Endpoint:** `DELETE /api/delivery-orders/delete-all`

**Authorization:**
- ⚠️ Admin or superadmin ONLY

**Description:**
Deletes ALL delivery orders in the system, regardless of status. This is a powerful operation that should be used with caution.

**Response:**
```json
{
  "message": "Successfully deleted all delivery orders",
  "total_deleted": 150
}
```

**If no orders exist:**
```json
{
  "message": "No orders to delete",
  "total_deleted": 0
}
```

---

### Taxi Orders

#### Delete Single Order (Updated)
**Endpoint:** `DELETE /api/taxi-orders/{order_id}`

**Authorization:** 
- Order owner, admin, or superadmin

**Restrictions:**
- Only cancelled or completed orders can be deleted

**Response:**
```json
{
  "message": "Order deleted successfully",
  "order_id": 123
}
```

#### Bulk Delete Orders (New)
**Endpoint:** `POST /api/taxi-orders/bulk-delete`

**Authorization:**
- Order owner (for their own orders), admin, or superadmin

**Request Body:**
```json
{
  "order_ids": [1, 2, 3, 4, 5]
}
```

**Response:**
```json
{
  "message": "Successfully deleted 3 order(s)",
  "deleted_orders": [1, 3, 5],
  "failed_orders": [
    {
      "order_id": 2,
      "reason": "Only cancelled or completed orders can be deleted"
    },
    {
      "order_id": 4,
      "reason": "Order not found"
    }
  ],
  "total_requested": 5,
  "total_deleted": 3,
  "total_failed": 2
}
```

#### Delete All Orders (New)
**Endpoint:** `DELETE /api/taxi-orders/delete-all`

**Authorization:**
- ⚠️ Admin or superadmin ONLY

**Description:**
Deletes ALL taxi orders in the system, regardless of status. This is a powerful operation that should be used with caution.

**Response:**
```json
{
  "message": "Successfully deleted all taxi orders",
  "total_deleted": 200
}
```

**If no orders exist:**
```json
{
  "message": "No orders to delete",
  "total_deleted": 0
}
```

---

## Files Modified

1. **`app/schemas.py`**
   - Added `BulkDeleteRequest` schema for bulk delete operations
   
2. **`app/routers/delivery_orders.py`**
   - Updated imports to include `UserRole` and `BulkDeleteRequest`
   - Modified `delete_delivery_order()` to allow admin/superadmin access
   - Added `bulk_delete_delivery_orders()` endpoint

3. **`app/routers/taxi_orders.py`**
   - Updated imports to include `UserRole` and `BulkDeleteRequest`
   - Modified `delete_taxi_order()` to allow admin/superadmin access
   - Added `bulk_delete_taxi_orders()` endpoint

---

## Testing

### Test Single Delete (as Admin/Superadmin)
```bash
# Delete a delivery order
curl -X DELETE "http://localhost:8000/api/delivery-orders/1" \
  -H "Authorization: Bearer YOUR_ADMIN_TOKEN"

# Delete a taxi order
curl -X DELETE "http://localhost:8000/api/taxi-orders/1" \
  -H "Authorization: Bearer YOUR_ADMIN_TOKEN"
```

### Test Bulk Delete
```bash
# Bulk delete delivery orders
curl -X POST "http://localhost:8000/api/delivery-orders/bulk-delete" \
  -H "Authorization: Bearer YOUR_ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"order_ids": [1, 2, 3, 4, 5]}'

# Bulk delete taxi orders
curl -X POST "http://localhost:8000/api/taxi-orders/bulk-delete" \
  -H "Authorization: Bearer YOUR_ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"order_ids": [1, 2, 3, 4, 5]}'
```

### Test Delete All (⚠️ Use with Caution!)
```bash
# Delete ALL delivery orders
curl -X DELETE "http://localhost:8000/api/delivery-orders/delete-all" \
  -H "Authorization: Bearer YOUR_ADMIN_TOKEN"

# Delete ALL taxi orders
curl -X DELETE "http://localhost:8000/api/taxi-orders/delete-all" \
  -H "Authorization: Bearer YOUR_ADMIN_TOKEN"
```

---

## Important Notes

1. **Order Status Requirement (Single & Bulk Delete):** 
   - Single delete and bulk delete operations only work for orders with status:
     - `CANCELLED`
     - `COMPLETED`
   - The "delete all" endpoint deletes orders regardless of status

2. **Authorization Logic:**
   - Regular users can only delete their own orders (single or bulk)
   - Admin and superadmin can delete any orders (single or bulk)
   - **Delete all** endpoint is restricted to admin/superadmin ONLY
   - All deletions (except delete-all) still respect the status requirement

3. **Bulk Delete Behavior:**
   - Continues processing all IDs even if some fail
   - Returns detailed information about successes and failures
   - Commits all successful deletions in a single transaction

4. **Delete All Endpoint:**
   - ⚠️ **DANGEROUS OPERATION** - Deletes ALL orders without status checks
   - Only accessible to admin and superadmin roles
   - Cannot be undone
   - Use only for maintenance or testing purposes
   - Returns total count of deleted orders

5. **Error Handling:**
   - Individual order failures don't stop the entire bulk operation
   - Each failed order includes the reason for failure
   - The response clearly indicates which orders were deleted and which failed
