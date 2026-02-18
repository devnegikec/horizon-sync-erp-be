# Default Accounts Infrastructure

## Overview

This document describes the default accounts infrastructure implemented for the ERP Chart of Accounts system. The infrastructure allows configuration of default accounts for common transaction types with support for multiple scenarios.

## Database Schema

### Table: `default_accounts`

Stores mappings between transaction types and account IDs, supporting multiple defaults per transaction type through scenarios.

**Columns:**
- `id` (UUID): Primary key, auto-generated
- `transaction_type` (VARCHAR(100)): Type of transaction (e.g., "INVENTORY_PURCHASE", "SALES_REVENUE")
- `scenario` (VARCHAR(100), nullable): Optional scenario for multiple defaults (e.g., "DOMESTIC", "INTERNATIONAL")
- `account_id` (UUID): Foreign key to accounts table (ON DELETE RESTRICT)
- `organization_id` (UUID): Multi-tenancy support
- `created_at` (TIMESTAMP): Record creation timestamp
- `updated_at` (TIMESTAMP): Record update timestamp

**Constraints:**
- Unique constraint on (`organization_id`, `transaction_type`, `scenario`)
- Foreign key to `accounts.id` with RESTRICT on delete

**Indexes:**
- `idx_default_accounts_transaction_type` on `transaction_type`
- `idx_default_accounts_scenario` on `scenario`
- `idx_default_accounts_organization_id` on `organization_id`

## SQLAlchemy Model

### `DefaultAccount` Model

Located in: `app/models/default_account.py`

**Features:**
- UUID primary key with auto-generation
- Relationship to Account model
- Automatic timestamp management (created_at, updated_at)
- Multi-tenancy support via organization_id
- String representation for debugging

**Usage Example:**

```python
from app.models.default_account import DefaultAccount

# Create a default account for domestic sales
default_account = DefaultAccount(
    transaction_type="SALES_REVENUE",
    scenario="DOMESTIC",
    account_id=domestic_sales_account_id,
    organization_id=org_id,
)
db.add(default_account)
db.commit()

# Create a default account without scenario
default_account = DefaultAccount(
    transaction_type="INVENTORY_PURCHASE",
    scenario=None,
    account_id=inventory_account_id,
    organization_id=org_id,
)
```

## Migration

**Migration File:** `alembic/versions/e5f6g7h8i9j0_add_default_accounts_table.py`

**Revision:** e5f6g7h8i9j0  
**Parent Revision:** d4e5f6g7h8i9

To apply the migration:
```bash
alembic upgrade head
```

To rollback:
```bash
alembic downgrade d4e5f6g7h8i9
```

## Requirements Satisfied

This infrastructure satisfies the following requirements from the ERP Chart of Accounts specification:

- **Requirement 12.1**: System allows configuration of default accounts for common transaction types
- **Requirement 12.5**: System supports multiple default accounts per transaction type for different scenarios

## Use Cases

### 1. Single Default Account
Configure one default account for a transaction type:
```python
# Default account for all inventory purchases
DefaultAccount(
    transaction_type="INVENTORY_PURCHASE",
    scenario=None,
    account_id=inventory_account_id,
    organization_id=org_id,
)
```

### 2. Multiple Scenarios
Configure different accounts for different scenarios:
```python
# Domestic sales revenue
DefaultAccount(
    transaction_type="SALES_REVENUE",
    scenario="DOMESTIC",
    account_id=domestic_sales_account_id,
    organization_id=org_id,
)

# International sales revenue
DefaultAccount(
    transaction_type="SALES_REVENUE",
    scenario="INTERNATIONAL",
    account_id=international_sales_account_id,
    organization_id=org_id,
)
```

## Testing

Unit tests are located in: `tests/test_default_account_model.py`

Run tests:
```bash
pytest tests/test_default_account_model.py -v
```

**Test Coverage:**
- Default account creation with scenario
- Default account creation without scenario
- Multiple scenarios for same transaction type
- String representation (repr)
- Model validation

## Next Steps

The following components need to be implemented to complete the default accounts feature:

1. **DefaultAccountService** - Business logic for managing default accounts
2. **API Endpoints** - REST API for CRUD operations on default accounts
3. **Validation** - Ensure account exists, is active, and is of appropriate type
4. **UI Components** - Frontend interface for configuring default accounts
5. **Integration** - Allow other modules to query default accounts

## Related Files

- Migration: `alembic/versions/e5f6g7h8i9j0_add_default_accounts_table.py`
- Model: `app/models/default_account.py`
- Tests: `tests/test_default_account_model.py`
- Model Export: `app/models/__init__.py`
