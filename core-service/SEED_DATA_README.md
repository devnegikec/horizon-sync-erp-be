# Seed Data Scripts - Quick Reference

This document provides a quick reference for all available seed data scripts in the Horizon Sync ERP system.

## Available Seed Scripts

### 1. Chart of Accounts Seed Data

**Script:** `seed_chart_of_accounts.py`

**Purpose:** Creates a comprehensive sample Chart of Accounts with 52 accounts across all account types (Assets, Liabilities, Equity, Income, Expenses).

**Usage:**
```bash
python seed_chart_of_accounts.py
```

**What it creates:**
- 52 accounts organized hierarchically
- Examples for each account type
- Multi-currency support (USD, EUR)
- Parent-child relationships
- Realistic account codes and descriptions

**Documentation:** See [docs/CHART_OF_ACCOUNTS_SEED_DATA.md](docs/CHART_OF_ACCOUNTS_SEED_DATA.md)

**Key Accounts Created:**
- Assets: Cash (1110), Accounts Receivable (1120), Inventory (1130)
- Liabilities: Accounts Payable (2110), Accrued Expenses (2120)
- Equity: Owner's Capital (3100), Retained Earnings (3200)
- Income: Domestic Sales (4110), Service Revenue (4200)
- Expenses: Material Costs (5110), Salaries (5210)

---

### 2. Suppliers Seed Data

**Script:** `seed_suppliers.py`

**Purpose:** Creates sample supplier records for testing procurement and sourcing workflows.

**Usage:**
```bash
python seed_suppliers.py
```

**What it creates:**
- 4 sample suppliers
- Various payment terms (30, 45, 60 days)
- Complete contact information
- Active status

**Suppliers Created:**
- Acme Corporation1 (ACME001)
- Global Suppliers1 (GLOBAL001)
- Tech Parts Ltd (TECH001)
- Industrial Materials Co (INDMAT001)

---

### 3. Inventory Seed Data

**Script:** `scripts/seed_data.py`

**Purpose:** Creates sample inventory data including warehouses, item groups, and items.

**Usage:**
```bash
python scripts/seed_data.py
```

**What it creates:**
- 3 warehouses (Main, Retail Store, Transit)
- 4 item groups (Raw Materials, Finished Goods, Consumables, Services)
- 7 sample items with various configurations

**Items Created:**
- Raw Materials: Steel Sheet, ABS Plastic Granules
- Finished Goods: Widget Pro, Gadget Max
- Consumables: Packaging Box
- Services: Installation Service, Annual Maintenance

---

## Running All Seed Scripts

To seed all data at once, run the scripts in this order:

```bash
# 1. Seed inventory data (warehouses, items, item groups)
python scripts/seed_data.py

# 2. Seed suppliers
python seed_suppliers.py

# 3. Seed Chart of Accounts
python seed_chart_of_accounts.py
```

## Configuration

All seed scripts use the following default configuration:

```python
DATABASE_URL = "postgresql://horizon_user:horizon_pass@localhost:5432/core_db"
ORG_ID = uuid.UUID("b1f71de1-0a19-424e-9580-1d3f871c5b1f")
```

### Customizing Configuration

To use different values:

1. **Edit the script directly** (quick for testing)
2. **Use environment variables** (recommended for different environments)
3. **Create a config file** (best for multiple configurations)

Example with environment variables:

```bash
export DATABASE_URL="postgresql://user:pass@host:5432/db"
export ORG_ID="your-org-id-here"
python seed_chart_of_accounts.py
```

## Prerequisites

Before running any seed script:

1. **Database is running:**
   ```bash
   # Check PostgreSQL status
   pg_isready -h localhost -p 5432
   ```

2. **Database exists:**
   ```bash
   psql -l | grep core_db
   ```

3. **Migrations are applied:**
   ```bash
   alembic upgrade head
   ```

4. **Dependencies are installed:**
   ```bash
   pip install -r requirements.txt
   ```

## Verifying Seed Data

After running seed scripts, verify the data:

```sql
-- Check Chart of Accounts
SELECT COUNT(*) FROM accounts;
SELECT account_type, COUNT(*) FROM accounts GROUP BY account_type;

-- Check Suppliers
SELECT COUNT(*) FROM suppliers;
SELECT supplier_code, supplier_name FROM suppliers;

-- Check Items
SELECT COUNT(*) FROM items;
SELECT item_code, item_name FROM items;

-- Check Warehouses
SELECT COUNT(*) FROM warehouses;
SELECT code, name FROM warehouses;
```

## Resetting Seed Data

To remove seeded data and start fresh:

