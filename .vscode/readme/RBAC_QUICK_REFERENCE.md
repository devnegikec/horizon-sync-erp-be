## Role API Authentication - Quick Reference Guide

### Authentication & Authorization Pattern

Every authenticated endpoint follows this pattern:

```python
async def endpoint_function(
    # ... endpoint-specific parameters ...
    current_user: CurrentUser = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    # Step 1: Check permission
    require_permission(current_user.permissions, "permission:code")
    
    # Step 2: Validate organization membership (for org-scoped operations)
    validate_user_in_organization(current_user.id, organization_id, db)
    
    # Step 3: Check system role protection (if modifying system roles)
    if existing_role["is_system"] and not is_system_admin(current_user.permissions):
        raise HTTPException(status_code=403, detail="Cannot modify system roles...")
    
    # Step 4: Perform business logic
    # ...
    
    # Step 5: Log with user context
    logger.info(f"User {current_user.id} performed action...")
```

---

## All 10 Endpoints At A Glance

| # | Method | Endpoint | Permission | Org Check | Sys Role Check |
|---|--------|----------|-----------|-----------|---|
| 1 | GET | /roles | `roles:read` | ✓ | ✗ |
| 2 | GET | /roles/{id} | `roles:read` | ✓ | ✗ |
| 3 | POST | /roles | `roles:create` | ✓ | ✗ |
| 4 | PUT | /roles/{id} | `roles:update` | ✓ | ✓ |
| 5 | DELETE | /roles/{id} | `roles:delete` | ✓ | ✓ |
| 6 | GET | /roles/{id}/permissions | `roles:read` | ✓ | ✗ |
| 7 | POST | /roles/{id}/permissions | `roles:manage_perms` | ✓ | ✓ |
| 8 | DELETE | /roles/{id}/permissions/{pid} | `roles:manage_perms` | ✓ | ✓ |
| 9 | POST | /roles/{id}/permissions/bulk | `roles:manage_perms` | ✓ | ✓ |
| 10 | GET | /roles/{id}/users | `roles:view_users` | ✓ | ✗ |

**Legend:**
- `Permission`: Required permission code to check
- `Org Check`: Validates user is in organization ✓ = yes, ✗ = no
- `Sys Role Check`: Prevents non-admins from modifying system roles ✓ = yes, ✗ = no

---

## Adding Authentication to a New Endpoint

To add authentication to any new endpoint:

### 1. Add Dependency
```python
from app.dependencies import CurrentUser, get_current_active_user
from sqlalchemy.orm import Session
from app.database import get_db

async def my_endpoint(
    # ... other parameters ...
    current_user: CurrentUser = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
```

### 2. Import Authorization Functions
```python
from app.core.authorization import (
    check_permission,
    is_system_admin,
    require_permission,
    validate_user_in_organization,
)
```

### 3. Add Permission Check
```python
# At the start of endpoint logic
require_permission(current_user.permissions, "permission:code")
```

### 4. Add Organization Validation (if multi-tenant)
```python
# Validate user is in the organization
validate_user_in_organization(current_user.id, org_id, db)
```

### 5. Add System Role Check (if modifying roles)
```python
# Check if role is system role
if role["is_system"] and not is_system_admin(current_user.permissions):
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Cannot modify system roles",
    )
```

### 6. Log with User Context
```python
logger.info(f"User {current_user.id} performed action...")
```

---

## Testing Authenticated Endpoints

### Test Fixture Dependencies

```python
# Get authenticated client
def test_something(client):
    # client is already authenticated as test_user
    response = client.get("/api/v1/roles")
    assert response.status_code == 200

# Test authentication failure
def test_auth_failure(client_no_override, access_token):
    # client_no_override requires explicit Bearer token
    headers = {"Authorization": f"Bearer {access_token}"}
    response = client_no_override.get("/api/v1/roles")
    # No token = 401 Unauthorized

# Test permission failure
def test_permission_failure(client_no_override, db_session, 
                           test_user_without_permission, access_token):
    from app.dependencies import get_current_active_user
    
    def override_get_current_active_user():
        return test_user_without_permission
    
    client_no_override.app.dependency_overrides[get_current_active_user] = override_get_current_active_user
    
    headers = {"Authorization": f"Bearer {access_token}"}
    response = client_no_override.get("/api/v1/roles", headers=headers)
    assert response.status_code == 403  # Forbidden
    
    # Clean up overrides
    client_no_override.app.dependency_overrides.clear()

# Test organization boundary
def test_org_boundary(client_no_override, db_session,
                     test_user_other_org, test_org_role, access_token_other_user):
    from app.dependencies import get_current_active_user
    
    def override_get_current_active_user():
        return test_user_other_org
    
    client_no_override.app.dependency_overrides[get_current_active_user] = override_get_current_active_user
    
    headers = {"Authorization": f"Bearer {access_token_other_user}"}
    response = client_no_override.get(
        f"/api/v1/roles/{test_org_role.id}",
        headers=headers
    )
    assert response.status_code == 403  # Forbidden - different org
    
    client_no_override.app.dependency_overrides.clear()

# Test system role protection
def test_system_role_protection(client_no_override, db_session,
                               test_user_without_permission, test_system_role):
    from app.dependencies import get_current_active_user
    
    def override_get_current_active_user():
        return test_user_without_permission
    
    client_no_override.app.dependency_overrides[get_current_active_user] = override_get_current_active_user
    
    response = client_no_override.put(
        f"/api/v1/roles/{test_system_role.id}",
        json={"name": "Hacked"}
    )
    assert response.status_code == 403  # Forbidden - system role
    
    client_no_override.app.dependency_overrides.clear()
```

