"""
Seed script: Dummy analytics data for org + assign permissions.
Usage: python seed_analytics_data.py

Creates:
  - 5 additional QR products (Electronics, Pharma, Fashion, Food, Auto)
  - ~75 product items across products
  - ~80 scan events across last 30 days with realistic geo/device/CTA data
  - Report permissions assigned to wms_admin role
"""

import os
import random
import sys
import uuid
from datetime import UTC, datetime, timedelta

import psycopg2
from psycopg2.extras import execute_values

# ── Config ────────────────────────────────────────────────────────────────────
ORG_ID = "b5863590-fb53-4d22-a956-956aafc1c13e"
USER_ID = "171e65d7-60c5-451b-a5b6-c174fbc842c1"
WMS_ADMIN_ROLE_ID = "d51883b9-2184-4390-8cf7-26e4dfd4acde"

# DB connections (from docker-compose defaults)
CORE_DB = os.getenv(
    "CORE_DB_URL", "postgresql://horizon_user:horizon_pass@localhost:5432/core_db"
)
IDENTITY_DB = os.getenv(
    "IDENTITY_DB_URL",
    "postgresql://horizon_user:horizon_pass@localhost:5432/identity_db",
)

# ── Realistic data pools ──────────────────────────────────────────────────────
PRODUCTS = [
    {
        "name": "iPhone 15 Pro",
        "generic_name": "Smartphone",
        "industry": "Electronics",
        "gtin": "8901234567001",
    },
    {
        "name": "EcoWash Detergent",
        "generic_name": "Laundry Detergent",
        "industry": "FMCG",
        "gtin": "8901234567002",
    },
    {
        "name": "Paracetamol 500mg",
        "generic_name": "Pain Reliever",
        "industry": "Pharma",
        "gtin": "8901234567003",
    },
    {
        "name": "Levi's 501 Jeans",
        "generic_name": "Denim Jeans",
        "industry": "Fashion",
        "gtin": "8901234567004",
    },
    {
        "name": "Amul Gold Milk",
        "generic_name": "Full Cream Milk",
        "industry": "Food & Beverage",
        "gtin": "8901234567005",
    },
]

CITIES = [
    {
        "city": "Mumbai",
        "state": "Maharashtra",
        "country": "India",
        "lat": 19.0760,
        "lng": 72.8777,
    },
    {
        "city": "Delhi",
        "state": "Delhi",
        "country": "India",
        "lat": 28.6139,
        "lng": 77.2090,
    },
    {
        "city": "Bangalore",
        "state": "Karnataka",
        "country": "India",
        "lat": 12.9716,
        "lng": 77.5946,
    },
    {
        "city": "Chennai",
        "state": "Tamil Nadu",
        "country": "India",
        "lat": 13.0827,
        "lng": 80.2707,
    },
    {
        "city": "Hyderabad",
        "state": "Telangana",
        "country": "India",
        "lat": 17.3850,
        "lng": 78.4867,
    },
    {
        "city": "Pune",
        "state": "Maharashtra",
        "country": "India",
        "lat": 18.5204,
        "lng": 73.8567,
    },
    {
        "city": "Ahmedabad",
        "state": "Gujarat",
        "country": "India",
        "lat": 23.0225,
        "lng": 72.5714,
    },
    {
        "city": "Kolkata",
        "state": "West Bengal",
        "country": "India",
        "lat": 22.5726,
        "lng": 88.3639,
    },
    {
        "city": "Jaipur",
        "state": "Rajasthan",
        "country": "India",
        "lat": 26.9124,
        "lng": 75.7873,
    },
    {
        "city": "Lucknow",
        "state": "Uttar Pradesh",
        "country": "India",
        "lat": 26.8467,
        "lng": 80.9462,
    },
    {"city": "Dubai", "state": None, "country": "UAE", "lat": 25.2048, "lng": 55.2708},
    {
        "city": "Abu Dhabi",
        "state": None,
        "country": "UAE",
        "lat": 24.4539,
        "lng": 54.3773,
    },
    {
        "city": "New York",
        "state": "New York",
        "country": "United States",
        "lat": 40.7128,
        "lng": -74.0060,
    },
    {
        "city": "London",
        "state": None,
        "country": "United Kingdom",
        "lat": 51.5074,
        "lng": -0.1278,
    },
    {
        "city": "Singapore",
        "state": None,
        "country": "Singapore",
        "lat": 1.3521,
        "lng": 103.8198,
    },
]

