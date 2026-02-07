# Invite User Screen - API Summary

## ✅ APIs You Already Have

### 1. **List Roles** (for dropdown)
```
GET /api/v1/identity/roles?organization_id={org_id}
```
- Returns list of roles with `id`, `name`, `code`
- Use for the "Assign Role" dropdown

### 2. **Create Invitation** (extended)
```
POST /api/v1/identity/invitations
```
**Request Body:**
```json
{
  "organization_id": "uuid",
  "email": "user@example.com",
  "first_name": "John",
  "last_name": "Doe",
  "role_id": "uuid",  // Optional - for dropdown selection
  "custom_permission_ids": ["uuid1", "uuid2"],  // NEW - for custom permissions
  "message": "Optional message"
}
```

## ✅ NEW APIs Added

### 1. **Get Permissions Grouped by Category** ⭐ NEW
```
GET /api/v1/identity/permissions/grouped?module={module}
```

**Response:**
```json
{
  "categories": [
    {
      "name": "CRM & Sales",
      "icon": "users",
      "module": "crm",
      "permissions": [
        {
          "id": "uuid",
          "code": "lead.read",
          "name": "View Leads & Contacts",
          "description": "...",
          "resource": "lead",
          "action": "read"
        },
        {
          "id": "uuid",
          "code": "lead.create",
          "name": "Create Leads & Contacts",
          "description": "..."
        }
      ]
    },
    {
      "name": "Inventory Management",
      "icon": "box",
      "module": "inventory",
      "permissions": [...]
    },
    {
      "name": "Billing & Subscriptions",
      "icon": "credit-card",
      "module": "billing",
      "permissions": [...]
    }
  ],
  "uncategorized": []
}
```

**Use Case:** Call this endpoint to populate the "Custom Permissions" section with checkboxes grouped by category.

## 📋 Implementation Checklist

### Frontend Implementation:

1. **Load Roles** (on modal open):
   ```javascript
   GET /api/v1/identity/roles?organization_id={current_org_id}
   // Populate "Assign Role" dropdown
   ```

2. **Load Permissions** (on modal open):
   ```javascript
   GET /api/v1/identity/permissions/grouped
   // Render checkboxes grouped by category
   // Each checkbox value = permission.id
   ```

3. **Submit Invitation**:
   ```javascript
   POST /api/v1/identity/invitations
   {
     organization_id: "...",
     email: "...",
     first_name: "...",
     last_name: "...",
     role_id: "...",  // From dropdown
     custom_permission_ids: [...],  // Selected checkbox IDs
     message: "..."
   }
   ```

## ⚠️ Important Notes

### Custom Permissions Storage
The `custom_permission_ids` field has been added to the invitation schema, but you'll need to:

1. **Update the database** to store custom permissions:
   - Option A: Add JSONB column to `invitations` table
   - Option B: Create `invitation_custom_permissions` junction table

2. **Update invitation service** to:
   - Store `custom_permission_ids` when creating invitation
   - Apply custom permissions when user accepts invitation

### Permission Override Logic
When a user accepts an invitation:
- If `role_id` is provided → assign role (which has its own permissions)
- If `custom_permission_ids` is provided → assign these permissions directly to user
- If both are provided → role permissions + custom permissions (or override, depending on your business logic)

## 🔄 Next Steps (Optional Enhancements)

1. **Update Invitation Service** to handle `custom_permission_ids`
2. **Add User Direct Permission Assignment API**:
   ```
   POST /api/v1/identity/users/{user_id}/permissions
   ```
3. **Add Permission Override Endpoint**:
   ```
   POST /api/v1/identity/users/{user_id}/permissions/override
   ```

## 📝 Example Frontend Code

```typescript
// Load data for modal
const [roles, setRoles] = useState([]);
const [permissions, setPermissions] = useState({ categories: [] });

useEffect(() => {
  // Load roles
  fetch(`/api/v1/identity/roles?organization_id=${orgId}`)
    .then(res => res.json())
    .then(data => setRoles(data.data));

  // Load grouped permissions
  fetch('/api/v1/identity/permissions/grouped')
    .then(res => res.json())
    .then(data => setPermissions(data));
}, []);

// Submit invitation
const handleSubmit = async (formData) => {
  const selectedPermissionIds = 
    Object.values(selectedPermissions).flat(); // Get all selected checkbox IDs

  await fetch('/api/v1/identity/invitations', {
    method: 'POST',
    body: JSON.stringify({
      ...formData,
      custom_permission_ids: selectedPermissionIds
    })
  });
};
```
