#!/bin/bash
# Quick diagnostic script to check for errors on server
# Run: bash quick_diagnose.sh

echo "============================================================"
echo "QUICK DIAGNOSTIC CHECK"
echo "============================================================"

PROJECT_DIR="/var/www/taxi-service/TAXI-NEW"
cd $PROJECT_DIR

GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "\n${GREEN}1. Checking if service is running...${NC}"
systemctl is-active taxi-service && echo "  ✅ Service is active" || echo -e "  ${RED}❌ Service is not running${NC}"

echo -e "\n${GREEN}2. Last 20 lines of service logs...${NC}"
echo "-----------------------------------------------------------"
journalctl -u taxi-service -n 20 --no-pager
echo "-----------------------------------------------------------"

echo -e "\n${GREEN}3. Checking for Python errors in logs...${NC}"
journalctl -u taxi-service -n 100 --no-pager | grep -i "error\|exception\|traceback" | tail -10 || echo "  ✅ No recent errors"

echo -e "\n${GREEN}4. Testing Python syntax of new files...${NC}"
source venv/bin/activate
python -m py_compile app/routers/bonus.py 2>&1 && echo "  ✅ bonus.py" || echo -e "  ${RED}❌ bonus.py has errors${NC}"
python -m py_compile app/routers/order_history.py 2>&1 && echo "  ✅ order_history.py" || echo -e "  ${RED}❌ order_history.py has errors${NC}"
python -m py_compile app/routers/pending_time.py 2>&1 && echo "  ✅ pending_time.py" || echo -e "  ${RED}❌ pending_time.py has errors${NC}"
python -m py_compile app/routers/public_orders.py 2>&1 && echo "  ✅ public_orders.py" || echo -e "  ${RED}❌ public_orders.py has errors${NC}"

echo -e "\n${GREEN}5. Testing imports...${NC}"
python -c "
try:
    from app.models import Gender, OrderAcceptanceHistory, Bonus
    print('  ✅ Models import successfully')
except Exception as e:
    print(f'  ❌ Models import error: {e}')
    
try:
    from app.routers import bonus, order_history, pending_time, public_orders
    print('  ✅ Routers import successfully')
except Exception as e:
    print(f'  ❌ Routers import error: {e}')

try:
    import main
    print('  ✅ main.py imports successfully')
except Exception as e:
    print(f'  ❌ main.py import error: {e}')
"

echo -e "\n${GREEN}6. Checking database connection...${NC}"
python -c "
from app.database import SessionLocal
try:
    db = SessionLocal()
    db.execute('SELECT 1')
    print('  ✅ Database connection OK')
    db.close()
except Exception as e:
    print(f'  ❌ Database error: {e}')
"

echo -e "\n${GREEN}7. Checking Git status...${NC}"
git status -s | head -5

echo -e "\n${GREEN}8. Checking latest commit...${NC}"
git log -1 --oneline

echo -e "\n============================================================"
echo "DIAGNOSTIC COMPLETE"
echo "============================================================"
