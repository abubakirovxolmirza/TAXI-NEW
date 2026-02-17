# Taxi Service Backend - FastAPI

A comprehensive backend system for a taxi service application with user management, driver functionality, order management, and admin panel.

## 🚀 Features

### User Features
- ✅ Registration and Login (JWT authentication)
- ✅ Profile management (name, password, profile picture, language)
- ✅ Taxi booking with automatic pricing and discounts
- ✅ Delivery orders
- ✅ Order history and active orders tracking
- ✅ Order cancellation with refunds
- ✅ Driver rating and reviews
- ✅ Real-time notifications
- ✅ Multi-language support (Uzbek Latin, Uzbek Cyrillic, Russian)

### Driver Features
- ✅ Driver application system
- ✅ Profile management
- ✅ View and accept new orders (5-minute acceptance window)
- ✅ Order filtering by region
- ✅ Complete orders
- ✅ Statistics (daily, monthly, total)
- ✅ Balance management
- ✅ Rating system

### Admin Features
- ✅ Approve/reject driver applications
- ✅ Manage drivers (block/unblock)
- ✅ Add balance to drivers
- ✅ Set pricing by region and service type
- ✅ Broadcast messages to users/drivers
- ✅ View statistics (daily, monthly, yearly)
- ✅ Export reports
- ✅ View feedback

### Superadmin Features
- ✅ All admin features
- ✅ Add new admins
- ✅ Reset user passwords

### Telegram Bot Features
- ✅ User bot for booking and orders
- ✅ Driver application via bot
- ✅ Feedback submission
- ✅ Admin bot for management
- ✅ Multi-language support

## 📋 Prerequisites

- Python 3.9+
- PostgreSQL 12+
- Redis (for caching and background tasks)
- Telegram Bot Token

## 🛠️ Installation

1. **Clone the repository**
```bash
git clone <repository-url>
cd TAXI
```

2. **Create virtual environment**
```bash
python -m venv venv
venv\Scripts\activate  # On Windows
# source venv/bin/activate  # On Linux/Mac
```

3. **Install dependencies**
```bash
pip install -r requirements.txt
```

4. **Set up environment variables**
```bash
copy .env.example .env
# Edit .env file with your configuration
```

5. **Create PostgreSQL database**
```sql
CREATE DATABASE taxi_db;
CREATE USER taxi_user WITH PASSWORD 'your_password';
GRANT ALL PRIVILEGES ON DATABASE taxi_db TO taxi_user;
```

6. **Run database migrations**
```bash
alembic upgrade head
```

7. **Seed initial data (optional)**
```bash
python scripts/seed_data.py
```

## 🚀 Running the Application

### Start the FastAPI server
```bash
python main.py
```

