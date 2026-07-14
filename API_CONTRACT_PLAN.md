# API Contract Plan: Roles, Permissions, and Role-Permissions

## Database Schema Overview

### 1. **Permissions Table**

```
id (UUID): Primary Key
code (String[100]): Unique identifier (e.g., "user:create", "invoice:read")
name (String[100]): Human-readable name
description (Text): Detailed description
resource (Enum: ResourceType): Which resource (users, roles, invoices, etc.)
action (Enum: ActionType): Action type (create, read, update, delete)
module (String[50]): Module name (e.g., "auth", "accounting", "inventory")
category (String[50]): Category (e.g., "admin", "user_management")
is_active (Boolean): Active/Inactive status
extra_data (JSON): Additional metadata
created_at (DateTime): Timestamp
updated_at (DateTime): Timestamp
```

### 2. **Roles Table**

```
id (UUID): Primary Key
organization_id (UUID): Foreign Key to organizations
name (String[100]): Role name (e.g., "Admin", "Manager", "Viewer")
code (String[50]): Unique code within org (e.g., "admin", "manager")
description (Text): Role description
is_system (Boolean): System role flag (cannot be deleted)
is_default (Boolean): Default role for new users
hierarchy_level (Integer): Role hierarchy level (0=highest)
is_active (Boolean): Active/Inactive status
extra_data (JSON): Additional metadata
created_at (DateTime): Timestamp
updated_at (DateTime): Timestamp
```

### 3. **Role_Permissions Table** (Junction)

```
id (UUID): Primary Key
role_id (UUID): Foreign Key to roles
permission_id (UUID): Foreign Key to permissions
conditions (JSON): Optional conditional permissions (e.g., department restrictions)
```

---

## API Endpoint Structure

### Base Path: `/api/v1/roles`, `/api/v1/permissions`

---

## 1. PERMISSIONS API

### 1.1 List All Permissions

**Endpoint:** `GET /api/v1/permissions`

**Query Parameters:**

- `skip` (int, default: 0): Pagination offset
- `limit` (int, default: 10): Pagination limit
- `is_active` (bool, optional): Filter by active status
- `resource` (string, optional): Filter by resource type
- `action` (string, optional): Filter by action type
- `module` (string, optional): Filter by module
- `search` (string, optional): Search by name or code

**Response (200 OK):**

```json
{
  "data": [
    {
      "id": "uuid",
      "code": "user:create",
      "name": "Create User",
      "description": "Permission to create new users",
      "resource": "users",
      "action": "create",
      "module": "auth",
      "category": "user_management",
      "is_active": true,
      "extra_data": {},
      "created_at": "2026-01-25T10:00:00Z",
      "updated_at": "2026-01-25T10:00:00Z"
    }
  ],
  "total": 100,
  "skip": 0,
  "limit": 10
}
```

---

### 1.2 Get Permission by ID

**Endpoint:** `GET /api/v1/permissions/{permission_id}`

**Response (200 OK):**

```json
{
  "id": "uuid",
  "code": "user:create",
  "name": "Create User",
  "description": "Permission to create new users",
  "resource": "users",
  "action": "create",
  "module": "auth",
  "category": "user_management",
  "is_active": true,
  "extra_data": {},
  "created_at": "2026-01-25T10:00:00Z",
  "updated_at": "2026-01-25T10:00:00Z"
}
```

---

### 1.3 Create Permission

**Endpoint:** `POST /api/v1/permissions`

**Request Body:**

```json
{
  "code": "user:create",
  "name": "Create User",
  "description": "Permission to create new users",
  "resource": "users",
  "action": "create",
  "module": "auth",
  "category": "user_management",
  "is_active": true,
  "extra_data": {}
}
```

**Response (201 Created):**

```json
{
  "id": "uuid",
  "code": "user:create",
  "name": "Create User",
  "description": "Permission to create new users",
  "resource": "users",
  "action": "create",
  "module": "auth",
  "category": "user_management",
  "is_active": true,
  "extra_data": {},
  "created_at": "2026-01-25T10:00:00Z",
  "updated_at": "2026-01-25T10:00:00Z"
}
```

**Error (400 Bad Request):**

```json
{
  "detail": "Code 'user:create' already exists"
}
```

---

### 1.4 Update Permission

**Endpoint:** `PUT /api/v1/permissions/{permission_id}`

**Request Body:**

