# API Requirements for "Invite New User" Screen

## Screen Analysis

The UI screen requires:

1. **User Information**: Email, First Name, Last Name
2. **Role Assignment**: Dropdown to select a role
3. **Custom Permissions**: Checkboxes grouped by categories:
   - CRM & Sales
   - Inventory Management
   - Billing & Subscriptions

## Existing APIs ✅

### 1. Invitation API

- ✅ `POST /api/v1/identity/invitations` - Create invitation
  - **Current**: Accepts `role_id` but NOT custom permissions
  - **Schema**: `InvitationCreate` has `role_id` but no `permission_ids`

### 2. Roles API

- ✅ `GET /api/v1/identity/roles` - List roles for dropdown
  - Returns roles with `id`, `name`, `code`
  - Can filter by `organization_id`

### 3. Permissions API

- ✅ `GET /api/v1/identity/permissions` - List permissions
  - **Current**: Returns flat list, NOT grouped by category
  - Has `module` and `category` fields but no grouping endpoint

## Missing APIs ❌

### 1. **GET Permissions Grouped by Category**

**Endpoint**: `GET /api/v1/identity/permissions/grouped`
**Purpose**: Return permissions organized by category/module for the UI

**Response Format**:

```json
{
  "categories": [
    {
      "name": "CRM & Sales",
      "icon": "users",  // or icon identifier
      "permissions": [
        {
          "id": "uuid",
          "code": "lead.read",
          "name": "View Leads & Contacts",
          "description": "..."
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
      "permissions": [...]
    }
  ]
}
```

### 2. **POST Invitation with Custom Permissions**

**Option A**: Extend existing invitation endpoint

- Add `custom_permission_ids: list[UUID]` to `InvitationCreate` schema
- Store custom permissions in invitation (new table or JSON field)

**Option B**: New endpoint for custom permissions

- `POST /api/v1/identity/invitations/{invitation_id}/permissions`
- Assign custom permissions after invitation creation

**Option C**: Direct user permission assignment

- `POST /api/v1/identity/users/{user_id}/permissions`
- Assign permissions directly to user (bypassing role)

### 3. **User Permission Override API** (Optional but Recommended)

**Endpoint**: `POST /api/v1/identity/users/{user_id}/permissions/override`
**Purpose**: Assign custom permissions that override role permissions

**Request**:

```json
{
  "organization_id": "uuid",
  "permission_ids": ["uuid1", "uuid2", ...],
  "mode": "override" | "add" | "remove"
}
```

## Recommended Implementation

### Phase 1: Quick Win (Use Existing APIs)

1. Use `GET /api/v1/identity/permissions?module=crm` to get permissions by module
2. Group them on frontend by `category` field
3. Use existing invitation API with `role_id` only (no custom permissions yet)

### Phase 2: Add Missing APIs

1. **Create grouped permissions endpoint**
2. **Extend invitation schema** to include `custom_permission_ids`
3. **Update invitation service** to store and apply custom permissions on acceptance

### Phase 3: User Permission Management

1. **Add user-permission direct assignment** (if not using role-based only)
2. **Add permission override logic** (custom permissions override role permissions)

## Database Considerations

### Current Schema

- `invitations` table has `role_id` but no `permission_ids`
- `user_organization_roles` links user → role → permissions (via role_permissions)
- No direct `user_permissions` table

### Options for Custom Permissions

**Option 1: Add to Invitation Table**

```sql
ALTER TABLE invitations ADD COLUMN custom_permission_ids UUID[];
```

**Option 2: New Table**

```sql
CREATE TABLE invitation_custom_permissions (
  id UUID PRIMARY KEY,
  invitation_id UUID REFERENCES invitations(id),
  permission_id UUID REFERENCES permissions(id),
  created_at TIMESTAMP
);
```

**Option 3: User Direct Permissions Table**

```sql
CREATE TABLE user_custom_permissions (
  id UUID PRIMARY KEY,
  user_id UUID REFERENCES users(id),
  organization_id UUID REFERENCES organizations(id),
  permission_id UUID REFERENCES permissions(id),
  created_at TIMESTAMP,
  UNIQUE(user_id, organization_id, permission_id)
);
```

## Implementation Priority

1. **HIGH**: Grouped permissions endpoint (needed for UI)
2. **HIGH**: Extend invitation with custom permissions (core feature)
3. **MEDIUM**: User permission override API (advanced feature)
