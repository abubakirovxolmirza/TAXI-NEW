# Implementation Summary - December 29, 2025

## Overview
This document summarizes the implementation of three major features:
1. **Timezone Fix** - Project-wide switch to Uzbekistan Time (Asia/Tashkent, UTC+5)
2. **Seat Position in Telegram Notifications** - Display front/back seat information
3. **Configurable Seat Visibility Timeout** - Dynamic API-based configuration

---

## 1. Timezone Fix (Asia/Tashkent - UTC+5)

### Problem
All timestamps (Telegram notifications, logs, API responses, database records) were using server timezone (Frankfurt).

### Solution
Implemented a centralized timezone utility to ensure all times are displayed in Uzbekistan local time.

### Changes Made

#### `app/utils.py`
- Added `UZBEKISTAN_TZ = timezone(timedelta(hours=5))` constant
- Created `get_uzbek_time(dt: Optional[datetime] = None) -> datetime` utility function
- Updated `record_order_acceptance_history()` to use `get_uzbek_time()`
- Updated `_format_schedule()` in Telegram message builder to use `get_uzbek_time()`

#### `app/websocket.py`
- Added `UZBEKISTAN_TZ` constant
- Added `get_uzbek_time()` utility function
- Updated `current_time = get_uzbek_time()` (line ~333)

#### `app/tasks.py`
- Added `UZBEKISTAN_TZ` constant
- Imported `get_uzbek_time` from `app.utils`
- Updated `check_unconfirmed_orders()` to use `get_uzbek_time()` for all time comparisons

### Impact
- **All Telegram notifications** now show Uzbekistan time
- **API responses** with timestamps are in UZB time
- **Logs and database operations** use consistent timezone
- **Server location** (Frankfurt) no longer affects displayed times

### Example
Before:
```
⏰ Reja vaqt: 29-dekabr 2025 • 14:30  (Frankfurt time)
```

After:
```
⏰ Reja vaqt: 29-dekabr 2025 • 19:30  (Uzbekistan time, UTC+5)
```

---

## 2. Seat Position in Telegram Notifications

### Problem
When orders were sent to Telegram channels, the seat position (front/back) was not displayed.

### Solution
Added seat position information to Telegram message templates for taxi orders.

### Changes Made

#### `app/utils.py` - `_build_order_telegram_message()`
- Added seat position formatting logic
- Extracts `seat_type` from order model (`SeatType.FRONT` or `SeatType.BACK`)
- Displays as "Old o'rindiq (front)" or "Orqa o'rindiq (back)"
- Shows "-" if seat type is not specified

### Message Format
```
🚖 *YANGI TAKSI BUYURTMA*

👤 *Mijoz:* Alisher Valiev

📍 *Yo'nalish:*
Toshkent, Chilonzor ➡️ Samarqand, Markaz

👥 *Yo'lovchilar soni:* 2 ta
💺 *O'rindiq:* Orqa o'rindiq (back)

⏰ *Reja vaqt:* 29-dekabr 2025 • 19:30

💰 *Narx:* 150 000 so'm
```

### Data Source
- Seat information comes from `TaxiOrder.seat_type` field in database
- Valid values: `FRONT`, `BACK` (defined in `app.models.SeatType` enum)

---

## 3. Seat Visibility Timeout - Configurable API

### Problem
When a driver accepts an order and the vehicle is not fully occupied, matching orders on the same route are shown exclusively to that driver for a **hardcoded 15-minute period**. This timeout was not configurable.

### Solution
Made the timeout dynamically configurable via system settings and API endpoints.

### Current Logic (Documented)

#### How It Works
1. **Driver A** accepts Order #1 (has available seats)
2. **Order #2** exists on the same route
3. **Order #2** is visible **only to Driver A** for the configured timeout period
4. **After timeout expires**, Order #2 becomes visible to **all drivers**

#### Default Timeout
- **15 minutes** (configurable via API)

