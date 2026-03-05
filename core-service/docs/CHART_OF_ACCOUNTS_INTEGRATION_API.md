# Chart of Accounts Integration API Documentation

This document provides comprehensive documentation for integrating other ERP modules with the Chart of Accounts system.

## Table of Contents

1. [Overview](#overview)
2. [Authentication](#authentication)
3. [Integration Endpoints](#integration-endpoints)
4. [Frontend Components](#frontend-components)
5. [Common Integration Scenarios](#common-integration-scenarios)
6. [Default Account Configuration](#default-account-configuration)
7. [Error Handling](#error-handling)
8. [Best Practices](#best-practices)
9. [Troubleshooting](#troubleshooting)

## Overview

The Chart of Accounts provides integration APIs and reusable components for other ERP modules (Inventory, Sourcing, etc.) to:

- Validate accounts before posting transactions
- Retrieve account information by ID or code
- Get default accounts for specific transaction types
- Search and filter accounts
- Access reusable UI components for account selection

### Key Features

- **RESTful API**: Standard HTTP endpoints with JSON payloads
- **Multi-tenancy**: Organization-scoped data isolation
- **Validation**: Comprehensive account validation before posting
- **Default Accounts**: Configurable default accounts for common transaction types
- **Reusable Components**: React components for account selection and management

## Authentication

All API endpoints require authentication using JWT tokens. Include the token in the Authorization header:

```http
Authorization: Bearer <your-jwt-token>
```

The token must contain:
- `user_id`: Unique identifier for the user
- `organization_id`: Organization context for multi-tenancy
- Valid expiration time

### Example Authentication

```typescript
const response = await fetch('/api/v1/accounts/validate-posting', {
  method: 'POST',
  headers: {
    'Authorization': `Bearer ${token}`,
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({ account_id: accountId })
});
```

## Integration Endpoints

### 1. Validate Posting Account

Validates if an account can receive transaction postings.

**Endpoint**: `POST /api/v1/accounts/validate-posting`

**Query Parameters**:
- `account_id` (required): UUID of the account to validate

**Response**: 
- `204 No Content`: Account is valid for posting
- `400 Bad Request`: Account is invalid (inactive or parent account)
- `404 Not Found`: Account does not exist

**Example**:

```python
# Python
import requests

response = requests.post(
    'http://api.example.com/api/v1/accounts/validate-posting',
    params={'account_id': '123e4567-e89b-12d3-a456-426614174000'},
    headers={'Authorization': f'Bearer {token}'}
)

if response.status_code == 204:
    print("Account is valid for posting")
```

```typescript
// TypeScript
async function validateAccount(accountId: string): Promise<boolean> {
  const response = await fetch(
    `/api/v1/accounts/validate-posting?account_id=${accountId}`,
    {
      method: 'POST',
      headers: { 'Authorization': `Bearer ${token}` }
    }
  );
  return response.status === 204;
}
```

### 2. Bulk Validate Posting Accounts

Validates multiple accounts in a single request for better performance.

**Endpoint**: `POST /api/v1/accounts/validate-posting/bulk`

**Query Parameters**:
- `account_ids` (required): Array of account UUIDs

**Response**: `200 OK`

```json
{
  "valid_count": 2,
  "invalid_count": 1,
  "valid": [
    "123e4567-e89b-12d3-a456-426614174000",
    "123e4567-e89b-12d3-a456-426614174001"
  ],
  "invalid": [
    {
      "account_id": "123e4567-e89b-12d3-a456-426614174002",
      "reason": "Account is inactive"
    }
  ]
}
```

**Example**:

```python
# Python - Validate multiple accounts
account_ids = [
    '123e4567-e89b-12d3-a456-426614174000',
    '123e4567-e89b-12d3-a456-426614174001',
    '123e4567-e89b-12d3-a456-426614174002'
]

response = requests.post(
    'http://api.example.com/api/v1/accounts/validate-posting/bulk',
    params={'account_ids': account_ids},
    headers={'Authorization': f'Bearer {token}'}
)

result = response.json()
print(f"Valid accounts: {result['valid_count']}")
print(f"Invalid accounts: {result['invalid_count']}")
```

### 3. Get Account by Code

Retrieves account details using the account code.

**Endpoint**: `GET /api/v1/accounts/by-code/{code}`

**Path Parameters**:
- `code` (required): Account code (e.g., "1000-01")

**Response**: `200 OK`

```json
{
  "id": "123e4567-e89b-12d3-a456-426614174000",
  "account_code": "1000-01",
  "account_name": "Cash - Operating",
  "account_type": "ASSET",
  "currency": "USD",
  "status": "ACTIVE",
  "is_posting_account": true,
  "parent_account_id": null,
  "description": "Main operating cash account"
}
```

**Example**:

```typescript
// TypeScript
async function getAccountByCode(code: string): Promise<Account | null> {
  const response = await fetch(
    `/api/v1/accounts/by-code/${code}`,
    { headers: { 'Authorization': `Bearer ${token}` } }
  );
  
  if (response.status === 404) return null;
  return await response.json();
}
```

### 4. Get Default Account

Retrieves the configured default account for a transaction type.

**Endpoint**: `POST /api/v1/accounts/default/{transaction_type}`

**Path Parameters**:
- `transaction_type` (required): Type of transaction (e.g., "inventory_purchase")

**Query Parameters**:
- `scenario` (optional): Specific scenario (e.g., "domestic", "international")

**Response**: `200 OK`

```json
{
  "id": "123e4567-e89b-12d3-a456-426614174000",
  "account_code": "5000-01",
  "account_name": "Cost of Goods Sold",
  "account_type": "EXPENSE",
  "currency": "USD",
  "status": "ACTIVE",
  "is_posting_account": true
}
```

**Error Responses**:
- `404 Not Found`: No default account configured for this transaction type
- `422 Unprocessable Entity`: Configured account no longer exists

**Example**:

```python
# Python - Get default account for inventory purchase
response = requests.post(
    'http://api.example.com/api/v1/accounts/default/inventory_purchase',
    headers={'Authorization': f'Bearer {token}'}
)

if response.status_code == 200:
    account = response.json()
    print(f"Default account: {account['account_code']} - {account['account_name']}")
elif response.status_code == 404:
    print("No default account configured for inventory_purchase")
```

```typescript
// TypeScript - Get default account with scenario
async function getDefaultAccount(
  transactionType: string,
  scenario?: string
): Promise<Account | null> {
  const url = new URL(`/api/v1/accounts/default/${transactionType}`, window.location.origin);
  if (scenario) url.searchParams.set('scenario', scenario);
  
  const response = await fetch(url.toString(), {
    method: 'POST',
    headers: { 'Authorization': `Bearer ${token}` }
  });
  
  if (response.status === 404) return null;
  return await response.json();
}
```

### 5. Search Accounts

Search accounts by code or name with optional filters.

**Endpoint**: `GET /api/v1/accounts`

**Query Parameters**:
- `search` (optional): Search term for code or name
- `account_type` (optional): Filter by account type (ASSET, LIABILITY, EQUITY, INCOME, EXPENSE)
- `status` (optional): Filter by status (ACTIVE, INACTIVE, ARCHIVED)
- `posting_accounts_only` (optional): Boolean to show only posting accounts
- `page` (optional): Page number (default: 1)
- `page_size` (optional): Items per page (default: 50)

**Response**: `200 OK`

```json
{
  "items": [
    {
      "id": "123e4567-e89b-12d3-a456-426614174000",
      "account_code": "1000-01",
      "account_name": "Cash - Operating",
      "account_type": "ASSET",
      "currency": "USD",
      "status": "ACTIVE",
      "is_posting_account": true
    }
  ],
  "total": 1,
  "page": 1,
  "page_size": 50,
  "total_pages": 1
}
```

**Example**:

```typescript
// TypeScript - Search for cash accounts
async function searchAccounts(
  searchTerm: string,
  filters?: { accountType?: string; status?: string }
): Promise<Account[]> {
  const url = new URL('/api/v1/accounts', window.location.origin);
  url.searchParams.set('search', searchTerm);
  if (filters?.accountType) url.searchParams.set('account_type', filters.accountType);
  if (filters?.status) url.searchParams.set('status', filters.status);
  
  const response = await fetch(url.toString(), {
    headers: { 'Authorization': `Bearer ${token}` }
  });
  
  const data = await response.json();
  return data.items;
}
```

## Frontend Components

The Chart of Accounts provides reusable React components for integration with other modules.

### AccountSelector Component

A dropdown component for selecting accounts with search and filtering capabilities.

**Import**:

```typescript
import { AccountSelector } from '@/components/accounts/AccountSelector';
```

**Props**:

```typescript
interface AccountSelectorProps {
  value?: string;                    // Selected account ID
  onChange: (accountId: string) => void;
  accountTypeFilter?: AccountType;   // Filter by account type
  postingAccountsOnly?: boolean;     // Show only posting accounts
  excludeAccountIds?: string[];      // Exclude specific accounts
  disabled?: boolean;
  error?: string;
  label?: string;
}
```

**Example Usage**:

```tsx
import { AccountSelector } from '@/components/accounts/AccountSelector';
import { useState } from 'react';

function InventoryTransactionForm() {
  const [accountId, setAccountId] = useState<string>('');
  
  return (
    <form>
      <AccountSelector
        value={accountId}
        onChange={setAccountId}
        accountTypeFilter="EXPENSE"
        postingAccountsOnly={true}
        label="Expense Account"
      />
    </form>
  );
}
```

### AccountCodeInput Component

An input component with validation for account codes.

**Import**:

```typescript
import { AccountCodeInput } from '@/components/accounts/AccountCodeInput';
```

**Props**:

```typescript
interface AccountCodeInputProps {
  value: string;
  onChange: (code: string) => void;
  onAccountFound?: (account: Account) => void;
  validateOnBlur?: boolean;
  disabled?: boolean;
  error?: string;
  label?: string;
}
```

**Example Usage**:

```tsx
import { AccountCodeInput } from '@/components/accounts/AccountCodeInput';
import { useState } from 'react';

function QuickPostingForm() {
  const [accountCode, setAccountCode] = useState('');
  const [account, setAccount] = useState<Account | null>(null);
  
  return (
    <form>
      <AccountCodeInput
        value={accountCode}
        onChange={setAccountCode}
        onAccountFound={setAccount}
        validateOnBlur={true}
        label="Account Code"
      />
      {account && <p>Selected: {account.account_name}</p>}
    </form>
  );
}
```

### AccountTypeFilter Component

A filter component for selecting account types.

**Import**:

```typescript
import { AccountTypeFilter } from '@/components/accounts/AccountTypeFilter';
```

**Props**:

```typescript
interface AccountTypeFilterProps {
  value?: AccountType;
  onChange: (type: AccountType | undefined) => void;
  allowAll?: boolean;  // Show "All Types" option
  label?: string;
}
```

**Example Usage**:

```tsx
import { AccountTypeFilter } from '@/components/accounts/AccountTypeFilter';
import { useState } from 'react';

function AccountListPage() {
  const [accountType, setAccountType] = useState<AccountType | undefined>();
  
  return (
    <div>
      <AccountTypeFilter
        value={accountType}
        onChange={setAccountType}
        allowAll={true}
        label="Filter by Type"
      />
      {/* Account list filtered by type */}
    </div>
  );
}
```

## Common Integration Scenarios

### Scenario 1: Posting an Inventory Purchase

When recording an inventory purchase, you need to post to both an inventory asset account and an accounts payable account.

**Steps**:

1. Get default accounts for the transaction type
2. Validate both accounts can receive postings
3. Post the transaction

**Example Code**:

```python
# Python - Post inventory purchase
import requests

def post_inventory_purchase(amount: float, supplier_id: str, token: str):
    base_url = 'http://api.example.com/api/v1'
    headers = {'Authorization': f'Bearer {token}'}
    
    # Step 1: Get default accounts
    inventory_account_response = requests.post(
        f'{base_url}/accounts/default/inventory_asset',
        headers=headers
    )
    payable_account_response = requests.post(
        f'{base_url}/accounts/default/accounts_payable',
        headers=headers
    )
    
    if inventory_account_response.status_code != 200:
        raise Exception("Inventory asset account not configured")
    if payable_account_response.status_code != 200:
        raise Exception("Accounts payable account not configured")
    
    inventory_account = inventory_account_response.json()
    payable_account = payable_account_response.json()
    
    # Step 2: Validate accounts (bulk validation for efficiency)
    validation_response = requests.post(
        f'{base_url}/accounts/validate-posting/bulk',
        params={'account_ids': [inventory_account['id'], payable_account['id']]},
        headers=headers
    )
    
    validation = validation_response.json()
    if validation['invalid_count'] > 0:
        raise Exception(f"Invalid accounts: {validation['invalid']}")
    
    # Step 3: Post transaction to general ledger
    # (This would be your transaction posting logic)
    transaction_data = {
        'entries': [
            {
                'account_id': inventory_account['id'],
                'debit': amount,
                'credit': 0
            },
            {
                'account_id': payable_account['id'],
                'debit': 0,
                'credit': amount
            }
        ],
        'description': f'Inventory purchase from supplier {supplier_id}',
        'reference_type': 'purchase_order',
        'reference_id': supplier_id
    }
    
    return transaction_data
```

### Scenario 2: Sales Revenue Posting with Scenarios

When recording sales, use different revenue accounts for domestic vs. international sales.

**Example Code**:

```typescript
// TypeScript - Post sales revenue with scenario
async function postSalesRevenue(
  amount: number,
  customerId: string,
  isInternational: boolean,
  token: string
): Promise<void> {
  const scenario = isInternational ? 'international' : 'domestic';
  
  // Get default revenue account based on scenario
  const revenueAccountResponse = await fetch(
    `/api/v1/accounts/default/sales_revenue?scenario=${scenario}`,
    {
      method: 'POST',
      headers: { 'Authorization': `Bearer ${token}` }
    }
  );
  
  if (!revenueAccountResponse.ok) {
    throw new Error(`Revenue account not configured for ${scenario} sales`);
  }
  
  const revenueAccount = await revenueAccountResponse.json();
  
  // Get accounts receivable account
  const receivableAccountResponse = await fetch(
    '/api/v1/accounts/default/accounts_receivable',
    {
      method: 'POST',
      headers: { 'Authorization': `Bearer ${token}` }
    }
  );
  
  const receivableAccount = await receivableAccountResponse.json();
  
  // Validate accounts
  const validationResponse = await fetch(
    `/api/v1/accounts/validate-posting/bulk?account_ids=${revenueAccount.id}&account_ids=${receivableAccount.id}`,
    {
      method: 'POST',
      headers: { 'Authorization': `Bearer ${token}` }
    }
  );
  
  const validation = await validationResponse.json();
  if (validation.invalid_count > 0) {
    throw new Error('Invalid accounts for posting');
  }
  
  // Post transaction
  const transactionData = {
    entries: [
      {
        account_id: receivableAccount.id,
        debit: amount,
        credit: 0
      },
      {
        account_id: revenueAccount.id,
        debit: 0,
        credit: amount
      }
    ],
    description: `${scenario} sales to customer ${customerId}`,
    reference_type: 'sales_order',
    reference_id: customerId
  };
  
  // Post to general ledger (your implementation)
}
```

### Scenario 3: Account Selection in UI Forms

Use the AccountSelector component to allow users to select accounts in forms.

**Example Code**:

```tsx
// React - Expense report form with account selection
import { AccountSelector } from '@/components/accounts/AccountSelector';
import { useState } from 'react';

interface ExpenseLineItem {
  description: string;
  amount: number;
  accountId: string;
}

function ExpenseReportForm() {
  const [lineItems, setLineItems] = useState<ExpenseLineItem[]>([
    { description: '', amount: 0, accountId: '' }
  ]);
  
  const addLineItem = () => {
    setLineItems([...lineItems, { description: '', amount: 0, accountId: '' }]);
  };
  
  const updateLineItem = (index: number, field: keyof ExpenseLineItem, value: any) => {
    const updated = [...lineItems];
    updated[index] = { ...updated[index], [field]: value };
    setLineItems(updated);
  };
  
  return (
    <form>
      <h2>Expense Report</h2>
      {lineItems.map((item, index) => (
        <div key={index} className="line-item">
          <input
            type="text"
            placeholder="Description"
            value={item.description}
            onChange={(e) => updateLineItem(index, 'description', e.target.value)}
          />
          <input
            type="number"
            placeholder="Amount"
            value={item.amount}
            onChange={(e) => updateLineItem(index, 'amount', parseFloat(e.target.value))}
          />
          <AccountSelector
            value={item.accountId}
            onChange={(accountId) => updateLineItem(index, 'accountId', accountId)}
            accountTypeFilter="EXPENSE"
            postingAccountsOnly={true}
            label="Expense Account"
          />
        </div>
      ))}
      <button type="button" onClick={addLineItem}>Add Line Item</button>
      <button type="submit">Submit Expense Report</button>
    </form>
  );
}
```

## Default Account Configuration

Default accounts must be configured before modules can use them. This is typically done during system setup.

### Required Default Accounts

The following default accounts should be configured for common ERP operations:

| Transaction Type | Account Type | Description |
|-----------------|--------------|-------------|
| `inventory_asset` | ASSET | Inventory on hand |
| `inventory_purchase` | EXPENSE | Cost of goods purchased |
| `accounts_payable` | LIABILITY | Amounts owed to suppliers |
| `accounts_receivable` | ASSET | Amounts owed by customers |
| `sales_revenue` | INCOME | Revenue from sales |
| `cost_of_goods_sold` | EXPENSE | Cost of items sold |
| `cash` | ASSET | Cash and cash equivalents |
| `bank_charges` | EXPENSE | Bank fees and charges |
| `exchange_gain_loss` | INCOME/EXPENSE | Foreign exchange gains/losses |

### Configuring Default Accounts

**Endpoint**: `PUT /api/v1/accounts/config/defaults`

**Request Body**:

```json
{
  "defaults": [
    {
      "transaction_type": "inventory_asset",
      "account_id": "123e4567-e89b-12d3-a456-426614174000"
    },
    {
      "transaction_type": "sales_revenue",
      "scenario": "domestic",
      "account_id": "123e4567-e89b-12d3-a456-426614174001"
    },
    {
      "transaction_type": "sales_revenue",
      "scenario": "international",
      "account_id": "123e4567-e89b-12d3-a456-426614174002"
    }
  ]
}
```

**Response**:

```json
{
  "success_count": 3,
  "error_count": 0,
  "updated": [
    {
      "transaction_type": "inventory_asset",
      "scenario": null,
      "account_id": "123e4567-e89b-12d3-a456-426614174000",
      "account_code": "1500",
      "account_name": "Inventory"
    }
  ],
  "errors": []
}
```

**Example Code**:

```python
# Python - Configure default accounts
import requests

def configure_default_accounts(account_mappings: list, token: str):
    """
    Configure default accounts for transaction types.
    
    Args:
        account_mappings: List of dicts with transaction_type, account_id, and optional scenario
        token: Authentication token
    """
    response = requests.put(
        'http://api.example.com/api/v1/accounts/config/defaults',
        json={'defaults': account_mappings},
        headers={'Authorization': f'Bearer {token}'}
    )
    
    result = response.json()
    print(f"Successfully configured: {result['success_count']}")
    print(f"Errors: {result['error_count']}")
    
    if result['error_count'] > 0:
        for error in result['errors']:
            print(f"  - {error['transaction_type']}: {error['error']}")
    
    return result

# Example usage
mappings = [
    {'transaction_type': 'inventory_asset', 'account_id': 'uuid-1'},
    {'transaction_type': 'accounts_payable', 'account_id': 'uuid-2'},
    {'transaction_type': 'sales_revenue', 'scenario': 'domestic', 'account_id': 'uuid-3'}
]

configure_default_accounts(mappings, token)
```

### Retrieving Default Account Configuration


**Endpoint**: `GET /api/v1/accounts/config/defaults`

**Query Parameters**:
- `transaction_type` (optional): Filter by transaction type

**Response**:

```json
[
  {
    "transaction_type": "inventory_asset",
    "scenario": null,
    "account_id": "123e4567-e89b-12d3-a456-426614174000",
    "account_code": "1500",
    "account_name": "Inventory",
    "account_type": "ASSET"
  },
  {
    "transaction_type": "sales_revenue",
    "scenario": "domestic",
    "account_id": "123e4567-e89b-12d3-a456-426614174001",
    "account_code": "4000",
    "account_name": "Sales Revenue - Domestic",
    "account_type": "INCOME"
  }
]
```

### Account Type Validation

The system validates that default accounts are of the appropriate type for their transaction type:

| Transaction Type | Required Account Type |
|-----------------|----------------------|
| `inventory_asset` | ASSET |
| `inventory_purchase` | EXPENSE |
| `accounts_payable` | LIABILITY |
| `accounts_receivable` | ASSET |
| `sales_revenue` | INCOME |
| `cost_of_goods_sold` | EXPENSE |
| `cash` | ASSET |
| `bank_charges` | EXPENSE |

If you attempt to configure an account with the wrong type, you'll receive an error:

```json
{
  "success_count": 0,
  "error_count": 1,
  "errors": [
    {
      "transaction_type": "sales_revenue",
      "error": "Account type EXPENSE is not appropriate for transaction type sales_revenue (expected INCOME)"
    }
  ]
}
```

## Error Handling

### Error Response Format

All errors follow a consistent format:

```json
{
  "detail": "Error message describing what went wrong"
}
```

### Common Error Codes

| Status Code | Meaning | Common Causes |
|------------|---------|---------------|
| 400 Bad Request | Invalid request | Account is inactive, parent account used for posting |
| 404 Not Found | Resource not found | Account doesn't exist, default account not configured |
| 422 Unprocessable Entity | Business rule violation | Configured account deleted, invalid account type |
| 401 Unauthorized | Authentication failed | Missing or invalid token |
| 403 Forbidden | Access denied | User doesn't have permission for organization |

### Error Handling Best Practices


**1. Always validate accounts before posting**:

```python
# Bad - No validation
def post_transaction(account_id, amount):
    # Directly post without checking if account is valid
    post_to_ledger(account_id, amount)

# Good - Validate first
def post_transaction(account_id, amount, token):
    response = requests.post(
        f'http://api.example.com/api/v1/accounts/validate-posting',
        params={'account_id': account_id},
        headers={'Authorization': f'Bearer {token}'}
    )
    
    if response.status_code != 204:
        raise ValueError(f"Invalid account: {response.json()['detail']}")
    
    post_to_ledger(account_id, amount)
```

**2. Handle missing default accounts gracefully**:

```typescript
// TypeScript - Graceful default account handling
async function getDefaultAccountOrPrompt(
  transactionType: string,
  token: string
): Promise<Account> {
  const response = await fetch(
    `/api/v1/accounts/default/${transactionType}`,
    {
      method: 'POST',
      headers: { 'Authorization': `Bearer ${token}` }
    }
  );
  
  if (response.status === 404) {
    // Prompt user to select account manually
    const account = await promptUserForAccount(transactionType);
    
    // Optionally save as default for future use
    await saveAsDefault(transactionType, account.id, token);
    
    return account;
  }
  
  if (!response.ok) {
    throw new Error(`Failed to get default account: ${await response.text()}`);
  }
  
  return await response.json();
}
```

**3. Use bulk validation for multiple accounts**:

```python
# Bad - Multiple individual requests
for account_id in account_ids:
    validate_account(account_id)  # N requests

# Good - Single bulk request
validate_accounts_bulk(account_ids)  # 1 request
```

**4. Implement retry logic for transient failures**:

```typescript
// TypeScript - Retry with exponential backoff
async function validateAccountWithRetry(
  accountId: string,
  token: string,
  maxRetries: number = 3
): Promise<boolean> {
  for (let attempt = 0; attempt < maxRetries; attempt++) {
    try {
      const response = await fetch(
        `/api/v1/accounts/validate-posting?account_id=${accountId}`,
        {
          method: 'POST',
          headers: { 'Authorization': `Bearer ${token}` }
        }
      );
      
      return response.status === 204;
    } catch (error) {
      if (attempt === maxRetries - 1) throw error;
      
      // Exponential backoff: 1s, 2s, 4s
      await new Promise(resolve => setTimeout(resolve, Math.pow(2, attempt) * 1000));
    }
  }
  
  return false;
}
```

## Best Practices

### 1. Cache Default Accounts

Default accounts rarely change, so cache them to reduce API calls:

```typescript
// TypeScript - Cache default accounts
class DefaultAccountCache {
  private cache: Map<string, Account> = new Map();
  private cacheExpiry: Map<string, number> = new Map();
  private readonly TTL = 3600000; // 1 hour in milliseconds
  
  async getDefaultAccount(
    transactionType: string,
    scenario: string | undefined,
    token: string
  ): Promise<Account | null> {
    const cacheKey = `${transactionType}:${scenario || 'default'}`;
    
    // Check cache
    const cached = this.cache.get(cacheKey);
    const expiry = this.cacheExpiry.get(cacheKey);
    
    if (cached && expiry && Date.now() < expiry) {
      return cached;
    }
    
    // Fetch from API
    const url = new URL(`/api/v1/accounts/default/${transactionType}`, window.location.origin);
    if (scenario) url.searchParams.set('scenario', scenario);
    
    const response = await fetch(url.toString(), {
      method: 'POST',
      headers: { 'Authorization': `Bearer ${token}` }
    });
    
    if (response.status === 404) return null;
    
    const account = await response.json();
    
    // Update cache
    this.cache.set(cacheKey, account);
    this.cacheExpiry.set(cacheKey, Date.now() + this.TTL);
    
    return account;
  }
  
  clearCache(): void {
    this.cache.clear();
    this.cacheExpiry.clear();
  }
}

// Usage
const cache = new DefaultAccountCache();
const account = await cache.getDefaultAccount('inventory_purchase', undefined, token);
```

### 2. Validate Early, Fail Fast

Validate accounts as early as possible in your workflow:

```python
# Python - Validate at form submission, not at posting time
def submit_purchase_order(po_data: dict, token: str):
    # Validate accounts immediately
    account_ids = [
        po_data['inventory_account_id'],
        po_data['payable_account_id']
    ]
    
    validation = validate_accounts_bulk(account_ids, token)
    
    if validation['invalid_count'] > 0:
        # Fail immediately with clear error message
        invalid_accounts = [inv['account_id'] for inv in validation['invalid']]
        raise ValueError(f"Invalid accounts: {invalid_accounts}")
    
    # Continue with purchase order creation
    create_purchase_order(po_data)
```

### 3. Use Descriptive Transaction References

When posting transactions, include clear references:

```python
transaction_data = {
    'entries': [...],
    'description': 'Inventory purchase from Supplier ABC',
    'reference_type': 'purchase_order',
    'reference_id': 'PO-2024-001',
    'metadata': {
        'supplier_id': 'supplier-uuid',
        'supplier_name': 'Supplier ABC',
        'purchase_date': '2024-01-15',
        'module': 'inventory'
    }
}
```

### 4. Handle Multi-Currency Transactions

When posting transactions in foreign currencies, ensure proper conversion:

```typescript
// TypeScript - Multi-currency transaction posting
interface CurrencyConversion {
  fromCurrency: string;
  toCurrency: string;
  rate: number;
  amount: number;
  convertedAmount: number;
}

async function postForeignCurrencyTransaction(
  accountId: string,
  amount: number,
  currency: string,
  token: string
): Promise<void> {
  // Get account details to check its currency
  const accountResponse = await fetch(`/api/v1/accounts/${accountId}`, {
    headers: { 'Authorization': `Bearer ${token}` }
  });
  const account = await accountResponse.json();
  
  let convertedAmount = amount;
  let conversion: CurrencyConversion | null = null;
  
  // If currencies don't match, convert
  if (account.currency !== currency) {
    const rateResponse = await fetch(
      `/api/v1/currency/exchange-rate?from=${currency}&to=${account.currency}`,
      { headers: { 'Authorization': `Bearer ${token}` } }
    );
    const rate = await rateResponse.json();
    
    convertedAmount = amount * rate.rate;
    conversion = {
      fromCurrency: currency,
      toCurrency: account.currency,
      rate: rate.rate,
      amount,
      convertedAmount
    };
  }
  
  // Post transaction with conversion details
  const transactionData = {
    account_id: accountId,
    amount: convertedAmount,
    currency: account.currency,
    original_amount: amount,
    original_currency: currency,
    conversion: conversion,
    metadata: {
      exchange_rate_date: new Date().toISOString()
    }
  };
  
  // Post to general ledger
}
```

### 5. Implement Proper Logging

Log all account-related operations for audit and debugging:

```python
# Python - Comprehensive logging
import logging

logger = logging.getLogger(__name__)

def post_transaction_with_logging(account_id: str, amount: float, token: str):
    logger.info(f"Starting transaction posting", extra={
        'account_id': account_id,
        'amount': amount,
        'operation': 'post_transaction'
    })
    
    try:
        # Validate account
        validation_response = requests.post(
            f'http://api.example.com/api/v1/accounts/validate-posting',
            params={'account_id': account_id},
            headers={'Authorization': f'Bearer {token}'}
        )
        
        if validation_response.status_code != 204:
            logger.error(f"Account validation failed", extra={
                'account_id': account_id,
                'status_code': validation_response.status_code,
                'error': validation_response.json()
            })
            raise ValueError("Invalid account")
        
        logger.info(f"Account validated successfully", extra={
            'account_id': account_id
        })
        
        # Post transaction
        result = post_to_ledger(account_id, amount)
        
        logger.info(f"Transaction posted successfully", extra={
            'account_id': account_id,
            'amount': amount,
            'transaction_id': result['id']
        })
        
        return result
        
    except Exception as e:
        logger.exception(f"Transaction posting failed", extra={
            'account_id': account_id,
            'amount': amount,
            'error': str(e)
        })
        raise
```

## Troubleshooting

### Issue 1: "Account not found" Error

**Symptom**: Receiving 404 errors when trying to validate or retrieve accounts.

**Possible Causes**:
1. Account ID is incorrect or doesn't exist
2. Account belongs to a different organization (multi-tenancy issue)
3. Account was deleted

**Solution**:

```python
# Verify account exists and belongs to your organization
def verify_account_exists(account_id: str, token: str) -> bool:
    response = requests.get(
        f'http://api.example.com/api/v1/accounts/{account_id}',
        headers={'Authorization': f'Bearer {token}'}
    )
    
    if response.status_code == 404:
        print(f"Account {account_id} not found")
        return False
    
    if response.status_code == 403:
        print(f"Account {account_id} belongs to different organization")
        return False
    
    account = response.json()
    print(f"Found account: {account['account_code']} - {account['account_name']}")
    return True
```

### Issue 2: "Default account not configured" Error

**Symptom**: Receiving 404 errors when requesting default accounts.

**Possible Causes**:
1. Default account mapping hasn't been configured
2. Transaction type name is incorrect (case-sensitive)
3. Scenario parameter doesn't match configured scenarios

**Solution**:

```python
# Check if default account is configured
def check_default_account_config(transaction_type: str, token: str):
    # List all configured defaults
    response = requests.get(
        'http://api.example.com/api/v1/accounts/config/defaults',
        headers={'Authorization': f'Bearer {token}'}
    )
    
    defaults = response.json()
    
    # Check if transaction type exists
    matching = [d for d in defaults if d['transaction_type'] == transaction_type]
    
    if not matching:
        print(f"No default account configured for '{transaction_type}'")
        print(f"Available transaction types:")
        for d in defaults:
            scenario_info = f" (scenario: {d['scenario']})" if d['scenario'] else ""
            print(f"  - {d['transaction_type']}{scenario_info}")
        return False
    
    print(f"Found {len(matching)} default account(s) for '{transaction_type}':")
    for d in matching:
        scenario_info = f" (scenario: {d['scenario']})" if d['scenario'] else ""
        print(f"  - {d['account_code']} - {d['account_name']}{scenario_info}")
    return True
```

### Issue 3: "Account is inactive" Error

**Symptom**: Validation fails with message that account is inactive.

**Possible Causes**:
1. Account was deactivated by administrator
2. Account is archived

**Solution**:

```typescript
// Check account status and suggest alternatives
async function checkAccountStatus(accountId: string, token: string): Promise<void> {
  const response = await fetch(`/api/v1/accounts/${accountId}`, {
    headers: { 'Authorization': `Bearer ${token}` }
  });
  
  const account = await response.json();
  
  console.log(`Account Status: ${account.status}`);
  
  if (account.status !== 'ACTIVE') {
    console.log(`Account ${account.account_code} is ${account.status}`);
    
    // Search for similar active accounts
    const searchResponse = await fetch(
      `/api/v1/accounts?search=${account.account_name}&status=ACTIVE`,
      { headers: { 'Authorization': `Bearer ${token}` } }
    );
    
    const searchResults = await searchResponse.json();
    
    if (searchResults.items.length > 0) {
      console.log('Suggested alternative accounts:');
      searchResults.items.forEach((alt: Account) => {
        console.log(`  - ${alt.account_code}: ${alt.account_name}`);
      });
    }
  }
}
```

### Issue 4: "Account is a parent account" Error

**Symptom**: Validation fails because account has child accounts.

**Possible Causes**:
1. Attempting to post to a control/summary account
2. Account has `is_posting_account = false`

**Solution**:

```python
# Find posting accounts under a parent account
def find_posting_accounts(parent_account_id: str, token: str):
    # Get all descendants
    response = requests.get(
        f'http://api.example.com/api/v1/accounts/{parent_account_id}/descendants',
        headers={'Authorization': f'Bearer {token}'}
    )
    
    descendants = response.json()
    
    # Filter for posting accounts
    posting_accounts = [
        acc for acc in descendants 
        if acc['is_posting_account'] and acc['status'] == 'ACTIVE'
    ]
    
    print(f"Found {len(posting_accounts)} posting accounts:")
    for acc in posting_accounts:
        print(f"  - {acc['account_code']}: {acc['account_name']}")
    
    return posting_accounts
```

### Issue 5: Bulk Validation Performance

**Symptom**: Bulk validation is slow with many accounts.

**Solution**:

```python
# Optimize bulk validation with batching
def validate_accounts_in_batches(account_ids: list, token: str, batch_size: int = 50):
    """
    Validate accounts in batches to avoid overwhelming the API.
    """
    results = {
        'valid': [],
        'invalid': []
    }
    
    for i in range(0, len(account_ids), batch_size):
        batch = account_ids[i:i + batch_size]
        
        response = requests.post(
            'http://api.example.com/api/v1/accounts/validate-posting/bulk',
            params={'account_ids': batch},
            headers={'Authorization': f'Bearer {token}'}
        )
        
        batch_result = response.json()
        results['valid'].extend(batch_result['valid'])
        results['invalid'].extend(batch_result['invalid'])
    
    return results
```

### Issue 6: Multi-Tenancy Issues

**Symptom**: Cannot access accounts that should exist.

**Possible Causes**:
1. JWT token has wrong organization_id
2. Attempting to access accounts from different organization

**Solution**:

```typescript
// Verify token organization matches expected organization
function verifyTokenOrganization(token: string, expectedOrgId: string): boolean {
  // Decode JWT (use a proper JWT library in production)
  const payload = JSON.parse(atob(token.split('.')[1]));
  
  if (payload.organization_id !== expectedOrgId) {
    console.error(
      `Token organization mismatch: expected ${expectedOrgId}, got ${payload.organization_id}`
    );
    return false;
  }
  
  return true;
}
```

### Issue 7: Account Code Format Validation Failures

**Symptom**: Account codes are rejected during creation.

**Solution**:

```python
# Check current account code format and validate before creation
def validate_account_code_format(account_code: str, token: str) -> bool:
    # Get current format pattern
    response = requests.get(
        'http://api.example.com/api/v1/accounts/config/format',
        headers={'Authorization': f'Bearer {token}'}
    )
    
    config = response.json()
    pattern = config['format_pattern']
    example = config['example']
    
    import re
    if not re.match(pattern, account_code):
        print(f"Account code '{account_code}' does not match required format")
        print(f"Pattern: {pattern}")
        print(f"Example: {example}")
        return False
    
    print(f"Account code '{account_code}' is valid")
    return True
```

### Getting Help

If you encounter issues not covered in this troubleshooting guide:

1. **Check API logs**: Review server logs for detailed error messages
2. **Verify authentication**: Ensure JWT token is valid and not expired
3. **Test with curl**: Use curl to isolate issues from application code
4. **Contact support**: Provide request/response details and error messages

**Example curl test**:

```bash
# Test account validation
curl -X POST "http://api.example.com/api/v1/accounts/validate-posting?account_id=YOUR_ACCOUNT_ID" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -v
```

---

## Summary

This integration API provides:

- **Validation endpoints** for ensuring accounts can receive postings
- **Retrieval endpoints** for getting account details by ID or code
- **Default account system** for automatic account selection
- **Search and filter** capabilities for account discovery
- **Reusable UI components** for consistent user experience
- **Comprehensive error handling** for robust integrations

For additional support or questions, refer to the main Chart of Accounts documentation or contact the development team.
