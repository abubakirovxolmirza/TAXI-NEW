# Quick Start Guide - New Features

## 🚀 How to Use the New Features

### For Developers

#### 1. Deploy the Changes
```bash
# Pull latest code
git pull origin main

# Run migration
alembic upgrade head

# Restart application
sudo systemctl restart taxi-api
# or
pm2 restart taxi-api
```

#### 2. Verify Everything Works
```bash
# Check health
curl http://localhost:8000/health

# Test new endpoint
curl http://localhost:8000/api/settings/seat-visibility-timeout
```

---

### For System Administrators

#### Viewing Current Timeout Setting
```bash
curl http://localhost:8000/api/settings/seat-visibility-timeout
```

Expected response:
```json
{
  "setting_key": "seat_visibility_timeout_minutes",
  "minutes": 15,
  "description": "Time in minutes before order becomes visible to all drivers"
}
```

#### Changing Timeout Setting
```bash
# First, get your admin token by logging in
curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"telephone": "+998901234567", "password": "your_password"}'

# Save the token from response, then update timeout
export ADMIN_TOKEN="your_token_here"

curl -X PUT http://localhost:8000/api/settings/seat-visibility-timeout \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"minutes": 30}'
```

#### Recommended Timeout Values
- **Busy urban areas**: 5-10 minutes (many drivers available)
- **Moderate traffic**: 15-20 minutes (default range)
- **Rural areas**: 30-45 minutes (fewer drivers)
- **Low-traffic times**: 45-60 minutes (night shifts)

---

### For End Users (Telegram)

#### What You'll See (Taxi Orders)
Before:
```
🚖 *YANGI TAKSI BUYURTMA*

👤 *Mijoz:* Alisher
📍 *Yo'nalish:* Toshkent ➡️ Samarqand
👥 *Yo'lovchilar soni:* 2 ta
⏰ *Reja vaqt:* 29-12-2025 14:30
💰 *Narx:* 150 000 so'm
```

After:
```
🚖 *YANGI TAKSI BUYURTMA*

👤 *Mijoz:* Alisher
📍 *Yo'nalish:* Toshkent ➡️ Samarqand
👥 *Yo'lovchilar soni:* 2 ta
💺 *O'rindiq:* Orqa o'rindiq (back)    ← NEW!
⏰ *Reja vaqt:* 29-dekabr 2025 • 19:30  ← UZB TIME!
💰 *Narx:* 150 000 so'm
```

**Changes:**
- ✅ Seat position now visible (front/back)
- ✅ Time shown in Uzbekistan timezone (UTC+5)
- ✅ Date format improved (29-dekabr 2025 instead of 29-12-2025)

---

### For API Consumers

#### Timezone in API Responses
All datetime fields now consistently use Uzbekistan timezone:

```json
{
  "id": 123,
  "created_at": "2025-12-29T19:30:00+05:00",  ← UTC+5
  "scheduled_datetime": "2025-12-30T08:00:00+05:00",
  "accepted_at": "2025-12-29T19:35:00+05:00"
}
```

#### New Endpoints Available

**GET** `/api/settings/seat-visibility-timeout`
- Public endpoint (no auth required)
- Returns current timeout in minutes

**PUT** `/api/settings/seat-visibility-timeout`
- Admin-only endpoint
- Updates timeout setting
- Changes apply immediately

See full API docs: `http://localhost:8000/docs`

---

## 🧪 Testing Guide

### Test Timezone Display
1. Create a new taxi order
2. Check Telegram notification
3. Verify time shows in Uzbek timezone (UTC+5)

### Test Seat Position
1. Create taxi order with `seat_type: "front"`
2. Check Telegram message
3. Should show: "💺 *O'rindiq:* Old o'rindiq (front)"

### Test Timeout Configuration
1. Login as admin
2. GET current timeout: should be 15 (default)
3. PUT new timeout: 25 minutes
4. GET again: should now be 25
5. Wait for background task cycle (~1 minute)
6. Verify new timeout is being used

---

## 🔧 Troubleshooting

### Issue: Telegram shows wrong time
**Solution**: Bot process may need restart
```bash
# Restart the bot
pm2 restart telegram-bot
# or
sudo systemctl restart telegram-bot
```

### Issue: Seat position not showing
**Solution**: Check if seat_type is set when creating order
```json
{
  "passengers": 2,
  "seat_type": "back",  ← Make sure this is included
  ...
}
```

### Issue: Can't update timeout (403 error)
**Solution**: Verify you're logged in as admin
```bash
# Check your role
curl http://localhost:8000/api/auth/me \
  -H "Authorization: Bearer $YOUR_TOKEN"

# Role should be "admin" or "superadmin"
```

### Issue: Timeout not applying
**Solution**: Wait up to 60 seconds (background task interval)
```bash
# Check task logs
tail -f /var/log/taxi-api/app.log | grep TASK
```

---

## 📚 Additional Resources

- Full Implementation Guide: `IMPLEMENTATION_SUMMARY_TIMEZONE_SEAT_FEATURES.md`
- API Reference: `API_QUICK_REFERENCE.md`
- Complete Summary: `IMPLEMENTATION_COMPLETE.md`
- API Documentation (Swagger): `http://localhost:8000/docs`

---

## ✅ Checklist After Deployment

- [ ] Migration ran successfully
- [ ] Application restarted without errors
- [ ] Health check passes
- [ ] New endpoint accessible
- [ ] Can GET current timeout
- [ ] Admin can PUT new timeout
- [ ] Telegram notifications show correct time
- [ ] Telegram shows seat position
- [ ] Background task logs show new timeout being used

---

## 🆘 Need Help?

Check logs:
```bash
# Application logs
tail -f /var/log/taxi-api/app.log

# Filter for relevant info
tail -f /var/log/taxi-api/app.log | grep -E "timezone|seat|timeout|TASK"
```

Rollback if needed:
```bash
git checkout <previous_commit>
alembic downgrade -1
sudo systemctl restart taxi-api
```

---

**Quick Links:**
- API Docs: http://localhost:8000/docs
- Health Check: http://localhost:8000/health
- Get Timeout: http://localhost:8000/api/settings/seat-visibility-timeout
