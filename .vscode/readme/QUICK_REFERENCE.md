# Quick Reference: Running Test Cases

## File Locations
```
identity-service/
├── tests/
│   ├── test_roles_api.py                  # 79 test cases for role endpoints
│   ├── test_permissions_api.py            # 39 test cases for permission endpoints
│   ├── TEST_CASES_DOCUMENTATION.md        # Detailed documentation
│   ├── IMPLEMENTATION_SUMMARY.md          # Summary of what was created
│   └── conftest.py                        # Pytest fixtures & configuration
```

## Quick Commands

### Run All API Tests
```bash
cd d:\Code\CRM_NEW\horizon-sync-erp-be
docker compose down
docker compose up -d --build
docker compose exec identity-service pytest tests/test_roles_api.py tests/test_permissions_api.py -v
```

### Run Roles API Tests Only
```bash
docker compose exec identity-service pytest tests/test_roles_api.py -v
```

### Run Permissions API Tests Only
```bash
docker compose exec identity-service pytest tests/test_permissions_api.py -v
```

### Run Specific Test Class
```bash
# List roles tests
docker compose exec identity-service pytest tests/test_roles_api.py::TestListRolesEndpoint -v

# Create role tests
docker compose exec identity-service pytest tests/test_roles_api.py::TestCreateRoleEndpoint -v

# List permissions tests
docker compose exec identity-service pytest tests/test_permissions_api.py::TestListPermissionsEndpoint -v
```

### Run Single Test Case
```bash
docker compose exec identity-service pytest tests/test_roles_api.py::TestListRolesEndpoint::test_list_roles_with_valid_auth -v
```

### Run with Coverage Report
```bash
docker compose exec identity-service pytest tests/test_roles_api.py tests/test_permissions_api.py --cov=app --cov-report=html
# View report at: identity-service/htmlcov/index.html
```

### Run Locally (without Docker)
```bash
cd identity-service
python -m pytest tests/test_roles_api.py tests/test_permissions_api.py -v
```

## Test Statistics

### Roles API (test_roles_api.py)
- **Total Tests**: 79
- **Test Classes**: 10
- **Endpoints Covered**: 10
- **Coverage Areas**:
  - ✅ GET /roles (10 tests)
  - ✅ GET /roles/{id} (6 tests)
  - ✅ POST /roles (7 tests)
  - ✅ PUT /roles/{id} (7 tests)
  - ✅ DELETE /roles/{id} (4 tests)
  - ✅ GET /roles/{id}/permissions (6 tests)
  - ✅ POST /roles/{id}/permissions (6 tests)
  - ✅ DELETE /roles/{id}/permissions/{perm_id} (4 tests)
  - ✅ POST /roles/{id}/permissions/bulk (5 tests)
  - ✅ GET /roles/{id}/users (5 tests)

### Permissions API (test_permissions_api.py)
- **Total Tests**: 39
- **Test Classes**: 7
- **Endpoints Covered**: 5
- **Coverage Areas**:
  - ✅ GET /permissions (10 tests)
  - ✅ GET /permissions/{id} (4 tests)
  - ✅ POST /permissions (6 tests)
  - ✅ PUT /permissions/{id} (7 tests)
  - ✅ DELETE /permissions/{id} (4 tests)
  - ✅ Filter combinations (5 tests)
  - ✅ Response structure (3 tests)

## What Gets Tested

### Roles Tests Include:
✅ Authentication (401 checks)
✅ Authorization (permission validation)
✅ CRUD operations (create, read, update, delete)
✅ Pagination (skip, limit)
✅ Filtering (organization, active, system)
✅ Search functionality
✅ Permission assignment
✅ Bulk operations
✅ Error handling (404, 409, 400, 422)
✅ System role protection
✅ Response structure validation

### Permissions Tests Include:
✅ CRUD operations (create, read, update, delete)
✅ Pagination (skip, limit)
✅ Filtering (resource, action, module, active)
✅ Search functionality
✅ Multi-filter combinations
✅ Duplicate prevention (409)
✅ Error handling (404, 400, 422)
✅ Response structure validation
✅ Extra data handling

