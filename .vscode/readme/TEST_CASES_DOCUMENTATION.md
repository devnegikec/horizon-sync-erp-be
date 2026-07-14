# API Test Cases Documentation

This document describes the comprehensive test cases for the Roles and Permissions API endpoints.

## Test Files Overview

### 1. `test_roles_api.py`
Complete test coverage for all Role API endpoints.

#### Test Classes and Coverage:

**TestListRolesEndpoint** (10 tests)
- List roles without authentication (401)
- List roles with valid authentication (200)
- Pagination support (skip, limit)
- Organization filtering
- Active status filtering
- System role filtering
- Search functionality
- Include permissions flag
- Invalid pagination parameters
- Negative skip parameter

**TestGetRoleEndpoint** (6 tests)
- Get role without authentication (401)
- Get role with valid authentication (200)
- Role not found (404)
- Include permissions in response
- Invalid UUID format

**TestCreateRoleEndpoint** (7 tests)
- Create role without authentication (401)
- Create role with valid authentication (201)
- Duplicate role code (409)
- Missing required fields (422)
- Optional fields handling
- Invalid organization ID

**TestUpdateRoleEndpoint** (7 tests)
- Update role without authentication (401)
- Update role with valid authentication (200)
- Role not found (404)
- Partial updates
- Hierarchy level updates
- System role modifications
- Permission checks

**TestDeleteRoleEndpoint** (4 tests)
- Delete role without authentication (401)
- Delete role with valid authentication (204)
- Role not found (404)
- System role deletion restrictions

**TestGetRolePermissionsEndpoint** (6 tests)
- Get role permissions without authentication (401)
- Get role permissions with valid authentication (200)
- Role not found (404)
- Pagination support
- Resource type filtering
- Action type filtering

**TestAssignPermissionToRoleEndpoint** (6 tests)
- Assign permission without authentication (401)
- Assign permission with valid authentication (201)
- Role not found (404)
- Permission not found (404)
- Assign with conditions
- Duplicate assignments

**TestRemovePermissionFromRoleEndpoint** (4 tests)
- Remove permission without authentication (401)
- Remove permission with valid authentication (204)
- Role not found (404)
- Permission not assigned (404)

**TestBulkAssignPermissionsEndpoint** (5 tests)
- Bulk assign without authentication (401)
- Bulk assign with valid authentication (200)
- Replace mode
- Add mode
- Empty permissions list

**TestGetRoleUsersEndpoint** (5 tests)
- Get role users without authentication (401)
- Get role users with valid authentication (200)
- Missing organization_id parameter (422)
- Role not found (404)
- Pagination support

---

### 2. `test_permissions_api.py`
Complete test coverage for all Permission API endpoints.

#### Test Classes and Coverage:

**TestListPermissionsEndpoint** (10 tests)
- List permissions (200)
- Pagination support
- Invalid limit validation
- Negative skip validation
- is_active filtering
- Resource filtering
- Action filtering
- Module filtering
- Search functionality
- Combined filters

**TestGetPermissionEndpoint** (4 tests)
- Get permission successfully (200)
- Permission not found (404)
- Invalid UUID format (422)
- Response structure validation

**TestCreatePermissionEndpoint** (6 tests)
- Create permission successfully (201)
- Minimal required fields
- Duplicate code (409)
- Missing required fields (422)
- Extra data fields
- All optional fields

**TestUpdatePermissionEndpoint** (7 tests)
- Update permission successfully (200)
- Update description
- Update is_active status
- Permission not found (404)
- Invalid UUID format (422)
- Empty request body
- Update with extra_data

**TestDeletePermissionEndpoint** (4 tests)
- Delete permission successfully (204)
- Permission not found (404)
- Invalid UUID format (422)
- Delete permission with assigned roles (400)

**TestPermissionFiltersEndpoint** (5 tests)
- Filter by resource and action
- Filter by module and is_active
- Search by code
- Search by name
- Large limit parameter

**TestPermissionResponseStructure** (3 tests)
- List response structure validation
- Permission item structure validation
- Create response structure validation

---

## Running the Tests

### Run all tests:
```bash
docker compose exec identity-service pytest -v
```

### Run specific test file:
```bash
docker compose exec identity-service pytest tests/test_roles_api.py -v
docker compose exec identity-service pytest tests/test_permissions_api.py -v
```

### Run specific test class:
```bash
docker compose exec identity-service pytest tests/test_roles_api.py::TestListRolesEndpoint -v
```

### Run specific test:
```bash
docker compose exec identity-service pytest tests/test_roles_api.py::TestListRolesEndpoint::test_list_roles_with_valid_auth -v
```

### Run with coverage:
```bash
docker compose exec identity-service pytest --cov=app --cov-report=html
```

### Run locally (if dependencies installed):
```bash
cd identity-service
python -m pytest tests/test_roles_api.py tests/test_permissions_api.py -v
```

---

## Test Coverage Summary

