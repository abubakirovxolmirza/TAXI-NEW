# Frontend API Changes - New Features

## 🆕 New API Endpoints

### 1. Bonus System (`/api/bonuses`)

**Get Active Bonus** (Public)
```http
GET /api/bonuses/active
Response: { "id": 1, "bonus_percent": "10.00", "description": "...", "is_active": true }
```

**Admin Only:**
- `GET /api/bonuses` - List all bonuses
- `POST /api/bonuses` - Create bonus config
- `PUT /api/bonuses/{id}` - Update bonus
- `DELETE /api/bonuses/{id}` - Delete bonus

### 2. Order Acceptance History (`/api/order-acceptance-history`)

**Admin Only:**
```http
GET /api/order-acceptance-history/driver/{driver_id}?order_type=taxi
GET /api/order-acceptance-history/order/taxi/{order_id}
GET /api/order-acceptance-history/order/delivery/{order_id}
```

### 3. Pending Time Management (`/api/pending-time`)

**Get Setting** (Public)
```http
GET /api/pending-time/
Response: { "setting_key": "public_order_pending_time", "setting_value": "15" }
```

**Admin Only:**
```http
PUT /api/pending-time/
Body: { "pending_time": 20 }

PUT /api/pending-time/taxi/{order_id}
Body: { "pending_time": 30 }

PUT /api/pending-time/delivery/{order_id}
Body: { "pending_time": 30 }
```

### 4. Public Orders (`/api/public-orders`)

**Driver Only:**
```http
GET /api/public-orders/taxi
GET /api/public-orders/delivery
Response: Array of orders with public_order=true
```

**Admin Only:**
```http
POST /api/public-orders/taxi/{order_id}/make-public
POST /api/public-orders/delivery/{order_id}/make-public
```

## 📝 Modified Request/Response Models

### Creating Orders (Taxi/Delivery)
**New Optional Field:**
```json
{
  "bonus_user_id": 123,  // Optional: User ID to receive bonus
  // ...existing fields
}
```

### Order Response
**New Fields in Response:**
```json
{
  "id": 1,
  "bonus_user_id": 123,      // NEW: Optional bonus recipient
  "public_order": false,     // NEW: Is order public to all drivers
  "pending_time": 15,        // NEW: Seconds before becoming public
  // ...existing fields
}
```

### User Model
**New Field:**
```json
{
  "id": 1,
  "bonus_ball": "50.00",    // NEW: User's bonus balance
  // ...existing fields
}
```

## ⚠️ Breaking Changes

### Gender Field
**REMOVED:** `"other"` option

**Now accepts 3 options:**
- `"male"` - Male only
- `"female"` - Female only  
- `"both"` - Both male and female (NEW)

Update all dropdowns/selects to remove "other" and add "both" option.

## 🔄 Automatic Behaviors

### Public Orders Timer
- Orders automatically become `public_order: true` after `pending_time` seconds
- Default: 15 seconds (configurable by admin)
- Frontend will receive WebSocket event: `{ "type": "order_now_public", "order_id": 123 }`

### Bonus Calculation
- When order is completed with `bonus_user_id` set
- Bonus automatically calculated: `order_price × bonus_percent ÷ 100`
- Added to `bonus_ball` of bonus user
- User receives notification

### Order Acceptance History
- Automatically tracked when drivers receive/ignore orders
- No frontend action needed

## 🎨 UI Updates Needed

### 1. Order Creation Form
- Add optional "Bonus User" dropdown/search field
- Show current bonus percentage from `/api/bonuses/active`

### 2. User Profile
- Display `bonus_ball` balance
- Format: "Bonus: 50.00 UZS"

### 3. Driver Order List
- Add "Public Orders" tab
- Fetch from `/api/public-orders/taxi` or `/delivery`
- Show badge/indicator for public orders

### 4. Admin Panel - Bonus Management
- CRUD interface for `/api/bonuses`
- Fields: bonus_percent, description, is_active
- Show current active bonus

### 5. Admin Panel - Pending Time
- Setting for global pending time (seconds)
- Per-order pending time override

### 6. Gender Selection
- Remove "Other" option from all forms
- Add "Both" option (for orders that accept both male and female)
- Options: "Male", "Female", "Both"

## 📱 Example Usage

### Create Order with Bonus User
```javascript
await fetch('/api/taxi-orders/', {
  method: 'POST',
  headers: { 'Authorization': `Bearer ${token}` },
  body: JSON.stringify({
    username: "John Doe",
    telephone: "998901234567",
    from_region_id: 1,
    to_region_id: 2,
    passengers: 2,
    bonus_user_id: 456,  // NEW: Optional
    // ...other fields
  })
});
```

### Get Public Orders (Driver)
```javascript
const publicOrders = await fetch('/api/public-orders/taxi', {
  headers: { 'Authorization': `Bearer ${driverToken}` }
}).then(r => r.json());
```

### Show Bonus Info
```javascript
const activeBonus = await fetch('/api/bonuses/active').then(r => r.json());
// Display: "Earn {activeBonus.bonus_percent}% bonus!"
```

## 🧪 Testing

API base URL: `http://164.90.229.192/api`

All endpoints are live and tested. Use `/docs` for interactive testing.
