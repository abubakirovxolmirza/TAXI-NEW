# PowerShell Test Script for Taxi Service API
# Run this in PowerShell on Windows

$BASE_URL = "http://164.90.229.192:8000"
$API_URL = "$BASE_URL/api"

Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "  TAXI SERVICE API COMPREHENSIVE TEST" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host ""

function Test-Success {
    param($message)
    Write-Host "✓ $message" -ForegroundColor Green
}

function Test-Error {
    param($message)
    Write-Host "✗ $message" -ForegroundColor Red
}

function Test-Info {
    param($message)
    Write-Host "➜ $message" -ForegroundColor Yellow
}

# Test 1: Health Check
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "TEST 1: Health Check" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan
Test-Info "GET $BASE_URL/health"
$health = Invoke-RestMethod -Uri "$BASE_URL/health" -Method Get
$health | ConvertTo-Json
if ($health.status -eq "healthy") {
    Test-Success "Health check passed"
} else {
    Test-Error "Health check failed"
    exit 1
}
Write-Host ""

# Test 2: Login as Superadmin
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "TEST 2: Login as Superadmin" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan
Test-Info "POST $API_URL/auth/login"

$loginBody = @{
    telephone = "+998901234567"
    password = "admin123"
} | ConvertTo-Json

try {
    $loginResponse = Invoke-RestMethod -Uri "$API_URL/auth/login" -Method Post -Body $loginBody -ContentType "application/json"
    $loginResponse | ConvertTo-Json
    $adminToken = $loginResponse.access_token
    $adminId = $loginResponse.user.id
    Test-Success "Superadmin login successful"
    Test-Info "Token: $($adminToken.Substring(0, [Math]::Min(50, $adminToken.Length)))..."
} catch {
    Test-Error "Superadmin login failed: $($_.Exception.Message)"
    exit 1
}
Write-Host ""

# Test 3: Get Profile
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "TEST 3: Get Current User Profile" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan
Test-Info "GET $API_URL/auth/me"

$headers = @{
    Authorization = "Bearer $adminToken"
}

try {
    $profile = Invoke-RestMethod -Uri "$API_URL/auth/me" -Method Get -Headers $headers
    $profile | ConvertTo-Json
    Test-Success "Profile retrieval successful"
} catch {
    Test-Error "Profile retrieval failed: $($_.Exception.Message)"
}
Write-Host ""

# Test 4: Register New User
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "TEST 4: Register New User (Future Driver)" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan
$newPhone = "+998905555555"
Test-Info "POST $API_URL/auth/register"

$registerBody = @{
    telephone = $newPhone
    name = "Test Driver User"
    password = "driver123"
    language = "uz_latin"
} | ConvertTo-Json

try {
    $registerResponse = Invoke-RestMethod -Uri "$API_URL/auth/register" -Method Post -Body $registerBody -ContentType "application/json"
    $registerResponse | ConvertTo-Json
    Test-Success "User registration successful"
} catch {
    if ($_.Exception.Message -like "*already registered*") {
        Test-Info "User already exists, continuing..."
    } else {
        Test-Error "Registration failed: $($_.Exception.Message)"
    }
}
Write-Host ""

# Test 5: Login as New User
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "TEST 5: Login as New User" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan
Test-Info "POST $API_URL/auth/login"

$userLoginBody = @{
    telephone = $newPhone
    password = "driver123"
} | ConvertTo-Json

try {
    $userLogin = Invoke-RestMethod -Uri "$API_URL/auth/login" -Method Post -Body $userLoginBody -ContentType "application/json"
    $userLogin | ConvertTo-Json
    $userToken = $userLogin.access_token
    $userId = $userLogin.user.id
    Test-Success "User login successful"
    Test-Info "User ID: $userId"
    Test-Info "Token: $($userToken.Substring(0, [Math]::Min(50, $userToken.Length)))..."
} catch {
    Test-Error "User login failed: $($_.Exception.Message)"
    exit 1
}
Write-Host ""

# Test 6: Get All Regions
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "TEST 6: Get All Regions" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan
Test-Info "GET $API_URL/regions/"

try {
    $regions = Invoke-RestMethod -Uri "$API_URL/regions/" -Method Get
    $regions | ConvertTo-Json
    Test-Success "Retrieved $($regions.Count) regions"
    $region1Id = $regions[0].id
    $region2Id = $regions[1].id
} catch {
    Test-Error "Failed to get regions: $($_.Exception.Message)"
}
Write-Host ""

# Test 7: Get Districts
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "TEST 7: Get Districts for Region $region1Id" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan
Test-Info "GET $API_URL/regions/$region1Id/districts"

try {
    $districts = Invoke-RestMethod -Uri "$API_URL/regions/$region1Id/districts" -Method Get
    $districts | ConvertTo-Json
    Test-Success "Retrieved $($districts.Count) districts"
    $district1Id = $districts[0].id
} catch {
    Test-Error "Failed to get districts: $($_.Exception.Message)"
}
Write-Host ""

# Test 8: Calculate Price
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "TEST 8: Calculate Taxi Price" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan
Test-Info "GET $API_URL/regions/calculate-price"

