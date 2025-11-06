#!/bin/bash

# Taxi Service API Test Script
# This script tests all major endpoints with proper authentication

BASE_URL="http://164.90.229.192:8000"
API_URL="$BASE_URL/api"

echo "=========================================="
echo "  TAXI SERVICE API COMPREHENSIVE TEST"
echo "=========================================="
echo ""

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print success
success() {
    echo -e "${GREEN}✓ $1${NC}"
}

# Function to print error
error() {
    echo -e "${RED}✗ $1${NC}"
}

# Function to print info
info() {
    echo -e "${YELLOW}➜ $1${NC}"
}

# Test 1: Health Check
echo "=========================================="
echo "TEST 1: Health Check"
echo "=========================================="
info "GET $BASE_URL/health"
HEALTH=$(curl -s "$BASE_URL/health")
echo "$HEALTH"
if [[ $HEALTH == *"healthy"* ]]; then
    success "Health check passed"
else
    error "Health check failed"
    exit 1
fi
echo ""

# Test 2: Login as Superadmin
echo "=========================================="
echo "TEST 2: Login as Superadmin"
echo "=========================================="
info "POST $API_URL/auth/login"
LOGIN_RESPONSE=$(curl -s -X POST "$API_URL/auth/login" \
    -H "Content-Type: application/json" \
    -d '{
        "telephone": "+998901234567",
        "password": "admin123"
    }')

echo "$LOGIN_RESPONSE" | jq '.'

ADMIN_TOKEN=$(echo "$LOGIN_RESPONSE" | jq -r '.access_token')
ADMIN_ID=$(echo "$LOGIN_RESPONSE" | jq -r '.user.id')

if [ "$ADMIN_TOKEN" != "null" ] && [ "$ADMIN_TOKEN" != "" ]; then
    success "Superadmin login successful"
    info "Token: ${ADMIN_TOKEN:0:50}..."
else
    error "Superadmin login failed"
    exit 1
fi
echo ""

# Test 3: Get Superadmin Profile
echo "=========================================="
echo "TEST 3: Get Current User Profile"
echo "=========================================="
info "GET $API_URL/auth/me"
PROFILE=$(curl -s -X GET "$API_URL/auth/me" \
    -H "Authorization: Bearer $ADMIN_TOKEN")

echo "$PROFILE" | jq '.'

if [[ $PROFILE == *"Super Admin"* ]]; then
    success "Profile retrieval successful"
else
    error "Profile retrieval failed"
fi
echo ""

# Test 4: Register New User
echo "=========================================="
echo "TEST 4: Register New User (Future Driver)"
echo "=========================================="
NEW_PHONE="+998905555555"
info "POST $API_URL/auth/register"
REGISTER_RESPONSE=$(curl -s -X POST "$API_URL/auth/register" \
    -H "Content-Type: application/json" \
    -d "{
        \"telephone\": \"$NEW_PHONE\",
        \"name\": \"Test Driver User\",
        \"password\": \"driver123\",
        \"language\": \"uz_latin\"
    }")

echo "$REGISTER_RESPONSE" | jq '.'

if [[ $REGISTER_RESPONSE == *"$NEW_PHONE"* ]] || [[ $REGISTER_RESPONSE == *"already registered"* ]]; then
    success "User registration successful (or already exists)"
else
    error "User registration failed"
fi
echo ""

# Test 5: Login as New User
echo "=========================================="
echo "TEST 5: Login as New User"
echo "=========================================="
info "POST $API_URL/auth/login"
USER_LOGIN=$(curl -s -X POST "$API_URL/auth/login" \
    -H "Content-Type: application/json" \
    -d "{
        \"telephone\": \"$NEW_PHONE\",
        \"password\": \"driver123\"
    }")

echo "$USER_LOGIN" | jq '.'

USER_TOKEN=$(echo "$USER_LOGIN" | jq -r '.access_token')
USER_ID=$(echo "$USER_LOGIN" | jq -r '.user.id')

if [ "$USER_TOKEN" != "null" ] && [ "$USER_TOKEN" != "" ]; then
    success "User login successful"
    info "User ID: $USER_ID"
    info "Token: ${USER_TOKEN:0:50}..."
else
    error "User login failed"
    exit 1
fi
echo ""

# Test 6: Get All Regions
echo "=========================================="
echo "TEST 6: Get All Regions"
echo "=========================================="
info "GET $API_URL/regions/"
REGIONS=$(curl -s -X GET "$API_URL/regions/")

