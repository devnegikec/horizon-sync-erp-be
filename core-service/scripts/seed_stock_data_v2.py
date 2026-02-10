"""Database seeding script for Stock Management Data - Version 2

This script seeds stock data using actual items and warehouses from the database.
It dynamically selects available items and warehouses instead of hardcoding specific codes.
"""

import os
import sys
from datetime import UTC, datetime, timedelta
from decimal import Decimal

from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from app.config import settings  # noqa: E402
from app.database import SessionLocal  # noqa: E402
from app.models import (  # noqa: E402
    Item,
    StockEntry,
    StockEntryItem,
    StockLevel,
    StockMovement,
    StockReconciliation,
    StockReconciliationItem,
    Warehouse,
)


def get_identity_session_factory():
    """Create a session factory for the identity database."""
    identity_db_url = settings.identity_database_url
    if not identity_db_url:
        return None
    engine = create_engine(identity_db_url)
    return sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_organization_id():
    """Get the default organization ID from identity-service database."""
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
    """Get the admin user ID from identity-service database."""
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


def seed_stock_data():
    """Seed the database with stock management data"""
    db: Session = SessionLocal()

    try:
        print("Starting Stock Management data seeding (V2)...")

        # Get organization and user
        org_id = get_organization_id()
        if not org_id:
            print("✗ Default organization not found!")
            return

        admin_user_id = get_admin_user_id()
        if not admin_user_id:
            print("✗ Admin user not found!")
            return

        print(f"✓ Found organization: {org_id}")
        print(f"✓ Found admin user: {admin_user_id}")

        # Check if stock data already exists
        existing_stock = (
            db.query(StockLevel).filter(StockLevel.organization_id == org_id).first()
        )
        if existing_stock:
            print("Stock data already seeded. Skipping...")
            return

        # Get existing items and warehouses
        items = (
            db.query(Item)
            .filter(
                Item.organization_id == org_id,
                Item.maintain_stock == True,  # noqa: E712
            )
            .limit(10)
            .all()
        )

        warehouses = (
            db.query(Warehouse)
            .filter(Warehouse.organization_id == org_id)
            .limit(5)
            .all()
        )

        if not items or len(items) < 5:
            print(f"✗ Need at least 5 stock items, found only {len(items)}")
            return

        if not warehouses or len(warehouses) < 2:
            print(f"✗ Need at least 2 warehouses, found only {len(warehouses)}")
            return

        print(f"✓ Found {len(items)} items and {len(warehouses)} warehouses")

        # Select items and warehouses
        item1, item2, item3, item4, item5 = (
            items[0],
            items[1],
            items[2],
            items[3],
            items[4],
        )
        warehouse1, warehouse2 = warehouses[0], warehouses[1]

        print(
            f"✓ Using items: {item1.item_code}, {item2.item_code}, {item3.item_code}, {item4.item_code}, {item5.item_code}"
        )
        print(
            f"✓ Using warehouses: {warehouse1.code} ({warehouse1.name}), {warehouse2.code} ({warehouse2.name})"
        )

        base_date = datetime.now(UTC) - timedelta(days=30)

        # ===================================================================
        # 1. CREATE STOCK ENTRIES
        # ===================================================================
        print("\n1. Creating Stock Entries...")

        stock_entries = []

        # Entry 1: Material Receipt
        entry1 = StockEntry(
            organization_id=org_id,
            stock_entry_no="STE-2024-001",
            stock_entry_type="material_receipt",
            to_warehouse_id=warehouse1.id,
            posting_date=base_date,
            posting_time="10:30:00",
            status="submitted",
            remarks="Initial stock receipt",
            total_value=Decimal("50000.00"),
            submitted_at=base_date,
            created_by=admin_user_id,
            updated_by=admin_user_id,
        )
        db.add(entry1)
        db.flush()
        stock_entries.append(entry1)

        # Add items to entry1
        db.add(
            StockEntryItem(
                organization_id=org_id,
                stock_entry_id=entry1.id,
                item_id=item1.id,
                target_warehouse_id=warehouse1.id,
                qty=Decimal("500.00"),
                uom=item1.uom or "Nos",
                basic_rate=Decimal("75.00"),
                basic_amount=Decimal("37500.00"),
                valuation_rate=Decimal("75.00"),
                description=f"{item1.item_name} - initial stock",
            )
        )

        db.add(
            StockEntryItem(
                organization_id=org_id,
                stock_entry_id=entry1.id,
                item_id=item2.id,
                target_warehouse_id=warehouse1.id,
                qty=Decimal("125.00"),
                uom=item2.uom or "Nos",
                basic_rate=Decimal("100.00"),
                basic_amount=Decimal("12500.00"),
                valuation_rate=Decimal("100.00"),
                description=f"{item2.item_name} - initial stock",
            )
        )

        print(f"✓ Created: {entry1.stock_entry_no}")

        # Entry 2: Material Receipt
        entry2 = StockEntry(
            organization_id=org_id,
            stock_entry_no="STE-2024-002",
            stock_entry_type="material_receipt",
            to_warehouse_id=warehouse1.id,
            posting_date=base_date + timedelta(days=2),
            posting_time="14:00:00",
            status="submitted",
            remarks="Production receipt",
            total_value=Decimal("90500.00"),
            submitted_at=base_date + timedelta(days=2),
            created_by=admin_user_id,
            updated_by=admin_user_id,
        )
        db.add(entry2)
        db.flush()
        stock_entries.append(entry2)

        db.add(
            StockEntryItem(
                organization_id=org_id,
                stock_entry_id=entry2.id,
                item_id=item3.id,
                target_warehouse_id=warehouse1.id,
                qty=Decimal("100.00"),
                uom=item3.uom or "Nos",
                basic_rate=Decimal("350.00"),
                basic_amount=Decimal("35000.00"),
                valuation_rate=Decimal("350.00"),
                description=f"{item3.item_name} units",
            )
        )

        db.add(
            StockEntryItem(
                organization_id=org_id,
                stock_entry_id=entry2.id,
                item_id=item4.id,
                target_warehouse_id=warehouse1.id,
                qty=Decimal("50.00"),
                uom=item4.uom or "Nos",
                basic_rate=Decimal("750.00"),
                basic_amount=Decimal("37500.00"),
                valuation_rate=Decimal("750.00"),
                description=f"{item4.item_name} units",
            )
        )

        db.add(
            StockEntryItem(
                organization_id=org_id,
                stock_entry_id=entry2.id,
                item_id=item5.id,
                target_warehouse_id=warehouse1.id,
                qty=Decimal("1000.00"),
                uom=item5.uom or "Nos",
                basic_rate=Decimal("18.00"),
                basic_amount=Decimal("18000.00"),
                valuation_rate=Decimal("18.00"),
                description=f"{item5.item_name} units",
            )
        )

        print(f"✓ Created: {entry2.stock_entry_no}")

        # Entry 3: Material Transfer
        entry3 = StockEntry(
            organization_id=org_id,
            stock_entry_no="STE-2024-003",
            stock_entry_type="material_transfer",
            from_warehouse_id=warehouse1.id,
            to_warehouse_id=warehouse2.id,
            posting_date=base_date + timedelta(days=5),
            posting_time="11:00:00",
            status="submitted",
            remarks=f"Transfer from {warehouse1.name} to {warehouse2.name}",
            total_value=Decimal("25500.00"),
            submitted_at=base_date + timedelta(days=5),
            created_by=admin_user_id,
            updated_by=admin_user_id,
        )
        db.add(entry3)
        db.flush()
        stock_entries.append(entry3)

        db.add(
            StockEntryItem(
                organization_id=org_id,
                stock_entry_id=entry3.id,
                item_id=item3.id,
                source_warehouse_id=warehouse1.id,
                target_warehouse_id=warehouse2.id,
                qty=Decimal("30.00"),
                uom=item3.uom or "Nos",
                basic_rate=Decimal("350.00"),
                basic_amount=Decimal("10500.00"),
                valuation_rate=Decimal("350.00"),
                description="Transfer",
            )
        )

        db.add(
            StockEntryItem(
                organization_id=org_id,
                stock_entry_id=entry3.id,
                item_id=item4.id,
                source_warehouse_id=warehouse1.id,
                target_warehouse_id=warehouse2.id,
                qty=Decimal("20.00"),
                uom=item4.uom or "Nos",
                basic_rate=Decimal("750.00"),
                basic_amount=Decimal("15000.00"),
                valuation_rate=Decimal("750.00"),
                description="Transfer",
            )
        )

        print(f"✓ Created: {entry3.stock_entry_no}")

        # Entry 4: Material Issue
        entry4 = StockEntry(
            organization_id=org_id,
            stock_entry_no="STE-2024-004",
            stock_entry_type="material_issue",
            from_warehouse_id=warehouse2.id,
            posting_date=base_date + timedelta(days=10),
            posting_time="15:30:00",
            status="submitted",
            remarks="Sales/Issue",
            total_value=Decimal("7250.00"),
            submitted_at=base_date + timedelta(days=10),
            created_by=admin_user_id,
            updated_by=admin_user_id,
        )
        db.add(entry4)
        db.flush()
        stock_entries.append(entry4)

        db.add(
            StockEntryItem(
                organization_id=org_id,
                stock_entry_id=entry4.id,
                item_id=item3.id,
                source_warehouse_id=warehouse2.id,
                qty=Decimal("10.00"),
                uom=item3.uom or "Nos",
                basic_rate=Decimal("350.00"),
                basic_amount=Decimal("3500.00"),
                valuation_rate=Decimal("350.00"),
                description="Sold",
            )
        )

        db.add(
            StockEntryItem(
                organization_id=org_id,
                stock_entry_id=entry4.id,
                item_id=item4.id,
                source_warehouse_id=warehouse2.id,
                qty=Decimal("5.00"),
                uom=item4.uom or "Nos",
                basic_rate=Decimal("750.00"),
                basic_amount=Decimal("3750.00"),
                valuation_rate=Decimal("750.00"),
                description="Sold",
            )
        )

        print(f"✓ Created: {entry4.stock_entry_no}")

        # ===================================================================
        # 2. CREATE STOCK MOVEMENTS
        # ===================================================================
        print("\n2. Creating Stock Movements...")

        movements_count = 0

        # Movements for entry1
        for item, qty, cost in [(item1, 500, 75), (item2, 125, 100)]:
            db.add(
                StockMovement(
                    organization_id=org_id,
                    product_id=item.id,
                    warehouse_id=warehouse1.id,
                    movement_type="in",
                    quantity=qty,
                    unit_cost=Decimal(str(cost)),
                    reference_type="stock_entry",
                    reference_id=entry1.id,
                    notes=f"Receipt - {item.item_name}",
                    performed_by=admin_user_id,
                    performed_at=base_date,
                )
            )
            movements_count += 1

        # Movements for entry2
        for item, qty, cost in [(item3, 100, 350), (item4, 50, 750), (item5, 1000, 18)]:
            db.add(
                StockMovement(
                    organization_id=org_id,
                    product_id=item.id,
                    warehouse_id=warehouse1.id,
                    movement_type="in",
                    quantity=qty,
                    unit_cost=Decimal(str(cost)),
                    reference_type="stock_entry",
                    reference_id=entry2.id,
                    notes=f"Receipt - {item.item_name}",
                    performed_by=admin_user_id,
                    performed_at=base_date + timedelta(days=2),
                )
            )
            movements_count += 1

        # Movements for entry3 (transfer OUT and IN)
        for item, qty, cost in [(item3, 30, 350), (item4, 20, 750)]:
            # OUT from warehouse1
            db.add(
                StockMovement(
                    organization_id=org_id,
                    product_id=item.id,
                    warehouse_id=warehouse1.id,
                    movement_type="out",
                    quantity=qty,
                    unit_cost=Decimal(str(cost)),
                    reference_type="stock_entry",
                    reference_id=entry3.id,
                    notes=f"Transfer out - {item.item_name}",
                    performed_by=admin_user_id,
                    performed_at=base_date + timedelta(days=5),
                )
            )
            movements_count += 1

            # IN to warehouse2
            db.add(
                StockMovement(
                    organization_id=org_id,
                    product_id=item.id,
                    warehouse_id=warehouse2.id,
                    movement_type="in",
                    quantity=qty,
                    unit_cost=Decimal(str(cost)),
                    reference_type="stock_entry",
                    reference_id=entry3.id,
                    notes=f"Transfer in - {item.item_name}",
                    performed_by=admin_user_id,
                    performed_at=base_date + timedelta(days=5),
                )
            )
            movements_count += 1

        # Movements for entry4 (issue)
        for item, qty, cost in [(item3, 10, 350), (item4, 5, 750)]:
            db.add(
                StockMovement(
                    organization_id=org_id,
                    product_id=item.id,
                    warehouse_id=warehouse2.id,
                    movement_type="out",
                    quantity=qty,
                    unit_cost=Decimal(str(cost)),
                    reference_type="stock_entry",
                    reference_id=entry4.id,
                    notes=f"Issue/Sale - {item.item_name}",
                    performed_by=admin_user_id,
                    performed_at=base_date + timedelta(days=10),
                )
            )
            movements_count += 1

        print(f"✓ Created {movements_count} stock movements")

        # ===================================================================
        # 3. CREATE STOCK LEVELS
        # ===================================================================
        print("\n3. Creating Stock Levels...")

        stock_levels_data = [
            # Warehouse 1
            (item1, warehouse1, 500, 50, 450),
            (item2, warehouse1, 125, 25, 100),
            (item3, warehouse1, 70, 10, 60),  # 100 - 30 transferred
            (item4, warehouse1, 30, 5, 25),  # 50 - 20 transferred
            (item5, warehouse1, 1000, 100, 900),
            # Warehouse 2
            (item3, warehouse2, 20, 0, 20),  # 30 - 10 sold
            (item4, warehouse2, 15, 0, 15),  # 20 - 5 sold
        ]

        levels_count = 0
        for item, warehouse, on_hand, reserved, available in stock_levels_data:
            db.add(
                StockLevel(
                    organization_id=org_id,
                    product_id=item.id,
                    warehouse_id=warehouse.id,
                    quantity_on_hand=on_hand,
                    quantity_reserved=reserved,
                    quantity_available=available,
                    last_counted_at=datetime.now(UTC) - timedelta(days=1),
                )
            )
            levels_count += 1

        print(f"✓ Created {levels_count} stock levels")

        # ===================================================================
        # 4. CREATE STOCK RECONCILIATIONS
        # ===================================================================
        print("\n4. Creating Stock Reconciliations...")

        # Reconciliation 1
        recon1 = StockReconciliation(
            organization_id=org_id,
            reconciliation_no="RECON-2024-001",
            purpose="Physical Stock Count - Monthly",
            posting_date=base_date + timedelta(days=15),
            posting_time="16:00:00",
            status="submitted",
            remarks="Monthly physical stock verification",
            submitted_at=base_date + timedelta(days=15),
            created_by=admin_user_id,
            updated_by=admin_user_id,
        )
        db.add(recon1)
        db.flush()

        recon_items_count = 0

        # Reconciliation items
        db.add(
            StockReconciliationItem(
                organization_id=org_id,
                reconciliation_id=recon1.id,
                item_id=item3.id,
                warehouse_id=warehouse1.id,
                current_qty=Decimal("70.00"),
                qty=Decimal("68.00"),
                qty_difference=Decimal("-2.00"),
                current_valuation_rate=Decimal("350.00"),
                valuation_rate=Decimal("350.00"),
            )
        )
        recon_items_count += 1

        db.add(
            StockReconciliationItem(
                organization_id=org_id,
                reconciliation_id=recon1.id,
                item_id=item5.id,
                warehouse_id=warehouse1.id,
                current_qty=Decimal("1000.00"),
                qty=Decimal("995.00"),
                qty_difference=Decimal("-5.00"),
                current_valuation_rate=Decimal("18.00"),
                valuation_rate=Decimal("18.00"),
            )
        )
        recon_items_count += 1

        db.add(
            StockReconciliationItem(
                organization_id=org_id,
                reconciliation_id=recon1.id,
                item_id=item4.id,
                warehouse_id=warehouse2.id,
                current_qty=Decimal("15.00"),
                qty=Decimal("16.00"),
                qty_difference=Decimal("1.00"),
                current_valuation_rate=Decimal("750.00"),
                valuation_rate=Decimal("750.00"),
            )
        )
        recon_items_count += 1

        print(f"✓ Created: {recon1.reconciliation_no} with {recon_items_count} items")

        # Reconciliation 2
        recon2 = StockReconciliation(
            organization_id=org_id,
            reconciliation_no="RECON-2024-002",
            purpose="Damage Write-off",
            posting_date=base_date + timedelta(days=20),
            posting_time="10:30:00",
            status="submitted",
            remarks="Write-off damaged items",
            submitted_at=base_date + timedelta(days=20),
            created_by=admin_user_id,
            updated_by=admin_user_id,
        )
        db.add(recon2)
        db.flush()

        recon2_items_count = 0

        db.add(
            StockReconciliationItem(
                organization_id=org_id,
                reconciliation_id=recon2.id,
                item_id=item1.id,
                warehouse_id=warehouse1.id,
                current_qty=Decimal("500.00"),
                qty=Decimal("495.00"),
                qty_difference=Decimal("-5.00"),
                current_valuation_rate=Decimal("75.00"),
                valuation_rate=Decimal("75.00"),
            )
        )
        recon2_items_count += 1

        print(f"✓ Created: {recon2.reconciliation_no} with {recon2_items_count} items")

        # Commit all changes
        db.commit()

        print("\n" + "=" * 70)
        print("Stock Management data seeding completed successfully!")
        print("=" * 70)
        print("\nSeeded Data Summary:")
        print("-" * 70)
        print(f"  Stock Entries: {len(stock_entries)}")
        print(f"  Stock Movements: {movements_count}")
        print(f"  Stock Levels: {levels_count}")
        print("  Stock Reconciliations: 2")
        print(f"  Reconciliation Items: {recon_items_count + recon2_items_count}")
        print("-" * 70)
        print("\nItems Used:")
        for i, item in enumerate([item1, item2, item3, item4, item5], 1):
            print(f"  {i}. {item.item_code} - {item.item_name}")
        print("\nWarehouses Used:")
        print(f"  1. {warehouse1.code} - {warehouse1.name}")
        print(f"  2. {warehouse2.code} - {warehouse2.name}")
        print("-" * 70)

    except Exception as e:
        print(f"\n✗ Error during seeding: {str(e)}")
        import traceback

        traceback.print_exc()
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    seed_stock_data()
