"""
WMS Demo Data Seed Script
=========================
Seeds a complete, realistic warehouse management dataset so the UI has
data to display across every WMS screen:

  - 1 Warehouse  (Main Distribution Centre)
  - Full location hierarchy: 2 Zones → 2 Aisles each → 2 Bays each →
    2 Levels each → 2 Bins each  (= 32 bins total)
  - 3 Item Groups  (Fast Movers, Slow Movers, Fragile)
  - 6 Items with packaging units and SKUs
  - Location allocations (exclusive + preferred)
  - Bin stock levels (stock spread across bins)
  - 2 completed inbound scan sessions → receiving slips → put-away lists
  - 1 pending receiving slip (pending_review)
  - 2 pick lists (one completed, one in-progress)
  - 1 gate verification session (verified) → dispatch record
  - Worker tasks for put-away and pick operations
  - Location scans (time tracking)

Usage:
    python seed_wms_demo_data.py

Requires the core-service .env to be present (DATABASE_URL).
"""

import json
import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# ---------------------------------------------------------------------------
# DB connection — mirrors the pattern used in other seed scripts
# ---------------------------------------------------------------------------
# Reads DATABASE_URL from the environment (set by Docker Compose).
# Falls back to the local dev URL when running outside the container.
import os
DATABASE_URL = os.environ.get(
    "DATABASE_URL",
    "postgresql://horizon_user:horizon_pass@localhost:5432/core_db",
)

# ---------------------------------------------------------------------------
# Fixed IDs — deterministic so re-running is idempotent
# ---------------------------------------------------------------------------
ORG_ID = uuid.UUID("b1f71de1-0a19-424e-9580-1d3f871c5b1f")

# Workers (users that already exist in the identity service)
WORKER_1_ID = uuid.UUID("11111111-0000-0000-0000-000000000001")
WORKER_2_ID = uuid.UUID("11111111-0000-0000-0000-000000000002")
MANAGER_ID  = uuid.UUID("11111111-0000-0000-0000-000000000003")

# Warehouse
WH_ID = uuid.UUID("aa000000-0000-0000-0000-000000000001")

# Item Groups
IG_FAST_ID     = uuid.UUID("bb000000-0000-0000-0000-000000000001")
IG_SLOW_ID     = uuid.UUID("bb000000-0000-0000-0000-000000000002")
IG_FRAGILE_ID  = uuid.UUID("bb000000-0000-0000-0000-000000000003")

# Items
ITEM_WIDGET_A_ID  = uuid.UUID("cc000000-0000-0000-0000-000000000001")
ITEM_WIDGET_B_ID  = uuid.UUID("cc000000-0000-0000-0000-000000000002")
ITEM_GADGET_X_ID  = uuid.UUID("cc000000-0000-0000-0000-000000000003")
ITEM_GADGET_Y_ID  = uuid.UUID("cc000000-0000-0000-0000-000000000004")
ITEM_GLASS_P_ID   = uuid.UUID("cc000000-0000-0000-0000-000000000005")
ITEM_CABLE_Z_ID   = uuid.UUID("cc000000-0000-0000-0000-000000000006")

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def now() -> datetime:
    return datetime.now(UTC)

def days_ago(n: int) -> datetime:
    return datetime.now(UTC) - timedelta(days=n)

def hours_ago(n: int) -> datetime:
    return datetime.now(UTC) - timedelta(hours=n)

def uid() -> uuid.UUID:
    return uuid.uuid4()

def qr_payload(item_code: str, qty: int, batch: str, qr_id: str | None = None) -> str:
    return json.dumps({
        "id": qr_id or str(uid()),
        "sku": item_code,
        "qty": qty,
        "batch": batch,
    })


# ---------------------------------------------------------------------------
# SECTION 1 — Warehouse
# ---------------------------------------------------------------------------

def seed_warehouse(db) -> None:
    existing = db.execute(
        text("SELECT id FROM warehouses_extended WHERE id = :id"),
        {"id": str(WH_ID)},
    ).fetchone()
    if existing:
        print("  [skip] Warehouse already exists")
        return

    db.execute(text("""
        INSERT INTO warehouses_extended
            (id, organization_id, name, code, description,
             address_line1, city, country, is_active, is_default,
             created_at, updated_at)
        VALUES
            (:id, :org, 'Main Distribution Centre', 'MDC-01',
             'Primary warehouse for all inbound and outbound operations',
             '1 Logistics Park', 'Mumbai', 'India',
             TRUE, TRUE, :now, :now)
    """), {"id": str(WH_ID), "org": str(ORG_ID), "now": now()})
    print("  [ok] Warehouse created: Main Distribution Centre (MDC-01)")


# ---------------------------------------------------------------------------
# SECTION 2 — Item Groups
# ---------------------------------------------------------------------------

ITEM_GROUPS = [
    (IG_FAST_ID,    "Fast Movers",  "FAST",    "High-velocity items near dock"),
    (IG_SLOW_ID,    "Slow Movers",  "SLOW",    "Low-velocity bulk items"),
    (IG_FRAGILE_ID, "Fragile",      "FRAGILE", "Handle with care items"),
]

def seed_item_groups(db) -> None:
    for ig_id, name, code, desc in ITEM_GROUPS:
        existing = db.execute(
            text("SELECT id FROM item_groups WHERE id = :id"),
            {"id": str(ig_id)},
        ).fetchone()
        if existing:
            print(f"  [skip] Item group {code} already exists")
            continue
        db.execute(text("""
            INSERT INTO item_groups
                (id, organization_id, name, code, description, is_active,
                 created_at, updated_at)
            VALUES
                (:id, :org, :name, :code, :desc, TRUE, :now, :now)
        """), {"id": str(ig_id), "org": str(ORG_ID), "name": name,
               "code": code, "desc": desc, "now": now()})
        print(f"  [ok] Item group: {name}")


# ---------------------------------------------------------------------------
# SECTION 3 — Items
# ---------------------------------------------------------------------------

ITEMS = [
    # (id, item_code, item_name, sku, uom, standard_rate, item_group_id)
    (ITEM_WIDGET_A_ID, "WGT-A-001", "Widget Alpha",   "SKU-WGT-A", "Nos",  250.00, IG_FAST_ID),
    (ITEM_WIDGET_B_ID, "WGT-B-002", "Widget Beta",    "SKU-WGT-B", "Nos",  180.00, IG_FAST_ID),
    (ITEM_GADGET_X_ID, "GDG-X-001", "Gadget X Pro",   "SKU-GDG-X", "Nos",  750.00, IG_SLOW_ID),
    (ITEM_GADGET_Y_ID, "GDG-Y-002", "Gadget Y Lite",  "SKU-GDG-Y", "Nos",  420.00, IG_SLOW_ID),
    (ITEM_GLASS_P_ID,  "GLS-P-001", "Glass Panel",    "SKU-GLS-P", "Nos", 1200.00, IG_FRAGILE_ID),
    (ITEM_CABLE_Z_ID,  "CBL-Z-001", "Cable Bundle Z", "SKU-CBL-Z", "Box",   95.00, IG_FAST_ID),
]

def seed_items(db) -> None:
    for item_id, code, name, sku, uom, rate, ig_id in ITEMS:
        existing = db.execute(
            text("SELECT id FROM items WHERE id = :id"),
            {"id": str(item_id)},
        ).fetchone()
        if existing:
            print(f"  [skip] Item {code} already exists")
            continue
        db.execute(text("""
            INSERT INTO items
                (id, organization_id, item_code, item_name, sku, uom,
                 item_group_id, maintain_stock, standard_rate, valuation_rate,
                 status, created_at, updated_at)
            VALUES
                (:id, :org, :code, :name, :sku, :uom,
                 :ig, TRUE, :rate, :rate,
                 'active', :now, :now)
        """), {"id": str(item_id), "org": str(ORG_ID), "code": code,
               "name": name, "sku": sku, "uom": uom, "ig": str(ig_id),
               "rate": rate, "now": now()})
        print(f"  [ok] Item: {name} ({code})")


# ---------------------------------------------------------------------------
# SECTION 4 — Packaging Units
# ---------------------------------------------------------------------------