```sql
-- WARNING: This will delete all data!

-- Delete Chart of Accounts (cascade will handle relationships)
DELETE FROM accounts WHERE organization_id = 'b1f71de1-0a19-424e-9580-1d3f871c5b1f';

-- Delete Suppliers
DELETE FROM suppliers WHERE organization_id = 'b1f71de1-0a19-424e-9580-1d3f871c5b1f';

-- Delete Items
DELETE FROM items WHERE organization_id = 'b1f71de1-0a19-424e-9580-1d3f871c5b1f';

-- Delete Warehouses
DELETE FROM warehouses WHERE organization_id = 'b1f71de1-0a19-424e-9580-1d3f871c5b1f';
```

Or use a complete database reset:

```bash
# Drop and recreate database
dropdb core_db
createdb core_db

# Run migrations
alembic upgrade head

# Re-run seed scripts
python scripts/seed_data.py
python seed_suppliers.py
python seed_chart_of_accounts.py
```

## Troubleshooting

### "Account/Supplier/Item already exists"

This is normal. Seed scripts check for existing records and skip duplicates. You'll see messages like:
```
⊘ 1000 - Assets (already exists)
```

### Database Connection Failed

Check:
- PostgreSQL is running: `pg_isready`
- Database exists: `psql -l | grep core_db`
- Credentials are correct in DATABASE_URL
- Network connectivity to database host

### Organization Not Found

Ensure the organization exists:
```sql
SELECT id, name FROM organizations;
```

Update the `ORG_ID` in the seed script to match an existing organization.

### Foreign Key Violations

This usually means:
- Organization doesn't exist
- Parent account doesn't exist (for Chart of Accounts)
- Item group doesn't exist (for Items)

Run seed scripts in the correct order (see "Running All Seed Scripts" above).

## Best Practices

### 1. Development Environment

Seed scripts are designed for development and testing:
```bash
# Safe to run multiple times
python seed_chart_of_accounts.py
```

### 2. Testing Environment

Use seed data for automated testing:
```python
# In your test setup
import subprocess
subprocess.run(["python", "seed_chart_of_accounts.py"])
```

### 3. Production Environment

**DO NOT** use seed scripts in production. Instead:
- Import from existing systems
- Use the UI to create accounts
- Use proper data migration tools
- Follow your organization's data governance policies

### 4. Backup Before Seeding

Always backup before running seed scripts on important data:
```bash
pg_dump core_db > backup_$(date +%Y%m%d_%H%M%S).sql
python seed_chart_of_accounts.py
```

## Integration Testing

After seeding, test the integration:

```bash
# Test Chart of Accounts API
curl http://localhost:8000/api/v1/accounts

# Test Suppliers API
curl http://localhost:8000/api/v1/suppliers

# Test Items API
curl http://localhost:8000/api/v1/items

# Test Warehouses API
curl http://localhost:8000/api/v1/warehouses
```

## Creating Custom Seed Scripts

To create a new seed script:

1. **Copy an existing script** as a template
2. **Define your data structure** in a list/dict
3. **Check for existing records** to avoid duplicates
4. **Use transactions** for data integrity
5. **Add helpful output** for debugging
6. **Document the script** in this README

Example template:

```python
"""Seed [entity] data for testing"""

import uuid
from datetime import datetime, UTC
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.models.your_model import YourModel

DATABASE_URL = "postgresql://horizon_user:horizon_pass@localhost:5432/core_db"
ORG_ID = uuid.UUID("b1f71de1-0a19-424e-9580-1d3f871c5b1f")

data = [
    # Your seed data here
]

def seed_data():
    engine = create_engine(DATABASE_URL)
    SessionLocal = sessionmaker(bind=engine)
    db = SessionLocal()
    
    try:
        for item in data:
            # Check if exists
            existing = db.query(YourModel).filter(...).first()
            if existing:
                print(f"Skipping {item['name']} (already exists)")
                continue
            
            # Create new record
            record = YourModel(**item)
            db.add(record)
            print(f"Created {item['name']}")
        
        db.commit()
        print("Seeding complete!")
    except Exception as e:
        db.rollback()
        print(f"Error: {e}")
        raise
    finally:
        db.close()

if __name__ == "__main__":
    seed_data()
```

## Related Documentation

- [Chart of Accounts Seed Data](docs/CHART_OF_ACCOUNTS_SEED_DATA.md)
- [Seeding Guide](scripts/SEEDING_GUIDE.md)
- [Stock Seed Data](scripts/STOCK_SEED_DATA_README.md)

## Support

For issues with seed scripts:
1. Check this README
2. Review the specific script's documentation
3. Verify prerequisites are met
4. Check database logs for errors
5. Review the script source code

## Contributing

When adding new seed scripts:
1. Follow the existing patterns
2. Add documentation to this README
3. Include error handling
4. Make scripts idempotent (safe to run multiple times)
5. Add verification queries
