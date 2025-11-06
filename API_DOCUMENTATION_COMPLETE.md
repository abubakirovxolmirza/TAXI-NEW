# Taxi Service API - Complete Documentation

**Base URL:** `http://164.90.229.192:8000`  
**API Documentation:** `http://164.90.229.192:8000/docs`  
**Alternative Docs:** `http://164.90.229.192:8000/redoc`

---

## Table of Contents

1. [Authentication](#authentication)
2. [User Management](#user-management)
3. [Taxi Orders](#taxi-orders)
4. [Delivery Orders](#delivery-orders)
5. [Driver Operations](#driver-operations)
6. [Admin Operations](#admin-operations)
7. [Regions & Districts](#regions--districts)
8. [Ratings](#ratings)
9. [Notifications](#notifications)
10. [Feedback](#feedback)
11. [Common Response Codes](#common-response-codes)
12. [Authentication Flow](#authentication-flow)

---

## Authentication

All endpoints marked with 🔒 require authentication via JWT Bearer token.

### Headers Required for Protected Endpoints
```http
Authorization: Bearer <your_jwt_token>
```

---

## 1. Authentication

### 1.1 Register New User

**POST** `/api/auth/register`

Create a new user account.

**Request Body:**
```json
{
  "telephone": "+998901234567",
  "name": "John Doe",
  "password": "securePassword123",
  "confirm_password": "securePassword123"
}
```

**Response:** `201 Created`
```json
{
  "id": 1,
  "telephone": "+998901234567",
  "name": "John Doe",
  "role": "user",
  "language": "uz_latin",
  "profile_picture": null,
  "is_active": true,
  "created_at": "2025-11-06T12:00:00Z"
}
```

**Errors:**
- `400 Bad Request`: User already exists or passwords don't match

---

### 1.2 Login

**POST** `/api/auth/login`

Authenticate and receive access token.

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
    "role": "user",
    "language": "uz_latin",
    "profile_picture": null,
    "is_active": true,
    "created_at": "2025-11-06T12:00:00Z"
  }
}
```

**Errors:**
- `401 Unauthorized`: Invalid credentials
- `403 Forbidden`: Account is inactive

---

### 1.3 Get Current User 🔒

**GET** `/api/auth/me`

Get authenticated user's profile information.

**Response:** `200 OK`
```json
{
  "id": 1,
  "telephone": "+998901234567",
  "name": "John Doe",
  "role": "user",
  "language": "uz_latin",
  "profile_picture": null,
  "is_active": true,
  "created_at": "2025-11-06T12:00:00Z"
}
```

**Errors:**
- `401 Unauthorized`: Invalid or expired token

---

### 1.4 Update Profile 🔒

**PUT** `/api/auth/profile`

Update user profile information.

**Request Body:**
```json
{
  "name": "John Smith",
  "language": "russian",
  "profile_picture": "/uploads/profile_pictures/user_1.jpg"
}
```

**Response:** `200 OK`
```json
{
  "id": 1,
  "telephone": "+998901234567",
  "name": "John Smith",
  "role": "user",
  "language": "russian",
  "profile_picture": "/uploads/profile_pictures/user_1.jpg",
  "is_active": true,
  "created_at": "2025-11-06T12:00:00Z"
}
```

---

### 1.5 Upload Profile Picture 🔒

**POST** `/api/auth/upload-profile-picture`

Upload a profile picture (JPEG/PNG only).

**Request:** `multipart/form-data`
```
file: <image_file>
```

**Response:** `200 OK`
```json
{
  "message": "Profile picture uploaded successfully",
  "file_path": "/uploads/profile_pictures/user_1_1699012345.jpg"
}
```

**Errors:**
- `400 Bad Request`: Invalid file type

---

### 1.6 Change Password 🔒

**POST** `/api/auth/change-password`

Change user password.

**Request Body:**
```json
{
  "old_password": "currentPassword123",
  "new_password": "newSecurePassword456",
  "confirm_password": "newSecurePassword456"
}
```

**Response:** `200 OK`
```json
{
  "message": "Password changed successfully"
}
```

**Errors:**
- `400 Bad Request`: Incorrect old password or passwords don't match

---

## 2. Taxi Orders

### 2.1 Create Taxi Order 🔒

**POST** `/api/taxi-orders/`

Create a new taxi order. Price is automatically calculated.

**Request Body:**
```json
{
  "username": "John Doe",
  "telephone": "+998901234567",
  "from_region_id": 1,
  "from_district_id": 1,
  "to_region_id": 2,
  "to_district_id": 9,
  "passengers": 3,
  "date": "08.11.2025",
  "time_start": "14:00",
  "time_end": "15:00",
  "note": "Please call when you arrive"
}
```

**Response:** `201 Created`
```json
{
  "id": 1,
  "user_id": 1,
  "driver_id": null,
  "username": "John Doe",
  "telephone": "+998901234567",
  "from_region_id": 1,
  "from_district_id": 1,
  "to_region_id": 2,
  "to_district_id": 9,
  "passengers": 3,
  "date": "08.11.2025",
  "time_start": "14:00",
  "time_end": "15:00",
  "price": "42500.00",
  "note": "Please call when you arrive",
  "status": "pending",
  "cancellation_reason": null,
  "created_at": "2025-11-06T12:00:00Z",
  "accepted_at": null,
  "completed_at": null
}
```

---

### 2.2 Get My Taxi Orders 🔒

**GET** `/api/taxi-orders/`

Get all taxi orders for the authenticated user.

**Query Parameters:**
- `status_filter` (optional): Filter by status (`pending`, `accepted`, `completed`, `cancelled`)

**Response:** `200 OK`
```json
[
  {
    "id": 1,
    "user_id": 1,
    "driver_id": null,
    "username": "John Doe",
    "telephone": "+998901234567",
    "from_region_id": 1,
    "from_district_id": 1,
    "to_region_id": 2,
    "to_district_id": 9,
    "passengers": 3,
    "date": "08.11.2025",
    "time_start": "14:00",
    "time_end": "15:00",
    "price": "42500.00",
    "note": "Please call when you arrive",
    "status": "pending",
    "cancellation_reason": null,
    "created_at": "2025-11-06T12:00:00Z",
    "accepted_at": null,
    "completed_at": null
  }
]
```

---

### 2.3 Get Active Taxi Orders 🔒

**GET** `/api/taxi-orders/active`

Get all active (pending or accepted) taxi orders for authenticated user.

**Response:** `200 OK`
```json
[
  {
    "id": 1,
    "status": "accepted",
    "driver_id": 5,
    ...
  }
]
```

---

### 2.4 Get Taxi Order History 🔒

**GET** `/api/taxi-orders/history`

Get completed and cancelled taxi orders.

**Response:** `200 OK`
```json
[
  {
    "id": 1,
    "status": "completed",
    "completed_at": "2025-11-06T15:30:00Z",
    ...
  }
]
```

---

### 2.5 Get Taxi Order Details 🔒

**GET** `/api/taxi-orders/{order_id}`

Get specific taxi order details.

**Path Parameters:**
- `order_id`: Order ID

**Response:** `200 OK`
```json
{
  "id": 1,
  "user_id": 1,
  "driver_id": 5,
  "status": "accepted",
  ...
}
```

**Errors:**
- `404 Not Found`: Order doesn't exist
- `403 Forbidden`: Not authorized to view this order

---

### 2.6 Cancel Taxi Order 🔒

**POST** `/api/taxi-orders/cancel`

Cancel a pending or accepted taxi order.

**Request Body:**
```json
{
  "order_id": 1,
  "cancellation_reason": "Plans changed"
}
```

**Response:** `200 OK`
```json
{
  "id": 1,
  "status": "cancelled",
  "cancellation_reason": "Plans changed",
  "cancelled_at": "2025-11-06T13:00:00Z",
  ...
}
```

**Errors:**
- `404 Not Found`: Order doesn't exist
- `403 Forbidden`: Not authorized to cancel
- `400 Bad Request`: Order cannot be cancelled (already completed)

---

## 3. Delivery Orders

### 3.1 Create Delivery Order 🔒

**POST** `/api/delivery-orders/`

Create a new delivery order.

**Request Body:**
```json
{
  "username": "John Doe",
  "sender_telephone": "+998901234567",
  "receiver_telephone": "+998909876543",
  "from_region_id": 1,
  "from_district_id": 1,
  "to_region_id": 2,
  "to_district_id": 9,
  "item_type": "documents",
  "date": "08.11.2025",
  "time_start": "14:00",
  "time_end": "15:00",
  "note": "Fragile package"
}
```

**Item Types:**
- `documents`: Documents
- `parcel`: Parcel
- `food`: Food
- `other`: Other

**Response:** `201 Created`
```json
{
  "id": 1,
  "user_id": 1,
  "driver_id": null,
  "username": "John Doe",
  "sender_telephone": "+998901234567",
  "receiver_telephone": "+998909876543",
  "from_region_id": 1,
  "from_district_id": 1,
  "to_region_id": 2,
  "to_district_id": 9,
  "item_type": "documents",
  "date": "08.11.2025",
  "time_start": "14:00",
  "time_end": "15:00",
  "price": "25000.00",
  "note": "Fragile package",
  "status": "pending",
  "created_at": "2025-11-06T12:00:00Z",
  "accepted_at": null,
  "completed_at": null
}
```

---

### 3.2 Get My Delivery Orders 🔒

**GET** `/api/delivery-orders/`

Get all delivery orders for authenticated user.

**Query Parameters:**
- `status_filter` (optional): Filter by status

**Response:** `200 OK`
```json
[
  {
    "id": 1,
    "status": "pending",
    "item_type": "documents",
    ...
  }
]
```

---

### 3.3 Get Active Delivery Orders 🔒

**GET** `/api/delivery-orders/active`

Get active delivery orders (pending/accepted).

---

### 3.4 Get Delivery Order History 🔒

**GET** `/api/delivery-orders/history`

Get completed and cancelled delivery orders.

---

### 3.5 Get Delivery Order Details 🔒

**GET** `/api/delivery-orders/{order_id}`

Get specific delivery order details.

---

### 3.6 Cancel Delivery Order 🔒

**POST** `/api/delivery-orders/cancel`

Cancel a delivery order.

**Request Body:**
```json
{
  "order_id": 1,
  "cancellation_reason": "No longer needed"
}
```

---

## 4. Driver Operations

### 4.1 Apply as Driver 🔒

**POST** `/api/driver/apply`

Submit application to become a driver.

**Request Body:**
```json
{
  "full_name": "John Driver",
  "car_model": "Toyota Camry 2020",
  "car_number": "01A777AA",
  "license_photo": "/uploads/licenses/license_1_1699012345.jpg"
}
```

**Response:** `201 Created`
```json
{
  "id": 1,
  "user_id": 1,
  "full_name": "John Driver",
  "telephone": "+998901234567",
  "car_model": "Toyota Camry 2020",
  "car_number": "01A777AA",
  "license_photo": "/uploads/licenses/license_1_1699012345.jpg",
  "status": "pending",
  "rejection_reason": null,
  "created_at": "2025-11-06T12:00:00Z"
}
```

**Errors:**
- `400 Bad Request`: Already a driver or have pending application

---

### 4.2 Upload License Photo 🔒

**POST** `/api/driver/upload-license`

Upload driving license photo (JPEG/PNG only).

**Request:** `multipart/form-data`
```
file: <license_image>
```

**Response:** `200 OK`
```json
{
  "message": "License photo uploaded successfully",
  "file_path": "/uploads/licenses/license_1_1699012345.jpg"
}
```

---

### 4.3 Check Driver Status 🔒

**GET** `/api/driver/status`

Check if user is a driver or has pending application.

**Response:** `200 OK`

If driver:
```json
{
  "is_driver": true,
  "driver_id": 5,
  "status": "approved"
}
```

If pending application:
```json
{
  "is_driver": false,
  "application_status": "pending",
  "application_id": 1
}
```

If no application:
```json
{
  "is_driver": false,
  "application_status": null
}
```

---

### 4.4 Get Driver Profile 🔒

**GET** `/api/driver/profile`

Get driver profile (must be an approved driver).

**Response:** `200 OK`
```json
{
  "id": 5,
  "user_id": 1,
  "full_name": "John Driver",
  "car_model": "Toyota Camry 2020",
  "car_number": "01A777AA",
  "license_photo": "/uploads/licenses/license_1.jpg",
  "rating": 4.8,
  "balance": "500000.00",
  "is_blocked": false,
  "created_at": "2025-11-06T12:00:00Z"
}
```

**Errors:**
- `404 Not Found`: Driver profile doesn't exist

---

### 4.5 Update Driver Profile 🔒

**PUT** `/api/driver/profile`

Update driver information.

**Request Body:**
```json
{
  "full_name": "John Smith",
  "car_model": "Toyota Camry 2021",
  "car_number": "01B888BB"
}
```

**Response:** `200 OK`
```json
{
  "id": 5,
  "full_name": "John Smith",
  "car_model": "Toyota Camry 2021",
  "car_number": "01B888BB",
  ...
}
```

---

### 4.6 Get Driver Statistics 🔒

**GET** `/api/driver/statistics`

Get driver performance statistics.

**Response:** `200 OK`
```json
{
  "daily_orders": 5,
  "daily_revenue": "125000.00",
  "monthly_orders": 48,
  "monthly_revenue": "1250000.00",
  "total_orders": 200,
  "total_revenue": "5000000.00",
  "current_balance": "500000.00",
  "rating": 4.8
}
```

---

### 4.7 Get New Orders 🔒

**GET** `/api/driver/orders/new`

Get new pending orders available for acceptance (drivers only).

**Query Parameters:**
- `from_region_id` (optional): Filter by origin region
- `to_region_id` (optional): Filter by destination region

**Response:** `200 OK`
```json
{
  "taxi_orders": [
    {
      "id": 1,
      "type": "taxi",
      "from_region_id": 1,
      "to_region_id": 2,
      "passengers": 3,
      "price": "42500.00",
      "date": "08.11.2025",
      "time_start": "14:00",
      "time_end": "15:00",
      "created_at": "2025-11-06T12:00:00Z"
    }
  ],
  "delivery_orders": [
    {
      "id": 1,
      "type": "delivery",
      "from_region_id": 1,
      "to_region_id": 2,
      "item_type": "documents",
      "price": "25000.00",
      "date": "08.11.2025",
      "time_start": "14:00",
      "time_end": "15:00",
      "created_at": "2025-11-06T12:00:00Z"
    }
  ]
}
```

---

### 4.8 Accept Order 🔒

**POST** `/api/driver/orders/accept/{order_type}/{order_id}`

Accept a taxi or delivery order (drivers only).

**Path Parameters:**
- `order_type`: Either `taxi` or `delivery`
- `order_id`: Order ID

**Response:** `200 OK`
```json
{
  "success": true,
  "message": "Order accepted successfully",
  "order": {
    "id": 1,
    "type": "taxi",
    "status": "accepted"
  }
}
```

**Errors:**
- `403 Forbidden`: Driver account blocked or insufficient balance
- `404 Not Found`: Order doesn't exist
- `400 Bad Request`: Order not available or acceptance time expired (5 min limit)

---

### 4.9 Complete Order 🔒

**POST** `/api/driver/orders/complete/{order_type}/{order_id}`

Mark order as completed (drivers only).

**Path Parameters:**
- `order_type`: Either `taxi` or `delivery`
- `order_id`: Order ID

**Response:** `200 OK`
```json
{
  "success": true,
  "message": "Order completed successfully",
  "order": {
    "id": 1,
    "type": "taxi",
    "status": "completed"
  }
}
```

**Errors:**
- `403 Forbidden`: Not assigned to this order
- `400 Bad Request`: Only accepted orders can be completed

---

## 5. Admin Operations

All admin endpoints require `admin` or `superadmin` role.

### 5.1 Get Pending Driver Applications 🔒

**GET** `/api/admin/driver-applications`

Get all pending driver applications (admin only).

**Response:** `200 OK`
```json
[
  {
    "id": 1,
    "user_id": 5,
    "full_name": "John Driver",
    "telephone": "+998901234567",
    "car_model": "Toyota Camry 2020",
    "car_number": "01A777AA",
    "license_photo": "/uploads/licenses/license_5.jpg",
    "status": "pending",
    "rejection_reason": null,
    "created_at": "2025-11-06T12:00:00Z"
  }
]
```

---

### 5.2 Review Driver Application 🔒

**POST** `/api/admin/driver-applications/review`

Approve or reject a driver application (admin only).

**Request Body:**

To approve:
```json
{
  "application_id": 1,
  "approved": true
}
```

To reject:
```json
{
  "application_id": 1,
  "approved": false,
  "rejection_reason": "Invalid license photo"
}
```

**Response:** `200 OK`
```json
{
  "success": true,
  "message": "Application reviewed successfully",
  "status": "approved"
}
```

**Errors:**
- `404 Not Found`: Application doesn't exist
- `400 Bad Request`: Application already reviewed

---

### 5.3 Get All Drivers 🔒

**GET** `/api/admin/drivers`

Get list of all drivers (admin only).

**Response:** `200 OK`
```json
[
  {
    "id": 5,
    "user_id": 1,
    "full_name": "John Driver",
    "car_model": "Toyota Camry 2020",
    "car_number": "01A777AA",
    "rating": 4.8,
    "balance": "500000.00",
    "is_blocked": false,
    "created_at": "2025-11-06T12:00:00Z"
  }
]
```

---

### 5.4 Block Driver 🔒

**POST** `/api/admin/drivers/{driver_id}/block`

Block a driver account (admin only).

**Path Parameters:**
- `driver_id`: Driver ID

**Response:** `200 OK`
```json
{
  "success": true,
  "message": "Driver blocked successfully"
}
```

---

### 5.5 Unblock Driver 🔒

**POST** `/api/admin/drivers/{driver_id}/unblock`

Unblock a driver account (admin only).

**Response:** `200 OK`
```json
{
  "success": true,
  "message": "Driver unblocked successfully"
}
```

---

### 5.6 Add Driver Balance 🔒

**POST** `/api/admin/drivers/balance/add`

Add balance to driver account (admin only).

**Request Body:**
```json
{
  "driver_id": 5,
  "amount": 100000.00,
  "description": "Monthly bonus"
}
```

**Response:** `200 OK`
```json
{
  "id": 1,
  "driver_id": 5,
  "amount": "100000.00",
  "transaction_type": "credit",
  "description": "Monthly bonus",
  "admin_id": 1,
  "created_at": "2025-11-06T12:00:00Z"
}
```

---

### 5.7 Create Pricing 🔒

**POST** `/api/admin/pricing`

Create pricing for a route (admin only).

**Request Body:**
```json
{
  "from_region_id": 1,
  "to_region_id": 2,
  "service_type": "taxi",
  "base_price": 35000.00,
  "price_per_passenger": 2500.00
}
```

**Service Types:**
- `taxi`: Taxi service
- `delivery`: Delivery service

**Response:** `201 Created`
```json
{
  "id": 1,
  "from_region_id": 1,
  "to_region_id": 2,
  "service_type": "taxi",
  "base_price": "35000.00",
  "price_per_passenger": "2500.00",
  "is_active": true,
  "created_at": "2025-11-06T12:00:00Z"
}
```

---

### 5.8 Update Pricing 🔒

**PUT** `/api/admin/pricing/{pricing_id}`

Update pricing configuration (admin only).

**Request Body:**
```json
{
  "base_price": 40000.00,
  "price_per_passenger": 3000.00,
  "is_active": true
}
```

---

### 5.9 Get All Pricing 🔒

**GET** `/api/admin/pricing`

Get all active pricing configurations (admin only).

**Response:** `200 OK`
```json
[
  {
    "id": 1,
    "from_region_id": 1,
    "to_region_id": 2,
    "service_type": "taxi",
    "base_price": "40000.00",
    "price_per_passenger": "3000.00",
    "is_active": true,
    "created_at": "2025-11-06T12:00:00Z"
  }
]
```

---

### 5.10 Broadcast Message 🔒

**POST** `/api/admin/broadcast`

Send broadcast message to users/drivers (admin only).

**Request Body:**
```json
{
  "target": "all",
  "title": "System Maintenance",
  "message": "The system will be under maintenance on Sunday 10:00-12:00"
}
```

**Target Options:**
- `users`: Send to all users
- `drivers`: Send to all drivers
- `all`: Send to everyone

**Response:** `200 OK`
```json
{
  "success": true,
  "message": "Message broadcasted successfully"
}
```

---

### 5.11 Get Order Statistics 🔒

**GET** `/api/admin/orders/statistics`

Get order statistics (admin only).

**Query Parameters:**
- `period`: `daily`, `monthly`, or `yearly` (default: `daily`)

**Response:** `200 OK`
```json
{
  "period": "daily",
  "taxi_orders": {
    "total": 25,
    "pending": 5,
    "accepted": 8,
    "completed": 10,
    "cancelled": 2,
    "revenue": "1250000.00"
  },
  "delivery_orders": {
    "total": 15,
    "pending": 3,
    "accepted": 5,
    "completed": 6,
    "cancelled": 1,
    "revenue": "450000.00"
  }
}
```

---

### 5.12 Get All Feedback 🔒

**GET** `/api/admin/feedback`

Get all user feedback (admin only).

**Response:** `200 OK`
```json
[
  {
    "id": 1,
    "user_id": 5,
    "message": "Great service!",
    "created_at": "2025-11-06T12:00:00Z"
  }
]
```

---

### 5.13 Add Admin 🔒

**POST** `/api/admin/users/add-admin`

Grant admin privileges to a user (superadmin only).

**Query Parameters:**
- `user_id`: User ID to promote

**Response:** `200 OK`
```json
{
  "id": 5,
  "telephone": "+998901234567",
  "name": "New Admin",
  "role": "admin",
  "language": "uz_latin",
  "is_active": true,
  "created_at": "2025-11-06T12:00:00Z"
}
```

---

### 5.14 Reset User Password 🔒

**POST** `/api/admin/users/{user_id}/reset-password`

Reset user password (superadmin only).

**Path Parameters:**
- `user_id`: User ID

**Query Parameters:**
- `new_password`: New password

**Response:** `200 OK`
```json
{
  "success": true,
  "message": "Password reset successfully"
}
```

---

## 6. Regions & Districts

### 6.1 Get All Regions

**GET** `/api/regions/`

Get all active regions with their districts.

**Response:** `200 OK`
```json
[
  {
    "id": 1,
    "name_uz_latin": "Toshkent shahri",
    "name_uz_cyrillic": "Тошкент шаҳри",
    "name_russian": "город Ташкент",
    "is_active": true,
    "districts": [
      {
        "id": 1,
        "name_uz_latin": "Bektemir",
        "name_uz_cyrillic": "Бектемир",
        "name_russian": "Бектемир",
        "region_id": 1,
        "is_active": true
      },
      {
        "id": 2,
        "name_uz_latin": "Mirzo Ulug'bek",
        "name_uz_cyrillic": "Мирзо Улуғбек",
        "name_russian": "Мирзо Улугбек",
        "region_id": 1,
        "is_active": true
      }
    ]
  },
  {
    "id": 2,
    "name_uz_latin": "Toshkent viloyati",
    "name_uz_cyrillic": "Тошкент вилояти",
    "name_russian": "Ташкентская область",
    "is_active": true,
    "districts": [...]
  }
]
```

---

### 6.2 Get Districts by Region

**GET** `/api/regions/{region_id}/districts`

Get all districts for a specific region.

**Path Parameters:**
- `region_id`: Region ID

**Response:** `200 OK`
```json
[
  {
    "id": 1,
    "name_uz_latin": "Bektemir",
    "name_uz_cyrillic": "Бектемир",
    "name_russian": "Бектемир",
    "region_id": 1,
    "is_active": true
  },
  {
    "id": 2,
    "name_uz_latin": "Mirzo Ulug'bek",
    "name_uz_cyrillic": "Мирзо Улуғбек",
    "name_russian": "Мирзо Улугбек",
    "region_id": 1,
    "is_active": true
  }
]
```

---

## 7. Ratings

### 7.1 Create Rating 🔒

**POST** `/api/ratings/`

Rate a completed order.

**Request Body:**
```json
{
  "order_id": 1,
  "order_type": "taxi",
  "driver_id": 5,
  "rating": 5,
  "comment": "Excellent driver, very professional!"
}
```

**Order Types:**
- `taxi`: Taxi order
- `delivery`: Delivery order

**Rating:** 1-5 stars

**Response:** `201 Created`
```json
{
  "id": 1,
  "user_id": 1,
  "driver_id": 5,
  "taxi_order_id": 1,
  "delivery_order_id": null,
  "rating": 5,
  "comment": "Excellent driver, very professional!",
  "created_at": "2025-11-06T12:00:00Z"
}
```

**Errors:**
- `404 Not Found`: Order doesn't exist
- `403 Forbidden`: Not authorized to rate this order
- `400 Bad Request`: Order not completed or already rated

---

### 7.2 Get Driver Ratings

**GET** `/api/ratings/driver/{driver_id}`

Get all ratings for a specific driver.

**Path Parameters:**
- `driver_id`: Driver ID

**Response:** `200 OK`
```json
[
  {
    "id": 1,
    "user_id": 1,
    "driver_id": 5,
    "rating": 5,
    "comment": "Excellent driver!",
    "created_at": "2025-11-06T12:00:00Z"
  },
  {
    "id": 2,
    "user_id": 2,
    "driver_id": 5,
    "rating": 4,
    "comment": "Good service",
    "created_at": "2025-11-06T11:00:00Z"
  }
]
```

---

## 8. Notifications

### 8.1 Get My Notifications 🔒

**GET** `/api/notifications/`

Get all notifications for authenticated user (and driver if applicable).

**Response:** `200 OK`
```json
[
  {
    "id": 1,
    "user_id": 1,
    "driver_id": null,
    "title": "Order Accepted",
    "message": "Your taxi order #1 has been accepted by a driver.",
    "notification_type": "order_accepted",
    "is_read": false,
    "created_at": "2025-11-06T12:00:00Z"
  },
  {
    "id": 2,
    "user_id": null,
    "driver_id": 5,
    "title": "New Rating",
    "message": "You received a 5-star rating from a customer.",
    "notification_type": "rating_received",
    "is_read": false,
    "created_at": "2025-11-06T11:00:00Z"
  }
]
```

**Notification Types:**
- `order_accepted`: Order accepted by driver
- `order_completed`: Order completed
- `order_cancelled`: Order cancelled
- `application_approved`: Driver application approved
- `application_rejected`: Driver application rejected
- `rating_received`: New rating received
- `balance_added`: Balance credited
- `account_blocked`: Account blocked
- `account_unblocked`: Account unblocked
- `broadcast`: Broadcast message
- `role_updated`: Role updated
- `password_reset`: Password reset

---

### 8.2 Get Unread Notifications 🔒

**GET** `/api/notifications/unread`

Get only unread notifications.

**Response:** `200 OK`
```json
[
  {
    "id": 1,
    "title": "Order Accepted",
    "message": "Your taxi order #1 has been accepted.",
    "is_read": false,
    "created_at": "2025-11-06T12:00:00Z"
  }
]
```

---

### 8.3 Mark Notification as Read 🔒

**POST** `/api/notifications/{notification_id}/mark-read`

Mark a specific notification as read.

**Path Parameters:**
- `notification_id`: Notification ID

**Response:** `200 OK`
```json
{
  "success": true,
  "message": "Notification marked as read"
}
```

**Errors:**
- `404 Not Found`: Notification doesn't exist
- `403 Forbidden`: Not authorized

---

### 8.4 Mark All Notifications as Read 🔒

**POST** `/api/notifications/mark-all-read`

Mark all user's notifications as read.

**Response:** `200 OK`
```json
{
  "success": true,
  "message": "All notifications marked as read"
}
```

---

## 9. Feedback

### 9.1 Submit Feedback 🔒

**POST** `/api/feedback/`

Submit feedback or complaint to admin.

**Request Body:**
```json
{
  "message": "The app is great but I suggest adding dark mode."
}
```

**Response:** `200 OK`
```json
{
  "id": 1,
  "user_id": 1,
  "message": "The app is great but I suggest adding dark mode.",
  "created_at": "2025-11-06T12:00:00Z"
}
```

---

## 10. System Endpoints

### 10.1 Root

**GET** `/`

API welcome message.

**Response:** `200 OK`
```json
{
  "message": "Welcome to Taxi Service API",
  "version": "1.0.0",
  "docs": "/docs",
  "redoc": "/redoc"
}
```

---

### 10.2 Health Check

**GET** `/health`

Check API health status.

**Response:** `200 OK`
```json
{
  "status": "healthy"
}
```

---

## Common Response Codes

| Code | Meaning | Description |
|------|---------|-------------|
| 200 | OK | Request successful |
| 201 | Created | Resource created successfully |
| 400 | Bad Request | Invalid request data |
| 401 | Unauthorized | Invalid or missing authentication token |
| 403 | Forbidden | Insufficient permissions |
| 404 | Not Found | Resource not found |
| 422 | Unprocessable Entity | Validation error |
| 500 | Internal Server Error | Server error |

---

## Authentication Flow

### For Regular Users

1. **Register**: `POST /api/auth/register`
2. **Login**: `POST /api/auth/login` → Receive JWT token
3. **Use Token**: Include in `Authorization: Bearer <token>` header for all protected endpoints

### For Drivers

1. Register as user
2. Login and get token
3. Apply as driver: `POST /api/driver/apply`
4. Wait for admin approval
5. Check status: `GET /api/driver/status`
6. Once approved, access driver endpoints

### For Admins

1. Superadmin creates admin: `POST /api/admin/users/add-admin`
2. Admin logs in with their credentials
3. Access admin endpoints

---

## Data Models Reference

### User Roles
- `user`: Regular user
- `driver`: Approved driver
- `admin`: Admin
- `superadmin`: Super admin

### Languages
- `uz_latin`: Uzbek (Latin)
- `uz_cyrillic`: Uzbek (Cyrillic)
- `russian`: Russian
- `english`: English

### Order Status
- `pending`: Waiting for driver
- `accepted`: Accepted by driver
- `completed`: Completed
- `cancelled`: Cancelled

### Application Status
- `pending`: Under review
- `approved`: Approved
- `rejected`: Rejected

### Item Types (Delivery)
- `documents`: Documents
- `parcel`: Parcel
- `food`: Food
- `other`: Other

---

## Example Authentication Header

```http
GET /api/auth/me HTTP/1.1
Host: 164.90.229.192:8000
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxIiwiZXhwIjoxNzY1MDUxMzg3fQ.IoO4MckoHUo6J5k6t1-Y6aqKhUATQl2zh-ONl2xYyKo
Content-Type: application/json
```

---

## Rate Limiting

Currently no rate limiting is implemented. Consider implementing in production.

---

## CORS Policy

Currently allows all origins (`*`). In production, specify exact allowed origins.

---

## Support

For issues or questions:
- API Documentation: http://164.90.229.192:8000/docs
- Interactive API Testing: http://164.90.229.192:8000/docs (Swagger UI)

---

**Last Updated:** November 6, 2025  
**API Version:** 1.0.0