def seed_packaging_units(db) -> None:
    units = [
        # Widget Alpha — Each + Box of 12
        (uid(), ITEM_WIDGET_A_ID, "Each",      "QR-WGT-A-EACH", 1,  None, None, None, None, True),
        (uid(), ITEM_WIDGET_A_ID, "Box of 12", "QR-WGT-A-BOX",  12, 300,  200,  150,  2400, False),
        # Widget Beta — Each + Box of 24
        (uid(), ITEM_WIDGET_B_ID, "Each",      "QR-WGT-B-EACH", 1,  None, None, None, None, True),
        (uid(), ITEM_WIDGET_B_ID, "Box of 24", "QR-WGT-B-BOX",  24, 400,  300,  200,  4800, False),
        # Gadget X — Each only
        (uid(), ITEM_GADGET_X_ID, "Each",      "QR-GDG-X-EACH", 1,  None, None, None, None, True),
        # Gadget Y — Each + Pallet of 48
        (uid(), ITEM_GADGET_Y_ID, "Each",      "QR-GDG-Y-EACH", 1,  None, None, None, None, True),
        (uid(), ITEM_GADGET_Y_ID, "Pallet of 48", "QR-GDG-Y-PLT", 48, 1200, 800, 150, 96000, False),
        # Glass Panel — Each only (fragile)
        (uid(), ITEM_GLASS_P_ID,  "Each",      "QR-GLS-P-EACH", 1,  None, None, None, None, True),
        # Cable Bundle — Box of 10
        (uid(), ITEM_CABLE_Z_ID,  "Box",       "QR-CBL-Z-BOX",  10, 500,  300,  200,  5000, True),
    ]
    for pu_id, item_id, unit_name, qr_id, factor, l, w, h, wg, is_base in units:
        existing = db.execute(
            text("SELECT id FROM item_packaging_units WHERE qr_identifier = :qr"),
            {"qr": qr_id},
        ).fetchone()
        if existing:
            print(f"  [skip] Packaging unit {unit_name} for item already exists")
            continue
        db.execute(text("""
            INSERT INTO item_packaging_units
                (id, organization_id, item_id, unit_name, qr_identifier,
                 conversion_factor, length_mm, width_mm, height_mm, weight_grams,
                 is_base_unit, is_active, created_at, updated_at)
            VALUES
                (:id, :org, :item, :name, :qr,
                 :factor, :l, :w, :h, :wg,
                 :base, TRUE, :now, :now)
        """), {"id": str(pu_id), "org": str(ORG_ID), "item": str(item_id),
               "name": unit_name, "qr": qr_id, "factor": factor,
               "l": l, "w": w, "h": h, "wg": wg, "base": is_base, "now": now()})
        print(f"  [ok] Packaging unit: {unit_name} (x{factor})")


# ---------------------------------------------------------------------------
# SECTION 5 — Warehouse Location Hierarchy
# ---------------------------------------------------------------------------
# Structure:
#   Zone A (Fast Movers)
#     Aisle A01
#       Bay A01-B01
#         Level A01-B01-L01  →  Bins A01-B01-L01-001, A01-B01-L01-002
#         Level A01-B01-L02  →  Bins A01-B01-L02-001, A01-B01-L02-002
#       Bay A01-B02
#         Level A01-B02-L01  →  Bins A01-B02-L01-001, A01-B02-L01-002
#         Level A01-B02-L02  →  Bins A01-B02-L02-001, A01-B02-L02-002
#     Aisle A02  (same structure)
#   Zone B (Slow / Fragile)
#     Aisle B01  (same structure)
#     Aisle B02  (same structure)
# Total: 2 zones × 2 aisles × 2 bays × 2 levels × 2 bins = 32 bins

# We'll store location IDs in a dict keyed by full_path for easy reference later
LOCATION_IDS: dict[str, uuid.UUID] = {}

def _loc(path: str) -> uuid.UUID:
    """Return the UUID for a location by its full_path."""
    return LOCATION_IDS[path]

def _insert_location(db, loc_id, parent_id, loc_type, code, full_path,
                     name, capacity, pos_x, pos_y,
                     max_vol=None, max_wt=None) -> None:
    existing = db.execute(
        text("SELECT id FROM warehouse_locations WHERE id = :id"),
        {"id": str(loc_id)},
    ).fetchone()
    if existing:
        return
    db.execute(text("""
        INSERT INTO warehouse_locations
            (id, organization_id, warehouse_id, parent_location_id,
             location_type, code, full_path, name,
             capacity, total_capacity, available_capacity, capacity_uom,
             position_x, position_y, max_volume_cc, max_weight_grams,
             is_active, version, created_at, updated_at)
        VALUES
            (:id, :org, :wh, :parent,
             :ltype, :code, :path, :name,
             :cap, :cap, :cap, 'Nos',
             :px, :py, :mvol, :mwt,
             TRUE, 1, :now, :now)
    """), {
        "id": str(loc_id), "org": str(ORG_ID), "wh": str(WH_ID),
        "parent": str(parent_id) if parent_id else None,
        "ltype": loc_type, "code": code, "path": full_path, "name": name,
        "cap": capacity, "px": pos_x, "py": pos_y,
        "mvol": max_vol, "mwt": max_wt, "now": now(),
    })
    LOCATION_IDS[full_path] = loc_id


