# Seed Data Guide - Core Service

## Problem
The seed script fails because tables don't exist yet or there's a mismatch between the model and database schema.

## Solution Options

### Option 1: Fix Seed Script (Recommended)
The seed script has been fixed to handle missing tables gracefully. After creating tables, run:

```bash
docker compose exec core-service python scripts/seed_data.py
```

### Option 2: Manual SQL Script (Quick Fix)

#### Step 1: Get UUIDs from identity_db

```bash
# Connect to identity_db
docker compose exec postgres psql -U horizon_user -d identity_db

# Get organization ID
SELECT id FROM organizations WHERE slug = 'default-org';

# Get admin user ID
SELECT id FROM users WHERE email = 'admin@example.com';

# Exit
\q
```

#### Step 2: Run the simple seed script

```bash
# Edit the script first to replace UUIDs
docker compose exec postgres psql -U horizon_user -d core_db

# Then copy-paste the content from seed_data_simple.sql
# OR use variables:
\set org_id 'your-org-uuid-here'
\set admin_user_id 'your-admin-uuid-here'
\i /app/scripts/seed_data_simple.sql
```

#### Step 3: One-liner (if you have the UUIDs)

```bash
# Replace UUIDs in the command below
ORG_ID="your-org-uuid"
ADMIN_ID="your-admin-uuid"

docker compose exec postgres psql -U horizon_user -d core_db << EOF
\set org_id '$ORG_ID'
\set admin_user_id '$ADMIN_ID'
\i /app/scripts/seed_data_simple.sql
EOF
```

### Option 3: Fully Automated Script

If you want to fetch UUIDs automatically, use `seed_data_manual.sql` (requires dblink extension):

```bash
# Enable dblink extension first
docker compose exec postgres psql -U horizon_user -d core_db -c "CREATE EXTENSION IF NOT EXISTS dblink;"

# Run the script
docker compose exec postgres psql -U horizon_user -d core_db -f /app/scripts/seed_data_manual.sql
```

## What Gets Seeded

- **3 Warehouses**: Main Warehouse, Retail Store, Transit Warehouse
- **4 Item Groups**: Raw Materials, Finished Goods, Consumables, Services
- **7 Items**:
  - Raw Materials: RM-STEEL-001, RM-PLAST-001
  - Finished Goods: FG-WIDGET-001, FG-GADGET-001
  - Consumables: CON-PACK-001
  - Services: SRV-INSTALL-001, SRV-MAINT-001

## Verification

After seeding, verify the data:

```sql
\c core_db;

SELECT 'Warehouses' AS type, COUNT(*) AS count FROM warehouses_extended
UNION ALL
SELECT 'Item Groups', COUNT(*) FROM item_groups
UNION ALL
SELECT 'Items', COUNT(*) FROM items;

-- View sample data
SELECT code, name FROM warehouses_extended;
SELECT code, name FROM item_groups;
SELECT item_code, item_name, item_type FROM items LIMIT 5;
```
