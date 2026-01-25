"""Database seeding script for Core Service

This script seeds inventory data that complements the identity-service data.
It connects to identity_db to fetch organization and user info,
then seeds data into core_db.
"""

import os
import sys
from decimal import Decimal

from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from app.config import settings  # noqa: E402
from app.database import SessionLocal  # noqa: E402
from app.models import (  # noqa: E402
    Item,
    ItemGroup,
    Warehouse,
)


def get_identity_session_factory():
    """
    Create a session factory for the identity database.
    Returns a sessionmaker instance that can be called to create sessions.
    """
    identity_db_url = settings.identity_database_url
    if not identity_db_url:
        return None

    engine = create_engine(identity_db_url)
    return sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_organization_id():
    """
    Get the default organization ID from identity-service database.

    The organization is created by identity-service with slug 'default-org'.
    """
    session_factory = get_identity_session_factory()
    if not session_factory:
        print("  Warning: IDENTITY_DATABASE_URL not configured")
        return None

    session = session_factory()
    try:
        result = session.execute(
            text("SELECT id FROM organizations WHERE slug = 'default-org' LIMIT 1")
        )
        row = result.fetchone()
        return row[0] if row else None
    except Exception as e:
        print(f"  Error connecting to identity_db: {str(e)}")
        return None
    finally:
        session.close()


def get_admin_user_id():
    """
    Get the admin user ID from identity-service database.

    The admin user is created by identity-service with email 'admin@example.com'.
    """
    session_factory = get_identity_session_factory()
    if not session_factory:
        return None

    session = session_factory()
    try:
        result = session.execute(
            text("SELECT id FROM users WHERE email = 'admin@example.com' LIMIT 1")
        )
        row = result.fetchone()
        return row[0] if row else None
    except Exception as e:
        print(f"  Error fetching admin user from identity_db: {str(e)}")
        return None
    finally:
        session.close()