def seed_locations(db) -> None:
    # ---- Zone A ----
    ZA = uuid.UUID("dd000000-0000-0000-0000-000000000001")
    _insert_location(db, ZA, None, "zone", "ZA", "ZA",
                     "Zone A — Fast Movers", 0, 0, 0)

    # Aisle A01
    AA01 = uuid.UUID("dd000000-0000-0000-0000-000000000002")
    _insert_location(db, AA01, ZA, "aisle", "A01", "ZA-A01",
                     "Aisle A01", 0, 0, 10)

    # Bay A01-B01
    AB01B01 = uuid.UUID("dd000000-0000-0000-0000-000000000003")
    _insert_location(db, AB01B01, AA01, "bay", "B01", "ZA-A01-B01",
                     "Bay B01", 0, 0, 10)

    # Level A01-B01-L01
    AL01 = uuid.UUID("dd000000-0000-0000-0000-000000000004")
    _insert_location(db, AL01, AB01B01, "level", "L01", "ZA-A01-B01-L01",
                     "Level L01", 0, 0, 10)
    # Bins
    B001 = uuid.UUID("dd000000-0000-0000-0000-000000000005")
    _insert_location(db, B001, AL01, "bin", "001", "ZA-A01-B01-L01-001",
                     "Bin 001", 200, 0, 10, max_vol=50000, max_wt=20000)
    B002 = uuid.UUID("dd000000-0000-0000-0000-000000000006")
    _insert_location(db, B002, AL01, "bin", "002", "ZA-A01-B01-L01-002",
                     "Bin 002", 200, 1, 10, max_vol=50000, max_wt=20000)

    # Level A01-B01-L02
    AL02 = uuid.UUID("dd000000-0000-0000-0000-000000000007")
    _insert_location(db, AL02, AB01B01, "level", "L02", "ZA-A01-B01-L02",
                     "Level L02", 0, 0, 11)
    B003 = uuid.UUID("dd000000-0000-0000-0000-000000000008")
    _insert_location(db, B003, AL02, "bin", "001", "ZA-A01-B01-L02-001",
                     "Bin 001", 200, 0, 11, max_vol=50000, max_wt=20000)
    B004 = uuid.UUID("dd000000-0000-0000-0000-000000000009")
    _insert_location(db, B004, AL02, "bin", "002", "ZA-A01-B01-L02-002",
                     "Bin 002", 200, 1, 11, max_vol=50000, max_wt=20000)

    # Bay A01-B02
    AB01B02 = uuid.UUID("dd000000-0000-0000-0000-000000000010")
    _insert_location(db, AB01B02, AA01, "bay", "B02", "ZA-A01-B02",
                     "Bay B02", 0, 2, 10)

    AL03 = uuid.UUID("dd000000-0000-0000-0000-000000000011")
    _insert_location(db, AL03, AB01B02, "level", "L01", "ZA-A01-B02-L01",
                     "Level L01", 0, 2, 10)
    B005 = uuid.UUID("dd000000-0000-0000-0000-000000000012")
    _insert_location(db, B005, AL03, "bin", "001", "ZA-A01-B02-L01-001",
                     "Bin 001", 200, 2, 10, max_vol=50000, max_wt=20000)
    B006 = uuid.UUID("dd000000-0000-0000-0000-000000000013")
    _insert_location(db, B006, AL03, "bin", "002", "ZA-A01-B02-L01-002",
                     "Bin 002", 200, 3, 10, max_vol=50000, max_wt=20000)

    AL04 = uuid.UUID("dd000000-0000-0000-0000-000000000014")
    _insert_location(db, AL04, AB01B02, "level", "L02", "ZA-A01-B02-L02",
                     "Level L02", 0, 2, 11)
    B007 = uuid.UUID("dd000000-0000-0000-0000-000000000015")
    _insert_location(db, B007, AL04, "bin", "001", "ZA-A01-B02-L02-001",
                     "Bin 001", 200, 2, 11, max_vol=50000, max_wt=20000)
    B008 = uuid.UUID("dd000000-0000-0000-0000-000000000016")
    _insert_location(db, B008, AL04, "bin", "002", "ZA-A01-B02-L02-002",
                     "Bin 002", 200, 3, 11, max_vol=50000, max_wt=20000)

    # Aisle A02
    AA02 = uuid.UUID("dd000000-0000-0000-0000-000000000017")
    _insert_location(db, AA02, ZA, "aisle", "A02", "ZA-A02",
                     "Aisle A02", 0, 5, 10)

    AB02B01 = uuid.UUID("dd000000-0000-0000-0000-000000000018")
    _insert_location(db, AB02B01, AA02, "bay", "B01", "ZA-A02-B01",
                     "Bay B01", 0, 5, 10)
    AL05 = uuid.UUID("dd000000-0000-0000-0000-000000000019")
    _insert_location(db, AL05, AB02B01, "level", "L01", "ZA-A02-B01-L01",
                     "Level L01", 0, 5, 10)
    B009 = uuid.UUID("dd000000-0000-0000-0000-000000000020")
    _insert_location(db, B009, AL05, "bin", "001", "ZA-A02-B01-L01-001",
                     "Bin 001", 200, 5, 10, max_vol=50000, max_wt=20000)
    B010 = uuid.UUID("dd000000-0000-0000-0000-000000000021")
    _insert_location(db, B010, AL05, "bin", "002", "ZA-A02-B01-L01-002",
                     "Bin 002", 200, 6, 10, max_vol=50000, max_wt=20000)

    AL06 = uuid.UUID("dd000000-0000-0000-0000-000000000022")
    _insert_location(db, AL06, AB02B01, "level", "L02", "ZA-A02-B01-L02",
                     "Level L02", 0, 5, 11)
    B011 = uuid.UUID("dd000000-0000-0000-0000-000000000023")
    _insert_location(db, B011, AL06, "bin", "001", "ZA-A02-B01-L02-001",
                     "Bin 001", 200, 5, 11, max_vol=50000, max_wt=20000)
    B012 = uuid.UUID("dd000000-0000-0000-0000-000000000024")
    _insert_location(db, B012, AL06, "bin", "002", "ZA-A02-B01-L02-002",
                     "Bin 002", 200, 6, 11, max_vol=50000, max_wt=20000)

    AB02B02 = uuid.UUID("dd000000-0000-0000-0000-000000000025")
    _insert_location(db, AB02B02, AA02, "bay", "B02", "ZA-A02-B02",
                     "Bay B02", 0, 7, 10)
    AL07 = uuid.UUID("dd000000-0000-0000-0000-000000000026")
    _insert_location(db, AL07, AB02B02, "level", "L01", "ZA-A02-B02-L01",
                     "Level L01", 0, 7, 10)
    B013 = uuid.UUID("dd000000-0000-0000-0000-000000000027")
    _insert_location(db, B013, AL07, "bin", "001", "ZA-A02-B02-L01-001",
                     "Bin 001", 200, 7, 10, max_vol=50000, max_wt=20000)
    B014 = uuid.UUID("dd000000-0000-0000-0000-000000000028")
    _insert_location(db, B014, AL07, "bin", "002", "ZA-A02-B02-L01-002",
                     "Bin 002", 200, 8, 10, max_vol=50000, max_wt=20000)

    AL08 = uuid.UUID("dd000000-0000-0000-0000-000000000029")
    _insert_location(db, AL08, AB02B02, "level", "L02", "ZA-A02-B02-L02",
                     "Level L02", 0, 7, 11)
    B015 = uuid.UUID("dd000000-0000-0000-0000-000000000030")
    _insert_location(db, B015, AL08, "bin", "001", "ZA-A02-B02-L02-001",
                     "Bin 001", 200, 7, 11, max_vol=50000, max_wt=20000)
    B016 = uuid.UUID("dd000000-0000-0000-0000-000000000031")
    _insert_location(db, B016, AL08, "bin", "002", "ZA-A02-B02-L02-002",
                     "Bin 002", 200, 8, 11, max_vol=50000, max_wt=20000)

    # ---- Zone B ----
    ZB = uuid.UUID("dd000000-0000-0000-0000-000000000032")
    _insert_location(db, ZB, None, "zone", "ZB", "ZB",
                     "Zone B — Slow Movers & Fragile", 0, 20, 0)

    BA01 = uuid.UUID("dd000000-0000-0000-0000-000000000033")
    _insert_location(db, BA01, ZB, "aisle", "B01", "ZB-B01",
                     "Aisle B01", 0, 20, 10)

    BB01B01 = uuid.UUID("dd000000-0000-0000-0000-000000000034")
    _insert_location(db, BB01B01, BA01, "bay", "B01", "ZB-B01-B01",
                     "Bay B01", 0, 20, 10)
    BL01 = uuid.UUID("dd000000-0000-0000-0000-000000000035")
    _insert_location(db, BL01, BB01B01, "level", "L01", "ZB-B01-B01-L01",
                     "Level L01", 0, 20, 10)
    B017 = uuid.UUID("dd000000-0000-0000-0000-000000000036")
    _insert_location(db, B017, BL01, "bin", "001", "ZB-B01-B01-L01-001",
                     "Bin 001", 100, 20, 10, max_vol=200000, max_wt=50000)
    B018 = uuid.UUID("dd000000-0000-0000-0000-000000000037")
    _insert_location(db, B018, BL01, "bin", "002", "ZB-B01-B01-L01-002",
                     "Bin 002", 100, 21, 10, max_vol=200000, max_wt=50000)

    BL02 = uuid.UUID("dd000000-0000-0000-0000-000000000038")
    _insert_location(db, BL02, BB01B01, "level", "L02", "ZB-B01-B01-L02",
                     "Level L02", 0, 20, 11)
    B019 = uuid.UUID("dd000000-0000-0000-0000-000000000039")
    _insert_location(db, B019, BL02, "bin", "001", "ZB-B01-B01-L02-001",
                     "Bin 001", 100, 20, 11, max_vol=200000, max_wt=50000)
    B020 = uuid.UUID("dd000000-0000-0000-0000-000000000040")
    _insert_location(db, B020, BL02, "bin", "002", "ZB-B01-B01-L02-002",
                     "Bin 002", 100, 21, 11, max_vol=200000, max_wt=50000)

    BB01B02 = uuid.UUID("dd000000-0000-0000-0000-000000000041")
    _insert_location(db, BB01B02, BA01, "bay", "B02", "ZB-B01-B02",
                     "Bay B02", 0, 23, 10)
    BL03 = uuid.UUID("dd000000-0000-0000-0000-000000000042")
    _insert_location(db, BL03, BB01B02, "level", "L01", "ZB-B01-B02-L01",
                     "Level L01", 0, 23, 10)
    B021 = uuid.UUID("dd000000-0000-0000-0000-000000000043")
    _insert_location(db, B021, BL03, "bin", "001", "ZB-B01-B02-L01-001",
                     "Bin 001", 100, 23, 10, max_vol=200000, max_wt=50000)
    B022 = uuid.UUID("dd000000-0000-0000-0000-000000000044")
    _insert_location(db, B022, BL03, "bin", "002", "ZB-B01-B02-L01-002",
                     "Bin 002", 100, 24, 10, max_vol=200000, max_wt=50000)

    BL04 = uuid.UUID("dd000000-0000-0000-0000-000000000045")
    _insert_location(db, BL04, BB01B02, "level", "L02", "ZB-B01-B02-L02",
                     "Level L02", 0, 23, 11)
    B023 = uuid.UUID("dd000000-0000-0000-0000-000000000046")
    _insert_location(db, B023, BL04, "bin", "001", "ZB-B01-B02-L02-001",
                     "Bin 001", 100, 23, 11, max_vol=200000, max_wt=50000)
    B024 = uuid.UUID("dd000000-0000-0000-0000-000000000047")
    _insert_location(db, B024, BL04, "bin", "002", "ZB-B01-B02-L02-002",
                     "Bin 002", 100, 24, 11, max_vol=200000, max_wt=50000)

    # Aisle B02
    BA02 = uuid.UUID("dd000000-0000-0000-0000-000000000048")
    _insert_location(db, BA02, ZB, "aisle", "B02", "ZB-B02",
                     "Aisle B02", 0, 28, 10)

    BB02B01 = uuid.UUID("dd000000-0000-0000-0000-000000000049")
    _insert_location(db, BB02B01, BA02, "bay", "B01", "ZB-B02-B01",
                     "Bay B01", 0, 28, 10)
    BL05 = uuid.UUID("dd000000-0000-0000-0000-000000000050")
    _insert_location(db, BL05, BB02B01, "level", "L01", "ZB-B02-B01-L01",
                     "Level L01", 0, 28, 10)
    B025 = uuid.UUID("dd000000-0000-0000-0000-000000000051")
    _insert_location(db, B025, BL05, "bin", "001", "ZB-B02-B01-L01-001",
                     "Bin 001", 50, 28, 10, max_vol=100000, max_wt=30000)
    B026 = uuid.UUID("dd000000-0000-0000-0000-000000000052")
    _insert_location(db, B026, BL05, "bin", "002", "ZB-B02-B01-L01-002",
                     "Bin 002", 50, 29, 10, max_vol=100000, max_wt=30000)

    BL06 = uuid.UUID("dd000000-0000-0000-0000-000000000053")
    _insert_location(db, BL06, BB02B01, "level", "L02", "ZB-B02-B01-L02",
                     "Level L02", 0, 28, 11)
    B027 = uuid.UUID("dd000000-0000-0000-0000-000000000054")
    _insert_location(db, B027, BL06, "bin", "001", "ZB-B02-B01-L02-001",
                     "Bin 001", 50, 28, 11, max_vol=100000, max_wt=30000)
    B028 = uuid.UUID("dd000000-0000-0000-0000-000000000055")
    _insert_location(db, B028, BL06, "bin", "002", "ZB-B02-B01-L02-002",
                     "Bin 002", 50, 29, 11, max_vol=100000, max_wt=30000)

    BB02B02 = uuid.UUID("dd000000-0000-0000-0000-000000000056")
    _insert_location(db, BB02B02, BA02, "bay", "B02", "ZB-B02-B02",
                     "Bay B02", 0, 31, 10)
    BL07 = uuid.UUID("dd000000-0000-0000-0000-000000000057")
    _insert_location(db, BL07, BB02B02, "level", "L01", "ZB-B02-B02-L01",
                     "Level L01", 0, 31, 10)
    B029 = uuid.UUID("dd000000-0000-0000-0000-000000000058")
    _insert_location(db, B029, BL07, "bin", "001", "ZB-B02-B02-L01-001",
                     "Bin 001", 50, 31, 10, max_vol=100000, max_wt=30000)
    B030 = uuid.UUID("dd000000-0000-0000-0000-000000000059")
    _insert_location(db, B030, BL07, "bin", "002", "ZB-B02-B02-L01-002",
                     "Bin 002", 50, 32, 10, max_vol=100000, max_wt=30000)

    BL08 = uuid.UUID("dd000000-0000-0000-0000-000000000060")
    _insert_location(db, BL08, BB02B02, "level", "L02", "ZB-B02-B02-L02",
                     "Level L02", 0, 31, 11)
    B031 = uuid.UUID("dd000000-0000-0000-0000-000000000061")
    _insert_location(db, B031, BL08, "bin", "001", "ZB-B02-B02-L02-001",
                     "Bin 001", 50, 31, 11, max_vol=100000, max_wt=30000)
    B032 = uuid.UUID("dd000000-0000-0000-0000-000000000062")
    _insert_location(db, B032, BL08, "bin", "002", "ZB-B02-B02-L02-002",
                     "Bin 002", 50, 32, 11, max_vol=100000, max_wt=30000)

    print(f"  [ok] Location hierarchy seeded ({len(LOCATION_IDS)} nodes)")