DEVICES = [
    {"device_type": "mobile", "os": "iOS", "browser": "Mobile Safari", "weight": 30},
    {
        "device_type": "mobile",
        "os": "Android",
        "browser": "Chrome Mobile",
        "weight": 35,
    },
    {
        "device_type": "mobile",
        "os": "Android",
        "browser": "Samsung Internet",
        "weight": 7,
    },
    {"device_type": "desktop", "os": "Windows", "browser": "Chrome", "weight": 12},
    {"device_type": "desktop", "os": "macOS", "browser": "Safari", "weight": 5},
    {"device_type": "desktop", "os": "Windows", "browser": "Firefox", "weight": 3},
    {"device_type": "tablet", "os": "iOS", "browser": "Mobile Safari", "weight": 5},
    {"device_type": "tablet", "os": "Android", "browser": "Chrome Mobile", "weight": 3},
]

CTA_ACTIONS = [
    {"action": "view_product", "weight": 45},
    {"action": "visit_website", "weight": 30},
    {"action": "verify_auth", "weight": 15},
    {"action": "call_support", "weight": 10},
]

REFERRERS = [
    "https://instagram.com/p/...",
    "https://facebook.com/share/...",
    "https://wa.me/?text=...",
    "https://twitter.com/status/...",
    "https://youtube.com/watch?v=...",
    "https://linkedin.com/feed/...",
    "https://t.me/share/...",
    "https://pinterest.com/pin/...",
    None,
    None,
    None,  # ~25% direct/no referrer
]

LANGUAGES = ["en-IN", "en-US", "hi-IN", "en-GB", "ar-AE", "ta-IN", "mr-IN"]

SERIAL_PREFIXES = {
    "Electronics": "ELEC",
    "FMCG": "FMCG",
    "Pharma": "PHAR",
    "Fashion": "FASH",
    "Food & Beverage": "FOOD",
}

# ── Helpers ────────────────────────────────────────────────────────────────────


def weighted_choice(pool, weight_key="weight"):
    total = sum(p[weight_key] for p in pool)
    r = random.uniform(0, total)
    acc = 0
    for item in pool:
        acc += item[weight_key]
        if r <= acc:
            return item
    return pool[-1]


def random_ip(country="India"):
    pools = {
        "India": ("103.15.", "106.215.", "117.99.", "152.58.", "157.50."),
        "UAE": ("2.48.", "5.31.", "86.98.", "91.73.", "94.200."),
        "United States": ("104.16.", "172.67.", "198.41.", "23.227.", "45.33."),
        "United Kingdom": ("51.6.", "81.128.", "86.134.", "90.206.", "109.148."),
        "Singapore": ("103.6.", "116.12.", "119.74.", "121.6.", "165.173."),
    }
    prefix = random.choice(pools.get(country, pools["India"]))
    return f"{prefix}{random.randint(1, 255)}.{random.randint(1, 254)}"


def random_serial(prefix, idx):
    return f"{prefix}-{random.randint(100000, 999999)}-{idx:04d}"


def random_timestamp(days_back=30):
    now = datetime.now(UTC)
    days = random.randint(0, days_back)
    hours = random.randint(0, 23)
    minutes = random.randint(0, 59)
    return now - timedelta(days=days, hours=hours, minutes=minutes)


def generate_user_agent(device):
    """Build extra_data["user_agent_parsed"]"""
    os_version = f"{random.randint(14, 18)}.{random.randint(0, 3)}"
    browser_version = f"{random.randint(100, 130)}.{random.randint(0, 3)}.{random.randint(0, 9999)}.{random.randint(0, 99)}"
    return {
        "browser": device["browser"],
        "browser_version": browser_version,
        "os": device["os"],
        "os_version": os_version,
        "device_type": device["device_type"],
        "is_mobile": device["device_type"] in ("mobile", "tablet"),
        "is_tablet": device["device_type"] == "tablet",
        "is_pc": device["device_type"] == "desktop",
    }


