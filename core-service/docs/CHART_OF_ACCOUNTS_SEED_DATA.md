# Chart of Accounts Seed Data Documentation

## Overview

The Chart of Accounts seed data script provides a comprehensive sample accounting structure for testing and demonstration purposes. It creates a realistic Chart of Accounts with hierarchical organization, multiple account types, and multi-currency support.

## Quick Start

### Prerequisites

1. PostgreSQL database running and accessible
2. Database migrations applied (Alembic)
3. Python environment with required dependencies installed

### Running the Seed Script

```bash
# From the core-service directory
cd horizon-sync-erp-be/core-service

# Run the seed script
python seed_chart_of_accounts.py
```

### Configuration

The script uses the following default configuration:

```python
DATABASE_URL = "postgresql://horizon_user:horizon_pass@localhost:5432/core_db"
ORG_ID = uuid.UUID("b1f71de1-0a19-424e-9580-1d3f871c5b1f")
ADMIN_USER = "admin@example.com"
```

To customize these values, you can either:
1. Edit the script directly
2. Set environment variables (requires script modification to read from env)
3. Pass parameters via command line (requires script modification)

## Account Structure

The seed data creates **52 accounts** organized into 5 main categories:

### 1. Assets (1000-1999)

Assets represent resources owned by the company.

**Parent Account:**
- `1000` - Assets (non-posting)

**Current Assets (1100-1199):**
- `1100` - Current Assets (non-posting parent)
  - `1110` - Cash and Cash Equivalents
  - `1120` - Accounts Receivable
  - `1130` - Inventory (non-posting parent)
    - `1131` - Raw Materials Inventory
    - `1132` - Finished Goods Inventory

**Fixed Assets (1200-1299):**
- `1200` - Fixed Assets (non-posting parent)
  - `1210` - Property, Plant and Equipment
  - `1220` - Accumulated Depreciation

### 2. Liabilities (2000-2999)

Liabilities represent obligations owed by the company.

**Parent Account:**
- `2000` - Liabilities (non-posting)

**Current Liabilities (2100-2199):**
- `2100` - Current Liabilities (non-posting parent)
  - `2110` - Accounts Payable
  - `2120` - Accrued Expenses
  - `2130` - Sales Tax Payable

**Long-term Liabilities (2200-2299):**
- `2200` - Long-term Liabilities (non-posting parent)
  - `2210` - Long-term Debt

### 3. Equity (3000-3999)

Equity represents the owner's stake in the company.

**Parent Account:**
- `3000` - Equity (non-posting)
  - `3100` - Owner's Capital
  - `3200` - Retained Earnings
  - `3300` - Drawings

### 4. Income/Revenue (4000-4999)

Income accounts track revenue and earnings.

**Parent Account:**
- `4000` - Revenue (non-posting)

**Sales Revenue (4100-4199):**
- `4100` - Sales Revenue (non-posting parent)
  - `4110` - Domestic Sales
  - `4120` - International Sales (non-posting parent)
    - `4121` - International Sales - EUR (EUR currency)

**Service Revenue (4200-4299):**
- `4200` - Service Revenue

**Other Income (4300-4399):**
- `4300` - Other Income (non-posting parent)
  - `4310` - Interest Income

### 5. Expenses (5000-5999)

Expense accounts track costs and expenditures.

**Parent Account:**
- `5000` - Expenses (non-posting)

**Cost of Goods Sold (5100-5199):**
- `5100` - Cost of Goods Sold (non-posting parent)
  - `5110` - Material Costs
  - `5120` - Labor Costs

**Operating Expenses (5200-5299):**
- `5200` - Operating Expenses (non-posting parent)
  - `5210` - Salaries and Wages
  - `5220` - Rent Expense
  - `5230` - Utilities
  - `5240` - Office Supplies

**Marketing Expenses (5300-5399):**
- `5300` - Marketing and Advertising (non-posting parent)
  - `5310` - Digital Marketing
  - `5320` - Traditional Marketing

**Other Expenses (5400-5499):**
- `5400` - Other Expenses (non-posting parent)
  - `5410` - Bank Charges
  - `5420` - Depreciation Expense

## Key Features

### Hierarchical Structure

The seed data demonstrates a 3-level hierarchy:
- **Level 1:** Main category accounts (Assets, Liabilities, etc.)
- **Level 2:** Sub-category accounts (Current Assets, Fixed Assets, etc.)
- **Level 3:** Specific posting accounts (Cash, Accounts Receivable, etc.)

Parent accounts are marked with `is_posting_account=False` to prevent direct transaction posting.

### Multi-Currency Support

The seed data includes accounts in multiple currencies:
- **USD:** Default currency for most accounts
- **EUR:** International Sales - EUR account (4121)

This demonstrates the system's ability to handle multi-currency transactions.

### Account Coding System

The account codes follow a standard numbering convention:
- **1000-1999:** Assets
- **2000-2999:** Liabilities
- **3000-3999:** Equity
- **4000-4999:** Income/Revenue
- **5000-5999:** Expenses

This makes it easy to identify account types at a glance.

## Usage Examples

### Testing Account Creation

```python
# The seed script can be run multiple times safely
# It checks for existing accounts and skips duplicates
python seed_chart_of_accounts.py
```

### Verifying Seeded Data