### Available Test Fixtures

| Fixture | Type | Description |
|---------|------|-------------|
| `client` | TestClient | Pre-authenticated as test_user (system admin) |
| `client_no_override` | TestClient | No auth overrides, requires Bearer token |
| `test_user` | User | System admin with all permissions |
| `test_user_without_permission` | User | Regular user with no special permissions |
| `test_user_other_org` | User | Admin from different organization |
| `test_organization` | Organization | Test organization |
| `test_permissions` | dict | All test permissions (roles:read, roles:create, etc.) |
| `test_system_role` | Role | System role (protected) |
| `test_org_role` | Role | Organization role with full permissions |
| `test_limited_role` | Role | Role with only read permission |
| `access_token` | str | Valid JWT token for test_user |
| `access_token_other_user` | str | Valid JWT token for test_user_other_org |
| `expired_token` | str | Expired JWT token |
| `db_session` | Session | Database session for tests |

---

## Permission Codes Reference

### Role Management
| Code | Purpose | Used By |
|------|---------|---------|
| `roles:read` | Read role information | LIST, GET |
| `roles:create` | Create new roles | CREATE |
| `roles:update` | Update existing roles | UPDATE |
| `roles:delete` | Delete roles | DELETE |
| `roles:manage_perms` | Manage role-permission mappings | ASSIGN, REMOVE, BULK |
| `roles:view_users` | View users with specific role | GET USERS |

### System Permissions
| Code | Purpose | Used By |
|------|---------|---------|
| `perms:read` | Read permissions | Permission endpoints |
| `users:read` | Read user information | User endpoints |

---

## Common Issues & Solutions

### Issue: 401 Unauthorized
**Causes:**
- Missing Authorization header
- Invalid Bearer token format
- Expired token

**Solution:**
```python
# Correct format: Authorization: Bearer <token>
headers = {"Authorization": f"Bearer {valid_token}"}
response = client.get("/api/v1/roles", headers=headers)
```

### Issue: 403 Forbidden
**Causes:**
- Missing required permission
- User not in organization
- Non-admin trying to modify system role

**Solution:**
1. Check permission is assigned to user's role
2. Verify user is in the organization
3. Verify user is system admin if modifying system roles

```python
# Debug: Check current_user.permissions
from app.core.authorization import check_permission

try:
    check_permission(current_user.permissions, "roles:read")
except Exception as e:
    print(f"Missing permission: {e}")
```

### Issue: 404 Not Found
**Causes:**
- Role doesn't exist
- Wrong UUID format
- Role in different organization

**Solution:**
```python
# Verify role exists and is in user's organization
role = db.query(Role).filter(Role.id == role_id).first()
if not role:
    raise HTTPException(status_code=404, detail="Role not found")
```

---

## Best Practices

1. **Always check permissions first** - Do it at the start of the endpoint
2. **Validate organization membership** - Before accessing any org-scoped data
3. **Check system role status** - For any role modification operations
4. **Log with user context** - Include user_id in all logs for audit trail
5. **Use appropriate status codes** - 401 for auth, 403 for authz, 404 for not found
6. **Document requirements** - Update docstring with auth and permission requirements
7. **Test all scenarios** - Auth, authz, org boundaries, success cases
8. **Use dependency injection** - FastAPI's Depends() is cleaner than checking manually

---

## HTTP Status Code Meanings

| Code | Name | When to Use |
|------|------|-----------|
| 200 | OK | Successful read or update |
| 201 | Created | Successful resource creation |
| 204 | No Content | Successful deletion (no body) |
| 400 | Bad Request | Invalid request data |
| 401 | Unauthorized | Missing/invalid authentication |
| 403 | Forbidden | Missing permissions or org boundary violation |
| 404 | Not Found | Resource doesn't exist |
| 409 | Conflict | Duplicate data or constraint violation |
| 500 | Server Error | Unexpected server error |

---

## Architecture Diagram

```
Client Request with Bearer Token
           ↓
    FastAPI Endpoint
           ↓
  get_current_active_user (JWT validation)
           ↓ ✓ Valid Token, ✗ 401 Unauthorized
    Endpoint Function
           ↓
  require_permission() check
           ↓ ✓ Has permission, ✗ 403 Forbidden
  validate_user_in_organization() check
           ↓ ✓ In org, ✗ 403 Forbidden
  is_system_admin() check (if needed)
           ↓ ✓ Can modify, ✗ 403 Forbidden
    Business Logic
           ↓
    Log with user_id
           ↓
    Return Response (200/201/204/404/409)
```

---

## For More Information

- **API Specification**: See `COMPLETE_API_SPECIFICATION.md`
- **Quick API Reference**: See `API_QUICK_REFERENCE.md`
- **API Contract**: See `API_CONTRACT.md`
- **Full Implementation Summary**: See `RBAC_IMPLEMENTATION_SUMMARY.md`
- **Test Examples**: See `tests/test_roles_auth.py`
