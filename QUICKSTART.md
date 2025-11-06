# Quick Start Guide - Taxi Service Backend

## 🚀 Getting Started in 5 Minutes

### 1. Clone and Setup

```bash
cd TAXI
python -m venv venv
venv\Scripts\activate  # Windows
pip install -r requirements.txt
```

### 2. Configure Database

Create PostgreSQL database:
```sql
CREATE DATABASE taxi_db;
```

Copy and edit `.env`:
```bash
copy .env.example .env
```

Edit `.env`:
```env
DATABASE_URL=postgresql://postgres:password@localhost:5432/taxi_db
SECRET_KEY=your-secret-key-min-32-chars
TELEGRAM_BOT_TOKEN=your-bot-token
TELEGRAM_ADMIN_GROUP_ID=your-group-id
```

### 3. Initialize Database

```bash
python scripts/seed_data.py
```

This creates:
- Database tables
- Sample regions and districts (Tashkent, Samarkand, Bukhara, etc.)
- Default pricing
- Superadmin account (phone: +998901234567, password: admin123)

### 4. Run the Server

```bash
python main.py
```

Server starts at: http://localhost:8000

### 5. Explore API

Open: http://localhost:8000/docs

## 📱 API Examples

### Registration

```bash
curl -X POST "http://localhost:8000/api/auth/register" \
  -H "Content-Type: application/json" \
  -d '{
    "telephone": "+998901111111",
    "name": "John Doe",
    "password": "securepass123",
    "confirm_password": "securepass123"
  }'
```

Response:
```json
{
  "id": 2,
  "telephone": "+998901111111",
  "name": "John Doe",
  "role": "user",
  "language": "uz_latin",
  "profile_picture": null,
  "is_active": true,
  "created_at": "2025-11-06T10:30:00"
}
```

### Login

```bash
curl -X POST "http://localhost:8000/api/auth/login" \
  -H "Content-Type: application/json" \
  -d '{
    "telephone": "+998901111111",
    "password": "securepass123"
  }'
```

Response:
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "user": {
    "id": 2,
    "telephone": "+998901111111",
    "name": "John Doe",
    "role": "user",
    "language": "uz_latin"
  }
}
```

### Get Regions

```bash
curl -X GET "http://localhost:8000/api/regions/"
```

### Create Taxi Order

```bash
curl -X POST "http://localhost:8000/api/taxi-orders/" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "username": "John Doe",
    "telephone": "+998901111111",
    "from_region_id": 1,
    "from_district_id": 1,
    "to_region_id": 2,
    "to_district_id": 5,
    "passengers": 2,
    "date": "07.11.2025",
    "time_start": "10:00",
    "time_end": "12:00",
    "note": "Please call when you arrive"
  }'
```

Response (price calculated automatically):
```json
{
  "id": 1,
  "user_id": 2,
  "driver_id": null,
  "username": "John Doe",
  "telephone": "+998901111111",
  "from_region_id": 1,
  "from_district_id": 1,
  "to_region_id": 2,
  "to_district_id": 5,
  "passengers": 2,
  "date": "07.11.2025",
  "time_start": "10:00",
  "time_end": "12:00",
  "price": "45000.00",
  "note": "Please call when you arrive",
  "status": "pending",
  "created_at": "2025-11-06T10:35:00"
}
```

### Apply as Driver

```bash
# First upload license photo
curl -X POST "http://localhost:8000/api/driver/upload-license" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -F "file=@license.jpg"

# Then submit application
curl -X POST "http://localhost:8000/api/driver/apply" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "full_name": "John Driver",
    "car_model": "Chevrolet Lacetti",
    "car_number": "01A123BC",
    "license_photo": "uploads/licenses/license_2_1234567890.jpg"
  }'
```

### Admin: Approve Driver Application

```bash
curl -X POST "http://localhost:8000/api/admin/driver-applications/review" \
  -H "Authorization: Bearer ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "application_id": 1,
    "approved": true
  }'
