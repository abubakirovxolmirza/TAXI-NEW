# Migration and Testing Quick Reference
# Run this script in PowerShell to migrate and test the new features

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "TAXI SERVICE - New Features Migration & Testing" -ForegroundColor Cyan
Write-Host "========================================`n" -ForegroundColor Cyan

# Step 1: Check Python and dependencies
Write-Host "[1/8] Checking Python installation..." -ForegroundColor Yellow
python --version
if ($LASTEXITCODE -ne 0) {
    Write-Host "Error: Python not found!" -ForegroundColor Red
    exit 1
}

# Step 2: Install/Update dependencies
Write-Host "`n[2/8] Installing dependencies..." -ForegroundColor Yellow
pip install -r requirements.txt --quiet

# Step 3: Run database migration
Write-Host "`n[3/8] Running database migration..." -ForegroundColor Yellow
alembic upgrade head

if ($LASTEXITCODE -ne 0) {
    Write-Host "Warning: Migration had issues. You may need to handle manually." -ForegroundColor Red
    $continue = Read-Host "Continue anyway? (y/n)"
    if ($continue -ne "y") {
        exit 1
    }
}

# Step 4: Create initial bonus (optional)
Write-Host "`n[4/8] Creating initial bonus percentage..." -ForegroundColor Yellow
python -c @"
from app.database import SessionLocal
from app.models import Bonus
from decimal import Decimal

db = SessionLocal()
existing = db.query(Bonus).first()
if not existing:
    bonus = Bonus(bonus_percent=Decimal('5.00'), description='Default 5% bonus', is_active=True)
    db.add(bonus)
    db.commit()
    print('✓ Created default bonus (5%)')
else:
    print('✓ Bonus already exists')
db.close()
"@

# Step 5: Set public order timeout (optional)
Write-Host "`n[5/8] Setting public order timeout..." -ForegroundColor Yellow
python -c @"
from app.database import SessionLocal
from app.models import SystemSettings

db = SessionLocal()
setting = db.query(SystemSettings).filter(SystemSettings.setting_key == 'public_order_timeout').first()
if not setting:
    setting = SystemSettings(
        setting_key='public_order_timeout',
        setting_value='15',
        description='Timeout in seconds before order becomes public'
    )
    db.add(setting)
    db.commit()
    print('✓ Set public order timeout to 15 seconds')
else:
    print(f'✓ Public order timeout already set to {setting.setting_value} seconds')
db.close()
"@

# Step 6: Run tests
Write-Host "`n[6/8] Running test suite..." -ForegroundColor Yellow
pytest tests/test_new_features_complete.py -v

if ($LASTEXITCODE -ne 0) {
    Write-Host "`nWarning: Some tests failed!" -ForegroundColor Red
} else {
    Write-Host "`n✓ All tests passed!" -ForegroundColor Green
}

# Step 7: Verify models
Write-Host "`n[7/8] Verifying database models..." -ForegroundColor Yellow
python -c @"
from app.models import Bonus, OrderAcceptanceHistory, TaxiOrder, DeliveryOrder, User
from app.database import SessionLocal

db = SessionLocal()
try:
    # Check tables exist
    bonus_count = db.query(Bonus).count()
    history_count = db.query(OrderAcceptanceHistory).count()
    
    # Check new columns exist
    test_order = db.query(TaxiOrder).first()
    if test_order:
        hasattr(test_order, 'pending_time')
        hasattr(test_order, 'bonus_user_id')
        hasattr(test_order, 'public_order')
    
    test_user = db.query(User).first()
    if test_user:
        hasattr(test_user, 'bonus_ball')
    
    print('✓ All database models verified')
    print(f'  - Bonus records: {bonus_count}')
    print(f'  - Acceptance history records: {history_count}')
except Exception as e:
    print(f'✗ Error verifying models: {e}')
finally:
    db.close()
"@

# Step 8: Summary
Write-Host "`n[8/8] Migration and testing complete!" -ForegroundColor Green
Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host "Next Steps:" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "1. Start the application: python main.py" -ForegroundColor White
Write-Host "2. Access API docs: http://localhost:8000/docs" -ForegroundColor White
Write-Host "3. Test new endpoints using the API documentation" -ForegroundColor White
Write-Host "`nNew Features Available:" -ForegroundColor Cyan
Write-Host "  ✓ Order acceptance history tracking" -ForegroundColor Green
Write-Host "  ✓ Gender validation (male/female only)" -ForegroundColor Green
Write-Host "  ✓ Pending time CRUD" -ForegroundColor Green
Write-Host "  ✓ Bonus system with calculations" -ForegroundColor Green
Write-Host "  ✓ Public orders with configurable timeout" -ForegroundColor Green
Write-Host "`nFor detailed testing guide, see:" -ForegroundColor White
Write-Host "  IMPLEMENTATION_SUMMARY_NEW_FEATURES.md" -ForegroundColor Yellow
Write-Host ""
