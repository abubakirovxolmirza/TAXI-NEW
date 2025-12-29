# Quick Reference - New Features

## 🕐 Timezone Changes

### What Changed
All timestamps now display in **Uzbekistan Time (UTC+5)** instead of server time.

### Affected Areas
- ✅ Telegram notifications
- ✅ API responses (created_at, updated_at, etc.)
- ✅ Logs
- ✅ Background tasks

### Example
```
Before: 2025-12-29T14:30:00Z (Frankfurt time)
After:  2025-12-29T19:30:00+05:00 (Uzbekistan time)
```

---

## 💺 Seat Position in Telegram

### What Changed
Telegram notifications now show seat position for taxi orders.

### Message Format
```
🚖 *YANGI TAKSI BUYURTMA*

👤 *Mijoz:* Alisher
📍 *Yo'nalish:* Toshkent ➡️ Samarqand
👥 *Yo'lovchilar soni:* 2 ta
💺 *O'rindiq:* Orqa o'rindiq (back)    ← NEW!
⏰ *Reja vaqt:* 29-dekabr 2025 • 19:30
💰 *Narx:* 150 000 so'm
```

### Seat Types
- **Old o'rindiq (front)** - Front seat
- **Orqa o'rindiq (back)** - Back seat
- **-** - Not specified

---

## ⚙️ Seat Visibility Timeout API

### What Is It?
Controls how long an order stays visible exclusively to a driver who has an accepted order on the same route.

### Default Behavior
- **Default timeout**: 15 minutes
- **Before timeout**: Order visible only to original driver
- **After timeout**: Order visible to all drivers

### API Endpoints

#### 📖 GET Current Timeout
```bash
GET /api/settings/seat-visibility-timeout
```

**Response:**
```json
{
  "setting_key": "seat_visibility_timeout_minutes",
  "minutes": 15,
  "description": "Time in minutes before order becomes visible to all drivers",
  "updated_at": "2025-12-29T14:30:00Z"
}
```

**cURL Example:**
```bash
curl -X GET "http://localhost:8000/api/settings/seat-visibility-timeout"
```

---

#### ✏️ PUT Update Timeout (Admin Only)
```bash
PUT /api/settings/seat-visibility-timeout
Authorization: Bearer <admin_token>
Content-Type: application/json
```

**Request Body:**
```json
{
  "minutes": 20
}
```

**Validation:**
- Minimum: 1 minute
- Maximum: 120 minutes

**Response:**
```json
{
  "setting_key": "seat_visibility_timeout_minutes",
  "minutes": 20,
  "description": "Time in minutes before order becomes visible to all drivers",
  "updated_at": "2025-12-29T14:35:00Z"
}
```

**cURL Example:**
```bash
curl -X PUT "http://localhost:8000/api/settings/seat-visibility-timeout" \
  -H "Authorization: Bearer YOUR_ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"minutes": 20}'
```

---

## 🎯 Use Cases

### Scenario 1: Increase Timeout to 30 Minutes
```bash
# Admin wants more time for drivers to see matched orders
curl -X PUT "http://localhost:8000/api/settings/seat-visibility-timeout" \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"minutes": 30}'
```

### Scenario 2: Check Current Setting
```bash
# Anyone can check current timeout
curl -X GET "http://localhost:8000/api/settings/seat-visibility-timeout"
```

### Scenario 3: Reset to Default (15 minutes)
```bash
curl -X PUT "http://localhost:8000/api/settings/seat-visibility-timeout" \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"minutes": 15}'
```

---

## 🚨 Error Responses

### 403 Forbidden
```json
{
  "detail": "Only admins can update seat visibility timeout"
}
```
**Solution**: Use admin or superadmin token

### 422 Validation Error
```json
{
  "detail": [
    {
      "loc": ["body", "minutes"],
      "msg": "ensure this value is greater than or equal to 1",
      "type": "value_error"
    }
  ]
}
```
**Solution**: Use value between 1-120 minutes

---

## 📊 Postman Collection

### GET Seat Visibility Timeout
- **Method**: GET
- **URL**: `{{base_url}}/api/settings/seat-visibility-timeout`
- **Headers**: None required

### PUT Seat Visibility Timeout
- **Method**: PUT
- **URL**: `{{base_url}}/api/settings/seat-visibility-timeout`
- **Headers**:
  - `Authorization: Bearer {{admin_token}}`
  - `Content-Type: application/json`
- **Body (raw JSON)**:
  ```json
  {
    "minutes": 25
  }
  ```

---

## 🔍 Testing

### Test GET Endpoint
```bash
# Should return current timeout
curl http://localhost:8000/api/settings/seat-visibility-timeout
```

### Test PUT Endpoint (Valid)
```bash
# Should succeed (admin token required)
curl -X PUT http://localhost:8000/api/settings/seat-visibility-timeout \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"minutes": 25}'
```

### Test PUT Endpoint (Invalid - No Auth)
```bash
# Should return 401/403
curl -X PUT http://localhost:8000/api/settings/seat-visibility-timeout \
  -H "Content-Type: application/json" \
  -d '{"minutes": 25}'
```

### Test PUT Endpoint (Invalid - Out of Range)
```bash
# Should return 422
curl -X PUT http://localhost:8000/api/settings/seat-visibility-timeout \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"minutes": 150}'
```

---

## 📝 Notes

1. **Changes apply immediately** - No server restart required
2. **Background task** checks every minute, so changes may take up to 60 seconds to take effect
3. **Default value** is seeded via database migration
4. **Only admins** can update the timeout (Superadmin also allowed)
5. **GET endpoint** is public (no authentication required)

---

## 🔗 Related Endpoints

- GET `/api/pending-time/` - Get/update public order pending time (separate setting)
- GET `/docs` - Full API documentation (Swagger UI)
- GET `/health` - Health check

---

## 💡 Tips

- Use **smaller timeout values** (5-10 min) for busy areas with many drivers
- Use **larger timeout values** (30-45 min) for rural areas with few drivers
- Monitor driver feedback to find optimal timeout for your region
- Check logs to see timeout effectiveness: `grep "preview hold expired" app.log`