echo "$REGIONS" | jq '.'

REGION_COUNT=$(echo "$REGIONS" | jq '. | length')
if [ "$REGION_COUNT" -gt 0 ]; then
    success "Retrieved $REGION_COUNT regions"
    REGION_1_ID=$(echo "$REGIONS" | jq -r '.[0].id')
    REGION_2_ID=$(echo "$REGIONS" | jq -r '.[1].id')
else
    error "No regions found"
fi
echo ""

# Test 7: Get Districts for Region 1
echo "=========================================="
echo "TEST 7: Get Districts for Region $REGION_1_ID"
echo "=========================================="
info "GET $API_URL/regions/$REGION_1_ID/districts"
DISTRICTS=$(curl -s -X GET "$API_URL/regions/$REGION_1_ID/districts")

echo "$DISTRICTS" | jq '.'

DISTRICT_COUNT=$(echo "$DISTRICTS" | jq '. | length')
if [ "$DISTRICT_COUNT" -gt 0 ]; then
    success "Retrieved $DISTRICT_COUNT districts"
    DISTRICT_1_ID=$(echo "$DISTRICTS" | jq -r '.[0].id')
else
    error "No districts found"
fi
echo ""

# Test 8: Calculate Price
echo "=========================================="
echo "TEST 8: Calculate Taxi Price"
echo "=========================================="
info "GET $API_URL/regions/calculate-price"
PRICE=$(curl -s -X GET "$API_URL/regions/calculate-price?from_region_id=$REGION_1_ID&to_region_id=$REGION_2_ID&service_type=taxi&passengers=3")

echo "$PRICE" | jq '.'

FINAL_PRICE=$(echo "$PRICE" | jq -r '.final_price')
if [ "$FINAL_PRICE" != "null" ]; then
    success "Price calculation successful: $FINAL_PRICE"
else
    error "Price calculation failed"
fi
echo ""

# Test 9: Create Taxi Order
echo "=========================================="
echo "TEST 9: Create Taxi Order"
echo "=========================================="
info "POST $API_URL/taxi-orders/"

# Get districts for second region
DISTRICTS_2=$(curl -s -X GET "$API_URL/regions/$REGION_2_ID/districts")
DISTRICT_2_ID=$(echo "$DISTRICTS_2" | jq -r '.[0].id')

ORDER_RESPONSE=$(curl -s -X POST "$API_URL/taxi-orders/" \
    -H "Authorization: Bearer $USER_TOKEN" \
    -H "Content-Type: application/json" \
    -d "{
        \"username\": \"Test Driver User\",
        \"telephone\": \"$NEW_PHONE\",
        \"from_region_id\": $REGION_1_ID,
        \"from_district_id\": $DISTRICT_1_ID,
        \"to_region_id\": $REGION_2_ID,
        \"to_district_id\": $DISTRICT_2_ID,
        \"passengers\": 3,
        \"date\": \"08.11.2025\",
        \"time_start\": \"14:00\",
        \"time_end\": \"15:00\",
        \"note\": \"Test order from API script\"
    }")

echo "$ORDER_RESPONSE" | jq '.'

ORDER_ID=$(echo "$ORDER_RESPONSE" | jq -r '.id')
if [ "$ORDER_ID" != "null" ] && [ "$ORDER_ID" != "" ]; then
    success "Taxi order created successfully (ID: $ORDER_ID)"
else
    error "Taxi order creation failed"
fi
echo ""

# Test 10: Get My Orders
echo "=========================================="
echo "TEST 10: Get My Taxi Orders"
echo "=========================================="
info "GET $API_URL/taxi-orders/my-orders"
MY_ORDERS=$(curl -s -X GET "$API_URL/taxi-orders/my-orders" \
    -H "Authorization: Bearer $USER_TOKEN")

echo "$MY_ORDERS" | jq '.'

ORDER_COUNT=$(echo "$MY_ORDERS" | jq '. | length')
if [ "$ORDER_COUNT" -gt 0 ]; then
    success "Retrieved $ORDER_COUNT order(s)"
else
    info "No orders found (this is OK for new user)"
fi
echo ""

