#!/bin/bash
# Deploy migration script - Run on server
# This script will backup database, run migration, and restart service

set -e

echo "============================================================"
echo "MIGRATION DEPLOYMENT SCRIPT"
echo "============================================================"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

PROJECT_DIR="/var/www/taxi-service/TAXI-NEW"
cd $PROJECT_DIR

# Activate venv
source venv/bin/activate

# Load database credentials
if [ -f ".env" ]; then
    export $(cat .env | grep -v '^#' | xargs)
else
    echo -e "${RED}❌ .env file not found${NC}"
    exit 1
fi

echo -e "\n${GREEN}[STEP 1] Creating database backup...${NC}"
BACKUP_FILE="backup_before_migration_$(date +%Y%m%d_%H%M%S).sql"
pg_dump -U $DB_USER -h $DB_HOST -d $DB_NAME > "/tmp/$BACKUP_FILE" 2>/dev/null || {
    echo -e "${YELLOW}⚠️  Backup failed (this is okay if you have other backups)${NC}"
}
echo "  Backup saved to: /tmp/$BACKUP_FILE"

echo -e "\n${GREEN}[STEP 2] Checking current migration status...${NC}"
alembic current

echo -e "\n${GREEN}[STEP 3] Running database migration...${NC}"
alembic upgrade head

echo -e "\n${GREEN}[STEP 4] Verifying migration...${NC}"
alembic current

echo -e "\n${GREEN}[STEP 5] Checking new tables...${NC}"
python -c "
from app.database import SessionLocal
from sqlalchemy import text
db = SessionLocal()
try:
    # Check bonuses table
    count = db.execute(text('SELECT COUNT(*) FROM bonuses')).scalar()
    print(f'  ✅ bonuses table exists ({count} records)')
    
    # Check order_acceptance_history table
    count = db.execute(text('SELECT COUNT(*) FROM order_acceptance_history')).scalar()
    print(f'  ✅ order_acceptance_history table exists ({count} records)')
    
    # Check new columns in users
    result = db.execute(text('SELECT bonus_ball FROM users LIMIT 1')).fetchone()
    print(f'  ✅ users.bonus_ball column exists')
    
    # Check new columns in taxi_orders
    result = db.execute(text('SELECT bonus_user_id, public_order, pending_time FROM taxi_orders LIMIT 1')).fetchone()
    print(f'  ✅ taxi_orders new columns exist')
    
    # Check Gender enum
    result = db.execute(text(\"SELECT unnest(enum_range(NULL::gender))\")).fetchall()
    values = [r[0] for r in result]
    print(f'  Gender enum: {values}')
    
except Exception as e:
    print(f'  ❌ Error: {e}')
    import traceback
    traceback.print_exc()
finally:
    db.close()
"

echo -e "\n${GREEN}[STEP 6] Restarting taxi service...${NC}"
systemctl restart taxi-service
sleep 3

echo -e "\n${GREEN}[STEP 7] Checking service status...${NC}"
systemctl status taxi-service --no-pager | head -15

echo -e "\n${GREEN}[STEP 8] Checking service logs for errors...${NC}"
journalctl -u taxi-service -n 50 --no-pager | grep -i error || echo "  ✅ No errors found in recent logs"

echo -e "\n============================================================"
echo -e "${GREEN}✅ MIGRATION DEPLOYMENT COMPLETE${NC}"
echo "============================================================"
echo ""
echo "Service is running. Monitor logs with:"
echo "  journalctl -u taxi-service -f"
echo ""
echo "If rollback needed, restore from backup:"
echo "  psql -U \$DB_USER -h \$DB_HOST -d \$DB_NAME < /tmp/$BACKUP_FILE"
echo ""
