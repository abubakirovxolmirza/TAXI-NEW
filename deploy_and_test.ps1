# Complete deployment and testing script for remote server
# Usage: .\deploy_and_test.ps1

param(
    [switch]$SkipMigration,
    [switch]$TestOnly
)

$SSH_KEY = "C:\Users\Xolmirza\.ssh\taxi"
$SERVER = "root@164.90.229.192"
$PROJECT_DIR = "/var/www/taxi-service/TAXI-NEW"

Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "REMOTE SERVER DEPLOYMENT AND TESTING" -ForegroundColor Yellow
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host ""

# Function to run command on server
function Invoke-SSHCommand {
    param([string]$Command)
    ssh -i $SSH_KEY $SERVER $Command
}

# Step 1: Push local changes to Git
if (-not $TestOnly) {
    Write-Host "[LOCAL] Pushing changes to Git..." -ForegroundColor Green
    git add .
    git commit -m "Deploy new features with tests" -ErrorAction SilentlyContinue
    git push
    Write-Host "  ✅ Changes pushed to repository" -ForegroundColor Green
}

# Step 2: Pull changes on server
Write-Host "`n[SERVER] Pulling latest changes..." -ForegroundColor Green
Invoke-SSHCommand "cd $PROJECT_DIR && git pull"

# Step 3: Copy test scripts to server
Write-Host "`n[SERVER] Uploading test scripts..." -ForegroundColor Green
scp -i $SSH_KEY ".\server_test.sh" "${SERVER}:${PROJECT_DIR}/"
scp -i $SSH_KEY ".\deploy_migration.sh" "${SERVER}:${PROJECT_DIR}/"
scp -i $SSH_KEY ".\verify_implementation.py" "${SERVER}:${PROJECT_DIR}/"

# Step 4: Make scripts executable
Write-Host "`n[SERVER] Making scripts executable..." -ForegroundColor Green
Invoke-SSHCommand "chmod +x $PROJECT_DIR/server_test.sh $PROJECT_DIR/deploy_migration.sh"

# Step 5: Run server tests
Write-Host "`n[SERVER] Running comprehensive tests..." -ForegroundColor Green
Write-Host "============================================================" -ForegroundColor Yellow
Invoke-SSHCommand "cd $PROJECT_DIR && bash server_test.sh"
Write-Host "============================================================" -ForegroundColor Yellow

if ($TestOnly) {
    Write-Host "`n✅ Test-only mode complete. Exiting without migration." -ForegroundColor Yellow
    exit 0
}

# Step 6: Ask for migration confirmation
Write-Host "`n" -NoNewline
Write-Host "============================================================" -ForegroundColor Yellow
Write-Host "MIGRATION REQUIRED?" -ForegroundColor Red
Write-Host "============================================================" -ForegroundColor Yellow
Write-Host ""

if ($SkipMigration) {
    Write-Host "⚠️  Skipping migration (--SkipMigration flag set)" -ForegroundColor Yellow
} else {
    $confirmation = Read-Host "Do you want to run the database migration? (yes/no)"
    
    if ($confirmation -eq "yes") {
        Write-Host "`n[SERVER] Running database migration..." -ForegroundColor Green
        Write-Host "============================================================" -ForegroundColor Yellow
        Invoke-SSHCommand "cd $PROJECT_DIR && bash deploy_migration.sh"
        Write-Host "============================================================" -ForegroundColor Yellow
        
        # Step 7: Final health check
        Write-Host "`n[SERVER] Running post-deployment health check..." -ForegroundColor Green
        Start-Sleep -Seconds 5
        
        Write-Host "`nChecking API health endpoint..." -ForegroundColor Cyan
        try {
            $response = Invoke-WebRequest -Uri "http://164.90.229.192/health" -TimeoutSec 10 -ErrorAction Stop
            Write-Host "  ✅ API is responding: $($response.StatusCode)" -ForegroundColor Green
        } catch {
            Write-Host "  ⚠️  API health check failed: $_" -ForegroundColor Yellow
        }
        
        Write-Host "`n" -NoNewline
        Write-Host "============================================================" -ForegroundColor Cyan
        Write-Host "✅ DEPLOYMENT COMPLETE" -ForegroundColor Green
        Write-Host "============================================================" -ForegroundColor Cyan
        
    } else {
        Write-Host "`n⚠️  Migration skipped by user" -ForegroundColor Yellow
    }
}

Write-Host "`nUseful commands:" -ForegroundColor Cyan
Write-Host "  View logs:    ssh -i $SSH_KEY $SERVER 'journalctl -u taxi-service -f'" -ForegroundColor White
Write-Host "  Check status: ssh -i $SSH_KEY $SERVER 'systemctl status taxi-service'" -ForegroundColor White
Write-Host "  Restart:      ssh -i $SSH_KEY $SERVER 'systemctl restart taxi-service'" -ForegroundColor White
Write-Host ""