# ── Main ───────────────────────────────────────────────────────────────────────


def main():
    print("=" * 60)
    print("Seeding Analytics Data + Permissions")
    print(f"Org:  {ORG_ID}")
    print(f"User: {USER_ID}")
    print("=" * 60)

    conn_core = psycopg2.connect(CORE_DB)
    conn_id = psycopg2.connect(IDENTITY_DB)
    cur_core = conn_core.cursor()
    cur_id = conn_id.cursor()

    try:
        # ── Step 1: Assign report permissions to wms_admin role ────────────────
        print("\n[1/4] Assigning report permissions to wms_admin role...")

        # Get report permission IDs
        cur_id.execute("""
            SELECT id, code FROM permissions
            WHERE code IN ('report.read', 'report.execute')
        """)
        perms = {row[1]: row[0] for row in cur_id.fetchall()}

        for code, pid in perms.items():
            # Check if already assigned
            cur_id.execute(
                "SELECT id FROM role_permissions WHERE role_id=%s AND permission_id=%s",
                (WMS_ADMIN_ROLE_ID, pid),
            )
            if cur_id.fetchone():
                print(f"  ⏭️  {code} (already assigned)")
                continue
            cur_id.execute(
                """
                INSERT INTO role_permissions (id, role_id, permission_id)
                VALUES (%s, %s, %s)
            """,
                (str(uuid.uuid4()), WMS_ADMIN_ROLE_ID, pid),
            )
            print(f"  ✅ {code} → wms_admin")

        # Also ensure user still has wms_admin role assignment
        cur_id.execute(
            "SELECT id FROM user_organization_roles WHERE user_id=%s AND organization_id=%s AND role_id=%s",
            (USER_ID, ORG_ID, WMS_ADMIN_ROLE_ID),
        )
        if not cur_id.fetchone():
            cur_id.execute(
                """
                INSERT INTO user_organization_roles (id, user_id, organization_id, role_id, is_primary, is_active)
                VALUES (%s, %s, %s, %s, true, true)
            """,
                (str(uuid.uuid4()), USER_ID, ORG_ID, WMS_ADMIN_ROLE_ID),
            )
            print("  ✅ User role assignment created")
        else:
            print("  ⏭️  User role assignment (already exists)")

        conn_id.commit()

        # ── Step 2: Create QR products ─────────────────────────────────────────
        print("\n[2/4] Creating QR products...")
        product_ids = ["57560cb3-419f-471d-a946-8e34d6291b15"]  # existing

        for prod in PRODUCTS:
            pid = str(uuid.uuid4())
            cur_core.execute(
                """
                INSERT INTO qr_products (id, organization_id, name, generic_name, gtin, industry, is_active, created_by)
                VALUES (%s, %s, %s, %s, %s, %s, true, %s)
                ON CONFLICT DO NOTHING
            """,
                (
                    pid,
                    ORG_ID,
                    prod["name"],
                    prod["generic_name"],
                    prod["gtin"],
                    prod["industry"],
                    USER_ID,
                ),
            )
            product_ids.append(pid)
            print(f"  ✅ {prod['name']} ({prod['industry']})")

        conn_core.commit()

        # ── Step 3: Create product items ───────────────────────────────────────
        print("\n[3/4] Creating product items...")
        item_map = {}  # product_id → list of (item_id, serial_number)

        # Existing items for Prestige Cooker
        cur_core.execute(
            """
            SELECT id, serial_number FROM product_items
            WHERE organization_id = %s
        """,
            (ORG_ID,),
        )
        for row in cur_core.fetchall():
            item_map.setdefault(product_ids[0], []).append((str(row[0]), row[1]))

        # Create items for new products
        for pid in product_ids[1:]:
            # Find which product this is
            cur_core.execute(
                "SELECT industry, name FROM qr_products WHERE id=%s", (pid,)
            )
            industry, name = cur_core.fetchone()
            prefix = SERIAL_PREFIXES.get(industry, "GEN")
            items = []
            for i in range(15):
                item_id = str(uuid.uuid4())
                serial = random_serial(prefix, i)
                cur_core.execute(
                    """
                    INSERT INTO product_items (id, organization_id, product_id, serial_number)
                    VALUES (%s, %s, %s, %s)
                """,
                    (item_id, ORG_ID, pid, serial),
                )
                items.append((item_id, serial))
            item_map[pid] = items
            print(f"  ✅ {name}: {len(items)} items")

        conn_core.commit()

        # ── Step 4: Generate scan events ───────────────────────────────────────
        print("\n[4/4] Generating ~80 scan events...")

        scan_rows = []
        # Flatten all items
        all_items = []
        for items in item_map.values():
            all_items.extend(items)

        for _ in range(80):
            item_id, serial = random.choice(all_items)
            city = random.choice(CITIES)
            device = weighted_choice(DEVICES)
            cta = weighted_choice(CTA_ACTIONS)
            ts = random_timestamp(30)
            lang = random.choice(LANGUAGES)
            referrer = random.choice(REFERRERS)
            ua = generate_user_agent(device)
            extra = {
                "cta_action": cta["action"],
                "qr_type": "product_auth",
                "referrer_url": referrer,
                "language": lang,
                "user_agent_parsed": ua,
            }

            scan_rows.append(
                (
                    str(uuid.uuid4()),
                    ORG_ID,
                    item_id,
                    serial,
                    ts,
                    device["device_type"],
                    device["os"],
                    device["browser"],
                    random_ip(city["country"]),
                    city["lat"] + random.uniform(-0.05, 0.05),
                    city["lng"] + random.uniform(-0.05, 0.05),
                    city["city"],
                    city["state"],
                    city["country"],
                    psycopg2.extras.Json(extra),
                )
            )

        execute_values(
            cur_core,
            """
            INSERT INTO qr_scan_events (
                id, organization_id, product_item_id, serial_number,
                scan_timestamp, device_type, os, browser,
                ip_address, latitude, longitude, city, state, country,
                extra_data
            ) VALUES %s
        """,
            scan_rows,
        )

        conn_core.commit()
        print(f"  ✅ {len(scan_rows)} scan events inserted")

        # ── Summary ─────────────────────────────────────────────────────────────
        print("\n" + "=" * 60)
        print("SEED COMPLETE")
        print("=" * 60)
        cur_core.execute(
            "SELECT COUNT(*) FROM qr_scan_events WHERE organization_id=%s", (ORG_ID,)
        )
        total = cur_core.fetchone()[0]
        print(f"  Total scans:       {total}")
        cur_core.execute(
            "SELECT COUNT(*) FROM qr_products WHERE organization_id=%s", (ORG_ID,)
        )
        print(f"  QR Products:       {cur_core.fetchone()[0]}")
        cur_core.execute(
            "SELECT COUNT(*) FROM product_items WHERE organization_id=%s", (ORG_ID,)
        )
        print(f"  Product Items:     {cur_core.fetchone()[0]}")
        cur_id.execute(
            """
            SELECT r.name FROM roles r
            JOIN user_organization_roles uor ON r.id = uor.role_id
            WHERE uor.user_id=%s AND uor.organization_id=%s
        """,
            (USER_ID, ORG_ID),
        )
        roles = [r[0] for r in cur_id.fetchall()]
        print(f"  User roles:        {', '.join(roles)}")

        cur_id.execute(
            """
            SELECT p.code FROM permissions p
            JOIN role_permissions rp ON p.id = rp.permission_id
            WHERE rp.role_id=%s
        """,
            (WMS_ADMIN_ROLE_ID,),
        )
        perms_list = [r[0] for r in cur_id.fetchall()]
        print(f"  wms_admin perms:   {len(perms_list)} total")
        report_perms = [p for p in perms_list if "report" in p]
        print(f"  Report perms:      {', '.join(report_perms)}")

    except Exception as e:
        conn_core.rollback()
        conn_id.rollback()
        print(f"\n❌ ERROR: {e}")
        sys.exit(1)
    finally:
        cur_core.close()
        cur_id.close()
        conn_core.close()
        conn_id.close()


if __name__ == "__main__":
    random.seed(42)  # reproducible
    main()
