# Quick Start: User Permissions API

## What is this?

Two new API endpoints that let you check what permissions a user has in an organization. Use this to show/hide UI elements without calling the backend repeatedly.

## Endpoints

### 1. Check My Permissions

```
GET /api/v1/users/me/permissions?organization_id={org_id}
Authorization: Bearer {token}
```

**Response:**

```json
{
  "user_id": "uuid",
  "organization_id": "uuid",
  "permissions": ["user.read", "item.create", "invoice.read"],
  "roles": ["Organization Administrator"],
  "has_access": true
}
```

### 2. Check Another User's Permissions (Admin)

```
GET /api/v1/users/{user_id}/permissions?organization_id={org_id}
Authorization: Bearer {token}
```

Requires `user.read` permission.

## Quick Examples

### cURL

```bash
# Get my permissions
curl -X GET "http://localhost:8000/api/v1/users/me/permissions?organization_id=11111111-1111-1111-1111-111111111111" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

### JavaScript/Fetch

```javascript
const response = await fetch(`/api/v1/users/me/permissions?organization_id=${orgId}`, {
  headers: { Authorization: `Bearer ${token}` },
});
const data = await response.json();

// Check permission
if (data.permissions.includes("user.create")) {
  // Show "Create User" button
}
```

### Python

```python
import requests

response = requests.get(
    f"{base_url}/api/v1/users/me/permissions",
    params={"organization_id": org_id},
    headers={"Authorization": f"Bearer {token}"}
)
data = response.json()

# Check permission
if "user.create" in data["permissions"]:
    # Show create button
```

## Common Use Cases

### 1. Navigation Menu

```javascript
const { permissions } = await getMyPermissions(orgId);

<nav>
  {permissions.includes("user.read") && <Link to="/users">Users</Link>}
  {permissions.includes("item.read") && <Link to="/items">Items</Link>}
  {permissions.includes("invoice.read") && <Link to="/invoices">Invoices</Link>}
</nav>;
```

### 2. Button Visibility

```javascript
{
  permissions.includes("user.create") && <button onClick={createUser}>Create User</button>;
}
```

### 3. Route Guards

```javascript
function ProtectedRoute({ permission, children }) {
  const { permissions } = usePermissions();

  if (!permissions.includes(permission)) {
    return <Navigate to="/unauthorized" />;
  }

  return children;
}
```

## Permission Format

Permissions follow the pattern: `{resource}.{action}`

Examples:

- `user.read` - View users
- `user.create` - Create users
- `item.update` - Update items
- `invoice.delete` - Delete invoices

Wildcards:

- `user.*` - All user permissions
- `*.*` - All permissions (system admin)

## Testing

Import the Postman collection:

```
identity-service/postman_collection_user_permissions.json
```

Or run the example script:

```bash
cd identity-service
python3 examples/check_user_permissions.py
```

## Important Notes

⚠️ **Security**: These endpoints are for UX only. Always validate permissions on the backend!

✅ **Caching**: Cache the response on the frontend to avoid repeated calls

✅ **Organization Context**: Always fetch permissions for the current organization

✅ **Refresh**: Update permissions when user switches organizations or roles change

## Full Documentation

See `identity-service/USER_PERMISSIONS_API.md` for complete documentation.

## Need Help?

- Check the example script: `identity-service/examples/check_user_permissions.py`
- Import Postman collection: `identity-service/postman_collection_user_permissions.json`
- Read full docs: `identity-service/USER_PERMISSIONS_API.md`
