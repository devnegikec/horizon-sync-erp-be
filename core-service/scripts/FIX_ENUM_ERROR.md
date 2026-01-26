# Fix Enum Error: 'stock' is not among the defined enum values

## Problem

The error occurs because PostgreSQL enum types have uppercase values (STOCK, NON_STOCK) but the code is trying to use lowercase values ('stock', 'non_stock').

## Solution

### Option 1: Quick Fix (Recommended if no important data)

```bash
# 1. Connect to database
docker compose exec postgres psql -U horizon_user -d core_db

# 2. Run the fix script
\i /app/scripts/fix_enums_safe.sql

# OR copy the script content and paste it directly
```

### Option 2: Manual Fix via Docker

```bash
# Copy script to container
docker compose cp core-service/scripts/fix_enums_safe.sql horizon_postgres:/tmp/

# Run it
docker compose exec postgres psql -U horizon_user -d core_db -f /tmp/fix_enums_safe.sql
```

### Option 3: Run SQL Directly

```bash
docker compose exec postgres psql -U horizon_user -d core_db << EOF
DROP TYPE IF EXISTS itemtype CASCADE;
DROP TYPE IF EXISTS itemstatus CASCADE;
DROP TYPE IF EXISTS valuationmethod CASCADE;
DROP TYPE IF EXISTS warehousetype CASCADE;

CREATE TYPE itemtype AS ENUM ('stock', 'non_stock', 'service', 'fixed_asset');
CREATE TYPE itemstatus AS ENUM ('active', 'inactive', 'discontinued');
CREATE TYPE valuationmethod AS ENUM ('fifo', 'lifo', 'moving_average', 'standard');
CREATE TYPE warehousetype AS ENUM ('warehouse', 'store', 'virtual', 'transit');
EOF
```

## After Fixing Enums

1. **Recreate tables** (if they were dropped):

   ```bash
   docker compose exec postgres psql -U horizon_user -d core_db -f /app/scripts/create_tables.sql
   ```

2. **OR run Alembic migrations**:

   ```bash
   docker compose exec core-service python -m alembic upgrade head
   ```

3. **Restart core-service**:
   ```bash
   docker compose restart core-service
   ```

## What Was Fixed

✅ **Seed script** (`seed_data.py`) - Now uses string values directly:

- `"warehouse"` instead of `WarehouseType.WAREHOUSE`
- `"stock"` instead of `ItemType.STOCK`
- `"fifo"` instead of `ValuationMethod.FIFO`
- `"active"` instead of `ItemStatus.ACTIVE`

✅ **Database enums** - Recreated with lowercase values

## Verification

After running the fix, verify enums:

```sql
SELECT
    t.typname AS enum_name,
    string_agg(e.enumlabel, ', ' ORDER BY e.enumsortorder) AS enum_values
FROM pg_type t
JOIN pg_enum e ON t.oid = e.enumtypid
WHERE t.typname IN ('itemtype', 'itemstatus', 'valuationmethod', 'warehousetype')
GROUP BY t.typname;
```

You should see lowercase values: `stock, non_stock, service, fixed_asset`