# ---------------------------------------------------------------------------
# SECTION 6 — Location Allocations
# ---------------------------------------------------------------------------

def seed_allocations(db) -> None:
    allocs = [
        # Zone A bins → Fast Movers (preferred)
        (uid(), "ZA-A01-B01-L01-001", IG_FAST_ID,    "preferred", 10),
        (uid(), "ZA-A01-B01-L01-002", IG_FAST_ID,    "preferred", 10),
        (uid(), "ZA-A01-B01-L02-001", IG_FAST_ID,    "preferred", 9),
        (uid(), "ZA-A01-B01-L02-002", IG_FAST_ID,    "preferred", 9),
        # Zone A aisle 2 → Fast Movers exclusive
        (uid(), "ZA-A02-B01-L01-001", IG_FAST_ID,    "exclusive", 10),
        (uid(), "ZA-A02-B01-L01-002", IG_FAST_ID,    "exclusive", 10),
        # Zone B → Slow Movers preferred
        (uid(), "ZB-B01-B01-L01-001", IG_SLOW_ID,    "preferred", 10),
        (uid(), "ZB-B01-B01-L01-002", IG_SLOW_ID,    "preferred", 10),
        # Zone B aisle 2 → Fragile exclusive
        (uid(), "ZB-B02-B01-L01-001", IG_FRAGILE_ID, "exclusive", 10),
        (uid(), "ZB-B02-B01-L01-002", IG_FRAGILE_ID, "exclusive", 10),
    ]
    for alloc_id, path, ig_id, atype, priority in allocs:
        if path not in LOCATION_IDS:
            print(f"  [warn] Location {path} not found, skipping allocation")
            continue
        loc_id = LOCATION_IDS[path]
        existing = db.execute(
            text("""SELECT id FROM location_allocations
                    WHERE location_id = :loc AND item_group_id = :ig"""),
            {"loc": str(loc_id), "ig": str(ig_id)},
        ).fetchone()
        if existing:
            continue
        db.execute(text("""
            INSERT INTO location_allocations
                (id, organization_id, location_id, item_group_id,
                 priority, allocation_type, is_active, created_at, updated_at)
            VALUES
                (:id, :org, :loc, :ig, :pri, :atype, TRUE, :now, :now)
        """), {"id": str(alloc_id), "org": str(ORG_ID), "loc": str(loc_id),
               "ig": str(ig_id), "pri": priority, "atype": atype, "now": now()})
    print("  [ok] Location allocations seeded")


# ---------------------------------------------------------------------------
# SECTION 7 — Bin Stock Levels
# ---------------------------------------------------------------------------