def seed_database():
    """Seed the database with initial inventory data"""
    db: Session = SessionLocal()

    try:
        print("Starting Core Service database seeding...")

        # Get organization from identity-service database
        org_id = get_organization_id()
        if not org_id:
            print("✗ Default organization not found in identity_db!")
            print("  Please ensure identity-service has seeded first.")
            print("  Skipping core-service seeding...")
            return

        admin_user_id = get_admin_user_id()
        if not admin_user_id:
            print("✗ Admin user not found in identity_db!")
            print("  Please ensure identity-service has seeded first.")
            print("  Skipping core-service seeding...")
            return

        print(f"✓ Found organization in identity_db: {org_id}")
        print(f"✓ Found admin user in identity_db: {admin_user_id}")

        # Check if data already exists (handle case where tables don't exist yet)
        try:
            existing_items = db.query(Item).filter(Item.organization_id == org_id).first()
            if existing_items:
                print("Database already seeded with inventory data. Skipping...")
                return
        except Exception as e:
            # Table doesn't exist yet, continue with seeding
            print(f"  Note: Tables may not exist yet ({str(e)}). Proceeding with seed...")

        # 1. Create Warehouses
        print("\nCreating warehouses...")
        warehouses_data = [
            {
                "name": "Main Warehouse",
                "code": "WH-MAIN",
                "description": "Primary warehouse for storage",
                "warehouse_type": "warehouse",  # Use string value directly
                "address_line1": "123 Industrial Ave",
                "city": "Mumbai",
                "state": "Maharashtra",
                "postal_code": "400001",
                "country": "India",
                "is_active": True,
                "is_default": True,
            },
            {
                "name": "Retail Store",
                "code": "WH-STORE",
                "description": "Retail outlet for direct sales",
                "warehouse_type": "store",  # Use string value directly
                "address_line1": "456 Market Street",
                "city": "Mumbai",
                "state": "Maharashtra",
                "postal_code": "400002",
                "country": "India",
                "is_active": True,
                "is_default": False,
            },
            {
                "name": "Transit Warehouse",
                "code": "WH-TRANSIT",
                "description": "Temporary storage during transit",
                "warehouse_type": "transit",  # Use string value directly
                "is_active": True,
                "is_default": False,
            },
        ]

        warehouses = {}
        for wh_data in warehouses_data:
            warehouse = Warehouse(
                organization_id=org_id,
                created_by=admin_user_id,
                updated_by=admin_user_id,
                **wh_data,
            )
            db.add(warehouse)
            db.flush()
            warehouses[wh_data["code"]] = warehouse
            print(f"✓ Created warehouse: {warehouse.name}")

        # 2. Create Item Groups
        print("\nCreating item groups...")
        item_groups_data = [
            {
                "name": "Raw Materials",
                "code": "RM",
                "description": "Raw materials for production",
                "default_valuation_method": "fifo",  # Use string value directly
                "default_uom": "Kg",
            },
            {
                "name": "Finished Goods",
                "code": "FG",
                "description": "Finished products ready for sale",
                "default_valuation_method": "moving_average",  # Use string value directly
                "default_uom": "Nos",
            },
            {
                "name": "Consumables",
                "code": "CON",
                "description": "Consumable items",
                "default_valuation_method": "fifo",  # Use string value directly
                "default_uom": "Nos",
            },
            {
                "name": "Services",
                "code": "SRV",
                "description": "Service items (non-stock)",
                "default_uom": "Hrs",
            },
        ]

        item_groups = {}
        for group_data in item_groups_data:
            group = ItemGroup(
                organization_id=org_id,
                created_by=admin_user_id,
                updated_by=admin_user_id,
                is_active=True,
                **group_data,
            )
            db.add(group)
            db.flush()
            item_groups[group_data["code"]] = group
            print(f"✓ Created item group: {group.name}")

        # 3. Create Items
        print("\nCreating items...")
        items_data = [
            # Raw Materials
            {
                "item_code": "RM-STEEL-001",
                "item_name": "Steel Sheet (2mm)",
                "description": "High quality steel sheet, 2mm thickness",
                "item_group_id": item_groups["RM"].id,
                "item_type": "stock",  # Use string value directly
                "uom": "Kg",
                "maintain_stock": True,
                "valuation_method": "fifo",  # Use string value directly
                "standard_rate": Decimal("85.00"),
                "valuation_rate": Decimal("75.00"),
                "reorder_level": 100,
                "reorder_qty": 500,
                "min_order_qty": 50,
                "has_batch_no": True,
            },
            {
                "item_code": "RM-PLAST-001",
                "item_name": "ABS Plastic Granules",
                "description": "ABS plastic granules for injection molding",
                "item_group_id": item_groups["RM"].id,
                "item_type": "stock",  # Use string value directly
                "uom": "Kg",
                "maintain_stock": True,
                "valuation_method": "moving_average",  # Use string value directly
                "standard_rate": Decimal("120.00"),
                "valuation_rate": Decimal("100.00"),
                "reorder_level": 200,
                "reorder_qty": 1000,
                "min_order_qty": 100,
            },
            # Finished Goods
            {
                "item_code": "FG-WIDGET-001",
                "item_name": "Widget Pro",
                "description": "Premium widget for industrial use",
                "item_group_id": item_groups["FG"].id,
                "item_type": "stock",  # Use string value directly
                "uom": "Nos",
                "maintain_stock": True,
                "valuation_method": "moving_average",  # Use string value directly
                "standard_rate": Decimal("599.00"),
                "valuation_rate": Decimal("350.00"),
                "reorder_level": 50,
                "reorder_qty": 200,
                "min_order_qty": 10,
                "has_serial_no": True,
                "barcode": "8901234567890",
            },
            {
                "item_code": "FG-GADGET-001",
                "item_name": "Gadget Max",
                "description": "Multi-purpose gadget for home and office",
                "item_group_id": item_groups["FG"].id,
                "item_type": "stock",  # Use string value directly
                "uom": "Nos",
                "maintain_stock": True,
                "valuation_method": "moving_average",  # Use string value directly
                "standard_rate": Decimal("1299.00"),
                "valuation_rate": Decimal("750.00"),
                "reorder_level": 25,
                "reorder_qty": 100,
                "min_order_qty": 5,
                "has_serial_no": True,
                "barcode": "8901234567891",
            },
            # Consumables
            {
                "item_code": "CON-PACK-001",
                "item_name": "Packaging Box (Medium)",
                "description": "Medium sized packaging box",
                "item_group_id": item_groups["CON"].id,
                "item_type": "stock",  # Use string value directly
                "uom": "Nos",
                "maintain_stock": True,
                "valuation_method": "fifo",  # Use string value directly
                "standard_rate": Decimal("25.00"),
                "valuation_rate": Decimal("18.00"),
                "reorder_level": 500,
                "reorder_qty": 2000,
                "min_order_qty": 100,
            },
            # Services
            {
                "item_code": "SRV-INSTALL-001",
                "item_name": "Installation Service",
                "description": "Professional installation service",
                "item_group_id": item_groups["SRV"].id,
                "item_type": "service",  # Use string value directly
                "uom": "Hrs",
                "maintain_stock": False,
                "standard_rate": Decimal("500.00"),
                "valuation_rate": Decimal("0.00"),
            },
            {
                "item_code": "SRV-MAINT-001",
                "item_name": "Annual Maintenance Contract",
                "description": "Yearly maintenance and support",
                "item_group_id": item_groups["SRV"].id,
                "item_type": "service",  # Use string value directly
                "uom": "Nos",
                "maintain_stock": False,
                "standard_rate": Decimal("5000.00"),
                "valuation_rate": Decimal("0.00"),
            },
        ]

        for item_data in items_data:
            item = Item(
                organization_id=org_id,
                created_by=admin_user_id,
                updated_by=admin_user_id,
                status="active",  # Use string value directly
                **item_data,
            )
            db.add(item)
            db.flush()
            print(f"✓ Created item: {item.item_code} - {item.item_name}")

        # Commit all changes
        db.commit()

        print("\n" + "=" * 60)
        print("Core Service database seeding completed successfully!")
        print("=" * 60)
        print("\nSeeded Data Summary:")
        print("-" * 60)
        print(f"  Warehouses: {len(warehouses_data)}")
        print(f"  Item Groups: {len(item_groups_data)}")
        print(f"  Items: {len(items_data)}")
        print("-" * 60)
        print("\nSample Items:")
        print("  Raw Materials: RM-STEEL-001, RM-PLAST-001")
        print("  Finished Goods: FG-WIDGET-001, FG-GADGET-001")
        print("  Consumables: CON-PACK-001")
        print("  Services: SRV-INSTALL-001, SRV-MAINT-001")
        print("-" * 60)

    except Exception as e:
        print(f"\n✗ Error during seeding: {str(e)}")
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    seed_database()