```sql
-- Count accounts by type
SELECT account_type, COUNT(*) 
FROM accounts 
WHERE organization_id = 'b1f71de1-0a19-424e-9580-1d3f871c5b1f'
GROUP BY account_type;

-- View account hierarchy
SELECT 
    a.account_code,
    a.account_name,
    a.account_type,
    p.account_code as parent_code,
    p.account_name as parent_name
FROM accounts a
LEFT JOIN accounts p ON a.parent_account_id = p.id
WHERE a.organization_id = 'b1f71de1-0a19-424e-9580-1d3f871c5b1f'
ORDER BY a.account_code;

-- View posting accounts only
SELECT account_code, account_name, account_type
FROM accounts
WHERE organization_id = 'b1f71de1-0a19-424e-9580-1d3f871c5b1f'
  AND is_posting_account = true
ORDER BY account_code;
```

### Testing with the API

```bash
# Get all accounts
curl http://localhost:8000/api/v1/accounts

# Get specific account
curl http://localhost:8000/api/v1/accounts/{account_id}

# Get account hierarchy
curl http://localhost:8000/api/v1/accounts/{account_id}/hierarchy

# Search accounts
curl http://localhost:8000/api/v1/accounts/search?query=cash

# Filter by type
curl http://localhost:8000/api/v1/accounts?account_type=asset
```

## Customization

### Adding More Accounts

To add additional accounts to the seed data:

1. Open `seed_chart_of_accounts.py`
2. Add new entries to the `accounts_data` list:

```python
{
    "account_code": "1140",
    "account_name": "Prepaid Expenses",
    "account_type": AccountType.ASSET,
    "currency": "USD",
    "description": "Expenses paid in advance",
    "parent_code": "1100",
    "is_posting_account": True,
}
```

3. Run the script again

### Changing Organization ID

To seed data for a different organization:

1. Update the `ORG_ID` constant in the script:

```python
ORG_ID = uuid.UUID("your-organization-id-here")
```

2. Run the script

### Multi-Currency Accounts

To add more multi-currency accounts:

```python
{
    "account_code": "4122",
    "account_name": "International Sales - GBP",
    "account_type": AccountType.INCOME,
    "currency": "GBP",  # British Pound
    "description": "Export sales in British Pounds",
    "parent_code": "4120",
}
```

## Integration with Other Modules

### Default Account Configuration

After seeding, you can configure default accounts for integration with other modules:

```python
# Example: Configure default accounts for inventory module
from app.services.default_account_service import DefaultAccountService

service = DefaultAccountService(db)

# Set default account for inventory purchases
service.set_default_account(
    transaction_type="inventory_purchase",
    account_code="1131",  # Raw Materials Inventory
    scenario="default"
)

# Set default account for sales
service.set_default_account(
    transaction_type="sales_revenue",
    account_code="4110",  # Domestic Sales
    scenario="domestic"
)
```

### Testing Transaction Posting

```python
# Example: Test posting a transaction to a seeded account
from app.services.chart_of_account_service import ChartOfAccountService

service = ChartOfAccountService(db)

# Validate account for posting
result = service.validate_posting_account("1110")  # Cash account
# Should return: {"valid": True, "account": {...}}

# Get account by code
account = service.get_account_by_code("1110")
```

## Troubleshooting

### Script Fails with "Account already exists"

This is normal behavior. The script checks for existing accounts and skips them. You'll see:
```
⊘ 1000 - Assets (already exists)
```

### Database Connection Error

Verify your database connection string:
```python
DATABASE_URL = "postgresql://user:password@host:port/database"
```

Ensure:
- PostgreSQL is running
- Database exists
- Credentials are correct
- Network connectivity is available

### Parent Account Not Found

If you see errors about parent accounts not found, ensure:
1. Parent accounts are defined before child accounts in `accounts_data`
2. The `parent_code` matches an existing `account_code`

### Organization ID Not Found

Ensure the organization exists in your database:
```sql
SELECT id, name FROM organizations;
```

Update the `ORG_ID` constant to match an existing organization.

## Best Practices

### 1. Run After Migrations

Always run database migrations before seeding:
```bash
alembic upgrade head
python seed_chart_of_accounts.py
```

### 2. Use in Development/Testing Only

The seed script is designed for development and testing environments. For production:
- Create accounts through the UI or API
- Import from existing accounting systems
- Use proper data migration tools

### 3. Backup Before Seeding

If running in an environment with existing data:
```bash
pg_dump core_db > backup_before_seed.sql
python seed_chart_of_accounts.py
```

### 4. Verify After Seeding

Always verify the seeded data:
```bash
# Check account count
psql -d core_db -c "SELECT COUNT(*) FROM accounts WHERE organization_id = 'your-org-id';"

# Check hierarchy integrity
psql -d core_db -c "SELECT COUNT(*) FROM accounts WHERE parent_account_id IS NOT NULL;"
```

## Related Documentation

- [Chart of Accounts Integration API](./CHART_OF_ACCOUNTS_INTEGRATION_API.md)
- [Default Accounts Infrastructure](./DEFAULT_ACCOUNTS_INFRASTRUCTURE.md)
- [Requirements Document](../../.kiro/specs/erp-chart-of-accounts/requirements.md)
- [Design Document](../../.kiro/specs/erp-chart-of-accounts/design.md)

## Support

For issues or questions:
1. Check the troubleshooting section above
2. Review the requirements and design documents
3. Examine the seed script source code
4. Test with the API endpoints

## License

This seed data script is part of the Horizon Sync ERP system and follows the same license terms.