#### Where Implemented
- `app/tasks.py` - `check_unconfirmed_orders()` function
- Checks every minute for expired holds
- Returns orders to pending state after timeout

### Changes Made

#### `app/utils.py`
- Added `DEFAULT_SEAT_VISIBILITY_TIMEOUT_MINUTES = 15` constant
- Created `get_seat_visibility_timeout_minutes(db: Session) -> int` function
- Reads from `system_settings` table with key `seat_visibility_timeout_minutes`
- Falls back to default (15 minutes) if not set

#### `app/tasks.py`
- Imported `get_seat_visibility_timeout_minutes` from utils
- Updated `check_unconfirmed_orders()` to use configurable timeout:
  ```python
  timeout_minutes = get_seat_visibility_timeout_minutes(db)
  expiration_time = current_time - timedelta(minutes=timeout_minutes)
  ```

#### `app/routers/system_settings.py` (NEW FILE)
Created new router with two endpoints:

**GET `/api/settings/seat-visibility-timeout`**
- Returns current timeout setting
- No authentication required (read-only)
- Response:
  ```json
  {
    "setting_key": "seat_visibility_timeout_minutes",
    "minutes": 15,
    "description": "Time in minutes before order becomes visible to all drivers",
    "updated_at": "2025-12-29T14:30:00Z"
  }
  ```

**PUT `/api/settings/seat-visibility-timeout`**
- Updates timeout setting (Admin only)
- Request body:
  ```json
  {
    "minutes": 20
  }
  ```
- Validation: 1-120 minutes
- Changes apply **immediately** (no restart required)

#### `main.py`
- Added `system_settings` router import
- Included router: `app.include_router(system_settings.router)`

#### `alembic/versions/add_seat_visibility_timeout.py` (NEW MIGRATION)
- Seeds default value in `system_settings` table
- Ensures setting exists on first deployment

### API Usage Examples

#### Get Current Timeout
```bash
GET /api/settings/seat-visibility-timeout
```

Response:
```json
{
  "setting_key": "seat_visibility_timeout_minutes",
  "minutes": 15,
  "description": "Time in minutes before order becomes visible to all drivers (default)",
  "updated_at": null
}
```

#### Update Timeout (Admin only)
```bash
PUT /api/settings/seat-visibility-timeout
Authorization: Bearer <admin_token>
Content-Type: application/json

{
  "minutes": 20
}
```

Response:
```json
{
  "setting_key": "seat_visibility_timeout_minutes",
  "minutes": 20,
  "description": "Time in minutes before order becomes visible to all drivers",
  "updated_at": "2025-12-29T14:35:00Z"
}
```

### Behavior Examples

**Scenario 1: Default Timeout (15 minutes)**
- 14:00 - Driver A accepts Order #1
- 14:05 - Order #2 created (same route) → visible only to Driver A
- 14:20 - 15 minutes passed → Order #2 visible to all drivers

**Scenario 2: Custom Timeout (30 minutes)**
- Admin sets timeout to 30 minutes via API
- 15:00 - Driver B accepts Order #3
- 15:10 - Order #4 created (same route) → visible only to Driver B
- 15:40 - 30 minutes passed → Order #4 visible to all drivers

---

## Database Schema Impact

### New System Setting
```sql
INSERT INTO system_settings (setting_key, setting_value, description)
VALUES (
  'seat_visibility_timeout_minutes', 
  '15', 
  'Time in minutes before order becomes visible to all drivers'
);
```

---

## Testing Checklist

### Timezone Tests
- [ ] Create order → Check Telegram notification shows UZB time
- [ ] Check API response timestamps (created_at, updated_at)
- [ ] Verify scheduled orders display correct time
- [ ] Test across different server timezones

### Seat Position Tests
- [ ] Create taxi order with `seat_type: "front"` → Verify Telegram shows "Old o'rindiq (front)"
- [ ] Create taxi order with `seat_type: "back"` → Verify Telegram shows "Orqa o'rindiq (back)"
- [ ] Create order without seat_type → Verify Telegram shows "-"