## Expected Output

When tests pass, you should see:
```
collected 118 items

tests/test_roles_api.py::TestListRolesEndpoint::test_list_roles_without_auth PASSED
tests/test_roles_api.py::TestListRolesEndpoint::test_list_roles_with_valid_auth PASSED
tests/test_roles_api.py::TestListRolesEndpoint::test_list_roles_with_pagination PASSED
...
tests/test_permissions_api.py::TestListPermissionsEndpoint::test_list_permissions_success PASSED
...

===================== 118 passed in 35.42s =====================
```

## Fixtures Available

Tests use these pytest fixtures from conftest.py:

```python
db_session                    # In-memory SQLite database
test_organization            # Test organization record
test_user                    # System admin user with full permissions
test_user_without_permission # User with limited permissions
test_user_other_org          # User in different organization
test_permissions             # Dict of test permission records
test_system_role             # System admin role
test_org_role                # Organization admin role
test_limited_role            # Standard user role
test_user_org_role          # User-organization-role mapping
client                       # Authenticated FastAPI TestClient
client_no_override          # Unauthenticated TestClient
access_token                # Valid JWT access token
expired_token               # Expired JWT token
```

## Common Test Scenarios

### Test without authentication
```python
def test_endpoint_without_auth(self, client_no_override):
    response = client_no_override.get("/api/v1/roles")
    assert response.status_code == status.HTTP_401_UNAUTHORIZED
```

### Test with authentication
```python
def test_endpoint_with_auth(self, client):
    response = client.get("/api/v1/roles")
    assert response.status_code == status.HTTP_200_OK
```

### Test with pagination
```python
response = client.get("/api/v1/roles?skip=0&limit=10")
assert response.json()["limit"] == 10
```

### Test with filters
```python
response = client.get(f"/api/v1/roles?organization_id={org_id}&is_active=true")
assert response.status_code == status.HTTP_200_OK
```

### Test error handling
```python
response = client.get(f"/api/v1/roles/{fake_id}")
assert response.status_code == status.HTTP_404_NOT_FOUND
```

## Troubleshooting

### Tests fail with "module not found"
```bash
docker compose down
docker compose up -d --build
```

### Tests fail with database errors
```bash
# Check if containers are running
docker compose ps

# View logs
docker compose logs identity-service

# Rebuild everything
docker compose down -v
docker compose up -d --build
```

### Tests timeout
- Increase timeout in pytest.ini if needed
- Check if containers have sufficient resources
- Run fewer tests to isolate issue

### Authentication/Permission errors
- Verify test_user fixture has proper roles
- Check test_user_org_role is created
- Ensure JWT token is valid and not expired

## CI/CD Integration

### GitHub Actions Example
```yaml
- name: Run API Tests
  run: |
    cd identity-service
    docker compose up -d --build
    docker compose exec -T identity-service pytest \
      tests/test_roles_api.py \
      tests/test_permissions_api.py \
      --cov=app \
      --junitxml=test-results.xml
    docker compose down
```

## Documentation

For more details, see:
- [TEST_CASES_DOCUMENTATION.md](TEST_CASES_DOCUMENTATION.md) - Complete test documentation
- [IMPLEMENTATION_SUMMARY.md](IMPLEMENTATION_SUMMARY.md) - What was implemented

## Next Steps

1. ✅ Run the tests to verify everything works
2. ✅ Check coverage report: `htmlcov/index.html`
3. ✅ Add to CI/CD pipeline
4. ✅ Integrate with team development workflow
5. ✅ Update as new endpoints are added

## Support

For issues or questions:
1. Check TEST_CASES_DOCUMENTATION.md for detailed information
2. Review test implementation in test_roles_api.py and test_permissions_api.py
3. Verify conftest.py fixtures are properly configured
4. Check Docker container logs for errors
