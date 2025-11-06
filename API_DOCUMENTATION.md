# 🚕 Taxi Service API Documentation

**Version:** 1.0.0  
**Base URL:** `http://164.90.229.192:8000`  
**API Documentation:** `http://164.90.229.192:8000/docs`

---

## 📋 Table of Contents

1. [Authentication](#authentication)
2. [User Management](#user-management)
3. [Driver Operations](#driver-operations)
4. [Taxi Orders](#taxi-orders)
5. [Delivery Orders](#delivery-orders)
6. [Admin Operations](#admin-operations)
7. [Regions & Districts](#regions--districts)
8. [Ratings & Reviews](#ratings--reviews)
9. [Notifications](#notifications)
10. [Error Handling](#error-handling)

---

## 🔐 Authentication

All protected endpoints require a JWT token in the Authorization header:
```
Authorization: Bearer <your_jwt_token>
```

### Register New User

**Endpoint:** `POST /auth/register`

**Request Body:**
```json
{
  "telephone": "+998901234567",
  "name": "John Doe",
  "password": "securePassword123",
  "language": "uz_latin"
}
```

**Parameters:**
- `telephone` (string, required): Phone number with country code
- `name` (string, required): Full name
- `password` (string, required): Minimum 6 characters
- `language` (string, optional): `uz_latin`, `uz_cyrillic`, or `russian` (default: `uz_latin`)

**Response:** `201 Created`
```json
{
  "id": 1,
  "telephone": "+998901234567",
  "name": "John Doe",
  "role": "user",
  "language": "uz_latin",
  "is_active": true,
  "created_at": "2025-11-06T12:00:00Z"
}
```

---

### Login

**Endpoint:** `POST /auth/login`

**Request Body:**
```json
{
  "telephone": "+998901234567",
  "password": "securePassword123"
}
```

**Response:** `200 OK`
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "user": {
    "id": 1,
    "telephone": "+998901234567",
    "name": "John Doe",
    "role": "user"
  }
}
```

**Save the `access_token` for subsequent requests!**

---

### Get Current User Profile

**Endpoint:** `GET /auth/me`

**Headers:**
```
Authorization: Bearer <token>
```

**Response:** `200 OK`
```json
{
  "id": 1,
  "telephone": "+998901234567",
  "name": "John Doe",
  "role": "user",
  "language": "uz_latin",
  "profile_picture": null,
  "telegram_chat_id": null,
  "is_active": true
}
```

---

### Update Profile

**Endpoint:** `PUT /auth/profile`

**Headers:**
```
Authorization: Bearer <token>
```

**Request Body:**
```json
{
  "name": "John Updated",
  "language": "russian"
}
```

**Response:** `200 OK`

---

### Upload Profile Picture

**Endpoint:** `POST /auth/profile-picture`

**Headers:**
```
Authorization: Bearer <token>
Content-Type: multipart/form-data
```

**Form Data:**
- `file`: Image file (PNG, JPG, JPEG - max 5MB)

**Response:** `200 OK`
```json
{
  "message": "Profile picture uploaded successfully",
  "file_path": "uploads/profiles/user_1_1699276800.jpg"
}
```

---

### Change Password

**Endpoint:** `PUT /auth/change-password`

**Headers:**
```
Authorization: Bearer <token>
```

**Request Body:**
```json
{
  "old_password": "oldPassword123",
  "new_password": "newSecurePassword456"
}
```

**Response:** `200 OK`

---

## 👨‍✈️ Driver Operations

### Apply as Driver

**Endpoint:** `POST /driver/apply`

**Headers:**
```
Authorization: Bearer <token>
```

**Request Body (multipart/form-data):**
```
full_name: John Doe Driver
telephone: +998901234567
car_model: Toyota Camry 2020
car_number: 01A777AA
license_photo: <file upload>
```

**Response:** `201 Created`
```json
{
  "id": 1,
  "user_id": 1,
  "full_name": "John Doe Driver",
  "telephone": "+998901234567",
  "car_model": "Toyota Camry 2020",
  "car_number": "01A777AA",
  "license_photo": "uploads/licenses/app_1_1699276800.jpg",
  "status": "pending",
  "created_at": "2025-11-06T12:00:00Z"
}
```

---

### Get Driver Profile

**Endpoint:** `GET /driver/profile`

**Headers:**
```
Authorization: Bearer <token>
```

**Required Role:** Driver, Admin, or Superadmin

**Response:** `200 OK`
```json
{
  "id": 1,
  "user_id": 1,
  "full_name": "John Doe Driver",
  "car_model": "Toyota Camry 2020",
  "car_number": "01A777AA",
  "rating": 4.85,
  "balance": 150000.00,
  "is_blocked": false,
  "total_orders": 45,
  "completed_orders": 42
}
```

---

### Get Available Orders

**Endpoint:** `GET /driver/available-orders`

**Headers:**
```
Authorization: Bearer <token>
```

**Query Parameters:**
- `order_type` (optional): `taxi` or `delivery`
- `skip` (optional): Pagination offset (default: 0)
- `limit` (optional): Results per page (default: 20)

**Response:** `200 OK`
```json
[
  {
    "id": 10,
    "type": "taxi",
    "username": "Customer Name",
    "telephone": "+998901111111",
    "from_region": "Toshkent shahri",
    "from_district": "Yunusobod",
    "to_region": "Samarqand",
    "to_district": "Samarqand shahri",
    "passengers": 3,
    "date": "07.11.2025",
    "time_start": "14:00",
    "time_end": "15:00",
    "price": 180000.00,
    "status": "pending"
  }
]
```

---

### Accept Order

**Endpoint:** `POST /driver/accept-order/{order_id}`

**Headers:**
```
Authorization: Bearer <token>
```

**Path Parameters:**
- `order_id`: ID of the order to accept

**Query Parameters:**
- `order_type`: `taxi` or `delivery`

**Response:** `200 OK`
```json
{
  "message": "Order accepted successfully",
  "order_id": 10,
  "customer_name": "Customer Name",
  "customer_phone": "+998901111111"
}
```

**Notes:**
- Driver must accept within 5 minutes of order creation
- Only one driver can accept an order
- Driver balance is deducted upon acceptance

---

### Complete Order

**Endpoint:** `POST /driver/complete-order/{order_id}`

**Headers:**
```
Authorization: Bearer <token>
```

**Path Parameters:**
- `order_id`: ID of the order to complete

**Query Parameters:**
- `order_type`: `taxi` or `delivery`

**Response:** `200 OK`
```json
{
  "message": "Order completed successfully",
  "order_id": 10
}
```

---

### Get Driver Statistics

**Endpoint:** `GET /driver/statistics`

**Headers:**
```
Authorization: Bearer <token>
```

**Response:** `200 OK`
```json
{
  "total_orders": 45,
  "completed_orders": 42,
  "cancelled_orders": 3,
  "total_earnings": 4500000.00,
  "current_balance": 150000.00,
  "average_rating": 4.85,
  "daily_statistics": {
    "today_orders": 3,
    "today_earnings": 250000.00
  },
  "monthly_statistics": {
    "this_month_orders": 15,
    "this_month_earnings": 1500000.00
  }
}
```

---

## 🚖 Taxi Orders

### Create Taxi Order

**Endpoint:** `POST /taxi-orders/`

**Headers:**
```
Authorization: Bearer <token>
```

**Request Body:**
```json
{
  "username": "John Doe",
  "telephone": "+998901234567",
  "from_region_id": 1,
  "from_district_id": 1,
  "to_region_id": 2,
  "to_district_id": 5,
  "passengers": 3,
  "date": "07.11.2025",
  "time_start": "14:00",
  "time_end": "15:00",
  "note": "Please call 5 minutes before arrival"
}
```

**Parameters:**
- `username` (string): Passenger name
- `telephone` (string): Contact phone
- `from_region_id` (int): Departure region ID
- `from_district_id` (int): Departure district ID
- `to_region_id` (int): Destination region ID
- `to_district_id` (int): Destination district ID
- `passengers` (int): Number of passengers (1-4)
- `date` (string): Format DD.MM.YYYY
- `time_start` (string): Start time HH:MM
- `time_end` (string): End time HH:MM
- `note` (string, optional): Additional notes

**Response:** `201 Created`
```json
{
  "id": 10,
  "username": "John Doe",
  "telephone": "+998901234567",
  "from_region": "Toshkent shahri",
  "from_district": "Yunusobod",
  "to_region": "Samarqand",
  "to_district": "Samarqand shahri",
  "passengers": 3,
  "date": "07.11.2025",
  "time_start": "14:00",
  "time_end": "15:00",
  "price": 180000.00,
  "status": "pending",
  "note": "Please call 5 minutes before arrival",
  "created_at": "2025-11-06T12:00:00Z"
}
```

**Pricing Logic:**
- Base price retrieved from pricing table
- Discounts applied based on number of passengers:
  - 1 passenger: 5% discount
  - 2 passengers: 10% discount
  - 3 passengers: 15% discount
  - 4 passengers (full car): 20% discount

---

### Get My Orders

**Endpoint:** `GET /taxi-orders/my-orders`

**Headers:**
```
Authorization: Bearer <token>
```

**Query Parameters:**
- `status` (optional): Filter by status (`pending`, `accepted`, `completed`, `cancelled`)
- `skip` (optional): Pagination offset (default: 0)
- `limit` (optional): Results per page (default: 20)

**Response:** `200 OK`
```json
[
  {
    "id": 10,
    "username": "John Doe",
    "from_region": "Toshkent shahri",
    "to_region": "Samarqand",
    "status": "accepted",
    "driver": {
      "name": "Driver Name",
      "car_model": "Toyota Camry",
      "car_number": "01A777AA",
      "phone": "+998909999999"
    },
    "price": 180000.00,
    "date": "07.11.2025",
    "time_start": "14:00"
  }
]
```

---

### Get Order Details

**Endpoint:** `GET /taxi-orders/{order_id}`

**Headers:**
```
Authorization: Bearer <token>
```

**Response:** `200 OK` (Full order details)

---

### Cancel Order

**Endpoint:** `POST /taxi-orders/{order_id}/cancel`

**Headers:**
```
Authorization: Bearer <token>
```

**Request Body:**
```json
{
  "reason": "Change of plans"
}
```

**Response:** `200 OK`
```json
{
  "message": "Order cancelled successfully",
  "order_id": 10
}
```

**Rules:**
- Can only cancel pending orders
- Cannot cancel after driver accepts (unless within 5 minutes)

---

## 📦 Delivery Orders

### Create Delivery Order

**Endpoint:** `POST /delivery-orders/`

**Headers:**
```
Authorization: Bearer <token>
```

**Request Body:**
```json
{
  "username": "John Doe",
  "sender_telephone": "+998901234567",
  "receiver_telephone": "+998909876543",
  "from_region_id": 1,
  "from_district_id": 1,
  "to_region_id": 2,
  "to_district_id": 5,
  "item_type": "document",
  "date": "07.11.2025",
  "time_start": "14:00",
  "time_end": "18:00",
  "note": "Fragile - handle with care"
}
```

**Parameters:**
- `item_type`: `document`, `box`, `luggage`, `valuable`, or `other`
- Other fields similar to taxi orders

**Response:** `201 Created`

---

### Get My Delivery Orders

**Endpoint:** `GET /delivery-orders/my-orders`

**Headers:**
```
Authorization: Bearer <token>
```

**Response:** `200 OK` (Similar to taxi orders)

---

## 👨‍💼 Admin Operations

### Review Driver Application

**Endpoint:** `POST /admin/applications/{application_id}/review`

**Headers:**
```
Authorization: Bearer <token>
```

**Required Role:** Admin or Superadmin

**Request Body:**
```json
{
  "action": "approve"
}
```

OR

```json
{
  "action": "reject",
  "reason": "Incomplete documentation"
}
```

**Response:** `200 OK`
```json
{
  "message": "Application approved. Driver account created.",
  "driver_id": 5,
  "application_id": 10
}
```

---

### Get Pending Applications

**Endpoint:** `GET /admin/applications`

**Headers:**
```
Authorization: Bearer <token>
```

**Query Parameters:**
- `status` (optional): `pending`, `approved`, `rejected`
- `skip`, `limit`: Pagination

**Response:** `200 OK`
```json
[
  {
    "id": 10,
    "user_id": 5,
    "full_name": "New Driver",
    "telephone": "+998905555555",
    "car_model": "Chevrolet Lacetti",
    "car_number": "01B123CD",
    "license_photo": "uploads/licenses/app_10.jpg",
    "status": "pending",
    "created_at": "2025-11-06T10:00:00Z"
  }
]
```

---

### Get All Drivers

**Endpoint:** `GET /admin/drivers`

**Headers:**
```
Authorization: Bearer <token>
```

**Query Parameters:**
- `is_blocked` (optional): true/false
- `skip`, `limit`: Pagination

**Response:** `200 OK`

---

### Block Driver

**Endpoint:** `POST /admin/drivers/{driver_id}/block`

**Headers:**
```
Authorization: Bearer <token>
```

**Request Body:**
```json
{
  "reason": "Multiple customer complaints"
}
```

**Response:** `200 OK`

---

### Unblock Driver

**Endpoint:** `POST /admin/drivers/{driver_id}/unblock`

**Headers:**
```
Authorization: Bearer <token>
```

**Response:** `200 OK`

---

### Add Driver Balance

**Endpoint:** `POST /admin/drivers/{driver_id}/add-balance`

**Headers:**
```
Authorization: Bearer <token>
```

**Request Body:**
```json
{
  "amount": 50000.00,
  "description": "Monthly bonus"
}
```

**Response:** `200 OK`
```json
{
  "message": "Balance added successfully",
  "new_balance": 200000.00,
  "transaction_id": 15
}
```

---

### Broadcast Message

**Endpoint:** `POST /admin/broadcast`

**Headers:**
```
Authorization: Bearer <token>
```

**Request Body:**
```json
{
  "title": "System Maintenance",
  "message": "The system will be under maintenance on Sunday",
  "target": "all"
}
```

**Parameters:**
- `target`: `all`, `users`, `drivers`, or `admins`

**Response:** `200 OK`
```json
{
  "message": "Broadcast sent successfully",
  "recipients_count": 150
}
```

---

### Get Order Statistics

**Endpoint:** `GET /admin/statistics`

**Headers:**
```
Authorization: Bearer <token>
```

**Query Parameters:**
- `start_date` (optional): YYYY-MM-DD
- `end_date` (optional): YYYY-MM-DD

**Response:** `200 OK`
```json
{
  "total_orders": 500,
  "taxi_orders": 350,
  "delivery_orders": 150,
  "pending_orders": 10,
  "active_orders": 25,
  "completed_orders": 450,
  "cancelled_orders": 15,
  "total_revenue": 45000000.00,
  "active_drivers": 50,
  "pending_applications": 5
}
```

---

## 🗺️ Regions & Districts

### Get All Regions

**Endpoint:** `GET /regions/`

**Response:** `200 OK`
```json
[
  {
    "id": 1,
    "name_uz_latin": "Toshkent shahri",
    "name_uz_cyrillic": "Тошкент шаҳри",
    "name_russian": "город Ташкент",
    "is_active": true
  }
]
```

---

### Get Districts by Region

**Endpoint:** `GET /regions/{region_id}/districts`

**Response:** `200 OK`
```json
[
  {
    "id": 1,
    "region_id": 1,
    "name_uz_latin": "Yunusobod",
    "name_uz_cyrillic": "Юнусобод",
    "name_russian": "Юнусабад",
    "is_active": true
  }
]
```

---

### Calculate Price

**Endpoint:** `GET /regions/calculate-price`

**Query Parameters:**
- `from_region_id`: Source region ID
- `to_region_id`: Destination region ID
- `service_type`: `taxi` or `delivery`
- `passengers` (optional): Number of passengers (1-4) for taxi

**Response:** `200 OK`
```json
{
  "base_price": 200000.00,
  "discount_percentage": 15.00,
  "final_price": 170000.00,
  "service_type": "taxi",
  "passengers": 3
}
```

---

## ⭐ Ratings & Reviews

### Rate Driver

**Endpoint:** `POST /ratings/`

**Headers:**
```
Authorization: Bearer <token>
```

**Request Body:**
```json
{
  "driver_id": 5,
  "taxi_order_id": 10,
  "rating": 5,
  "comment": "Excellent service, very professional driver"
}
```

**Parameters:**
- `rating`: Integer 1-5
- `taxi_order_id` OR `delivery_order_id`: One is required
- `comment` (optional): Review text

**Response:** `201 Created`

**Rules:**
- Can only rate completed orders
- One rating per order
- Must be the customer who placed the order

---

### Get Driver Ratings

**Endpoint:** `GET /ratings/driver/{driver_id}`

**Query Parameters:**
- `skip`, `limit`: Pagination

**Response:** `200 OK`
```json
{
  "average_rating": 4.85,
  "total_ratings": 42,
  "ratings": [
    {
      "id": 15,
      "rating": 5,
      "comment": "Excellent service",
      "user_name": "John Doe",
      "created_at": "2025-11-05T14:00:00Z"
    }
  ]
}
```

---

## 🔔 Notifications

### Get My Notifications

**Endpoint:** `GET /notifications/`

**Headers:**
```
Authorization: Bearer <token>
```

**Query Parameters:**
- `is_read` (optional): true/false
- `skip`, `limit`: Pagination

**Response:** `200 OK`
```json
[
  {
    "id": 20,
    "title": "Order Accepted",
    "message": "Your taxi order #10 has been accepted by driver",
    "notification_type": "order_update",
    "is_read": false,
    "created_at": "2025-11-06T12:00:00Z"
  }
]
```

---

### Mark Notification as Read

**Endpoint:** `PUT /notifications/{notification_id}/read`

**Headers:**
```
Authorization: Bearer <token>
```

**Response:** `200 OK`

---

### Mark All as Read

**Endpoint:** `PUT /notifications/mark-all-read`

**Headers:**
```
Authorization: Bearer <token>
```

**Response:** `200 OK`

---

## ❌ Error Handling

### Error Response Format

All errors follow this structure:

```json
{
  "detail": "Error message description"
}
```

### HTTP Status Codes

| Code | Meaning | Description |
|------|---------|-------------|
| 200 | OK | Request successful |
| 201 | Created | Resource created successfully |
| 400 | Bad Request | Invalid request data |
| 401 | Unauthorized | Missing or invalid authentication |
| 403 | Forbidden | Insufficient permissions |
| 404 | Not Found | Resource not found |
| 422 | Unprocessable Entity | Validation error |
| 500 | Internal Server Error | Server error |

### Common Error Examples

**401 Unauthorized:**
```json
{
  "detail": "Could not validate credentials"
}
```

**403 Forbidden:**
```json
{
  "detail": "Not authorized. Admin access required."
}
```

**404 Not Found:**
```json
{
  "detail": "Order not found"
}
```

**422 Validation Error:**
```json
{
  "detail": [
    {
      "loc": ["body", "telephone"],
      "msg": "field required",
      "type": "value_error.missing"
    }
  ]
}
```

---

## 📝 Complete Workflow Examples

### Example 1: Creating a Driver Account

1. **Register as user:**
```bash
POST /auth/register
{
  "telephone": "+998901234567",
  "name": "John Driver",
  "password": "password123"
}
```

2. **Login:**
```bash
POST /auth/login
# Save the token
```

3. **Apply as driver:**
```bash
POST /driver/apply
# Upload license photo and car details
```

4. **Admin approves application:**
```bash
POST /admin/applications/{id}/review
{
  "action": "approve"
}
```

5. **Driver can now accept orders!**

---

### Example 2: Booking a Taxi

1. **Login as user**
2. **Get available regions:**
```bash
GET /regions/
```

3. **Get districts:**
```bash
GET /regions/1/districts
```

4. **Calculate price:**
```bash
GET /regions/calculate-price?from_region_id=1&to_region_id=2&service_type=taxi&passengers=3
```

5. **Create order:**
```bash
POST /taxi-orders/
{
  "from_region_id": 1,
  "to_region_id": 2,
  "passengers": 3,
  ...
}
```

6. **Track order status:**
```bash
GET /taxi-orders/my-orders
```

7. **After completion, rate driver:**
```bash
POST /ratings/
{
  "driver_id": 5,
  "taxi_order_id": 10,
  "rating": 5
}
```

---

## 🔗 Additional Resources

- **Interactive API Docs:** http://164.90.229.192:8000/docs
- **Alternative Docs (ReDoc):** http://164.90.229.192:8000/redoc
- **Health Check:** http://164.90.229.192:8000/health

---

## 📞 Support

For issues or questions, please submit feedback through:
- Telegram User Bot
- Admin Panel

---

**Last Updated:** November 6, 2025
