# User Permissions API

## Overview

The User Permissions API provides endpoints to retrieve a user's permissions within an organization. This allows frontend applications to determine which UI elements, navigation items, and features a user can access without making additional backend calls to check permissions.

## Endpoints

### 1. Get My Permissions

**Endpoint:** `GET /api/v1/users/me/permissions`

**Description:** Get the current authenticated user's permissions within a specific organization.

**Authentication:** Required (Bearer token)

**Query Parameters:**

- `organization_id` (required): UUID of the organization to get permissions for

**Response:**

```json
{
  "user_id": "uuid",
  "organization_id": "uuid",
  "permissions": ["user.read", "user.create", "item.read", "item.update"],
  "roles": ["Organization Administrator"],
  "has_access": true
}
```

**Example Usage:**

```bash
curl -X GET "https://api.example.com/api/v1/users/me/permissions?organization_id=123e4567-e89b-12d3-a456-426614174000" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

**Use Cases:**

- Determine which navigation menu items to show
- Enable/disable UI buttons based on permissions
- Show/hide entire sections of the application
- Client-side route guards

---

### 2. Get User Permissions (Admin)

**Endpoint:** `GET /api/v1/users/{user_id}/permissions`

**Description:** Get a specific user's permissions within an organization. Requires `user.read` permission.

**Authentication:** Required (Bearer token)

**Path Parameters:**

- `user_id` (required): UUID of the user to get permissions for

**Query Parameters:**

- `organization_id` (required): UUID of the organization to get permissions for

**Response:**

```json
{
  "user_id": "uuid",
  "organization_id": "uuid",
  "permissions": ["user.read", "item.read"],
  "roles": ["User"],
  "has_access": true
}
```

**Example Usage:**

```bash
curl -X GET "https://api.example.com/api/v1/users/456e7890-e89b-12d3-a456-426614174000/permissions?organization_id=123e4567-e89b-12d3-a456-426614174000" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

**Use Cases:**

- Admin dashboards showing user permissions
- User management interfaces
- Audit and compliance reporting
- Debugging permission issues

---

## Response Fields

| Field             | Type             | Description                                                              |
| ----------------- | ---------------- | ------------------------------------------------------------------------ |
| `user_id`         | string (UUID)    | The user's unique identifier                                             |
| `organization_id` | string (UUID)    | The organization's unique identifier                                     |
| `permissions`     | array of strings | List of permission codes the user has (e.g., "user.read", "item.create") |
| `roles`           | array of strings | List of role names the user has in the organization                      |
| `has_access`      | boolean          | Whether the user has any access to the organization                      |

---

## Frontend Integration Examples

### React Example

```javascript
import { useEffect, useState } from "react";

function useUserPermissions(organizationId) {
  const [permissions, setPermissions] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function fetchPermissions() {
      try {
        const response = await fetch(
          `/api/v1/users/me/permissions?organization_id=${organizationId}`,
          {
            headers: {
              Authorization: `Bearer ${getAccessToken()}`,
            },
          },
        );
        const data = await response.json();
        setPermissions(data.permissions);
      } catch (error) {
        console.error("Failed to fetch permissions:", error);
      } finally {
        setLoading(false);
      }
    }

    fetchPermissions();
  }, [organizationId]);

  return { permissions, loading };
}

// Usage in component
function Navigation() {
  const { permissions, loading } = useUserPermissions(currentOrgId);

  if (loading) return <div>Loading...</div>;

  return (
    <nav>
      {permissions.includes("user.read") && <Link to="/users">Users</Link>}
      {permissions.includes("item.read") && <Link to="/items">Items</Link>}
      {permissions.includes("invoice.read") && <Link to="/invoices">Invoices</Link>}
    </nav>
  );
}
```

### Vue Example

```javascript
// composables/usePermissions.js
import { ref, onMounted } from 'vue';

export function usePermissions(organizationId) {
  const permissions = ref([]);
  const loading = ref(true);

  const hasPermission = (permission) => {
    return permissions.value.includes(permission);
  };

  onMounted(async () => {
    try {
      const response = await fetch(
        `/api/v1/users/me/permissions?organization_id=${organizationId}`,
        {
          headers: {
            'Authorization': `Bearer ${getAccessToken()}`
          }
        }
      );
      const data = await response.json();
      permissions.value = data.permissions;
    } catch (error) {
      console.error('Failed to fetch permissions:', error);
    } finally {
      loading.value = false;
    }
  });

  return { permissions, loading, hasPermission };
}

// Usage in component
<template>
  <nav v-if="!loading">
    <router-link v-if="hasPermission('user.read')" to="/users">
      Users
    </router-link>
    <router-link v-if="hasPermission('item.read')" to="/items">
      Items
    </router-link>
  </nav>
</template>

<script setup>
import { usePermissions } from '@/composables/usePermissions';

const { permissions, loading, hasPermission } = usePermissions(currentOrgId);
</script>
```

---

## Permission Codes

Common permission codes follow the pattern: `{resource}.{action}`

Examples:

- `user.read` - View users
- `user.create` - Create new users
- `user.update` - Update existing users
- `user.delete` - Delete users
- `item.read` - View items
- `item.create` - Create items
- `invoice.read` - View invoices
- `invoice.create` - Create invoices
- `org.read` - View organization details
- `org.update` - Update organization settings

Wildcard permissions:

- `user.*` - All user permissions
- `*.*` - All permissions (system admin)

---

## Error Responses

### 401 Unauthorized

```json
{
  "detail": "Invalid authentication credentials"
}
```

### 403 Forbidden

```json
{
  "detail": "You don't have access to this organization"
}
```

### 422 Validation Error

```json
{
  "detail": [
    {
      "loc": ["query", "organization_id"],
      "msg": "field required",
      "type": "value_error.missing"
    }
  ]
}
```

---

## Best Practices

1. **Cache Permissions**: Cache the permissions response on the frontend to avoid repeated API calls. Refresh when the user switches organizations or after role changes.

2. **Graceful Degradation**: If the permissions API fails, consider showing a minimal UI or redirecting to a safe default page.

3. **Server-Side Validation**: Always validate permissions on the backend. Frontend permission checks are for UX only, not security.

4. **Permission Helpers**: Create utility functions to check permissions consistently across your application.

5. **Loading States**: Show appropriate loading states while fetching permissions to avoid UI flicker.

6. **Organization Context**: Always fetch permissions for the current organization context. Update permissions when the user switches organizations.

---

## Security Notes

- These endpoints only return permissions for organizations the user is a member of
- The `/users/{user_id}/permissions` endpoint requires `user.read` permission
- Both the requesting user and target user must be members of the specified organization
- Permissions are fetched from active roles only (inactive roles are excluded)
- Only active permissions are returned (inactive permissions are excluded)