```

### Driver: Get New Orders

```bash
curl -X GET "http://localhost:8000/api/driver/orders/new?from_region_id=1&to_region_id=2" \
  -H "Authorization: Bearer DRIVER_TOKEN"
```

### Driver: Accept Order

```bash
curl -X POST "http://localhost:8000/api/driver/orders/accept/taxi/1" \
  -H "Authorization: Bearer DRIVER_TOKEN"
```

### Driver: Complete Order

```bash
curl -X POST "http://localhost:8000/api/driver/orders/complete/taxi/1" \
  -H "Authorization: Bearer DRIVER_TOKEN"
```

### Rate Driver

```bash
curl -X POST "http://localhost:8000/api/ratings/" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "driver_id": 1,
    "order_id": 1,
    "order_type": "taxi",
    "rating": 5,
    "comment": "Excellent service!"
  }'
```

### Admin: Set Pricing

```bash
curl -X POST "http://localhost:8000/api/admin/pricing" \
  -H "Authorization: Bearer ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "from_region_id": 1,
    "to_region_id": 3,
    "service_type": "taxi",
    "base_price": 80000.00,
    "discount_1_passenger": 5.00,
    "discount_2_passengers": 10.00,
    "discount_3_passengers": 15.00,
    "discount_full_car": 25.00
  }'
```

### Admin: Broadcast Message

```bash
curl -X POST "http://localhost:8000/api/admin/broadcast" \
  -H "Authorization: Bearer ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "target": "all",
    "title": "System Maintenance",
    "message": "Service will be under maintenance on Nov 7, 2025 from 2-4 AM"
  }'
```

### Get Notifications

```bash
curl -X GET "http://localhost:8000/api/notifications/" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

### Get Driver Statistics

```bash
curl -X GET "http://localhost:8000/api/driver/statistics" \
  -H "Authorization: Bearer DRIVER_TOKEN"
```

Response:
```json
{
  "daily_orders": 5,
  "daily_revenue": "250000.00",
  "monthly_orders": 120,
  "monthly_revenue": "6000000.00",
  "total_orders": 450,
  "total_revenue": "22500000.00",
  "current_balance": "1500000.00",
  "rating": "4.85"
}
```

## 🔑 Default Accounts

### Superadmin
- Phone: +998901234567
- Password: admin123
- Role: superadmin

**⚠️ Change password immediately after first login!**

## 🧪 Testing Flow

### 1. User Registration & Booking

```bash
# Register user
# Login
# Get regions
# Create taxi order
# Check notifications
```

### 2. Driver Flow

```bash
# Register as user
# Apply as driver
# Admin approves (use superadmin account)
# Login again (now as driver)
# View new orders
# Accept order
# Complete order
```

### 3. User Rating

```bash
# User receives notification
# User rates driver
# Driver sees rating in profile
```

## 🐛 Common Issues

### Issue: Database connection error
```bash
# Check PostgreSQL is running
# Verify DATABASE_URL in .env
# Check database exists
psql -U postgres -c "SELECT datname FROM pg_database;"
```

### Issue: Import errors
```bash
# Reinstall dependencies
pip install --force-reinstall -r requirements.txt
```

### Issue: Token expired
```bash
# Login again to get new token
# Token expires after 30 days by default
```

## 📚 Next Steps

1. ✅ Test all API endpoints in Swagger UI
2. ✅ Set up Telegram bot (bot/user_bot.py)
3. ✅ Configure admin bot (bot/admin_bot.py)
4. ✅ Add more regions and pricing
5. ✅ Customize for your needs
6. ✅ Deploy to production (see DEPLOYMENT.md)

## 💡 Tips

- Use Swagger UI for interactive testing: http://localhost:8000/docs
- Check API logs for debugging
- Monitor database with pgAdmin or similar tools
- Use Postman collection for easier API testing

## 📞 Support

- Check README.md for full documentation
- Check DEPLOYMENT.md for production setup
- API documentation: http://localhost:8000/docs