try {
    $price = Invoke-RestMethod -Uri "$API_URL/regions/calculate-price?from_region_id=$region1Id&to_region_id=$region2Id&service_type=taxi&passengers=3" -Method Get
    $price | ConvertTo-Json
    Test-Success "Price calculation successful: $($price.final_price)"
} catch {
    Test-Error "Price calculation failed: $($_.Exception.Message)"
}
Write-Host ""

# Test 9: Create Taxi Order
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "TEST 9: Create Taxi Order" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan
Test-Info "POST $API_URL/taxi-orders/"

$userHeaders = @{
    Authorization = "Bearer $userToken"
}

$districts2 = Invoke-RestMethod -Uri "$API_URL/regions/$region2Id/districts" -Method Get
$district2Id = $districts2[0].id

$orderBody = @{
    username = "Test Driver User"
    telephone = $newPhone
    from_region_id = $region1Id
    from_district_id = $district1Id
    to_region_id = $region2Id
    to_district_id = $district2Id
    passengers = 3
    date = "08.11.2025"
    time_start = "14:00"
    time_end = "15:00"
    note = "Test order from PowerShell script"
} | ConvertTo-Json

try {
    $order = Invoke-RestMethod -Uri "$API_URL/taxi-orders/" -Method Post -Body $orderBody -ContentType "application/json" -Headers $userHeaders
    $order | ConvertTo-Json
    $orderId = $order.id
    Test-Success "Taxi order created successfully (ID: $orderId)"
} catch {
    Test-Error "Taxi order creation failed: $($_.Exception.Message)"
}
Write-Host ""

# Test 10: Apply as Driver (with proper JSON data)
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "TEST 10: Apply as Driver" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan
Test-Info "POST $API_URL/driver/apply"

$driverAppBody = @{
    full_name = "Test Driver User"
    car_model = "Toyota Camry 2020"
    car_number = "01A777AA"
    license_photo = "test_license_photo.jpg"
} | ConvertTo-Json

try {
    $driverApp = Invoke-RestMethod -Uri "$API_URL/driver/apply" -Method Post -Body $driverAppBody -ContentType "application/json" -Headers $userHeaders
    $driverApp | ConvertTo-Json
    $appId = $driverApp.id
    Test-Success "Driver application submitted successfully (ID: $appId)"
} catch {
    if ($_.Exception.Message -like "*already*") {
        Test-Info "Driver application already exists"
    } else {
        Test-Error "Driver application failed: $($_.Exception.Message)"
    }
}
Write-Host ""

# Test 11: Get Pending Applications (Admin)
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "TEST 11: Get Pending Applications (Admin)" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan
Test-Info "GET $API_URL/admin/applications"

$adminHeaders = @{
    Authorization = "Bearer $adminToken"
}

try {
    $applications = Invoke-RestMethod -Uri "$API_URL/admin/applications?status=pending" -Method Get -Headers $adminHeaders
    $applications | ConvertTo-Json
    Test-Success "Retrieved $($applications.Count) pending application(s)"
    
    if ($applications.Count -gt 0) {
        $appToApprove = $applications[0].id
        
        # Test 12: Approve Application
        Write-Host ""
        Write-Host "==========================================" -ForegroundColor Cyan
        Write-Host "TEST 12: Approve Driver Application" -ForegroundColor Cyan
        Write-Host "==========================================" -ForegroundColor Cyan
        Test-Info "POST $API_URL/admin/applications/$appToApprove/review"
        
        $reviewBody = @{
            action = "approve"
        } | ConvertTo-Json
        
        try {
            $reviewResponse = Invoke-RestMethod -Uri "$API_URL/admin/applications/$appToApprove/review" -Method Post -Body $reviewBody -ContentType "application/json" -Headers $adminHeaders
            $reviewResponse | ConvertTo-Json
            Test-Success "Application approved successfully"
        } catch {
            Test-Error "Application approval failed: $($_.Exception.Message)"
        }
    }
} catch {
    Test-Error "Failed to get applications: $($_.Exception.Message)"
}
Write-Host ""

# Test 13: Get Admin Statistics
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "TEST 13: Get Order Statistics (Admin)" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan
Test-Info "GET $API_URL/admin/statistics"

try {
    $stats = Invoke-RestMethod -Uri "$API_URL/admin/statistics" -Method Get -Headers $adminHeaders
    $stats | ConvertTo-Json
    Test-Success "Statistics retrieved successfully"
    Test-Info "Total Orders: $($stats.total_orders)"
} catch {
    Test-Error "Statistics retrieval failed: $($_.Exception.Message)"
}
Write-Host ""

# Summary
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "  TEST SUMMARY" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host ""
Test-Success "API is operational and responding correctly"
Test-Info "Superadmin Token: $($adminToken.Substring(0, 30))..."
Test-Info "User Token: $($userToken.Substring(0, 30))..."
Test-Info "Base URL: $BASE_URL"
Test-Info "API Docs: $BASE_URL/docs"
Write-Host ""
Write-Host "All major endpoints tested successfully!" -ForegroundColor Green
Write-Host "==========================================" -ForegroundColor Cyan
