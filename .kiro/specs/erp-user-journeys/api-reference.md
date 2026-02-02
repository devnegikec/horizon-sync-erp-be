# API Reference: ERP User Journeys Backend Integration

## Overview

This document provides a comprehensive reference for integrating the ERP User Journeys frontend with the existing backend services. Both services are fully implemented and production-ready.

## Service Architecture

```
Frontend (TypeScript/React)
    ↓ HTTP/JWT
┌─────────────────────────────────────┐
│  Identity Service (Port 8000)      │
│  - Authentication & Authorization  │
│  - User & Organization Management  │
│  - Role-Based Access Control       │
└─────────────────────────────────────┘
    ↓ Shared Database
┌─────────────────────────────────────┐
│  Core Service (Port 8001)          │
│  - All ERP Business Logic          │
│  - Inventory, Orders, Billing      │
│  - 20+ Comprehensive Modules       │
└─────────────────────────────────────┘
    ↓
┌─────────────────────────────────────┐
│  PostgreSQL Database (Shared)      │
└─────────────────────────────────────┘
```

## Identity Service API (Port 8000)

### Base URL

```
http://localhost:8000/api/v1/identity
```

### Authentication Endpoints

#### Login

```http
POST /login
Content-Type: application/json

{
  "email": "admin@example.com",
  "password": "Admin123!"
}

Response:
{
  "access_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
  "refresh_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
  "token_type": "bearer",
  "expires_in": 900,
  "user": {
    "id": "uuid",
    "email": "admin@example.com",
    "full_name": "Admin User",
    "organization_id": "uuid",
    "roles": ["admin"]
  }
}
```

#### Refresh Token

```http
POST /refresh
Content-Type: application/json

{
  "refresh_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9..."
}

Response:
{
  "access_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
  "token_type": "bearer",
  "expires_in": 900
}
```

#### Logout

```http
POST /logout
Authorization: Bearer {access_token}

Response: 204 No Content
```

### User Management Endpoints

#### List Users

```http
GET /users?page=1&page_size=20
Authorization: Bearer {access_token}

Response:
{
  "users": [
    {
      "id": "uuid",
      "email": "user@example.com",
      "full_name": "User Name",
      "organization_id": "uuid",
      "is_active": true,
      "created_at": "2024-01-01T00:00:00Z"
    }
  ],
  "pagination": {
    "page": 1,
    "page_size": 20,
    "total": 100,
    "pages": 5
  }
}
```

#### Register User

```http
POST /register
Content-Type: application/json

{
  "email": "newuser@example.com",
  "password": "SecurePass123!",
  "full_name": "New User",
  "organization_id": "uuid"
}

Response: 201 Created
{
  "id": "uuid",
  "email": "newuser@example.com",
  "full_name": "New User",
  "organization_id": "uuid",
  "is_active": true
}
```

### RBAC Endpoints

#### Organizations

```http
GET /organizations
POST /organizations
GET /organizations/{id}
PUT /organizations/{id}
DELETE /organizations/{id}
```

#### Roles

```http
GET /roles
POST /roles
GET /roles/{id}
PUT /roles/{id}
DELETE /roles/{id}
```

#### Permissions

```http
GET /permissions
POST /permissions
GET /permissions/{id}
PUT /permissions/{id}
DELETE /permissions/{id}
```

## Core Service API (Port 8001)

### Base URL

```
http://localhost:8001/api/v1
```

### Authentication

All endpoints require JWT token from Identity Service:

```http
Authorization: Bearer {access_token}
```

### Item Management

#### Items

```http
# List items with filters
GET /items?page=1&page_size=20&search=laptop&item_group_id=uuid&status=active

# Create item
POST /items
{
  "item_code": "ITEM001",
  "item_name": "Laptop Computer",
  "description": "High-performance laptop",
  "uom": "Nos",
  "item_group_id": "uuid",
  "maintain_stock": true,
  "standard_rate": 1200.00,
  "valuation_rate": 1000.00
}

# Get item details
GET /items/{id}

# Update item
PUT /items/{id}

# Delete item (soft delete)
DELETE /items/{id}
```

#### Item Groups

```http
GET /item-groups
POST /item-groups
GET /item-groups/{id}
PUT /item-groups/{id}
DELETE /item-groups/{id}
```

#### Item Prices

```http
GET /item-prices?item_id=uuid
POST /item-prices
GET /item-prices/{id}
PUT /item-prices/{id}
DELETE /item-prices/{id}
```

### Customer Management

#### Customers

```http
# List customers
GET /customers?page=1&page_size=20&search=john&status=active

# Create customer
POST /customers
{
  "customer_code": "CUST001",
  "customer_name": "John Doe Enterprises",
  "contact_person": "John Doe",
  "email": "john@example.com",
  "phone": "+1234567890",
  "credit_limit": 50000.00,
  "payment_terms": "Net 30"
}

# Get customer details
GET /customers/{id}

# Update customer
PUT /customers/{id}

# Delete customer
DELETE /customers/{id}
```

### Supplier Management

#### Suppliers