def seed_bin_stock(db) -> None:
    # (bin_path, item_id, qty, batch)
    stock_entries = [
        # Zone A — Fast Movers
        ("ZA-A01-B01-L01-001", ITEM_WIDGET_A_ID, 120, "BATCH-WGT-A-2025-01"),
        ("ZA-A01-B01-L01-002", ITEM_WIDGET_A_ID,  80, "BATCH-WGT-A-2025-02"),
        ("ZA-A01-B01-L02-001", ITEM_WIDGET_B_ID, 150, "BATCH-WGT-B-2025-01"),
        ("ZA-A01-B01-L02-002", ITEM_WIDGET_B_ID,  60, "BATCH-WGT-B-2025-02"),
        ("ZA-A01-B02-L01-001", ITEM_CABLE_Z_ID,   90, "BATCH-CBL-Z-2025-01"),
        ("ZA-A01-B02-L01-002", ITEM_CABLE_Z_ID,   45, "BATCH-CBL-Z-2025-02"),
        ("ZA-A02-B01-L01-001", ITEM_WIDGET_A_ID,  50, "BATCH-WGT-A-2025-03"),
        ("ZA-A02-B01-L01-002", ITEM_WIDGET_B_ID,  70, "BATCH-WGT-B-2025-03"),
        ("ZA-A02-B01-L02-001", ITEM_CABLE_Z_ID,   30, "BATCH-CBL-Z-2025-03"),
        # Zone B — Slow Movers
        ("ZB-B01-B01-L01-001", ITEM_GADGET_X_ID,  40, "BATCH-GDG-X-2025-01"),
        ("ZB-B01-B01-L01-002", ITEM_GADGET_X_ID,  25, "BATCH-GDG-X-2025-02"),
        ("ZB-B01-B01-L02-001", ITEM_GADGET_Y_ID,  60, "BATCH-GDG-Y-2025-01"),
        ("ZB-B01-B01-L02-002", ITEM_GADGET_Y_ID,  35, "BATCH-GDG-Y-2025-02"),
        ("ZB-B01-B02-L01-001", ITEM_GADGET_X_ID,  15, "BATCH-GDG-X-2025-03"),
        # Zone B — Fragile
        ("ZB-B02-B01-L01-001", ITEM_GLASS_P_ID,   20, "BATCH-GLS-P-2025-01"),
        ("ZB-B02-B01-L01-002", ITEM_GLASS_P_ID,   10, "BATCH-GLS-P-2025-02"),
        ("ZB-B02-B01-L02-001", ITEM_GLASS_P_ID,    8, "BATCH-GLS-P-2025-03"),
    ]
    for path, item_id, qty, batch in stock_entries:
        if path not in LOCATION_IDS:
            print(f"  [warn] Bin {path} not found, skipping stock")
            continue
        bin_id = LOCATION_IDS[path]
        existing = db.execute(
            text("""SELECT id FROM bin_stock_levels
                    WHERE bin_location_id = :bin AND item_id = :item
                    AND batch_number = :batch"""),
            {"bin": str(bin_id), "item": str(item_id), "batch": batch},
        ).fetchone()
        if existing:
            continue
        db.execute(text("""
            INSERT INTO bin_stock_levels
                (id, organization_id, bin_location_id, item_id,
                 quantity_on_hand, batch_number, created_at, updated_at)
            VALUES
                (:id, :org, :bin, :item, :qty, :batch, :now, :now)
        """), {"id": str(uid()), "org": str(ORG_ID), "bin": str(bin_id),
               "item": str(item_id), "qty": qty, "batch": batch, "now": now()})

    # Update available_capacity on bins (simple: capacity - qty_on_hand)
    db.execute(text("""
        UPDATE warehouse_locations wl
        SET available_capacity = wl.capacity - COALESCE((
            SELECT SUM(bsl.quantity_on_hand)
            FROM bin_stock_levels bsl
            WHERE bsl.bin_location_id = wl.id
        ), 0)
        WHERE wl.location_type = 'bin'
          AND wl.organization_id = :org
    """), {"org": str(ORG_ID)})
    print(f"  [ok] Bin stock levels seeded ({len(stock_entries)} entries)")


# ---------------------------------------------------------------------------
# SECTION 8 — Inbound: Scan Sessions + Receiving Slips + Put-Away Lists
# ---------------------------------------------------------------------------

def _insert_scan_session(db, sess_id, sess_type, status, worker_id,
                         dock, started, ended=None) -> None:
    existing = db.execute(
        text("SELECT id FROM scan_sessions WHERE id = :id"), {"id": str(sess_id)}
    ).fetchone()
    if existing:
        return
    db.execute(text("""
        INSERT INTO scan_sessions
            (id, organization_id, session_type, worker_id, warehouse_id,
             dock_location, status, total_boxes_scanned,
             started_at, ended_at, created_at, updated_at)
        VALUES
            (:id, :org, :stype, :worker, :wh,
             :dock, :status, 0,
             :started, :ended, :started, :started)
    """), {"id": str(sess_id), "org": str(ORG_ID), "stype": sess_type,
           "worker": str(worker_id), "wh": str(WH_ID),
           "dock": dock, "status": status,
           "started": started, "ended": ended})


def _insert_scan_item(db, item_id, sess_id, qr_id, sku, raw_qty, batch, raw_data) -> None:
    existing = db.execute(
        text("SELECT id FROM scan_session_items WHERE id = :id"), {"id": str(item_id)}
    ).fetchone()
    if existing:
        return
    db.execute(text("""
        INSERT INTO scan_session_items
            (id, organization_id, session_id, qr_identifier, sku,
             raw_quantity, batch_number, raw_qr_data, scanned_at)
        VALUES
            (:id, :org, :sess, :qr, :sku, :qty, :batch, :raw, :now)
    """), {"id": str(item_id), "org": str(ORG_ID), "sess": str(sess_id),
           "qr": qr_id, "sku": sku, "qty": raw_qty, "batch": batch,
           "raw": raw_data, "now": now()})


def _update_session_box_count(db, sess_id, count) -> None:
    db.execute(
        text("UPDATE scan_sessions SET total_boxes_scanned = :c WHERE id = :id"),
        {"c": count, "id": str(sess_id)},
    )


def _insert_receiving_slip(db, slip_id, slip_no, sess_id, status,
                           total_boxes, total_items) -> None:
    existing = db.execute(
        text("SELECT id FROM receiving_slips WHERE id = :id"), {"id": str(slip_id)}
    ).fetchone()
    if existing:
        return
    db.execute(text("""
        INSERT INTO receiving_slips
            (id, organization_id, slip_number, session_id, warehouse_id,
             status, total_boxes, total_items, created_at, updated_at)
        VALUES
            (:id, :org, :no, :sess, :wh,
             :status, :boxes, :items, :now, :now)
    """), {"id": str(slip_id), "org": str(ORG_ID), "no": slip_no,
           "sess": str(sess_id), "wh": str(WH_ID),
           "status": status, "boxes": total_boxes, "items": total_items,
           "now": now()})


def _insert_slip_item(db, si_id, slip_id, sku, batch, qty, box_count, flag="ok") -> None:
    existing = db.execute(
        text("SELECT id FROM receiving_slip_items WHERE id = :id"), {"id": str(si_id)}
    ).fetchone()
    if existing:
        return
    db.execute(text("""
        INSERT INTO receiving_slip_items
            (id, organization_id, slip_id, sku, batch_number,
             quantity, box_count, flag, created_at, updated_at)
        VALUES
            (:id, :org, :slip, :sku, :batch,
             :qty, :boxes, :flag, :now, :now)
    """), {"id": str(si_id), "org": str(ORG_ID), "slip": str(slip_id),
           "sku": sku, "batch": batch, "qty": qty, "boxes": box_count,
           "flag": flag, "now": now()})


def _insert_put_away_list(db, pal_id, pal_no, slip_id, status, worker_id) -> None:
    existing = db.execute(
        text("SELECT id FROM put_away_lists WHERE id = :id"), {"id": str(pal_id)}
    ).fetchone()
    if existing:
        return
    db.execute(text("""
        INSERT INTO put_away_lists
            (id, organization_id, warehouse_id, put_away_list_no,
             status, receiving_slip_id, assigned_to, created_at, updated_at)
        VALUES
            (:id, :org, :wh, :no,
             :status, :slip, :worker, :now, :now)
    """), {"id": str(pal_id), "org": str(ORG_ID), "wh": str(WH_ID),
           "no": pal_no, "status": status, "slip": str(slip_id),
           "worker": str(worker_id), "now": now()})


