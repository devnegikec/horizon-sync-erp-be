"""Import TTK Prestige items from CSV into items table."""
import csv
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))

from uuid import uuid4

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

DB_URL = os.getenv(
    "DATABASE_URL", "postgresql://horizon_user:horizon_pass@localhost:5432/core_db"
)
ORG_ID = "8614e0b8-3316-4f84-a6bb-92791ceacd23"
PRODUCTS_GROUP_ID = "66bac143-d81e-439c-91cd-c4777026f725"
CSV_PATH = os.path.join(os.path.dirname(__file__), "items_import_ttk_prestige.csv")

engine = create_engine(DB_URL)
Session = sessionmaker(bind=engine)
db = Session()

# 1. Create item groups if they don't exist
groups_needed = {"Cookware": "COOKWARE", "Appliances": "APPLIANCES"}
for gname, gcode in groups_needed.items():
    exists = db.execute(
        text(
            "SELECT id FROM item_groups WHERE organization_id = :org AND name = :name"
        ),
        {"org": ORG_ID, "name": gname},
    ).fetchone()
    if not exists:
        gid = str(uuid4())
        db.execute(
            text(
                """INSERT INTO item_groups (id, organization_id, name, code, parent_item_group_id, is_active, created_at, updated_at)
                    VALUES (:id, :org, :name, :code, :parent, true, NOW(), NOW())"""
            ),
            {
                "id": gid,
                "org": ORG_ID,
                "name": gname,
                "code": gcode,
                "parent": PRODUCTS_GROUP_ID,
            },
        )
        print(f"Created item group: {gname}")
db.commit()

# 2. Import items
with open(CSV_PATH) as f:
    reader = csv.DictReader(f)
    count = 0
    for row in reader:
        sku = row["sku"].strip()
        # Skip if already exists
        existing = db.execute(
            text("SELECT id FROM items WHERE organization_id = :org AND sku = :sku"),
            {"org": ORG_ID, "sku": sku},
        ).fetchone()
        if existing:
            print(f"SKIP (exists): {sku}")
            continue

        # Lookup group
        group = db.execute(
            text(
                "SELECT id FROM item_groups WHERE organization_id = :org AND name = :name"
            ),
            {"org": ORG_ID, "name": row["item_group_name"].strip()},
        ).fetchone()
        if not group:
            print(
                f"SKIP (no group): {sku} — group '{row['item_group_name']}' not found"
            )
            continue

        db.execute(
            text(
                """INSERT INTO items (id, organization_id, item_name, description, item_type, status, uom,
                     standard_rate, maintain_stock, sku, barcode, item_group_id, valuation_method,
                     min_order_qty, max_order_qty, is_active, created_at, updated_at)
                    VALUES (:id, :org, :name, :desc, :type, :status, :uom,
                            :rate, :stock, :sku, :barcode, :group, :val,
                            :min_qty, :max_qty, true, NOW(), NOW())"""
            ),
            {
                "id": str(uuid4()),
                "org": ORG_ID,
                "name": row["item_name"].strip(),
                "desc": row["description"].strip(),
                "type": row["item_type"].strip(),
                "status": row["status"].strip(),
                "uom": row["uom"].strip(),
                "rate": float(row["standard_rate"]),
                "stock": row["maintain_stock"].strip().upper() == "TRUE",
                "sku": sku,
                "barcode": row.get("barcode", "").strip() or None,
                "group": group[0],
                "val": row.get("valuation_method", "fifo").strip() or "fifo",
                "min_qty": int(row.get("min_order_qty", 1)),
                "max_qty": int(row.get("max_order_qty", 100)),
            },
        )
        count += 1
        print(f"ADDED: {sku} → {row['item_name']}")

db.commit()
print(f"\nDone! {count} items imported.")
db.close()
