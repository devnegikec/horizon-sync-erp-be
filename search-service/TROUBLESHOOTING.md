# Search Service Troubleshooting Guide

## Issue: 403 Forbidden when calling search endpoints

### Symptoms
- Postman/curl requests to `/api/v1/search/global` or `/api/v1/search/{entity_type}` return 403 Forbidden
- Logs show: `"POST /api/v1/search/global HTTP/1.1" 403 Forbidden`
- Identity service call succeeds: `HTTP Request: GET http://identity-service:8000/api/v1/identity/me "HTTP/1.1 200 OK"`

### Root Cause
The user doesn't have the required permissions (`search.global` or `search.local`) assigned in the identity service.

### Solution

#### Option 1: Assign permissions via Identity Service API

1. **Get your user's role ID** (if you don't have it):
```bash
curl --location 'http://localhost:8000/api/v1/identity/me' \
--header 'Authorization: Bearer YOUR_TOKEN'
```

2. **Create search permissions** (if they don't exist):
```bash
# Create search.global permission
curl --location 'http://localhost:8000/api/v1/identity/permissions' \
--header 'Content-Type: application/json' \
--header 'Authorization: Bearer YOUR_ADMIN_TOKEN' \
--data '{
  "code": "search.global",
  "name": "Global Search",
  "description": "Perform global search across all entity types",
  "resource": "search",
  "action": "global"
}'

# Create search.local permission
curl --location 'http://localhost:8000/api/v1/identity/permissions' \
--header 'Content-Type: application/json' \
--header 'Authorization: Bearer YOUR_ADMIN_TOKEN' \
--data '{
  "code": "search.local",
  "name": "Local Search",
  "description": "Perform local search within specific entity types",
  "resource": "search",
  "action": "local"
}'
```

3. **Assign permissions to your role**:
```bash
curl --location 'http://localhost:8000/api/v1/identity/roles/{ROLE_ID}/permissions' \
--header 'Content-Type: application/json' \
--header 'Authorization: Bearer YOUR_ADMIN_TOKEN' \
--data '{
  "permission_codes": ["search.global", "search.local"]
}'
```

#### Option 2: Use wildcard permissions

If your user has `*.*` (all permissions) or `search.*` (all search permissions), the endpoints will work automatically.

#### Option 3: Temporary workaround for development

For development/testing, you can temporarily modify the endpoint to not require permissions:

**In `search-service/app/api/v1/endpoints/search.py`:**

Change:
```python
current_user: UserContext = Depends(require_permission("search.global")),
```

To:
```python
current_user: UserContext = Depends(get_current_active_user),
```

⚠️ **Warning:** This removes permission checks. Only use for development!

### Verification

After assigning permissions, test the endpoint:

```bash
curl --location 'http://localhost:8002/api/v1/search/global' \
--header 'Content-Type: application/json' \
--header 'Authorization: Bearer YOUR_TOKEN' \
--data '{
  "query": "test",
  "page": 1,
  "page_size": 20
}'
```

You should get a 200 OK response with search results.

## Other Common Issues

### Issue: 401 Unauthorized

**Cause:** Invalid or expired JWT token

**Solution:** 
1. Login again to get a fresh token
2. Verify the token is not expired (check `exp` claim)
3. Ensure the `SECRET_KEY` matches between identity-service and search-service

### Issue: 400 Bad Request - "String should have at least 1 character"

**Cause:** Empty query string

**Solution:** Ensure the `query` field in your request body is not empty:
```json
{
  "query": "your search term",  // Must not be empty
  "page": 1,
  "page_size": 20
}
```

### Issue: 500 Internal Server Error

**Cause:** Database connection issues or missing migrations

**Solution:**
1. Check database is running: `docker ps | grep postgres`
2. Run migrations: `docker exec horizon_search python -m alembic upgrade head`
3. Check logs: `docker logs horizon_search`

### Issue: Service not responding

**Cause:** Service not running or port conflict

**Solution:**
1. Check if container is running: `docker ps | grep horizon_search`
2. Check if port 8002 is available: `netstat -an | grep 8002`
3. Restart the service: `docker restart horizon_search`

## Required Permissions

The search service requires these permissions:

| Permission | Description | Endpoint |
|-----------|-------------|----------|
| `search.global` | Global search across all entity types | POST `/api/v1/search/global` |
| `search.local` | Local search within specific entity types | POST `/api/v1/search/{entity_type}` |

## Checking User Permissions

To see what permissions your user has:

```bash
curl --location 'http://localhost:8000/api/v1/identity/me' \
--header 'Authorization: Bearer YOUR_TOKEN'
```

Look for the `permissions` array in the response:
```json
{
  "user_id": "...",
  "email": "...",
  "permissions": ["search.global", "search.local", ...]
}
```

## Docker Logs

To view real-time logs:
```bash
docker logs -f horizon_search
```

To view last 100 lines:
```bash
docker logs horizon_search --tail 100
```

## Health Check

Verify the service is healthy:
```bash
curl http://localhost:8002/health
```

Expected response:
```json
{
  "status": "healthy",
  "service": "search-service",
  "version": "1.0.0",
  "environment": "development",
  "timestamp": "2026-02-09T...",
  "database": "connected"
}
```

## API Documentation

Access the interactive API documentation:
- Swagger UI: http://localhost:8002/docs
- ReDoc: http://localhost:8002/redoc
- OpenAPI JSON: http://localhost:8002/openapi.json