def _insert_put_away_item(db, pai_id, pal_id, item_id, sku, batch,
                          qty, bin_path, sort_order, status) -> None:
    existing = db.execute(
        text("SELECT id FROM put_away_list_items WHERE id = :id"), {"id": str(pai_id)}
    ).fetchone()
    if existing:
        return
    bin_id = LOCATION_IDS.get(bin_path)
    db.execute(text("""
        INSERT INTO put_away_list_items
            (id, organization_id, put_away_list_id, item_id, sku,
             batch_number, quantity, bin_location_id, sort_order,
             status, created_at, updated_at)
        VALUES
            (:id, :org, :pal, :item, :sku,
             :batch, :qty, :bin, :sort,
             :status, :now, :now)
    """), {"id": str(pai_id), "org": str(ORG_ID), "pal": str(pal_id),
           "item": str(item_id), "sku": sku, "batch": batch, "qty": qty,
           "bin": str(bin_id) if bin_id else None, "sort": sort_order,
           "status": status, "now": now()})


def seed_inbound(db) -> None:
    # ---- Session 1: Completed 3 days ago, slip approved → put-away complete ----
    S1_ID  = uuid.UUID("ee000000-0000-0000-0000-000000000001")
    RS1_ID = uuid.UUID("ee000000-0000-0000-0000-000000000002")
    PA1_ID = uuid.UUID("ee000000-0000-0000-0000-000000000003")

    _insert_scan_session(db, S1_ID, "inbound", "closed", WORKER_1_ID,
                         "Dock A", days_ago(3), days_ago(3))

    scans_s1 = [
        (uid(), "QR-S1-001", "SKU-WGT-A", 50, "BATCH-WGT-A-2025-01"),
        (uid(), "QR-S1-002", "SKU-WGT-A", 50, "BATCH-WGT-A-2025-01"),
        (uid(), "QR-S1-003", "SKU-WGT-B", 60, "BATCH-WGT-B-2025-01"),
        (uid(), "QR-S1-004", "SKU-WGT-B", 60, "BATCH-WGT-B-2025-01"),
        (uid(), "QR-S1-005", "SKU-CBL-Z", 90, "BATCH-CBL-Z-2025-01"),
    ]
    for si_id, qr_id, sku, qty, batch in scans_s1:
        _insert_scan_item(db, si_id, S1_ID, qr_id, sku, qty, batch,
                          qr_payload(sku, qty, batch, qr_id))
    _update_session_box_count(db, S1_ID, len(scans_s1))

    _insert_receiving_slip(db, RS1_ID, "RS-2025-001", S1_ID,
                           "putaway_complete", 5, 310)
    _insert_slip_item(db, uid(), RS1_ID, "SKU-WGT-A", "BATCH-WGT-A-2025-01", 100, 2)
    _insert_slip_item(db, uid(), RS1_ID, "SKU-WGT-B", "BATCH-WGT-B-2025-01", 120, 2)
    _insert_slip_item(db, uid(), RS1_ID, "SKU-CBL-Z", "BATCH-CBL-Z-2025-01",  90, 1)

    _insert_put_away_list(db, PA1_ID, "PAL-2025-001", RS1_ID,
                          "completed", WORKER_1_ID)
    pa1_items = [
        (uid(), ITEM_WIDGET_A_ID, "SKU-WGT-A", "BATCH-WGT-A-2025-01",
         100, "ZA-A01-B01-L01-001", 1, "completed"),
        (uid(), ITEM_WIDGET_B_ID, "SKU-WGT-B", "BATCH-WGT-B-2025-01",
         120, "ZA-A01-B01-L02-001", 2, "completed"),
        (uid(), ITEM_CABLE_Z_ID,  "SKU-CBL-Z", "BATCH-CBL-Z-2025-01",
          90, "ZA-A01-B02-L01-001", 3, "completed"),
    ]
    for pai_id, item_id, sku, batch, qty, bin_path, sort, status in pa1_items:
        _insert_put_away_item(db, pai_id, PA1_ID, item_id, sku, batch,
                              qty, bin_path, sort, status)

    # ---- Session 2: Completed 1 day ago, slip approved → put-away in-progress ----
    S2_ID  = uuid.UUID("ee000000-0000-0000-0000-000000000010")
    RS2_ID = uuid.UUID("ee000000-0000-0000-0000-000000000011")
    PA2_ID = uuid.UUID("ee000000-0000-0000-0000-000000000012")

    _insert_scan_session(db, S2_ID, "inbound", "closed", WORKER_2_ID,
                         "Dock B", days_ago(1), days_ago(1))

    scans_s2 = [
        (uid(), "QR-S2-001", "SKU-GDG-X", 20, "BATCH-GDG-X-2025-01"),
        (uid(), "QR-S2-002", "SKU-GDG-X", 20, "BATCH-GDG-X-2025-01"),
        (uid(), "QR-S2-003", "SKU-GDG-Y", 30, "BATCH-GDG-Y-2025-01"),
        (uid(), "QR-S2-004", "SKU-GLS-P", 10, "BATCH-GLS-P-2025-01"),
    ]
    for si_id, qr_id, sku, qty, batch in scans_s2:
        _insert_scan_item(db, si_id, S2_ID, qr_id, sku, qty, batch,
                          qr_payload(sku, qty, batch, qr_id))
    _update_session_box_count(db, S2_ID, len(scans_s2))

    _insert_receiving_slip(db, RS2_ID, "RS-2025-002", S2_ID,
                           "pending_putaway", 4, 80)
    _insert_slip_item(db, uid(), RS2_ID, "SKU-GDG-X", "BATCH-GDG-X-2025-01", 40, 2)
    _insert_slip_item(db, uid(), RS2_ID, "SKU-GDG-Y", "BATCH-GDG-Y-2025-01", 30, 1)
    _insert_slip_item(db, uid(), RS2_ID, "SKU-GLS-P", "BATCH-GLS-P-2025-01", 10, 1)

    _insert_put_away_list(db, PA2_ID, "PAL-2025-002", RS2_ID,
                          "in_progress", WORKER_2_ID)
    pa2_items = [
        (uid(), ITEM_GADGET_X_ID, "SKU-GDG-X", "BATCH-GDG-X-2025-01",
         40, "ZB-B01-B01-L01-001", 1, "completed"),
        (uid(), ITEM_GADGET_Y_ID, "SKU-GDG-Y", "BATCH-GDG-Y-2025-01",
         30, "ZB-B01-B01-L02-001", 2, "pending"),
        (uid(), ITEM_GLASS_P_ID,  "SKU-GLS-P", "BATCH-GLS-P-2025-01",
         10, "ZB-B02-B01-L01-001", 3, "pending"),
    ]
    for pai_id, item_id, sku, batch, qty, bin_path, sort, status in pa2_items:
        _insert_put_away_item(db, pai_id, PA2_ID, item_id, sku, batch,
                              qty, bin_path, sort, status)

    # ---- Session 3: Just ended today, slip pending review ----
    S3_ID  = uuid.UUID("ee000000-0000-0000-0000-000000000020")
    RS3_ID = uuid.UUID("ee000000-0000-0000-0000-000000000021")

    _insert_scan_session(db, S3_ID, "inbound", "closed", WORKER_1_ID,
                         "Dock A", hours_ago(2), hours_ago(1))

    scans_s3 = [
        (uid(), "QR-S3-001", "SKU-WGT-A", 24, "BATCH-WGT-A-2025-03"),
        (uid(), "QR-S3-002", "SKU-WGT-B", 24, "BATCH-WGT-B-2025-03"),
        (uid(), "QR-S3-003", "SKU-CBL-Z", 30, "BATCH-CBL-Z-2025-03"),
    ]
    for si_id, qr_id, sku, qty, batch in scans_s3:
        _insert_scan_item(db, si_id, S3_ID, qr_id, sku, qty, batch,
                          qr_payload(sku, qty, batch, qr_id))
    _update_session_box_count(db, S3_ID, len(scans_s3))

    _insert_receiving_slip(db, RS3_ID, "RS-2025-003", S3_ID,
                           "pending_review", 3, 78)
    _insert_slip_item(db, uid(), RS3_ID, "SKU-WGT-A", "BATCH-WGT-A-2025-03", 24, 1)
    _insert_slip_item(db, uid(), RS3_ID, "SKU-WGT-B", "BATCH-WGT-B-2025-03", 24, 1)
    _insert_slip_item(db, uid(), RS3_ID, "SKU-CBL-Z", "BATCH-CBL-Z-2025-03", 30, 1,
                      flag="short")  # flagged short

    print("  [ok] Inbound sessions, receiving slips, and put-away lists seeded")


