# Quick Seed Commands Reference

## 🚀 Quick Start (One Command)

```bash
# Seed everything (identity + core basic + stock)
./core-service/scripts/run_seed.sh all
```

## 📋 Step-by-Step Commands

### 1. Start Docker Containers

```bash
docker-compose up -d
```

### 2. Seed Identity Service (if not already done)

```bash
docker exec -it horizon_identity python scripts/seed_data.py
```

### 3. Seed Core Service - Basic Data

```bash
docker exec -it horizon_core python scripts/seed_data.py
```

### 4. Seed Core Service - Stock Data

```bash
docker exec -it horizon_core python scripts/seed_stock_data.py
```

## 🔍 Verify Data

```bash
# Connect to database
docker exec -it horizon_postgres psql -U horizon_user -d core_db

# Check items
SELECT item_code, item_name FROM items;

# Check stock levels
SELECT
    i.item_code,
    w.code as warehouse,
    sl.quantity_on_hand
FROM stock_levels sl
JOIN items i ON sl.product_id = i.id
JOIN warehouses w ON sl.warehouse_id = w.id;

# Exit
\q
```

## 🧹 Clean Up (Re-seed)

```bash
# Delete stock data only
docker exec -it horizon_postgres psql -U horizon_user -d core_db -c "
DELETE FROM stock_reconciliation_items;
DELETE FROM stock_reconciliations;
DELETE FROM stock_entry_items;
DELETE FROM stock_entries;
DELETE FROM stock_movements;
DELETE FROM stock_levels;
"

# Re-run stock seed
docker exec -it horizon_core python scripts/seed_stock_data.py
```

## 📊 What Gets Created

### Basic Seed Data

- ✅ 3 Item Groups
- ✅ 5 Items (Raw Materials, Finished Goods, Consumables)
- ✅ 2 Warehouses (Main Warehouse, Retail Store)

### Stock Seed Data

- ✅ 4 Stock Entries (receipts, transfers, issues)
- ✅ 11 Stock Movements (audit trail)
- ✅ 7 Stock Levels (current inventory)
- ✅ 2 Stock Reconciliations (physical count, damage write-off)

## 🆘 Troubleshooting

| Error                  | Solution                            |
| ---------------------- | ----------------------------------- |
| Container not running  | `docker-compose up -d`              |
| Organization not found | Seed identity service first         |
| No items/warehouses    | Run basic seed data first           |
| Already seeded         | Data exists, skip or clean up first |

## 📚 Full Documentation

- [SEEDING_GUIDE.md](./core-service/scripts/SEEDING_GUIDE.md) - Complete seeding guide
- [STOCK_SEED_DATA_README.md](./core-service/scripts/STOCK_SEED_DATA_README.md) - Stock data details