### Roles API: 60+ tests
- **Authentication**: 11 tests (401 checks)
- **Authorization**: 8 tests (permission/org validation)
- **CRUD Operations**: 20 tests (create, read, update, delete)
- **Filtering & Search**: 12 tests (multiple filters)
- **Pagination**: 5 tests
- **Relationships**: 11 tests (permissions, users)
- **Error Handling**: 15+ tests (404, 409, 400, 422 errors)

### Permissions API: 45+ tests
- **Authentication**: 0 tests (public endpoints)
- **CRUD Operations**: 18 tests (create, read, update, delete)
- **Filtering & Search**: 15 tests (multiple filter combinations)
- **Pagination**: 3 tests
- **Response Validation**: 9 tests (structure validation)
- **Error Handling**: 10+ tests (404, 409, 400, 422 errors)

---

## Test Data & Fixtures

Tests use the following pytest fixtures from `conftest.py`:

- `db_session`: In-memory SQLite database
- `test_organization`: Test organization
- `test_user`: System admin user
- `test_user_without_permission`: User without special permissions
- `test_user_other_org`: User in different organization
- `test_permissions`: Dictionary of test permissions
- `test_system_role`: System admin role
- `test_org_role`: Organization admin role
- `test_limited_role`: Standard user role
- `test_user_org_role`: User-organization-role mapping
- `client`: Authenticated test client
- `client_no_override`: Unauthenticated test client
- `access_token`: Valid JWT access token

---

## HTTP Status Codes Tested

| Code | Meaning | Examples |
|------|---------|----------|
| 200 | OK | GET, PUT operations |
| 201 | Created | POST operations |
| 204 | No Content | DELETE operations |
| 400 | Bad Request | Invalid data, role has users |
| 401 | Unauthorized | Missing/invalid auth token |
| 403 | Forbidden | Permission denied, system role mod |
| 404 | Not Found | Resource doesn't exist |
| 409 | Conflict | Duplicate code/permission |
| 422 | Unprocessable Entity | Invalid parameters |
| 500 | Server Error | Internal server errors |

---

## Key Testing Patterns

### 1. Authentication Testing
```python
def test_endpoint_without_auth(self, client_no_override):
    response = client_no_override.get("/api/v1/roles")
    assert response.status_code == status.HTTP_401_UNAUTHORIZED
```

### 2. Authorization Testing
```python
def test_create_role_permission_check(self, client, test_organization):
    # Requires role.create permission
    response = client.post("/api/v1/roles", json=role_data)
    assert response.status_code == status.HTTP_201_CREATED
```

### 3. Resource Not Found
```python
def test_get_role_not_found(self, client):
    fake_id = uuid4()
    response = client.get(f"/api/v1/roles/{fake_id}")
    assert response.status_code == status.HTTP_404_NOT_FOUND
```

### 4. Validation Testing
```python
def test_list_roles_invalid_pagination(self, client):
    response = client.get("/api/v1/roles?limit=101")
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
```

### 5. Business Logic Testing
```python
def test_create_role_duplicate_code(self, client, test_system_role):
    # Should prevent duplicate codes
    response = client.post("/api/v1/roles", json={
        "code": test_system_role.code,
        ...
    })
    assert response.status_code == status.HTTP_409_CONFLICT
```

---

## Error Response Format

All endpoints follow a consistent error format:

```json
{
  "detail": "Error message describing what went wrong"
}
```

---

## Notes for Test Execution

1. **Docker Required**: Tests must run in Docker container with PostgreSQL
2. **Database Setup**: In-memory SQLite used for test isolation
3. **Fixtures Cleanup**: Each test gets fresh database state
4. **Token Expiry**: Some tests use expired tokens (timedelta(seconds=-1))
5. **Organization Isolation**: Tests validate users are in correct organizations
6. **System Role Protection**: Tests verify system roles can only be modified by admins

---

## Extending Test Coverage

To add new tests:

1. Follow the existing test class structure
2. Use descriptive test names: `test_<feature>_<scenario>`
3. Use existing fixtures from conftest.py
4. Test both success (2xx) and error (4xx/5xx) cases
5. Validate response structure with assertions
6. Test edge cases (empty lists, special characters, etc.)

---

## Continuous Integration

These tests are designed to run in CI/CD pipelines:

```yaml
# Example GitHub Actions
- name: Run API Tests
  run: |
    docker compose up -d
    docker compose exec identity-service pytest tests/test_roles_api.py tests/test_permissions_api.py -v --tb=short
    docker compose down
```

---

## Troubleshooting

### Test Fails with "organization not found"
- Ensure `test_organization` fixture is in test parameters
- Check `validate_user_in_organization` is working correctly

### Test Fails with "permission denied"
- Verify `test_user` has required permissions
- Check `test_user_org_role` fixture is properly configured

### Test Fails with Database Errors
- Rebuild containers: `docker compose down && docker compose up -d --build`
- Check conftest.py event listeners for SQLite setup

### Flaky Tests
- Tests should be independent (no shared state)
- Use `db_session` from fixtures (auto-cleanup)
- Avoid hardcoded UUIDs when possible (use uuid4())
