# Installation Checklist

## ✅ Pre-Installation

- [ ] Python 3.9+ installed
- [ ] PostgreSQL 12+ installed and running
- [ ] Redis installed (optional, for production)
- [ ] Git installed (optional)
- [ ] Code editor (VS Code recommended)

## ✅ Step 1: Setup Project

- [ ] Navigate to project directory
- [ ] Create virtual environment: `python -m venv venv`
- [ ] Activate virtual environment:
  - Windows: `venv\Scripts\activate`
  - Linux/Mac: `source venv/bin/activate`
- [ ] Install dependencies: `pip install -r requirements.txt`

## ✅ Step 2: Database Setup

- [ ] Create PostgreSQL database: `CREATE DATABASE taxi_db;`
- [ ] Create database user (optional)
- [ ] Grant privileges to user

## ✅ Step 3: Environment Configuration

- [ ] Copy `.env.example` to `.env`
- [ ] Update `DATABASE_URL` in `.env`
- [ ] Generate and set `SECRET_KEY` (at least 32 characters)
- [ ] Set `TELEGRAM_BOT_TOKEN` (get from @BotFather)
- [ ] Set `TELEGRAM_ADMIN_GROUP_ID`
- [ ] Configure other settings as needed

## ✅ Step 4: Initialize Database

- [ ] Run seed script: `python scripts/seed_data.py`
- [ ] Verify regions were created
- [ ] Verify superadmin was created
- [ ] Note down superadmin credentials

## ✅ Step 5: Test the Application

- [ ] Start server: `python main.py` or `./run.bat` (Windows) or `./run.sh` (Linux/Mac)
- [ ] Open browser: http://localhost:8000
- [ ] Check API docs: http://localhost:8000/docs
- [ ] Try health check: http://localhost:8000/health

## ✅ Step 6: Test API Endpoints

- [ ] Test registration endpoint
- [ ] Test login endpoint (should get JWT token)
- [ ] Test protected endpoints with token
- [ ] Test regions endpoint
- [ ] Create a test taxi order
- [ ] Login with superadmin account

## ✅ Step 7: Telegram Bot Setup (Optional)

### User Bot
- [ ] Create bot via @BotFather
- [ ] Get bot token
- [ ] Update `TELEGRAM_BOT_TOKEN` in `.env`
- [ ] Run user bot: `python bot/user_bot.py`
- [ ] Test bot with `/start` command

### Admin Bot
- [ ] Create admin group in Telegram
- [ ] Add bot to group
- [ ] Get group ID
- [ ] Update `TELEGRAM_ADMIN_GROUP_ID` in `.env`
- [ ] Run admin bot: `python bot/admin_bot.py`
- [ ] Test admin commands

## ✅ Step 8: Import Postman Collection

- [ ] Open Postman
- [ ] Import `Taxi_Service_API.postman_collection.json`
- [ ] Set base_url variable to `http://localhost:8000`
- [ ] Test authentication flow
- [ ] Save access token to variable

## ✅ Step 9: Create Test Data

- [ ] Register test user
- [ ] Login and get token
- [ ] Create test taxi order
- [ ] Apply as driver (different user)
- [ ] Admin approve driver application
- [ ] Driver accept order
- [ ] Driver complete order
- [ ] User rate driver

## ✅ Step 10: Verify Features

### User Features
- [ ] User registration
- [ ] User login
- [ ] Profile update
- [ ] Password change
- [ ] Profile picture upload
- [ ] Language selection
- [ ] Create taxi order
- [ ] Create delivery order
- [ ] View orders
- [ ] Cancel order
- [ ] Rate driver

### Driver Features
- [ ] Apply as driver
- [ ] Upload license
- [ ] View driver status
- [ ] View new orders
- [ ] Filter orders
- [ ] Accept order
- [ ] Complete order
- [ ] View statistics
- [ ] Check balance

### Admin Features
- [ ] View pending applications
- [ ] Approve driver
- [ ] Reject driver
- [ ] View all drivers
- [ ] Block driver
- [ ] Unblock driver
- [ ] Add driver balance
- [ ] Create pricing
- [ ] Update pricing
- [ ] Broadcast message
- [ ] View statistics
- [ ] View feedback

### Superadmin Features
- [ ] Add new admin
- [ ] Reset user password

## ✅ Production Deployment (Optional)

- [ ] Set up production server
- [ ] Install requirements on server
- [ ] Configure production database
- [ ] Set up Nginx
- [ ] Configure SSL/TLS
- [ ] Set up Supervisor
- [ ] Configure firewall
- [ ] Set DEBUG=False
- [ ] Set up backups
- [ ] Configure monitoring
- [ ] Test production deployment

## ✅ Documentation Review

- [ ] Read README.md
- [ ] Read QUICKSTART.md
- [ ] Read DEPLOYMENT.md (for production)
- [ ] Review PROJECT_SUMMARY.md
- [ ] Check API documentation at /docs

## 📝 Notes

### Default Superadmin Credentials
- **Phone:** +998901234567
- **Password:** admin123
- **⚠️ CHANGE THIS PASSWORD IMMEDIATELY!**

### Common Issues and Solutions

**Issue: Database connection error**
```bash
# Check PostgreSQL is running
# Verify DATABASE_URL in .env
```

**Issue: Import errors**
```bash
pip install --force-reinstall -r requirements.txt
```

**Issue: Port 8000 already in use**
```bash
# Change port in main.py or kill process using port 8000
```

**Issue: Telegram bot not responding**
```bash
# Verify bot token
# Check bot is running
# Ensure /start command is sent
```

## 🎉 Success Indicators

- ✅ Server runs without errors
- ✅ API documentation accessible
- ✅ Can register and login users
- ✅ Can create orders
- ✅ Can apply as driver
- ✅ Admin can approve drivers
- ✅ Drivers can accept orders
- ✅ Pricing is calculated correctly
- ✅ Notifications work
- ✅ Telegram bots respond (if configured)

## 📞 Need Help?

If you encounter issues:

1. Check error logs in terminal
2. Review .env configuration
3. Verify database connection
4. Check Python version (3.9+)
5. Ensure all dependencies installed
6. Review documentation

## ✨ You're Ready!

Once all checkboxes are complete, your Taxi Service Backend is fully operational!

Next steps:
- Customize for your region
- Add more cities/regions
- Configure pricing
- Set up frontend
- Deploy to production
- Start accepting real orders!

Good luck with your taxi service! 🚖