### Seat Visibility Timeout Tests
- [ ] GET `/api/settings/seat-visibility-timeout` → Should return 15 (default)
- [ ] PUT with invalid value (0, 121) → Should return validation error
- [ ] PUT with valid value (20) as admin → Should succeed
- [ ] PUT as regular user → Should return 403 Forbidden
- [ ] After update, verify background task uses new timeout
- [ ] Test order visibility behavior with custom timeout

---

## Deployment Steps

1. **Pull latest code** from repository
2. **Run database migration**:
   ```bash
   alembic upgrade head
   ```
3. **Restart application**:
   ```bash
   systemctl restart taxi-api
   # or
   pm2 restart taxi-api
   ```
4. **Verify endpoints**:
   ```bash
   curl http://localhost:8000/api/settings/seat-visibility-timeout
   ```

---

## Rollback Plan

If issues occur, revert to previous version:

```bash
# Rollback migration
alembic downgrade -1

# Restore previous code
git checkout <previous_commit_hash>

# Restart application
systemctl restart taxi-api
```

---

## Configuration Reference

### System Settings Table
| setting_key | setting_value | description |
|-------------|---------------|-------------|
| `seat_visibility_timeout_minutes` | `15` | Timeout for exclusive order visibility (minutes) |
| `service_fee_percentage` | `10.00` | Platform service fee percentage |
| `public_order_pending_time` | `15` | Time before order becomes public (seconds) |

### Environment Variables (no changes required)
All timezone changes are code-level only. No new environment variables needed.

---

## API Documentation

### New Endpoints

#### GET `/api/settings/seat-visibility-timeout`
- **Description**: Get current seat visibility timeout
- **Authentication**: None
- **Response**: `SeatVisibilityTimeoutResponse`

#### PUT `/api/settings/seat-visibility-timeout`
- **Description**: Update seat visibility timeout
- **Authentication**: Admin/Superadmin required
- **Request Body**: `SeatVisibilityTimeoutUpdate`
- **Response**: `SeatVisibilityTimeoutResponse`

Full API documentation available at: `/docs` (Swagger UI)

---

## Performance Impact

- **Minimal**: Timezone conversion is computationally cheap
- **No database schema changes** for timezone (only new system_setting row)
- **Seat position**: One additional line in Telegram message (negligible)
- **Timeout query**: Already existing, just uses configurable value

---

## Future Enhancements

### Potential Improvements
1. **Multiple timezone support** - Allow users to select their timezone
2. **Seat preference history** - Remember user's preferred seat position
3. **Dynamic timeout per route** - Different timeouts for different routes
4. **Admin dashboard** - UI for managing all system settings

---

## Support & Troubleshooting

### Common Issues

**Issue**: Telegram still shows old timezone
- **Solution**: Check if bot is using cached message templates. Restart bot process.

**Issue**: Seat position shows "-" for all orders
- **Solution**: Verify `seat_type` is being set when creating orders. Check API payload.

**Issue**: Timeout setting doesn't apply
- **Solution**: Background task runs every minute. Wait up to 60 seconds for change to take effect.

**Issue**: 403 Forbidden when updating timeout
- **Solution**: Ensure user has Admin or Superadmin role. Check authentication token.

### Logs
Check application logs for timezone operations:
```bash
tail -f /var/log/taxi-api/app.log | grep -E "timezone|seat|timeout"
```

---

## Contributors
- Implementation Date: December 29, 2025
- Feature Requests: User Requirements (Timezone, Seat Position, Configurable Timeout)

---

## References
- Python datetime timezone handling: https://docs.python.org/3/library/datetime.html
- FastAPI routing: https://fastapi.tiangolo.com/tutorial/bigger-applications/
- Alembic migrations: https://alembic.sqlalchemy.org/