```json
{
  "name": "Create New User",
  "description": "Updated description",
  "is_active": true,
  "extra_data": {}
}
```

**Response (200 OK):**

```json
{
  "id": "uuid",
  "code": "user:create",
  "name": "Create New User",
  "description": "Updated description",
  "resource": "users",
  "action": "create",
  "module": "auth",
  "category": "user_management",
  "is_active": true,
  "extra_data": {},
  "created_at": "2026-01-25T10:00:00Z",
  "updated_at": "2026-01-25T10:30:00Z"
}
```

---

### 1.5 Delete Permission

**Endpoint:** `DELETE /api/v1/permissions/{permission_id}`

**Response (204 No Content)**

**Error (400 Bad Request):**

```json
{
  "detail": "Cannot delete permission with active role assignments"
}
```

---

### 1.6 Bulk Assign Permissions to Role

**Endpoint:** `POST /api/v1/permissions/bulk-assign`

**Request Body:**

```json
{
  "role_id": "uuid",
  "permission_ids": ["uuid1", "uuid2", "uuid3"]
}
```

**Response (200 OK):**

```json
{
  "message": "Successfully assigned 3 permissions to role",
  "role_id": "uuid",
  "assigned_count": 3
}
```

---

## 2. ROLES API

### 2.1 List All Roles

**Endpoint:** `GET /api/v1/roles`

**Query Parameters:**

- `skip` (int, default: 0): Pagination offset
- `limit` (int, default: 10): Pagination limit
- `organization_id` (UUID, optional): Filter by organization (required for non-admin)
- `is_active` (bool, optional): Filter by active status
- `is_system` (bool, optional): Filter by system role flag
- `search` (string, optional): Search by name or code
- `include_permissions` (bool, default: false): Include permissions in response

**Response (200 OK):**

```json
{
  "data": [
    {
      "id": "uuid",
      "organization_id": "uuid",
      "name": "Admin",
      "code": "admin",
      "description": "System administrator role",
      "is_system": true,
      "is_default": false,
      "hierarchy_level": 0,
      "is_active": true,
      "extra_data": {},
      "created_at": "2026-01-25T10:00:00Z",
      "updated_at": "2026-01-25T10:00:00Z",
      "permissions": []
    }
  ],
  "total": 5,
  "skip": 0,
  "limit": 10
}
```

---

### 2.2 Get Role by ID

**Endpoint:** `GET /api/v1/roles/{role_id}`

**Query Parameters:**

- `include_permissions` (bool, default: false): Include permissions in response

**Response (200 OK):**

```json
{
  "id": "uuid",
  "organization_id": "uuid",
  "name": "Admin",
  "code": "admin",
  "description": "System administrator role",
  "is_system": true,
  "is_default": false,
  "hierarchy_level": 0,
  "is_active": true,
  "extra_data": {},
  "created_at": "2026-01-25T10:00:00Z",
  "updated_at": "2026-01-25T10:00:00Z",
  "permissions": [
    {
      "id": "uuid",
      "code": "user:create",
      "name": "Create User",
      "resource": "users",
      "action": "create"
    }
  ]
}
```

---

### 2.3 Create Role

**Endpoint:** `POST /api/v1/roles`

**Request Body:**

```json
{
  "organization_id": "uuid",
  "name": "Manager",
  "code": "manager",
  "description": "Manager role with limited permissions",
  "is_system": false,
  "is_default": false,
  "hierarchy_level": 1,
  "is_active": true,
  "extra_data": {}
}
```

**Response (201 Created):**

```json
{
  "id": "uuid",
  "organization_id": "uuid",
  "name": "Manager",
  "code": "manager",
  "description": "Manager role with limited permissions",
  "is_system": false,
  "is_default": false,
  "hierarchy_level": 1,
  "is_active": true,
  "extra_data": {},
  "created_at": "2026-01-25T10:00:00Z",
  "updated_at": "2026-01-25T10:00:00Z"
}
```

**Error (400 Bad Request):**

```json
{
  "detail": "Role code 'manager' already exists in this organization"
}
```

---

### 2.4 Update Role

**Endpoint:** `PUT /api/v1/roles/{role_id}`

**Request Body:**

```json
{
  "name": "Senior Manager",
  "description": "Updated description",
  "hierarchy_level": 1,
  "is_active": true,
  "extra_data": {}
}
```

**Response (200 OK):**