# ---------------------------------------------------------------------------
# SECTION 9 — Outbound: Pick Lists + Gate Verification + Dispatch
# ---------------------------------------------------------------------------

def _insert_pick_list(db, pl_id, pl_no, status, invoice_ref,
                      completed_at=None) -> None:
    existing = db.execute(
        text("SELECT id FROM pick_lists WHERE id = :id"), {"id": str(pl_id)}
    ).fetchone()
    if existing:
        return
    db.execute(text("""
        INSERT INTO pick_lists
            (id, organization_id, pick_list_no, warehouse_id, status,
             reference_type, invoice_reference, pick_date,
             completed_at, created_at, updated_at)
        VALUES
            (:id, :org, :no, :wh, :status,
             'sales_invoice', :inv, :now,
             :comp, :now, :now)
    """), {"id": str(pl_id), "org": str(ORG_ID), "no": pl_no,
           "wh": str(WH_ID), "status": status, "inv": invoice_ref,
           "now": now(), "comp": completed_at})


def _insert_pick_item(db, pli_id, pl_id, item_id, qty, picked_qty,
                      uom, batch, bin_path, sort_order) -> None:
    existing = db.execute(
        text("SELECT id FROM pick_list_items WHERE id = :id"), {"id": str(pli_id)}
    ).fetchone()
    if existing:
        return
    bin_id = LOCATION_IDS.get(bin_path)
    db.execute(text("""
        INSERT INTO pick_list_items
            (id, organization_id, pick_list_id, item_id, warehouse_id,
             qty, picked_qty, uom, batch_no, bin_location_id,
             sort_order, created_at, updated_at)
        VALUES
            (:id, :org, :pl, :item, :wh,
             :qty, :pqty, :uom, :batch, :bin,
             :sort, :now, :now)
    """), {"id": str(pli_id), "org": str(ORG_ID), "pl": str(pl_id),
           "item": str(item_id), "wh": str(WH_ID),
           "qty": qty, "pqty": picked_qty, "uom": uom, "batch": batch,
           "bin": str(bin_id) if bin_id else None,
           "sort": sort_order, "now": now()})


def seed_outbound(db) -> None:
    # ---- Pick List 1: Completed 2 days ago ----
    PL1_ID  = uuid.UUID("ff000000-0000-0000-0000-000000000001")
    GVS1_ID = uuid.UUID("ff000000-0000-0000-0000-000000000002")
    DR1_ID  = uuid.UUID("ff000000-0000-0000-0000-000000000003")

    _insert_pick_list(db, PL1_ID, "PL-2025-001", "completed",
                      "SAP-INV-2025-0042", completed_at=days_ago(2))

    pl1_items = [
        (uid(), ITEM_WIDGET_A_ID, 30, 30, "Nos", "BATCH-WGT-A-2025-01",
         "ZA-A01-B01-L01-001", 1),
        (uid(), ITEM_WIDGET_B_ID, 20, 20, "Nos", "BATCH-WGT-B-2025-01",
         "ZA-A01-B01-L02-001", 2),
        (uid(), ITEM_CABLE_Z_ID,  15, 15, "Box", "BATCH-CBL-Z-2025-01",
         "ZA-A01-B02-L01-001", 3),
    ]
    for pli_id, item_id, qty, pqty, uom, batch, bin_path, sort in pl1_items:
        _insert_pick_item(db, pli_id, PL1_ID, item_id, qty, pqty,
                          uom, batch, bin_path, sort)

    # Gate verification session for PL1 — verified
    existing_gvs = db.execute(
        text("SELECT id FROM gate_verification_sessions WHERE id = :id"),
        {"id": str(GVS1_ID)},
    ).fetchone()
    if not existing_gvs:
        db.execute(text("""
            INSERT INTO gate_verification_sessions
                (id, organization_id, pick_list_id, warehouse_id, worker_id,
                 vehicle_number, driver_name, driver_contact,
                 status, verified_at, created_at, updated_at)
            VALUES
                (:id, :org, :pl, :wh, :worker,
                 'MH-12-AB-1234', 'Ramesh Kumar', '+91-9876543210',
                 'verified', :verified, :now, :now)
        """), {"id": str(GVS1_ID), "org": str(ORG_ID), "pl": str(PL1_ID),
               "wh": str(WH_ID), "worker": str(WORKER_2_ID),
               "verified": days_ago(2), "now": now()})

        # Gate items
        gate_scans = [
            (uid(), "QR-GATE-001", "SKU-WGT-A", 30, "verified"),
            (uid(), "QR-GATE-002", "SKU-WGT-B", 20, "verified"),
            (uid(), "QR-GATE-003", "SKU-CBL-Z", 15, "verified"),
        ]
        for gi_id, qr_id, sku, qty, status in gate_scans:
            db.execute(text("""
                INSERT INTO gate_verification_items
                    (id, organization_id, gate_session_id, qr_identifier,
                     sku, quantity, status, scanned_at)
                VALUES
                    (:id, :org, :gvs, :qr, :sku, :qty, :status, :now)
            """), {"id": str(gi_id), "org": str(ORG_ID), "gvs": str(GVS1_ID),
                   "qr": qr_id, "sku": sku, "qty": qty,
                   "status": status, "now": days_ago(2)})

    # Dispatch record for PL1
    existing_dr = db.execute(
        text("SELECT id FROM dispatch_records WHERE id = :id"),
        {"id": str(DR1_ID)},
    ).fetchone()
    if not existing_dr:
        db.execute(text("""
            INSERT INTO dispatch_records
                (id, organization_id, dispatch_number, pick_list_id,
                 gate_session_id, invoice_reference, vehicle_number,
                 driver_name, dispatched_at, created_at, updated_at)
            VALUES
                (:id, :org, 'DN-2025-001', :pl,
                 :gvs, 'SAP-INV-2025-0042', 'MH-12-AB-1234',
                 'Ramesh Kumar', :dispatched, :now, :now)
        """), {"id": str(DR1_ID), "org": str(ORG_ID), "pl": str(PL1_ID),
               "gvs": str(GVS1_ID), "dispatched": days_ago(2), "now": now()})

        # Link dispatch back to pick list
        db.execute(text("""
            UPDATE pick_lists SET dispatch_record_id = :dr WHERE id = :pl
        """), {"dr": str(DR1_ID), "pl": str(PL1_ID)})

    # ---- Pick List 2: In-progress (today) ----
    PL2_ID = uuid.UUID("ff000000-0000-0000-0000-000000000010")

    _insert_pick_list(db, PL2_ID, "PL-2025-002", "in_progress",
                      "SAP-INV-2025-0055")

    pl2_items = [
        (uid(), ITEM_GADGET_X_ID, 10, 5,  "Nos", "BATCH-GDG-X-2025-01",
         "ZB-B01-B01-L01-001", 1),
        (uid(), ITEM_GADGET_Y_ID, 15, 0,  "Nos", "BATCH-GDG-Y-2025-01",
         "ZB-B01-B01-L02-001", 2),
        (uid(), ITEM_WIDGET_A_ID, 20, 20, "Nos", "BATCH-WGT-A-2025-02",
         "ZA-A01-B01-L01-002", 3),
    ]
    for pli_id, item_id, qty, pqty, uom, batch, bin_path, sort in pl2_items:
        _insert_pick_item(db, pli_id, PL2_ID, item_id, qty, pqty,
                          uom, batch, bin_path, sort)

    # ---- Pick List 3: Draft (just created) ----
    PL3_ID = uuid.UUID("ff000000-0000-0000-0000-000000000020")

    _insert_pick_list(db, PL3_ID, "PL-2025-003", "draft",
                      "SAP-INV-2025-0061")

    pl3_items = [
        (uid(), ITEM_GLASS_P_ID,  5, 0, "Nos", "BATCH-GLS-P-2025-01",
         "ZB-B02-B01-L01-001", 1),
        (uid(), ITEM_CABLE_Z_ID, 10, 0, "Box", "BATCH-CBL-Z-2025-02",
         "ZA-A01-B02-L01-002", 2),
    ]
    for pli_id, item_id, qty, pqty, uom, batch, bin_path, sort in pl3_items:
        _insert_pick_item(db, pli_id, PL3_ID, item_id, qty, pqty,
                          uom, batch, bin_path, sort)

    print("  [ok] Pick lists, gate verification, and dispatch records seeded")