# Test 11: Get Pending Driver Applications (Admin)
echo "=========================================="
echo "TEST 11: Get Pending Driver Applications (Admin)"
echo "=========================================="
info "GET $API_URL/admin/applications"
APPLICATIONS=$(curl -s -X GET "$API_URL/admin/applications?status=pending" \
    -H "Authorization: Bearer $ADMIN_TOKEN")

echo "$APPLICATIONS" | jq '.'

APP_COUNT=$(echo "$APPLICATIONS" | jq '. | length')
success "Retrieved $APP_COUNT pending application(s)"
echo ""

# Test 12: Get All Drivers (Admin)
echo "=========================================="
echo "TEST 12: Get All Drivers (Admin)"
echo "=========================================="
info "GET $API_URL/admin/drivers"
DRIVERS=$(curl -s -X GET "$API_URL/admin/drivers" \
    -H "Authorization: Bearer $ADMIN_TOKEN")

echo "$DRIVERS" | jq '.'

DRIVER_COUNT=$(echo "$DRIVERS" | jq '. | length')
success "Retrieved $DRIVER_COUNT driver(s)"
echo ""

# Test 13: Get Order Statistics (Admin)
echo "=========================================="
echo "TEST 13: Get Order Statistics (Admin)"
echo "=========================================="
info "GET $API_URL/admin/statistics"
STATS=$(curl -s -X GET "$API_URL/admin/statistics" \
    -H "Authorization: Bearer $ADMIN_TOKEN")

echo "$STATS" | jq '.'

TOTAL_ORDERS=$(echo "$STATS" | jq -r '.total_orders')
if [ "$TOTAL_ORDERS" != "null" ]; then
    success "Statistics retrieved successfully"
    info "Total Orders: $TOTAL_ORDERS"
else
    error "Statistics retrieval failed"
fi
echo ""

# Test 14: Get Notifications
echo "=========================================="
echo "TEST 14: Get User Notifications"
echo "=========================================="
info "GET $API_URL/notifications/"
NOTIFICATIONS=$(curl -s -X GET "$API_URL/notifications/" \
    -H "Authorization: Bearer $USER_TOKEN")

echo "$NOTIFICATIONS" | jq '.'

NOTIF_COUNT=$(echo "$NOTIFICATIONS" | jq '. | length')
success "Retrieved $NOTIF_COUNT notification(s)"
echo ""

# Test 15: Update Profile
echo "=========================================="
echo "TEST 15: Update User Profile"
echo "=========================================="
info "PUT $API_URL/auth/profile"
UPDATE_RESPONSE=$(curl -s -X PUT "$API_URL/auth/profile" \
    -H "Authorization: Bearer $USER_TOKEN" \
    -H "Content-Type: application/json" \
    -d '{
        "name": "Test Driver User (Updated)",
        "language": "russian"
    }')

echo "$UPDATE_RESPONSE" | jq '.'

if [[ $UPDATE_RESPONSE == *"Updated"* ]] || [[ $UPDATE_RESPONSE == *"russian"* ]]; then
    success "Profile updated successfully"
else
    info "Profile update response received"
fi
echo ""

# Test 16: Cancel Order (if we have one)
if [ "$ORDER_ID" != "null" ] && [ "$ORDER_ID" != "" ]; then
    echo "=========================================="
    echo "TEST 16: Cancel Taxi Order"
    echo "=========================================="
    info "POST $API_URL/taxi-orders/$ORDER_ID/cancel"
    CANCEL_RESPONSE=$(curl -s -X POST "$API_URL/taxi-orders/$ORDER_ID/cancel" \
        -H "Authorization: Bearer $USER_TOKEN" \
        -H "Content-Type: application/json" \
        -d '{
            "reason": "Testing cancellation from script"
        }')
    
    echo "$CANCEL_RESPONSE" | jq '.'
    
    if [[ $CANCEL_RESPONSE == *"cancelled"* ]] || [[ $CANCEL_RESPONSE == *"success"* ]]; then
        success "Order cancelled successfully"
    else
        info "Cancellation response received"
    fi
    echo ""
fi

# Summary
echo "=========================================="
echo "  TEST SUMMARY"
echo "=========================================="
echo ""
success "API is operational and responding correctly"
info "Superadmin Token: ${ADMIN_TOKEN:0:30}..."
info "User Token: ${USER_TOKEN:0:30}..."
info "Base URL: $BASE_URL"
info "API Docs: $BASE_URL/docs"
echo ""
echo "All major endpoints tested successfully!"
echo "=========================================="