```json
{
  "id": "uuid",
  "organization_id": "uuid",
  "name": "Senior Manager",
  "code": "manager",
  "description": "Updated description",
  "is_system": false,
  "is_default": false,
  "hierarchy_level": 1,
  "is_active": true,
  "extra_data": {},
  "created_at": "2026-01-25T10:00:00Z",
  "updated_at": "2026-01-25T10:30:00Z"
}
```

**Error (400 Bad Request):**

```json
{
  "detail": "Cannot modify system role 'admin'"
}
```

---

### 2.5 Delete Role

**Endpoint:** `DELETE /api/v1/roles/{role_id}`

**Response (204 No Content)**

**Error (400 Bad Request):**

```json
{
  "detail": "Cannot delete role with active user assignments (5 users)"
}
```

**Error (403 Forbidden):**

```json
{
  "detail": "Cannot delete system role"
}
```

---

### 2.6 Get Role Permissions

**Endpoint:** `GET /api/v1/roles/{role_id}/permissions`

**Query Parameters:**

- `skip` (int, default: 0): Pagination offset
- `limit` (int, default: 10): Pagination limit
- `resource` (string, optional): Filter by resource type
- `action` (string, optional): Filter by action type

**Response (200 OK):**

```json
{
  "data": [
    {
      "id": "uuid",
      "permission_id": "uuid",
      "code": "user:create",
      "name": "Create User",
      "resource": "users",
      "action": "create",
      "module": "auth",
      "conditions": {}
    }
  ],
  "total": 25,
  "skip": 0,
  "limit": 10
}
```

---

### 2.7 Assign Permission to Role

**Endpoint:** `POST /api/v1/roles/{role_id}/permissions`

**Request Body:**

```json
{
  "permission_id": "uuid",
  "conditions": {
    "department_ids": ["uuid1", "uuid2"],
    "resource_tags": ["public"]
  }
}
```

**Response (201 Created):**

```json
{
  "id": "uuid",
  "role_id": "uuid",
  "permission_id": "uuid",
  "conditions": {
    "department_ids": ["uuid1", "uuid2"],
    "resource_tags": ["public"]
  },
  "created_at": "2026-01-25T10:00:00Z"
}
```

**Error (409 Conflict):**

```json
{
  "detail": "Permission already assigned to this role"
}
```

---

### 2.8 Remove Permission from Role

**Endpoint:** `DELETE /api/v1/roles/{role_id}/permissions/{permission_id}`

**Response (204 No Content)**

---

### 2.9 Bulk Assign Permissions to Role

**Endpoint:** `POST /api/v1/roles/{role_id}/permissions/bulk`

**Request Body:**

```json
{
  "permission_ids": ["uuid1", "uuid2", "uuid3"],
  "mode": "replace" // "replace" or "add"
}
```

**Response (200 OK):**

```json
{
  "message": "Successfully assigned 3 permissions",
  "role_id": "uuid",
  "assigned_count": 3,
  "previous_count": 5
}
```

---

### 2.10 Get Users with Role

**Endpoint:** `GET /api/v1/roles/{role_id}/users`

**Query Parameters:**

- `skip` (int, default: 0): Pagination offset
- `limit` (int, default: 10): Pagination limit
- `organization_id` (UUID, required): Organization filter

**Response (200 OK):**

```json
{
  "data": [
    {
      "id": "uuid",
      "user_id": "uuid",
      "email": "user@example.com",
      "first_name": "John",
      "last_name": "Doe",
      "is_primary": true,
      "is_active": true,
      "status": "active",
      "joined_at": "2026-01-25T10:00:00Z"
    }
  ],
  "total": 10,
  "skip": 0,
  "limit": 10
}
```

---

## 3. ROLE-PERMISSIONS API (Junction Table Management)

### 3.1 Get Role Permission by ID

**Endpoint:** `GET /api/v1/role-permissions/{role_permission_id}`

**Response (200 OK):**

```json
{
  "id": "uuid",
  "role_id": "uuid",
  "permission_id": "uuid",
  "conditions": {}
}
```

---

### 3.2 Update Role Permission Conditions

**Endpoint:** `PUT /api/v1/role-permissions/{role_permission_id}`

**Request Body:**

```json
{
  "conditions": {
    "department_ids": ["uuid1", "uuid2"],
    "resource_tags": ["public", "shared"]
  }
}
```

**Response (200 OK):**