# ---------------------------------------------------------------------------
# SECTION 10 — Worker Tasks + Location Scans (Time Tracking)
# ---------------------------------------------------------------------------

def _insert_worker_task(db, wt_id, task_type, worker_id, reference_id,
                        status, started=None, completed=None) -> None:
    existing = db.execute(
        text("SELECT id FROM worker_tasks WHERE id = :id"), {"id": str(wt_id)}
    ).fetchone()
    if existing:
        return
    db.execute(text("""
        INSERT INTO worker_tasks
            (id, organization_id, task_type, worker_id, reference_id,
             status, assigned_at, started_at, completed_at,
             created_at, updated_at)
        VALUES
            (:id, :org, :ttype, :worker, :ref,
             :status, :now, :started, :completed,
             :now, :now)
    """), {"id": str(wt_id), "org": str(ORG_ID), "ttype": task_type,
           "worker": str(worker_id), "ref": str(reference_id),
           "status": status, "now": now(),
           "started": started, "completed": completed})


def _insert_location_scan(db, ls_id, wt_id, loc_code, scan_type,
                          scanned_at, elapsed=None) -> None:
    existing = db.execute(
        text("SELECT id FROM location_scans WHERE id = :id"), {"id": str(ls_id)}
    ).fetchone()
    if existing:
        return
    db.execute(text("""
        INSERT INTO location_scans
            (id, organization_id, worker_task_id, location_code,
             scan_type, scanned_at, elapsed_seconds, created_at)
        VALUES
            (:id, :org, :wt, :loc, :stype, :scanned, :elapsed, :now)
    """), {"id": str(ls_id), "org": str(ORG_ID), "wt": str(wt_id),
           "loc": loc_code, "stype": scan_type,
           "scanned": scanned_at, "elapsed": elapsed, "now": now()})


def seed_worker_tasks(db) -> None:
    PA1_ID = uuid.UUID("ee000000-0000-0000-0000-000000000003")
    PA2_ID = uuid.UUID("ee000000-0000-0000-0000-000000000012")
    PL1_ID = uuid.UUID("ff000000-0000-0000-0000-000000000001")
    PL2_ID = uuid.UUID("ff000000-0000-0000-0000-000000000010")

    # Task 1: Put-away for PA1 — completed
    WT1_ID = uuid.UUID("aa100000-0000-0000-0000-000000000001")
    _insert_worker_task(db, WT1_ID, "put_away", WORKER_1_ID, PA1_ID,
                        "completed",
                        started=days_ago(3),
                        completed=days_ago(3))

    # Location scans for WT1 (3 bins visited)
    t_base = days_ago(3)
    scan_pairs_wt1 = [
        ("ZA-A01-B01-L01-001", 0,   420),   # 7 min
        ("ZA-A01-B01-L02-001", 500, 380),   # ~6 min
        ("ZA-A01-B02-L01-001", 950, 300),   # 5 min
    ]
    for loc, start_offset, elapsed in scan_pairs_wt1:
        start_t = t_base + timedelta(seconds=start_offset)
        finish_t = start_t + timedelta(seconds=elapsed)
        _insert_location_scan(db, uid(), WT1_ID, loc, "start",  start_t)
        _insert_location_scan(db, uid(), WT1_ID, loc, "finish", finish_t, elapsed)

    # Task 2: Put-away for PA2 — in-progress
    WT2_ID = uuid.UUID("aa100000-0000-0000-0000-000000000002")
    _insert_worker_task(db, WT2_ID, "put_away", WORKER_2_ID, PA2_ID,
                        "in_progress", started=days_ago(1))

    t_base2 = days_ago(1)
    _insert_location_scan(db, uid(), WT2_ID, "ZB-B01-B01-L01-001",
                          "start",  t_base2)
    _insert_location_scan(db, uid(), WT2_ID, "ZB-B01-B01-L01-001",
                          "finish", t_base2 + timedelta(seconds=510), 510)

    # Task 3: Pick for PL1 — completed
    WT3_ID = uuid.UUID("aa100000-0000-0000-0000-000000000003")
    _insert_worker_task(db, WT3_ID, "pick", WORKER_1_ID, PL1_ID,
                        "completed",
                        started=days_ago(2),
                        completed=days_ago(2))

    t_base3 = days_ago(2)
    scan_pairs_wt3 = [
        ("ZA-A01-B01-L01-001", 0,   300),
        ("ZA-A01-B01-L02-001", 360, 280),
        ("ZA-A01-B02-L01-001", 700, 250),
    ]
    for loc, start_offset, elapsed in scan_pairs_wt3:
        start_t = t_base3 + timedelta(seconds=start_offset)
        finish_t = start_t + timedelta(seconds=elapsed)
        _insert_location_scan(db, uid(), WT3_ID, loc, "start",  start_t)
        _insert_location_scan(db, uid(), WT3_ID, loc, "finish", finish_t, elapsed)

    # Task 4: Pick for PL2 — in-progress
    WT4_ID = uuid.UUID("aa100000-0000-0000-0000-000000000004")
    _insert_worker_task(db, WT4_ID, "pick", WORKER_2_ID, PL2_ID,
                        "in_progress", started=hours_ago(1))

    t_base4 = hours_ago(1)
    _insert_location_scan(db, uid(), WT4_ID, "ZB-B01-B01-L01-001",
                          "start",  t_base4)
    _insert_location_scan(db, uid(), WT4_ID, "ZB-B01-B01-L01-001",
                          "finish", t_base4 + timedelta(seconds=390), 390)

    print("  [ok] Worker tasks and location scans seeded")


# ---------------------------------------------------------------------------
# MAIN
# ---------------------------------------------------------------------------

def main() -> None:
    engine = create_engine(DATABASE_URL)
    Session = sessionmaker(bind=engine)
    db = Session()

    try:
        print("\n=== WMS Demo Data Seed ===\n")

        print("1. Warehouse...")
        seed_warehouse(db)
        db.commit()

        print("2. Item Groups...")
        seed_item_groups(db)
        db.commit()

        print("3. Items...")
        seed_items(db)
        db.commit()

        print("4. Packaging Units...")
        seed_packaging_units(db)
        db.commit()

        print("5. Location Hierarchy...")
        seed_locations(db)
        db.commit()

        print("6. Location Allocations...")
        seed_allocations(db)
        db.commit()

        print("7. Bin Stock Levels...")
        seed_bin_stock(db)
        db.commit()

        print("8. Inbound Flow (sessions / slips / put-away)...")
        seed_inbound(db)
        db.commit()

        print("9. Outbound Flow (pick lists / gate / dispatch)...")
        seed_outbound(db)
        db.commit()

        print("10. Worker Tasks & Time Tracking...")
        seed_worker_tasks(db)
        db.commit()

        print("\n✓ All WMS demo data seeded successfully!\n")
        print("Summary:")
        print("  • 1 warehouse (MDC-01)")
        print("  • 3 item groups, 6 items with packaging units")
        print("  • 32 bin locations across 2 zones")
        print("  • 17 bin stock entries")
        print("  • 10 location allocations")
        print("  • 3 inbound sessions → 3 receiving slips → 2 put-away lists")
        print("  • 3 pick lists (completed / in-progress / draft)")
        print("  • 1 gate verification session (verified) + dispatch record")
        print("  • 4 worker tasks + location scan time tracking")

    except Exception as exc:
        db.rollback()
        print(f"\n✗ Seed failed: {exc}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
