#!/bin/bash

# Test Organization API - Verify all fields are returned
# This script tests that GET /api/v1/identity/organizations/{id} returns all required fields

echo "=========================================="
echo "Testing Organization API Fields"
echo "=========================================="
echo ""

# Configuration
API_BASE="http://localhost:8000"
EMAIL="devendera.negi@gmail.com"
PASSWORD="Test@123"

# Step 1: Login
echo "1. Logging in..."
LOGIN_RESPONSE=$(curl -s -X POST "$API_BASE/api/v1/identity/login" \
  -H "Content-Type: application/json" \
  -d "{\"email\":\"$EMAIL\",\"password\":\"$PASSWORD\"}")

TOKEN=$(echo $LOGIN_RESPONSE | python3 -c "import sys, json; print(json.load(sys.stdin)['access_token'])" 2>/dev/null)

if [ -z "$TOKEN" ]; then
  echo "❌ Login failed"
  echo "Response: $LOGIN_RESPONSE"
  exit 1
fi

echo "✅ Login successful"
echo ""

# Step 2: Get user info to find organization_id
echo "2. Getting user info..."
USER_RESPONSE=$(curl -s -X GET "$API_BASE/api/v1/identity/users/me" \
  -H "Authorization: Bearer $TOKEN")

ORG_ID=$(echo $USER_RESPONSE | python3 -c "import sys, json; print(json.load(sys.stdin)['organization_id'])" 2>/dev/null)

if [ -z "$ORG_ID" ]; then
  echo "❌ Failed to get organization ID"
  echo "Response: $USER_RESPONSE"
  exit 1
fi

echo "✅ Organization ID: $ORG_ID"
echo ""

# Step 3: Get organization details
echo "3. Getting organization details..."
ORG_RESPONSE=$(curl -s -X GET "$API_BASE/api/v1/identity/organizations/$ORG_ID" \
  -H "Authorization: Bearer $TOKEN")

echo "Response:"
echo "$ORG_RESPONSE" | python3 -m json.tool
echo ""

# Step 4: Verify all required fields are present
echo "4. Verifying required fields..."
FIELDS=(
  "id"
  "name"
  "slug"
  "address_line1"
  "address_line2"
  "city"
  "state"
  "postal_code"
  "country"
  "logo_url"
  "settings"
  "extra_data"
  "created_at"
  "updated_at"
)

MISSING_FIELDS=()
for field in "${FIELDS[@]}"; do
  HAS_FIELD=$(echo "$ORG_RESPONSE" | python3 -c "import sys, json; data = json.load(sys.stdin); print('$field' in data)" 2>/dev/null)

  if [ "$HAS_FIELD" = "True" ]; then
    echo "✅ Field '$field' is present"
  else
    echo "❌ Field '$field' is MISSING"
    MISSING_FIELDS+=("$field")
  fi
done

echo ""

if [ ${#MISSING_FIELDS[@]} -eq 0 ]; then
  echo "=========================================="
  echo "✅ All required fields are present!"
  echo "=========================================="
else
  echo "=========================================="
  echo "❌ Missing fields: ${MISSING_FIELDS[*]}"
  echo "=========================================="
  exit 1
fi
