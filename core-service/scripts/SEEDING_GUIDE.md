# Database Seeding Guide

This guide explains how to seed your PostgreSQL database with test data.

## Prerequisites

1. **Docker containers must be running**:

   ```bash
   docker-compose up -d
   ```

2. **Migrations must be applied**:

   - Identity service migrations (runs automatically on container start)
   - Core service migrations (runs automatically on container start)

3. **Identity service must be seeded first**:
   - The identity service creates the default organization and admin user
   - Core service seed scripts depend on this data

## Seed Scripts

### 1. Basic Seed Data (`seed_data.py`)

Creates foundational inventory data:

- Item Groups (Raw Materials, Finished Goods, Consumables)
- Items (Steel, Plastic, Widgets, Gadgets, Packaging)
- Warehouses (Main Warehouse, Retail Store)

### 2. Stock Management Seed Data (`seed_stock_data.py`)

Creates stock management data:

- Stock Entries (4 entries: receipts, transfers, issues)
- Stock Movements (11 movements: audit trail)
- Stock Levels (7 levels across warehouses)
- Stock Reconciliations (2 reconciliations: physical count, damage write-off)

**Note**: This script requires basic seed data to be run first!

## How to Run

### Method 1: Using the Helper Script (Easiest)

```bash
# Run all seed scripts (basic + stock)
./core-service/scripts/run_seed.sh all

# Run only basic seed data
./core-service/scripts/run_seed.sh basic

# Run only stock seed data
./core-service/scripts/run_seed.sh stock
```

### Method 2: Using Docker Exec Directly

```bash
# Run basic seed data
docker exec -it horizon_core python scripts/seed_data.py

# Run stock seed data
docker exec -it horizon_core python scripts/seed_stock_data.py
```

### Method 3: From Local Machine (Advanced)

If you want to run from your local machine:

```bash
cd core-service

# Install dependencies
pip install -r requirements.txt

# Update .env to use localhost instead of 'postgres'
# Change:
#   DATABASE_URL=postgresql://horizon_user:horizon_pass@postgres:5432/core_db
# To:
#   DATABASE_URL=postgresql://horizon_user:horizon_pass@localhost:5432/core_db
#
# And:
#   IDENTITY_DATABASE_URL=postgresql://horizon_user:horizon_pass@postgres:5432/identity_db
# To:
#   IDENTITY_DATABASE_URL=postgresql://horizon_user:horizon_pass@localhost:5432/identity_db

# Run the scripts
python scripts/seed_data.py
python scripts/seed_stock_data.py
```

## Seeding Order

**IMPORTANT**: Always follow this order:

1. **Identity Service Seeding** (if not already done)

   ```bash
   docker exec -it horizon_identity python scripts/seed_data.py
   ```

2. **Core Service Basic Seeding**

   ```bash
   docker exec -it horizon_core python scripts/seed_data.py
   ```

3. **Core Service Stock Seeding**
   ```bash
   docker exec -it horizon_core python scripts/seed_stock_data.py
   ```

## Verification

After seeding, verify the data:

### Check Basic Data

```bash
# Connect to database
docker exec -it horizon_postgres psql -U horizon_user -d core_db

# Check items
SELECT item_code, item_name, item_type FROM items;

# Check warehouses
SELECT code, name, warehouse_type FROM warehouses;

# Exit
\q
```

### Check Stock Data

```bash
# Connect to database
docker exec -it horizon_postgres psql -U horizon_user -d core_db

# Check stock entries
SELECT stock_entry_no, stock_entry_type, status FROM stock_entries;

# Check stock levels
SELECT
    i.item_code,
    w.code as warehouse,
    sl.quantity_on_hand,
    sl.quantity_available
FROM stock_levels sl
JOIN items i ON sl.product_id = i.id
JOIN warehouses w ON sl.warehouse_id = w.id;

# Check stock movements
SELECT COUNT(*) as total_movements FROM stock_movements;

# Exit
\q
```

## Troubleshooting

### Error: "Container not running"

```bash
# Start containers
docker-compose up -d

# Check status
docker-compose ps
```

### Error: "Default organization not found"

```bash
# Seed identity service first
docker exec -it horizon_identity python scripts/seed_data.py
```

### Error: "No items or warehouses found"

```bash
# Run basic seed data first
docker exec -it horizon_core python scripts/seed_data.py
```

### Error: "Stock data already seeded"

The script detects existing data and skips seeding. To re-seed:

```bash
# Connect to database
docker exec -it horizon_postgres psql -U horizon_user -d core_db

# Delete stock data (in order)
DELETE FROM stock_reconciliation_items;
DELETE FROM stock_reconciliations;
DELETE FROM stock_entry_items;
DELETE FROM stock_entries;
DELETE FROM stock_movements;
DELETE FROM stock_levels;

# Exit and re-run seed script
\q
docker exec -it horizon_core python scripts/seed_stock_data.py
```

## Database Connection Details

- **Host**: localhost (from host machine) or postgres (from containers)
- **Port**: 5432
- **User**: horizon_user
- **Password**: horizon_pass
- **Databases**:
  - `identity_db` - Identity service database
  - `core_db` - Core service database

## Quick Reference

```bash
# Start services
docker-compose up -d

# Seed all data
./core-service/scripts/run_seed.sh all

# View logs
docker-compose logs -f core-service

# Connect to database
docker exec -it horizon_postgres psql -U horizon_user -d core_db

# Stop services
docker-compose down

# Stop and remove volumes (WARNING: deletes all data)
docker-compose down -v
```

## Next Steps

After seeding:

1. **Test APIs**: Use the seeded data to test your APIs
2. **View Data**: Check the data in your database or through API endpoints
3. **Run Queries**: Use the queries in `stock_queries.sql` for analysis
4. **Create More Data**: Use the APIs to create additional records

## Additional Resources

- [STOCK_SEED_DATA_README.md](./STOCK_SEED_DATA_README.md) - Detailed documentation of stock seed data
- [stock_queries.sql](./stock_queries.sql) - Useful SQL queries for analysis
- [SEED_DATA_GUIDE.md](./SEED_DATA_GUIDE.md) - Guide for basic seed data
