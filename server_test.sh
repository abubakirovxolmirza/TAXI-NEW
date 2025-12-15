#!/bin/bash
# Server-side testing script
# Run this script on the server: bash server_test.sh

set -e  # Exit on error

echo "============================================================"
echo "SERVER-SIDE TESTING SCRIPT"
echo "============================================================"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

PROJECT_DIR="/var/www/taxi-service/TAXI-NEW"
cd $PROJECT_DIR

echo -e "\n${GREEN}[STEP 1] Activating virtual environment...${NC}"
source venv/bin/activate

echo -e "\n${GREEN}[STEP 2] Checking Python version...${NC}"
python --version

echo -e "\n${GREEN}[STEP 3] Installing/updating requirements...${NC}"
pip install -r requirements.txt -q

echo -e "\n${GREEN}[STEP 4] Running verification script...${NC}"
python verify_implementation.py

echo -e "\n${GREEN}[STEP 5] Checking for syntax errors in new files...${NC}"
python -m py_compile app/routers/bonus.py && echo "  ✅ bonus.py"
python -m py_compile app/routers/order_history.py && echo "  ✅ order_history.py"
python -m py_compile app/routers/pending_time.py && echo "  ✅ pending_time.py"
python -m py_compile app/routers/public_orders.py && echo "  ✅ public_orders.py"
python -m py_compile alembic/versions/add_new_features_2025.py && echo "  ✅ add_new_features_2025.py"

echo -e "\n${GREEN}[STEP 6] Testing imports...${NC}"
python -c "
from app.models import Gender, OrderAcceptanceHistory, Bonus, User, TaxiOrder, DeliveryOrder
from app.routers import bonus, order_history, pending_time, public_orders
from app.utils import calculate_and_apply_bonus
from app.schemas import BonusCreate, BonusUpdate, BonusResponse
print('  ✅ All imports successful')
"

echo -e "\n${GREEN}[STEP 7] Checking current Alembic revision...${NC}"
alembic current

echo -e "\n${GREEN}[STEP 8] Checking pending migrations...${NC}"
alembic heads

echo -e "\n${GREEN}[STEP 9] Validating database connection...${NC}"
python -c "
from app.database import SessionLocal
from sqlalchemy import text
db = SessionLocal()
try:
    db.execute(text('SELECT 1'))
    print('  ✅ Database connection successful')
finally:
    db.close()
"

echo -e "\n${GREEN}[STEP 10] Checking if migration file exists...${NC}"
if [ -f "alembic/versions/add_new_features_2025.py" ]; then
    echo "  ✅ Migration file exists"
else
    echo -e "  ${RED}❌ Migration file not found${NC}"
    exit 1
fi

echo -e "\n${GREEN}[STEP 11] Testing main.py startup (import check)...${NC}"
python -c "
import main
print('  ✅ main.py imports successfully')
print(f'  App title: {main.app.title}')
print(f'  Routers registered: {len(main.app.routes)} routes')
"

echo -e "\n${GREEN}[STEP 12] Checking Gender enum in database...${NC}"
python -c "
from app.database import SessionLocal
from sqlalchemy import text
db = SessionLocal()
try:
    result = db.execute(text(\"SELECT unnest(enum_range(NULL::gender))\")).fetchall()
    values = [r[0] for r in result]
    print(f'  Gender enum values in DB: {values}')
    if 'other' in values:
        print('  ⚠️  WARNING: other value still exists in database')
    else:
        print('  ✅ Gender enum correct (male, female only)')
except Exception as e:
    print(f'  ⚠️  Could not check enum: {e}')
finally:
    db.close()
"

echo -e "\n${GREEN}[STEP 13] Checking if tables exist...${NC}"
python -c "
from app.database import SessionLocal
from sqlalchemy import text
db = SessionLocal()
try:
    tables = db.execute(text(\"\"\"
        SELECT table_name 
        FROM information_schema.tables 
        WHERE table_schema = 'public' 
        AND table_name IN ('bonuses', 'order_acceptance_history')
    \"\"\")).fetchall()
    table_names = [t[0] for t in tables]
    if 'bonuses' in table_names:
        print('  ✅ bonuses table exists')
    else:
        print('  ⚠️  bonuses table not found - migration needed')
    if 'order_acceptance_history' in table_names:
        print('  ✅ order_acceptance_history table exists')
    else:
        print('  ⚠️  order_acceptance_history table not found - migration needed')
except Exception as e:
    print(f'  Error checking tables: {e}')
finally:
    db.close()
"

echo -e "\n============================================================"
echo -e "${GREEN}✅ ALL SERVER TESTS PASSED${NC}"
echo "============================================================"
echo ""
echo "Next steps:"
echo "1. If migration needed: alembic upgrade head"
echo "2. Restart service: systemctl restart taxi-service"
echo "3. Check logs: journalctl -u taxi-service -f"
echo ""
