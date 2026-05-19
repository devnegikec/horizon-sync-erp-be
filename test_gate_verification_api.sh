#!/bin/bash
# Test script for Gate Verification and Dispatch API endpoints
# Tests the newly added endpoints after gate_verification.py schema was created

BASE_URL="http://localhost:8001/api/v1/outbound"
TOKEN="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJiYjY5NzhjOS0xNjkwLTQ0N2YtODdjZS1mNDI0NTQxZDg2NjUiLCJlbWFpbCI6InlhdGVuMzIxM0BnbWFpbC5jb20iLCJ0eXBlIjoiYWNjZXNzIiwidXNlcl90eXBlIjoidXNlciIsImV4cCI6MTc3ODk2NjMzOH0.c2t6MnShUHb2fY2Wn89Ph1tOh_wjIJVe8hfcZ_x_e04"
AUTH="Authorization: Bearer $TOKEN"
CT="Content-Type: application/json"

PASS=0
FAIL=0
RESULTS=""

test_endpoint() {
    local method=$1
    local url=$2
    local data=$3
    local expected_status=$4
    local description=$5

    if [ -n "$data" ]; then
        response=$(curl -s -w "\n%{http_code}" -X "$method" "$url" -H "$AUTH" -H "$CT" -d "$data")
    else
        response=$(curl -s -w "\n%{http_code}" -X "$method" "$url" -H "$AUTH")
    fi

    status_code=$(echo "$response" | tail -1)
    body=$(echo "$response" | sed '$d')

    if [ "$status_code" = "$expected_status" ]; then
        PASS=$((PASS + 1))
        RESULTS="$RESULTS\n✅ PASS [$status_code] $description"
    else
        FAIL=$((FAIL + 1))
        RESULTS="$RESULTS\n❌ FAIL [$status_code expected $expected_status] $description"
        RESULTS="$RESULTS\n   Response: $(echo $body | head -c 200)"
    fi
}

echo "============================================"
echo "  Gate Verification & Dispatch API Tests"
echo "============================================"
echo ""

# --- PICK LIST ENDPOINTS (existing) ---
echo "--- Pick List Endpoints ---"

# 1. List pick lists
test_endpoint "GET" "$BASE_URL" "" "200" "GET /outbound - List pick lists"

# 2. Create from invoice (valid payload)
test_endpoint "POST" "$BASE_URL/from-invoice" '{"invoice_reference":"INV-TEST-001","warehouse_id":"11111111-1111-1111-1111-111111111111","items":[{"sku":"ITEM-001","item_id":"11111111-1111-1111-1111-111111111111","quantity":10}]}' "201" "POST /outbound/from-invoice - Create pick list from SAP invoice"

# 3. Create from invoice (missing required fields)
test_endpoint "POST" "$BASE_URL/from-invoice" '{}' "422" "POST /outbound/from-invoice - Missing required fields returns 422"

# 4. Get non-existent pick list
test_endpoint "GET" "$BASE_URL/00000000-0000-0000-0000-000000000000" "" "404" "GET /outbound/{id} - Non-existent pick list returns 404"

# 5. Complete non-existent pick list
test_endpoint "POST" "$BASE_URL/00000000-0000-0000-0000-000000000000/complete" "" "404" "POST /outbound/{id}/complete - Non-existent returns 404"

# 6. Cancel non-existent pick list
test_endpoint "POST" "$BASE_URL/00000000-0000-0000-0000-000000000000/cancel" "" "404" "POST /outbound/{id}/cancel - Non-existent returns 404"

# 7. Scan on non-existent pick list
test_endpoint "POST" "$BASE_URL/00000000-0000-0000-0000-000000000000/scan" '{"qr_data":"{\"id\":\"qr-001\",\"sku\":\"ITEM-001\",\"qty\":5,\"batch\":\"B001\"}"}' "404" "POST /outbound/{id}/scan - Non-existent returns 404"

echo ""
echo "--- Gate Verification Endpoints ---"

# 8. Start gate session (with non-existent pick list)
test_endpoint "POST" "$BASE_URL/gate-sessions" '{"pick_list_id":"00000000-0000-0000-0000-000000000000","vehicle_number":"KA-01-AB-1234","driver_name":"Test Driver","driver_contact":"9876543210"}' "404" "POST /gate-sessions - Non-existent pick list returns 404"

# 9. Start gate session (missing required field)
test_endpoint "POST" "$BASE_URL/gate-sessions" '{"vehicle_number":"KA-01-AB-1234"}' "422" "POST /gate-sessions - Missing pick_list_id returns 422"

# 10. Record gate scan on non-existent session
test_endpoint "POST" "$BASE_URL/gate-sessions/00000000-0000-0000-0000-000000000000/scan" '{"qr_data":"{\"id\":\"qr-001\",\"sku\":\"ITEM-001\",\"qty\":5,\"batch\":\"B001\"}"}' "404" "POST /gate-sessions/{id}/scan - Non-existent session returns 404"

# 11. Get progress of non-existent session
test_endpoint "GET" "$BASE_URL/gate-sessions/00000000-0000-0000-0000-000000000000/progress" "" "404" "GET /gate-sessions/{id}/progress - Non-existent session returns 404"

# 12. Verify non-existent session
test_endpoint "POST" "$BASE_URL/gate-sessions/00000000-0000-0000-0000-000000000000/verify" "" "404" "POST /gate-sessions/{id}/verify - Non-existent session returns 404"

# 13. Gate scan with empty qr_data
test_endpoint "POST" "$BASE_URL/gate-sessions/00000000-0000-0000-0000-000000000000/scan" '{"qr_data":""}' "422" "POST /gate-sessions/{id}/scan - Empty qr_data returns 422"

echo ""
echo "--- Dispatch Endpoints ---"

# 14. Create dispatch with non-existent gate session
test_endpoint "POST" "$BASE_URL/dispatches" '{"gate_session_id":"00000000-0000-0000-0000-000000000000"}' "404" "POST /dispatches - Non-existent gate session returns 404"

# 15. Create dispatch with missing required field
test_endpoint "POST" "$BASE_URL/dispatches" '{}' "422" "POST /dispatches - Missing gate_session_id returns 422"

# 16. List dispatches
test_endpoint "GET" "$BASE_URL/dispatches" "" "200" "GET /dispatches - List dispatches"

# 17. Get non-existent dispatch
test_endpoint "GET" "$BASE_URL/dispatches/00000000-0000-0000-0000-000000000000" "" "404" "GET /dispatches/{id} - Non-existent dispatch returns 404"

echo ""
echo "--- Endpoint Availability Tests ---"

# 18. Verify gate-sessions endpoint exists (not captured as UUID)
test_endpoint "POST" "$BASE_URL/gate-sessions" '{"pick_list_id":"00000000-0000-0000-0000-000000000001"}' "404" "POST /gate-sessions - Endpoint exists (not 405/422 for method)"

# 19. Verify dispatches endpoint exists
test_endpoint "GET" "$BASE_URL/dispatches" "" "200" "GET /dispatches - Endpoint exists and returns 200"

echo ""
echo "============================================"
echo "  RESULTS"
echo "============================================"
echo -e "$RESULTS"
echo ""
echo "============================================"
echo "  SUMMARY: $PASS passed, $FAIL failed"
echo "============================================"
