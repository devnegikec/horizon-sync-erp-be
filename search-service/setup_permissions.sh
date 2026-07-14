#!/bin/bash

# Script to set up search permissions in the identity service
# Usage: ./setup_permissions.sh <ADMIN_TOKEN>

set -e

IDENTITY_URL="http://localhost:8000"
ADMIN_TOKEN="$1"

if [ -z "$ADMIN_TOKEN" ]; then
    echo "Error: Admin token required"
    echo "Usage: ./setup_permissions.sh <ADMIN_TOKEN>"
    echo ""
    echo "Get your admin token by logging in:"
    echo "  curl -X POST http://localhost:8000/api/v1/identity/auth/login \\"
    echo "    -H 'Content-Type: application/json' \\"
    echo "    -d '{\"email\":\"admin@example.com\",\"password\":\"your_password\"}'"
    exit 1
fi

echo "========================================="
echo "Setting up Search Service Permissions"
echo "========================================="
echo ""

# Create search.global permission
echo "Creating search.global permission..."
RESPONSE=$(curl -s -w "\n%{http_code}" -X POST "${IDENTITY_URL}/api/v1/identity/permissions" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer ${ADMIN_TOKEN}" \
  -d '{
    "code": "search.global",
    "name": "Global Search",
    "description": "Perform global search across all entity types",
    "resource": "search",
    "action": "global"
  }')

HTTP_CODE=$(echo "$RESPONSE" | tail -n1)
BODY=$(echo "$RESPONSE" | sed '$d')

if [ "$HTTP_CODE" = "201" ] || [ "$HTTP_CODE" = "200" ]; then
    echo "✓ search.global permission created successfully"
elif [ "$HTTP_CODE" = "409" ]; then
    echo "✓ search.global permission already exists"
else
    echo "✗ Failed to create search.global permission (HTTP $HTTP_CODE)"
    echo "Response: $BODY"
fi

echo ""

# Create search.local permission
echo "Creating search.local permission..."
RESPONSE=$(curl -s -w "\n%{http_code}" -X POST "${IDENTITY_URL}/api/v1/identity/permissions" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer ${ADMIN_TOKEN}" \
  -d '{
    "code": "search.local",
    "name": "Local Search",
    "description": "Perform local search within specific entity types",
    "resource": "search",
    "action": "local"
  }')

HTTP_CODE=$(echo "$RESPONSE" | tail -n1)
BODY=$(echo "$RESPONSE" | sed '$d')

if [ "$HTTP_CODE" = "201" ] || [ "$HTTP_CODE" = "200" ]; then
    echo "✓ search.local permission created successfully"
elif [ "$HTTP_CODE" = "409" ]; then
    echo "✓ search.local permission already exists"
else
    echo "✗ Failed to create search.local permission (HTTP $HTTP_CODE)"
    echo "Response: $BODY"
fi

echo ""

# Create search.sync permission
echo "Creating search.sync permission..."
RESPONSE=$(curl -s -w "\n%{http_code}" -X POST "${IDENTITY_URL}/api/v1/identity/permissions" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer ${ADMIN_TOKEN}" \
  -d '{
    "code": "search.sync",
    "name": "Search Sync",
    "description": "Synchronize data from core-service to search index",
    "resource": "search",
    "action": "sync"
  }')

HTTP_CODE=$(echo "$RESPONSE" | tail -n1)
BODY=$(echo "$RESPONSE" | sed '$d')

if [ "$HTTP_CODE" = "201" ] || [ "$HTTP_CODE" = "200" ]; then
    echo "✓ search.sync permission created successfully"
elif [ "$HTTP_CODE" = "409" ]; then
    echo "✓ search.sync permission already exists"
else
    echo "✗ Failed to create search.sync permission (HTTP $HTTP_CODE)"
    echo "Response: $BODY"
fi

echo ""
echo "========================================="
echo "Permissions created successfully!"
echo "========================================="
echo ""
echo "Permissions created:"
echo "  - search.global (Global search across all entity types)"
echo "  - search.local (Local search within specific entity types)"
echo "  - search.sync (Synchronize data from core-service)"
echo ""
echo "Next steps:"
echo "1. Assign these permissions to your role:"
echo "   curl -X POST ${IDENTITY_URL}/api/v1/identity/roles/{ROLE_ID}/permissions \\"
echo "     -H 'Content-Type: application/json' \\"
echo "     -H 'Authorization: Bearer ${ADMIN_TOKEN}' \\"
echo "     -d '{\"permission_codes\": [\"search.global\", \"search.local\", \"search.sync\"]}'"
echo ""
echo "2. Sync data from core-service:"
echo "   curl -X POST http://localhost:8002/api/v1/sync/all \\"
echo "     -H 'Authorization: Bearer YOUR_USER_TOKEN'"
echo ""
echo "3. Test the search endpoint:"
echo "   curl -X POST http://localhost:8002/api/v1/search/global \\"
echo "     -H 'Content-Type: application/json' \\"
echo "     -H 'Authorization: Bearer YOUR_USER_TOKEN' \\"
echo "     -d '{\"query\": \"test\", \"page\": 1, \"page_size\": 20}'"