Or with uvicorn directly:
```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### Run with Docker Compose
```bash
docker-compose up --build -d
```

Check status/logs:
```bash
docker-compose ps
docker-compose logs -f taxi-back
```

### Start Telegram bots (in separate terminals)

**User Bot:**
```bash
python bot/user_bot.py
```

**Admin Bot:**
```bash
python bot/admin_bot.py
```

## 📚 API Documentation

Once the server is running, visit:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

## 🔐 Authentication

All protected endpoints require a Bearer token in the Authorization header:

```
Authorization: Bearer <your_jwt_token>
```

Get token by calling `/api/auth/login` endpoint.

## 📊 API Endpoints Overview

### Authentication
- `POST /api/auth/register` - Register new user
- `POST /api/auth/login` - Login and get token
- `GET /api/auth/me` - Get current user info
- `PUT /api/auth/profile` - Update profile
- `POST /api/auth/upload-profile-picture` - Upload profile picture
- `POST /api/auth/change-password` - Change password

### Taxi Orders
- `POST /api/taxi-orders/` - Create taxi order
- `GET /api/taxi-orders/` - Get user's taxi orders
- `GET /api/taxi-orders/active` - Get active orders
- `GET /api/taxi-orders/history` - Get order history
- `GET /api/taxi-orders/{order_id}` - Get order details
- `POST /api/taxi-orders/cancel` - Cancel order

### Delivery Orders
- `POST /api/delivery-orders/` - Create delivery order
- `GET /api/delivery-orders/` - Get user's delivery orders
- `GET /api/delivery-orders/active` - Get active orders
- `GET /api/delivery-orders/history` - Get order history
- `GET /api/delivery-orders/{order_id}` - Get order details
- `POST /api/delivery-orders/cancel` - Cancel order

### Driver
- `POST /api/driver/apply` - Apply as driver
- `GET /api/driver/status` - Check driver status
- `GET /api/driver/profile` - Get driver profile
- `PUT /api/driver/profile` - Update driver profile
- `GET /api/driver/statistics` - Get driver statistics
- `GET /api/driver/orders/new` - Get new available orders
- `POST /api/driver/orders/accept/{order_type}/{order_id}` - Accept order
- `POST /api/driver/orders/complete/{order_type}/{order_id}` - Complete order

### Ratings
- `POST /api/ratings/` - Rate driver
- `GET /api/ratings/driver/{driver_id}` - Get driver ratings

### Regions
- `GET /api/regions/` - Get all regions
- `GET /api/regions/{region_id}/districts` - Get districts by region

### Notifications
- `GET /api/notifications/` - Get user notifications
- `GET /api/notifications/unread` - Get unread notifications
- `POST /api/notifications/{notification_id}/mark-read` - Mark as read
- `POST /api/notifications/mark-all-read` - Mark all as read

### Admin (requires admin role)
- `GET /api/admin/driver-applications` - Get pending applications
- `POST /api/admin/driver-applications/review` - Review application
- `GET /api/admin/drivers` - Get all drivers
- `POST /api/admin/drivers/{driver_id}/block` - Block driver
- `POST /api/admin/drivers/{driver_id}/unblock` - Unblock driver
- `POST /api/admin/drivers/balance/add` - Add driver balance
- `POST /api/admin/pricing` - Create pricing
- `PUT /api/admin/pricing/{pricing_id}` - Update pricing
- `GET /api/admin/pricing` - Get all pricing
- `POST /api/admin/broadcast` - Broadcast message
- `GET /api/admin/orders/statistics` - Get order statistics
- `GET /api/admin/feedback` - Get feedback

### Superadmin (requires superadmin role)
- `POST /api/admin/users/add-admin` - Add admin
- `POST /api/admin/users/{user_id}/reset-password` - Reset password

## 🗄️ Database Schema

### Main Tables
- `users` - User accounts
- `drivers` - Driver profiles
- `regions` - Geographic regions
- `districts` - Districts within regions
- `taxi_orders` - Taxi booking orders
- `delivery_orders` - Delivery orders
- `ratings` - Driver ratings
- `driver_applications` - Driver applications
- `pricing` - Pricing configurations
- `balance_transactions` - Driver balance transactions
- `notifications` - User/driver notifications
- `feedback` - User feedback

## 🔧 Configuration

Key environment variables in `.env`:

```env
DATABASE_URL=postgresql://user:password@localhost:5432/taxi_db
SECRET_KEY=your-secret-key
TELEGRAM_BOT_TOKEN=your-bot-token
TELEGRAM_ADMIN_GROUP_ID=admin-group-id
```

## 📱 Telegram Bot Commands

### User Bot
- `/start` - Start bot and main menu
- Language selection
- Book taxi
- Order delivery
- Apply as driver
- Submit feedback
- Contact info

### Admin Bot
- `/start` - Admin panel
- View pending applications
- Approve/reject drivers
- View statistics
- Manage drivers
- Broadcast messages
- Add balance

## 🏗️ Project Structure

```
TAXI/
├── app/
│   ├── routers/
│   │   ├── auth.py
│   │   ├── taxi_orders.py
│   │   ├── delivery_orders.py
│   │   ├── driver.py
│   │   ├── admin.py
│   │   ├── ratings.py
│   │   ├── regions.py
│   │   ├── notifications.py
│   │   └── feedback.py
│   ├── models.py
│   ├── schemas.py
│   ├── database.py
│   ├── config.py
│   ├── auth.py
│   └── utils.py
├── bot/
│   ├── user_bot.py
│   └── admin_bot.py
├── uploads/
├── main.py
├── requirements.txt
├── .env.example
└── README.md
```

## 🧪 Testing

Run tests with pytest:
```bash
pytest tests/
```

## 🚀 Deployment

### Production Considerations

1. **Use a production WSGI server**
```bash
gunicorn -w 4 -k uvicorn.workers.UvicornWorker main:app
```

2. **Set up Nginx as reverse proxy**

3. **Use environment-specific .env files**

4. **Enable CORS only for trusted origins**

5. **Set up SSL/TLS certificates**

6. **Configure database connection pooling**

7. **Set up monitoring and logging**

8. **Use Redis for session management**

## 📄 License

This project is licensed under the MIT License.

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## 📞 Support

For support, email support@taxiservice.uz or contact via Telegram.

## 🔄 Version History

- **v1.0.0** - Initial release with all core features
