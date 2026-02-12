# User Permissions API Feature

## Summary

Created two new API endpoints to retrieve user permissions within an organization. This allows frontend applications to determine which UI elements, navigation items, and features a user can access without making additional backend calls.

## New Endpoints

### 1. GET /api/v1/users/me/permissions

- **Purpose**: Get current authenticated user's permissions in an organization
- **Authentication**: Required (Bearer token)
- **Parameters**: `organization_id` (query parameter)
- **Use Case**: Frontend navigation, UI element visibility, client-side route guards

### 2. GET /api/v1/users/{user_id}/permissions

- **Purpose**: Get any user's permissions in an organization (admin feature)
- **Authentication**: Required (Bearer token) + `user.read` permission
- **Parameters**: `user_id` (path), `organization_id` (query parameter)
- **Use Case**: Admin dashboards, user management, audit/compliance

## Response Format

```json
{
  "user_id": "uuid",
  "organization_id": "uuid",
  "permissions": ["user.read", "user.create", "item.read"],
  "roles": ["Organization Administrator"],
  "has_access": true
}
```

## Files Created/Modified

### Modified

- `identity-service/app/api/v1/endpoints/users.py` - Added two new endpoints

### Created

- `identity-service/tests/test_user_permissions.py` - Comprehensive test suite
- `identity-service/USER_PERMISSIONS_API.md` - Complete API documentation with examples
- `identity-service/examples/check_user_permissions.py` - Python example script
- `USER_PERMISSIONS_FEATURE.md` - This summary document

## Key Features

1. **Organization-scoped**: Permissions are always checked within a specific organization context
2. **Security**:
   - Users can only see permissions for organizations they belong to
   - Admin endpoint requires `user.read` permission
   - Returns empty permissions for users not in the organization
3. **Wildcard support**: Handles wildcard permissions like `user.*` and `*.*`
4. **Role information**: Returns both permissions and role names
5. **Access indicator**: `has_access` boolean for quick checks

## Frontend Integration

The API enables:

- **Dynamic navigation menus** - Show/hide menu items based on permissions
- **Conditional UI rendering** - Enable/disable buttons and features
- **Route guards** - Protect routes on the client side
- **Feature flags** - Control access to entire application sections
- **User experience** - Avoid showing "Access Denied" errors by hiding inaccessible features

## Example Usage

```javascript
// React example
const { permissions } = await fetchUserPermissions(orgId);

return (
  <nav>
    {permissions.includes("user.read") && <Link to="/users">Users</Link>}
    {permissions.includes("item.read") && <Link to="/items">Items</Link>}
    {permissions.includes("invoice.read") && (
      <Link to="/invoices">Invoices</Link>
    )}
  </nav>
);
```

## Testing

Run tests with:

```bash
cd identity-service
python3 -m pytest tests/test_user_permissions.py -v
```

Test coverage includes:

- Successful permission retrieval
- No access scenarios
- Authentication failures
- Missing parameters
- Permission checks
- Cross-organization access attempts

## Documentation

See `identity-service/USER_PERMISSIONS_API.md` for:

- Complete API reference
- Request/response examples
- Frontend integration guides (React, Vue)
- Error handling
- Best practices
- Security notes

## Next Steps

1. **Cache Strategy**: Implement frontend caching to reduce API calls
2. **Refresh Mechanism**: Add webhook/SSE for permission updates
3. **Batch Endpoint**: Consider adding bulk permission checks
4. **Permission Groups**: Group related permissions for easier UI management
5. **Audit Logging**: Log permission checks for compliance

## Benefits

✅ **Reduced Backend Calls**: Check permissions once, use throughout the session
✅ **Better UX**: Hide inaccessible features instead of showing errors
✅ **Faster Development**: Frontend developers can implement access control without backend changes
✅ **Security**: Server-side validation remains in place; this is UX-only
✅ **Flexibility**: Supports complex permission schemes with wildcards
✅ **Scalability**: Single API call provides all needed permission data
