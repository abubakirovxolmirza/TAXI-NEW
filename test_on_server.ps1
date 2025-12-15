# PowerShell script to test the project on the remote server
# Usage: .\test_on_server.ps1

$SSH_KEY = "C:\Users\Xolmirza\.ssh\taxi"
$SERVER = "root@164.90.229.192"
$PROJECT_DIR = "/var/www/taxi-service/TAXI-NEW"

Write-Host "=" -NoNewline -ForegroundColor Cyan
Write-Host ("=" * 59) -ForegroundColor Cyan
Write-Host "TESTING PROJECT ON REMOTE SERVER" -ForegroundColor Yellow
Write-Host "=" -NoNewline -ForegroundColor Cyan
Write-Host ("=" * 59) -ForegroundColor Cyan

# Step 1: Pull latest changes
Write-Host "`n[STEP 1] Pulling latest changes from Git..." -ForegroundColor Green
ssh -i $SSH_KEY $SERVER "cd $PROJECT_DIR && git pull"

# Step 2: Activate virtual environment and install dependencies
Write-Host "`n[STEP 2] Installing/updating dependencies..." -ForegroundColor Green
ssh -i $SSH_KEY $SERVER "cd $PROJECT_DIR && source venv/bin/activate && pip install -r requirements.txt"

# Step 3: Run verification script
Write-Host "`n[STEP 3] Running verification script..." -ForegroundColor Green
ssh -i $SSH_KEY $SERVER "cd $PROJECT_DIR && source venv/bin/activate && python verify_implementation.py"

# Step 4: Check for syntax errors in all Python files
Write-Host "`n[STEP 4] Checking for Python syntax errors..." -ForegroundColor Green
ssh -i $SSH_KEY $SERVER "cd $PROJECT_DIR && source venv/bin/activate && python -m py_compile app/models.py app/utils.py app/routers/bonus.py app/routers/pending_time.py app/routers/public_orders.py app/routers/order_history.py"

# Step 5: Run database migration check
Write-Host "`n[STEP 5] Checking database migration..." -ForegroundColor Green
ssh -i $SSH_KEY $SERVER "cd $PROJECT_DIR && source venv/bin/activate && alembic current"

# Step 6: Test import of all modules
Write-Host "`n[STEP 6] Testing module imports..." -ForegroundColor Green
ssh -i $SSH_KEY $SERVER @"
cd $PROJECT_DIR && source venv/bin/activate && python -c '
import sys
try:
    from app.models import Gender, OrderAcceptanceHistory, Bonus
    from app.routers import bonus, order_history, pending_time, public_orders
    from app.utils import calculate_and_apply_bonus
    print(""✅ All modules imported successfully"")
except Exception as e:
    print(f""❌ Import error: {e}"")
    sys.exit(1)
'
"@

# Step 7: Check current service status
Write-Host "`n[STEP 7] Checking service status..." -ForegroundColor Green
ssh -i $SSH_KEY $SERVER "systemctl status taxi-service --no-pager | head -20"

Write-Host "`n" -NoNewline
Write-Host "=" -NoNewline -ForegroundColor Cyan
Write-Host ("=" * 59) -ForegroundColor Cyan
Write-Host "TESTING COMPLETE" -ForegroundColor Yellow
Write-Host "=" -NoNewline -ForegroundColor Cyan
Write-Host ("=" * 59) -ForegroundColor Cyan