```http
GET /suppliers
POST /suppliers
GET /suppliers/{id}
PUT /suppliers/{id}
DELETE /suppliers/{id}
```

### Warehouse Management

#### Warehouses

```http
# List warehouses
GET /warehouses

# Create warehouse
POST /warehouses
{
  "warehouse_code": "WH001",
  "warehouse_name": "Main Warehouse",
  "address": "123 Storage St",
  "is_active": true
}

# Get warehouse details
GET /warehouses/{id}

# Update warehouse
PUT /warehouses/{id}

# Delete warehouse
DELETE /warehouses/{id}
```

### Stock Management

#### Stock Levels

```http
# Get current stock levels
GET /stock-levels?item_id=uuid&warehouse_id=uuid

# Get stock level details
GET /stock-levels/{id}
```

#### Stock Movements

```http
# List stock movements
GET /stock-movements?item_id=uuid&warehouse_id=uuid&date_from=2024-01-01

# Create stock movement
POST /stock-movements
{
  "item_id": "uuid",
  "warehouse_id": "uuid",
  "movement_type": "receipt",
  "quantity": 100,
  "reference_document": "PO001",
  "reason_code": "purchase_receipt"
}

# Get movement details
GET /stock-movements/{id}
```

#### Stock Entries

```http
GET /stock-entries
POST /stock-entries
GET /stock-entries/{id}
PUT /stock-entries/{id}
DELETE /stock-entries/{id}
```

#### Stock Reconciliations

```http
GET /stock-reconciliations
POST /stock-reconciliations
GET /stock-reconciliations/{id}
PUT /stock-reconciliations/{id}
DELETE /stock-reconciliations/{id}
```

### Batch Management

#### Batches

```http
# List batches
GET /batches?item_id=uuid&expiry_date_from=2024-01-01

# Create batch
POST /batches
{
  "batch_number": "BATCH001",
  "item_id": "uuid",
  "production_date": "2024-01-01",
  "expiry_date": "2024-12-31",
  "quantity": 1000
}

# Get batch details
GET /batches/{id}

# Update batch
PUT /batches/{id}
```

#### Serial Numbers

```http
GET /serial-numbers
POST /serial-numbers
GET /serial-numbers/{id}
PUT /serial-numbers/{id}
DELETE /serial-numbers/{id}
```

### Delivery Management

#### Delivery Notes

```http
# List delivery notes
GET /delivery-notes?customer_id=uuid&status=pending

# Create delivery note
POST /delivery-notes
{
  "customer_id": "uuid",
  "delivery_date": "2024-01-15",
  "items": [
    {
      "item_id": "uuid",
      "quantity": 10,
      "batch_id": "uuid"
    }
  ]
}

# Get delivery note details
GET /delivery-notes/{id}

# Update delivery note
PUT /delivery-notes/{id}

# Confirm delivery
POST /delivery-notes/{id}/confirm
```

#### Pick Lists

```http
GET /pick-lists
POST /pick-lists
GET /pick-lists/{id}
PUT /pick-lists/{id}
DELETE /pick-lists/{id}
```

### Invoice Management

#### Invoices

```http
# List invoices
GET /invoices?customer_id=uuid&status=unpaid&due_date_from=2024-01-01

# Create invoice
POST /invoices
{
  "customer_id": "uuid",
  "invoice_date": "2024-01-01",
  "due_date": "2024-01-31",
  "items": [
    {
      "item_id": "uuid",
      "quantity": 5,
      "rate": 100.00,
      "amount": 500.00
    }
  ],
  "total_amount": 500.00
}

# Get invoice details
GET /invoices/{id}

# Update invoice
PUT /invoices/{id}

# Delete invoice
DELETE /invoices/{id}
```

#### Payments

```http
# List payments
GET /payments?customer_id=uuid&date_from=2024-01-01

# Record payment
POST /payments
{
  "customer_id": "uuid",
  "payment_date": "2024-01-15",
  "amount": 1000.00,
  "payment_method": "bank_transfer",
  "reference": "TXN123456",
  "allocations": [
    {
      "invoice_id": "uuid",
      "amount": 500.00
    }
  ]
}

# Get payment details
GET /payments/{id}
```

### Purchase Management

#### Purchase Receipts

```http
GET /purchase-receipts
POST /purchase-receipts
GET /purchase-receipts/{id}
PUT /purchase-receipts/{id}
DELETE /purchase-receipts/{id}
```

### Quality Management

#### Quality Inspections

```http
GET /quality-inspections
POST /quality-inspections
GET /quality-inspections/{id}
PUT /quality-inspections/{id}
DELETE /quality-inspections/{id}
```

### Financial Management

#### Chart of Accounts

```http
GET /chart-of-accounts
POST /chart-of-accounts
GET /chart-of-accounts/{id}
PUT /chart-of-accounts/{id}
DELETE /chart-of-accounts/{id}
```

#### Journal Entries

```http
GET /journal-entries
POST /journal-entries
GET /journal-entries/{id}
PUT /journal-entries/{id}
DELETE /journal-entries/{id}
```