```json
{
  "id": "uuid",
  "role_id": "uuid",
  "permission_id": "uuid",
  "conditions": {
    "department_ids": ["uuid1", "uuid2"],
    "resource_tags": ["public", "shared"]
  }
}
```

---

## 4. PYDANTIC SCHEMAS (Request/Response Models)

### Permissions Schemas

```python
class PermissionBase(BaseModel):
    code: str
    name: str
    description: Optional[str] = None
    resource: ResourceType
    action: ActionType
    module: Optional[str] = None
    category: Optional[str] = None
    is_active: bool = True
    extra_data: Optional[dict] = {}

class PermissionCreate(PermissionBase):
    pass

class PermissionUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    is_active: Optional[bool] = None
    extra_data: Optional[dict] = None

class PermissionResponse(PermissionBase):
    id: UUID
    created_at: datetime
    updated_at: datetime

class PermissionListResponse(BaseModel):
    data: List[PermissionResponse]
    total: int
    skip: int
    limit: int
```

### Roles Schemas

```python
class RoleBase(BaseModel):
    name: str
    code: str
    description: Optional[str] = None
    is_system: bool = False
    is_default: bool = False
    hierarchy_level: int = 0
    is_active: bool = True
    extra_data: Optional[dict] = {}

class RoleCreate(RoleBase):
    organization_id: UUID

class RoleUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    hierarchy_level: Optional[int] = None
    is_active: Optional[bool] = None
    extra_data: Optional[dict] = None

class RoleResponse(RoleBase):
    id: UUID
    organization_id: UUID
    created_at: datetime
    updated_at: datetime
    permissions: Optional[List[PermissionResponse]] = []

class RoleListResponse(BaseModel):
    data: List[RoleResponse]
    total: int
    skip: int
    limit: int
```

### Role-Permission Schemas

```python
class RolePermissionBase(BaseModel):
    role_id: UUID
    permission_id: UUID
    conditions: Optional[dict] = {}

class RolePermissionCreate(RolePermissionBase):
    pass

class RolePermissionUpdate(BaseModel):
    conditions: Optional[dict] = None

class RolePermissionResponse(RolePermissionBase):
    id: UUID

class BulkAssignPermissionsRequest(BaseModel):
    permission_ids: List[UUID]
    mode: str = "replace"  # "replace" or "add"
```

---

## 5. AUTHORIZATION & SECURITY

### Required Permissions for Endpoints

- `GET /permissions` → `permission:read`
- `POST /permissions` → `permission:create`
- `PUT /permissions/{id}` → `permission:update`
- `DELETE /permissions/{id}` → `permission:delete`
- `GET /roles` → `role:read`
- `POST /roles` → `role:create`
- `PUT /roles/{id}` → `role:update`
- `DELETE /roles/{id}` → `role:delete`

### Rules

1. Users can only view/manage roles within their organization
2. System roles cannot be deleted or modified
3. Hierarchy level restrictions: Only higher hierarchy users can manage lower hierarchy roles
4. Cannot assign/remove permissions from system roles
5. Cannot delete a role with active user assignments

---

## 6. ERROR RESPONSES

### Common Error Codes

- `400 Bad Request` → Validation failed
- `401 Unauthorized` → Missing/invalid authentication
- `403 Forbidden` → Insufficient permissions
- `404 Not Found` → Resource not found
- `409 Conflict` → Resource already exists
- `422 Unprocessable Entity` → Invalid request data

### Standard Error Response Format

```json
{
  "detail": "Error message",
  "error_code": "ROLE_NOT_FOUND",
  "status_code": 404
}
```

---

## 7. IMPLEMENTATION CHECKLIST

- [ ] Create Pydantic schemas in `app/schemas/role.py`
- [ ] Create Pydantic schemas in `app/schemas/permission.py`
- [ ] Create repositories in `app/repositories/role_repository.py`
- [ ] Create repositories in `app/repositories/permission_repository.py`
- [ ] Create services in `app/services/role_service.py`
- [ ] Create services in `app/services/permission_service.py`
- [ ] Create endpoints in `app/api/v1/endpoints/roles.py`
- [ ] Create endpoints in `app/api/v1/endpoints/permissions.py`
- [ ] Add routes to `app/api/v1/router.py`
- [ ] Add unit tests for services
- [ ] Add integration tests for endpoints
- [ ] Add database migration (if needed)
- [ ] Update API documentation/Swagger
