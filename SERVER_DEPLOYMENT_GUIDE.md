# Server Testing and Deployment Guide

## Current Status ✅

Based on the diagnostic check, all code is working correctly:
- ✅ All Python files have correct syntax (bonus.py, order_history.py, pending_time.py, public_orders.py)
- ✅ All models import successfully (Gender, Bonus, OrderAcceptanceHistory)
- ✅ All routers import successfully
- ✅ main.py imports without errors
- ⚠️  Service is not running (needs to be started)
- ⚠️  Database migration needed (new tables don't exist yet)

## Step-by-Step Instructions

### 1. Connect to Server
```bash
ssh -i C:\Users\Xolmirza/.ssh/taxi root@164.90.229.192
cd /var/www/taxi-service/TAXI-NEW
```

### 2. Run Comprehensive Tests (Uploaded Scripts)
```bash
# Quick diagnostic
bash quick_diagnose.sh

# Full server test
bash server_test.sh
```

### 3. Check What Needs Migration
The following tables need to be created:
- `bonuses` - Bonus configuration table
- `order_acceptance_history` - Driver acceptance tracking

The following columns need to be added:
- `users.bonus_ball` - User bonus balance
- `taxi_orders.bonus_user_id` - Optional bonus recipient
- `taxi_orders.public_order` - Public order flag
- `taxi_orders.pending_time` - Timer before public
- `delivery_orders.bonus_user_id` - Optional bonus recipient  
- `delivery_orders.public_order` - Public order flag
- `delivery_orders.pending_time` - Timer before public

Gender enum needs update:
- Remove 'other' value
- Keep only 'male' and 'female'

### 4. Backup Database (IMPORTANT!)
```bash
# Create backup before migration
pg_dump -U $DB_USER -h $DB_HOST -d $DB_NAME > /tmp/backup_$(date +%Y%m%d_%H%M%S).sql
```

### 5. Check Current Migration Status
```bash
source venv/bin/activate
alembic current
alembic heads
```

### 6. Run Database Migration
```bash
# If backup is successful, run migration
alembic upgrade head

# Verify migration completed
alembic current
```

### 7. Verify New Tables and Columns
```bash
python -c "
from app.database import SessionLocal
from sqlalchemy import text
db = SessionLocal()

# Check bonuses table
print('Bonuses:', db.execute(text('SELECT COUNT(*) FROM bonuses')).scalar())

# Check order_acceptance_history table  
print('History:', db.execute(text('SELECT COUNT(*) FROM order_acceptance_history')).scalar())

# Check new columns exist
print('Users bonus_ball:', db.execute(text('SELECT bonus_ball FROM users LIMIT 1')).scalar())
print('Orders columns:', db.execute(text('SELECT bonus_user_id, public_order, pending_time FROM taxi_orders LIMIT 1')).fetchone())

db.close()
"
```

### 8. Start/Restart Service
```bash
# If using systemd
systemctl restart taxi-service
systemctl status taxi-service

# If running manually with uvicorn
pkill -f uvicorn
source venv/bin/activate
nohup uvicorn main:app --host 0.0.0.0 --port 8000 &

# Check if running
ps aux | grep uvicorn
netstat -tulpn | grep 8000
```

### 9. Test API Endpoints
```bash
# Health check
curl http://localhost:8000/health

# Check docs
curl http://localhost:8000/docs

# Test new endpoints (require authentication)
curl http://localhost:8000/api/bonuses/active
curl http://localhost:8000/api/pending-time/
```

### 10. Monitor Logs
```bash
# If using systemd
journalctl -u taxi-service -f

# If running manually
tail -f nohup.out

# Check for errors
journalctl -u taxi-service -n 100 | grep -i error
```

## Rollback (If Something Goes Wrong)

```bash
# Restore database from backup
psql -U $DB_USER -h $DB_HOST -d $DB_NAME < /tmp/backup_YYYYMMDD_HHMMSS.sql

# Rollback migration
alembic downgrade -1

# Restart service
systemctl restart taxi-service
```

## Testing Individual Features

### Test Bonus System
```bash
python -c "
from app.database import SessionLocal
from app.models import Bonus
from decimal import Decimal

db = SessionLocal()
bonus = Bonus(bonus_percent=Decimal('10.00'), description='Test', is_active=True)
db.add(bonus)
db.commit()
print('✅ Bonus created:', bonus.id)
db.close()
"
```

### Test Order Acceptance History
```bash
python -c "
from app.database import SessionLocal
from app.models import OrderAcceptanceHistory

db = SessionLocal()
history = OrderAcceptanceHistory(driver_id=1, taxi_order_id=1, action='received')
db.add(history)
db.commit()
print('✅ History entry created:', history.id)
db.close()
"
```

### Test Gender Enum
```bash
python -c "
from app.models import Gender
values = [g.value for g in Gender]
print('Gender values:', values)
assert 'other' not in values, 'ERROR: other should not exist'
assert len(values) == 2, 'ERROR: should have exactly 2 values'
print('✅ Gender enum correct')
"
```

## Common Issues and Solutions

### Issue: "Service not found"
**Solution**: Service might not be configured. Run manually:
```bash
cd /var/www/taxi-service/TAXI-NEW
source venv/bin/activate
uvicorn main:app --host 0.0.0.0 --port 8000
```

### Issue: "Module import error"
**Solution**: Install missing dependencies:
```bash
source venv/bin/activate
pip install -r requirements.txt
```

### Issue: "Database connection error"
**Solution**: Check .env file and database credentials:
```bash
cat .env | grep DB_
psql -U $DB_USER -h $DB_HOST -d $DB_NAME -c "SELECT 1"
```

### Issue: "Migration fails"
**Solution**: Check if conflicting migrations exist:
```bash
alembic heads  # Should show only one head
ls alembic/versions/ | grep merge  # Check for merge files
```

## Verification Checklist

After deployment, verify:
- [ ] Service is running (`systemctl status taxi-service` or `ps aux | grep uvicorn`)
- [ ] API responds (`curl http://localhost:8000/health`)
- [ ] New tables exist (`\dt bonuses order_acceptance_history` in psql)
- [ ] New columns exist (check with `\d users`, `\d taxi_orders` in psql)
- [ ] Gender enum updated (`SELECT unnest(enum_range(NULL::gender))` in psql)
- [ ] No errors in logs (`journalctl -u taxi-service -n 50`)
- [ ] All endpoints accessible (`/docs` shows new endpoints)

## Need Help?

Run the uploaded scripts:
```bash
bash quick_diagnose.sh      # Quick health check
bash server_test.sh          # Comprehensive test
bash deploy_migration.sh     # Deploy with backup and migration
```