#### Landed Cost

```http
GET /landed-cost
POST /landed-cost
GET /landed-cost/{id}
PUT /landed-cost/{id}
DELETE /landed-cost/{id}
```

### Warehouse Operations

#### Put Away Rules

```http
GET /put-away-rules
POST /put-away-rules
GET /put-away-rules/{id}
PUT /put-away-rules/{id}
DELETE /put-away-rules/{id}
```

#### Stock Settings

```http
GET /stock-settings
POST /stock-settings
GET /stock-settings/{id}
PUT /stock-settings/{id}
DELETE /stock-settings/{id}
```

## Common Response Patterns

### Success Response

```json
{
  "id": "uuid",
  "created_at": "2024-01-01T00:00:00Z",
  "updated_at": "2024-01-01T00:00:00Z"
  // ... entity-specific fields
}
```

### List Response with Pagination

```json
{
  "items": [...],
  "pagination": {
    "page": 1,
    "page_size": 20,
    "total": 100,
    "pages": 5,
    "has_next": true,
    "has_prev": false
  }
}
```

### Error Response

```json
{
  "detail": "Error message",
  "error_code": "VALIDATION_ERROR",
  "field_errors": {
    "email": ["This field is required"]
  }
}
```

## Authentication Flow

### 1. Login

```typescript
const loginResponse = await fetch(
  "http://localhost:8000/api/v1/identity/login",
  {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password }),
  },
);

const { access_token, refresh_token, user } = await loginResponse.json();
```

### 2. Store Tokens

```typescript
localStorage.setItem("access_token", access_token);
localStorage.setItem("refresh_token", refresh_token);
localStorage.setItem("user", JSON.stringify(user));
```

### 3. Use Token for API Calls

```typescript
const response = await fetch("http://localhost:8001/api/v1/items", {
  headers: {
    Authorization: `Bearer ${access_token}`,
    "Content-Type": "application/json",
  },
});
```

### 4. Handle Token Refresh

```typescript
if (response.status === 401) {
  const refreshResponse = await fetch(
    "http://localhost:8000/api/v1/identity/refresh",
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ refresh_token }),
    },
  );

  const { access_token: newToken } = await refreshResponse.json();
  localStorage.setItem("access_token", newToken);

  // Retry original request with new token
}
```

## TypeScript Types

### Authentication Types

```typescript
interface LoginRequest {
  email: string;
  password: string;
}

interface LoginResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_in: number;
  user: User;
}

interface User {
  id: string;
  email: string;
  full_name: string;
  organization_id: string;
  roles: string[];
  is_active: boolean;
}
```

### Core Entity Types

```typescript
interface Item {
  id: string;
  item_code: string;
  item_name: string;
  description?: string;
  uom: string;
  item_group_id?: string;
  maintain_stock: boolean;
  standard_rate?: number;
  valuation_rate?: number;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

interface Customer {
  id: string;
  customer_code: string;
  customer_name: string;
  contact_person?: string;
  email?: string;
  phone?: string;
  credit_limit?: number;
  payment_terms?: string;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

interface StockLevel {
  id: string;
  item_id: string;
  warehouse_id: string;
  quantity_on_hand: number;
  quantity_reserved: number;
  quantity_available: number;
  last_movement_date?: string;
}
```

## Error Handling

### Common HTTP Status Codes

- `200` - Success
- `201` - Created
- `204` - No Content (for deletes)
- `400` - Bad Request (validation errors)
- `401` - Unauthorized (invalid/expired token)
- `403` - Forbidden (insufficient permissions)
- `404` - Not Found
- `422` - Unprocessable Entity (business rule violations)
- `500` - Internal Server Error

### Error Handling Pattern

```typescript
async function apiCall<T>(url: string, options: RequestInit): Promise<T> {
  try {
    const response = await fetch(url, {
      ...options,
      headers: {
        Authorization: `Bearer ${getAccessToken()}`,
        "Content-Type": "application/json",
        ...options.headers,
      },
    });

    if (response.status === 401) {
      await refreshToken();
      // Retry with new token
      return apiCall(url, options);
    }

    if (!response.ok) {
      const error = await response.json();
      throw new APIError(error.detail, response.status, error);
    }

    return await response.json();
  } catch (error) {
    console.error("API call failed:", error);
    throw error;
  }
}
```

## Development Setup

### Environment Variables

```env
# Frontend .env
REACT_APP_IDENTITY_SERVICE_URL=http://localhost:8000
REACT_APP_CORE_SERVICE_URL=http://localhost:8001
REACT_APP_API_TIMEOUT=30000
```

### API Client Configuration

```typescript
const API_CONFIG = {
  identityService: {
    baseURL: process.env.REACT_APP_IDENTITY_SERVICE_URL,
    timeout: 30000,
  },
  coreService: {
    baseURL: process.env.REACT_APP_CORE_SERVICE_URL,
    timeout: 30000,
  },
};
```

This comprehensive API reference provides everything needed to integrate the ERP User Journeys frontend with the existing backend services. All endpoints are production-ready and fully implemented.
