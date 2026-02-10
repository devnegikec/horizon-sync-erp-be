"""Database seeding script for Stock Management Data

This script seeds:
- Stock Levels (current inventory)
- Stock Movements (audit trail)
- Stock Entries (receipts, issues, transfers)
- Stock Reconciliations (physical count adjustments)
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
        print("Starting Stock Management data seeding...")

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
        items = db.query(Item).filter(Item.organization_id == org_id).all()
        warehouses = (
            db.query(Warehouse).filter(Warehouse.organization_id == org_id).all()
        )

        if not items or not warehouses:
            print("✗ No items or warehouses found. Please run seed_data.py first!")
            return

        print(f"✓ Found {len(items)} items and {len(warehouses)} warehouses")

        # Create dictionaries for easy lookup
        items_dict = {item.item_code: item for item in items}
        warehouses_dict = {wh.code: wh for wh in warehouses}

        # Get stock items only
        stock_items = [item for item in items if item.maintain_stock]
        print(f"✓ Found {len(stock_items)} stock items")

        # Select items for seeding (use first available items)
        if len(stock_items) < 5:
            print(f"✗ Need at least 5 stock items, found only {len(stock_items)}")
            return

        # Select warehouses (prefer warehouse and store types)
        warehouse_list = [
            wh for wh in warehouses if wh.warehouse_type in ["warehouse", "store"]
        ]
        if len(warehouse_list) < 2:
            print(f"✗ Need at least 2 warehouses, found only {len(warehouse_list)}")
            return

        # Use first 5 items and first 2 warehouses
        item1 = stock_items[0]  # Will be used as raw material 1
        item2 = stock_items[1]  # Will be used as raw material 2
        item3 = stock_items[2]  # Will be used as finished good 1
        item4 = stock_items[3]  # Will be used as finished good 2
        item5 = stock_items[4]  # Will be used as consumable

        warehouse1 = warehouse_list[0]  # Main warehouse
        warehouse2 = warehouse_list[1]  # Secondary warehouse/store

        print(
            f"✓ Using items: {item1.item_code}, {item2.item_code}, {item3.item_code}, {item4.item_code}, {item5.item_code}"
        )
        print(f"✓ Using warehouses: {warehouse1.code}, {warehouse2.code}")

        # ===================================================================
        # 1. CREATE STOCK ENTRIES (Material Receipts)
        # ===================================================================
        print("\n1. Creating Stock Entries (Material Receipts)...")

        stock_entries = []
        base_date = datetime.now(UTC) - timedelta(days=30)

        # Stock Entry 1: Material Receipt for Raw Materials
        entry1 = StockEntry(
            organization_id=org_id,
            stock_entry_no="STE-2024-001",
            stock_entry_type="material_receipt",
            to_warehouse_id=warehouse1.id,
            posting_date=base_date,
            posting_time="10:30:00",
            status="submitted",
            remarks="Initial stock receipt - Raw materials",
            total_value=Decimal("50000.00"),
            submitted_at=base_date,
            created_by=admin_user_id,
            updated_by=admin_user_id,
        )
        db.add(entry1)
        db.flush()
        stock_entries.append(entry1)

        # Add items to entry1
        entry1_item1 = StockEntryItem(
            organization_id=org_id,
            stock_entry_id=entry1.id,
            item_id=item1.id,
            target_warehouse_id=warehouse1.id,
            qty=Decimal("500.00"),
            uom=item1.uom or "Kg",
            basic_rate=Decimal("75.00"),
            basic_amount=Decimal("37500.00"),
            valuation_rate=Decimal("75.00"),
            batch_no="BATCH-001",
            description=f"{item1.item_name} initial stock",
        )
        db.add(entry1_item1)

        entry1_item2 = StockEntryItem(
            organization_id=org_id,
            stock_entry_id=entry1.id,
            item_id=item2.id,
            target_warehouse_id=warehouse1.id,
            qty=Decimal("125.00"),
            uom=item2.uom or "Kg",
            basic_rate=Decimal("100.00"),
            basic_amount=Decimal("12500.00"),
            valuation_rate=Decimal("100.00"),
            description=f"{item2.item_name} initial stock",
        )
        db.add(entry1_item2)

        print(f"✓ Created stock entry: {entry1.stock_entry_no}")

        # Stock Entry 2: Material Receipt for Finished Goods
        entry2 = StockEntry(
            organization_id=org_id,
            stock_entry_no="STE-2024-002",
            stock_entry_type="material_receipt",
            to_warehouse_id=warehouse1.id,
            posting_date=base_date + timedelta(days=2),
            posting_time="14:00:00",
            status="submitted",
            remarks="Finished goods from production",
            total_value=Decimal("75000.00"),
            submitted_at=base_date + timedelta(days=2),
            created_by=admin_user_id,
            updated_by=admin_user_id,
        )
        db.add(entry2)
        db.flush()
        stock_entries.append(entry2)

        # Add items to entry2
        entry2_item1 = StockEntryItem(
            organization_id=org_id,
            stock_entry_id=entry2.id,
            item_id=item3.id,
            target_warehouse_id=warehouse1.id,
            qty=Decimal("100.00"),
            uom=item3.uom or "Nos",
            basic_rate=Decimal("350.00"),
            basic_amount=Decimal("35000.00"),
            valuation_rate=Decimal("350.00"),
            serial_nos=["SN-001", "SN-002", "SN-003"],
            description=f"{item3.item_name} units",
        )
        db.add(entry2_item1)

        entry2_item2 = StockEntryItem(
            organization_id=org_id,
            stock_entry_id=entry2.id,
            item_id=item4.id,
            target_warehouse_id=warehouse1.id,
            qty=Decimal("50.00"),
            uom=item4.uom or "Nos",
            basic_rate=Decimal("750.00"),
            basic_amount=Decimal("37500.00"),
            valuation_rate=Decimal("750.00"),
            serial_nos=["SN-004", "SN-005"],
            description=f"{item4.item_name} units",
        )
        db.add(entry2_item2)

        entry2_item3 = StockEntryItem(
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
        db.add(entry2_item3)

        print(f"✓ Created stock entry: {entry2.stock_entry_no}")

        # Stock Entry 3: Material Transfer (Main to Store)
        entry3 = StockEntry(
            organization_id=org_id,
            stock_entry_no="STE-2024-003",
            stock_entry_type="material_transfer",
            from_warehouse_id=warehouses_dict["WH-MAIN"].id,
            to_warehouse_id=warehouses_dict["WH-STORE"].id,
            posting_date=base_date + timedelta(days=5),
            posting_time="11:00:00",
            status="submitted",
            remarks="Transfer to retail store",
            total_value=Decimal("30000.00"),
            submitted_at=base_date + timedelta(days=5),
            created_by=admin_user_id,
            updated_by=admin_user_id,
        )
        db.add(entry3)
        db.flush()
        stock_entries.append(entry3)

        # Add items to entry3
        if "FG-WIDGET-001" in items_dict:
            item6 = StockEntryItem(
                organization_id=org_id,
                stock_entry_id=entry3.id,
                item_id=items_dict["FG-WIDGET-001"].id,
                source_warehouse_id=warehouses_dict["WH-MAIN"].id,
                target_warehouse_id=warehouses_dict["WH-STORE"].id,
                qty=Decimal("30.00"),
                uom="Nos",
                basic_rate=Decimal("350.00"),
                basic_amount=Decimal("10500.00"),
                valuation_rate=Decimal("350.00"),
                description="Transfer to store",
            )
            db.add(item6)

        if "FG-GADGET-001" in items_dict:
            item7 = StockEntryItem(
                organization_id=org_id,
                stock_entry_id=entry3.id,
                item_id=items_dict["FG-GADGET-001"].id,
                source_warehouse_id=warehouses_dict["WH-MAIN"].id,
                target_warehouse_id=warehouses_dict["WH-STORE"].id,
                qty=Decimal("20.00"),
                uom="Nos",
                basic_rate=Decimal("750.00"),
                basic_amount=Decimal("15000.00"),
                valuation_rate=Decimal("750.00"),
                description="Transfer to store",
            )
            db.add(item7)

        print(f"✓ Created stock entry: {entry3.stock_entry_no}")

        # Stock Entry 4: Material Issue
        entry4 = StockEntry(
            organization_id=org_id,
            stock_entry_no="STE-2024-004",
            stock_entry_type="material_issue",
            from_warehouse_id=warehouses_dict["WH-STORE"].id,
            posting_date=base_date + timedelta(days=10),
            posting_time="15:30:00",
            status="submitted",
            remarks="Sales from retail store",
            total_value=Decimal("8500.00"),
            submitted_at=base_date + timedelta(days=10),
            created_by=admin_user_id,
            updated_by=admin_user_id,
        )
        db.add(entry4)
        db.flush()
        stock_entries.append(entry4)

        # Add items to entry4
        if "FG-WIDGET-001" in items_dict:
            item8 = StockEntryItem(
                organization_id=org_id,
                stock_entry_id=entry4.id,
                item_id=items_dict["FG-WIDGET-001"].id,
                source_warehouse_id=warehouses_dict["WH-STORE"].id,
                qty=Decimal("10.00"),
                uom="Nos",
                basic_rate=Decimal("350.00"),
                basic_amount=Decimal("3500.00"),
                valuation_rate=Decimal("350.00"),
                description="Sold to customer",
            )
            db.add(item8)

        if "FG-GADGET-001" in items_dict:
            item9 = StockEntryItem(
                organization_id=org_id,
                stock_entry_id=entry4.id,
                item_id=items_dict["FG-GADGET-001"].id,
                source_warehouse_id=warehouses_dict["WH-STORE"].id,
                qty=Decimal("5.00"),
                uom="Nos",
                basic_rate=Decimal("750.00"),
                basic_amount=Decimal("3750.00"),
                valuation_rate=Decimal("750.00"),
                description="Sold to customer",
            )
            db.add(item9)

        print(f"✓ Created stock entry: {entry4.stock_entry_no}")

        # ===================================================================
        # 2. CREATE STOCK MOVEMENTS (Audit Trail)
        # ===================================================================
        print("\n2. Creating Stock Movements...")

        movements_count = 0

        # Movement 1: Receipt of Steel
        if "RM-STEEL-001" in items_dict:
            movement1 = StockMovement(
                organization_id=org_id,
                product_id=items_dict["RM-STEEL-001"].id,
                warehouse_id=warehouses_dict["WH-MAIN"].id,
                movement_type="in",
                quantity=500,
                unit_cost=Decimal("75.00"),
                reference_type="stock_entry",
                reference_id=entry1.id,
                notes="Initial receipt - Steel sheets",
                performed_by=admin_user_id,
                performed_at=base_date,
            )
            db.add(movement1)
            movements_count += 1

        # Movement 2: Receipt of Plastic
        if "RM-PLAST-001" in items_dict:
            movement2 = StockMovement(
                organization_id=org_id,
                product_id=items_dict["RM-PLAST-001"].id,
                warehouse_id=warehouses_dict["WH-MAIN"].id,
                movement_type="in",
                quantity=125,
                unit_cost=Decimal("100.00"),
                reference_type="stock_entry",
                reference_id=entry1.id,
                notes="Initial receipt - ABS plastic",
                performed_by=admin_user_id,
                performed_at=base_date,
            )
            db.add(movement2)
            movements_count += 1

        # Movement 3: Receipt of Widgets
        if "FG-WIDGET-001" in items_dict:
            movement3 = StockMovement(
                organization_id=org_id,
                product_id=items_dict["FG-WIDGET-001"].id,
                warehouse_id=warehouses_dict["WH-MAIN"].id,
                movement_type="in",
                quantity=100,
                unit_cost=Decimal("350.00"),
                reference_type="stock_entry",
                reference_id=entry2.id,
                notes="Production receipt - Widgets",
                performed_by=admin_user_id,
                performed_at=base_date + timedelta(days=2),
            )
            db.add(movement3)
            movements_count += 1

        # Movement 4: Receipt of Gadgets
        if "FG-GADGET-001" in items_dict:
            movement4 = StockMovement(
                organization_id=org_id,
                product_id=items_dict["FG-GADGET-001"].id,
                warehouse_id=warehouses_dict["WH-MAIN"].id,
                movement_type="in",
                quantity=50,
                unit_cost=Decimal("750.00"),
                reference_type="stock_entry",
                reference_id=entry2.id,
                notes="Production receipt - Gadgets",
                performed_by=admin_user_id,
                performed_at=base_date + timedelta(days=2),
            )
            db.add(movement4)
            movements_count += 1

        # Movement 5: Receipt of Packaging
        if "CON-PACK-001" in items_dict:
            movement5 = StockMovement(
                organization_id=org_id,
                product_id=items_dict["CON-PACK-001"].id,
                warehouse_id=warehouses_dict["WH-MAIN"].id,
                movement_type="in",
                quantity=1000,
                unit_cost=Decimal("18.00"),
                reference_type="stock_entry",
                reference_id=entry2.id,
                notes="Receipt - Packaging boxes",
                performed_by=admin_user_id,
                performed_at=base_date + timedelta(days=2),
            )
            db.add(movement5)
            movements_count += 1

        # Movement 6-7: Transfer OUT from Main (Widgets)
        if "FG-WIDGET-001" in items_dict:
            movement6 = StockMovement(
                organization_id=org_id,
                product_id=items_dict["FG-WIDGET-001"].id,
                warehouse_id=warehouses_dict["WH-MAIN"].id,
                movement_type="out",
                quantity=30,
                unit_cost=Decimal("350.00"),
                reference_type="stock_entry",
                reference_id=entry3.id,
                notes="Transfer to retail store",
                performed_by=admin_user_id,
                performed_at=base_date + timedelta(days=5),
            )
            db.add(movement6)
            movements_count += 1

            # Transfer IN to Store
            movement7 = StockMovement(
                organization_id=org_id,
                product_id=items_dict["FG-WIDGET-001"].id,
                warehouse_id=warehouses_dict["WH-STORE"].id,
                movement_type="in",
                quantity=30,
                unit_cost=Decimal("350.00"),
                reference_type="stock_entry",
                reference_id=entry3.id,
                notes="Received from main warehouse",
                performed_by=admin_user_id,
                performed_at=base_date + timedelta(days=5),
            )
            db.add(movement7)
            movements_count += 1

        # Movement 8-9: Transfer OUT from Main (Gadgets)
        if "FG-GADGET-001" in items_dict:
            movement8 = StockMovement(
                organization_id=org_id,
                product_id=items_dict["FG-GADGET-001"].id,
                warehouse_id=warehouses_dict["WH-MAIN"].id,
                movement_type="out",
                quantity=20,
                unit_cost=Decimal("750.00"),
                reference_type="stock_entry",
                reference_id=entry3.id,
                notes="Transfer to retail store",
                performed_by=admin_user_id,
                performed_at=base_date + timedelta(days=5),
            )
            db.add(movement8)
            movements_count += 1

            # Transfer IN to Store
            movement9 = StockMovement(
                organization_id=org_id,
                product_id=items_dict["FG-GADGET-001"].id,
                warehouse_id=warehouses_dict["WH-STORE"].id,
                movement_type="in",
                quantity=20,
                unit_cost=Decimal("750.00"),
                reference_type="stock_entry",
                reference_id=entry3.id,
                notes="Received from main warehouse",
                performed_by=admin_user_id,
                performed_at=base_date + timedelta(days=5),
            )
            db.add(movement9)
            movements_count += 1

        # Movement 10-11: Sales from Store
        if "FG-WIDGET-001" in items_dict:
            movement10 = StockMovement(
                organization_id=org_id,
                product_id=items_dict["FG-WIDGET-001"].id,
                warehouse_id=warehouses_dict["WH-STORE"].id,
                movement_type="out",
                quantity=10,
                unit_cost=Decimal("350.00"),
                reference_type="stock_entry",
                reference_id=entry4.id,
                notes="Sold to customer",
                performed_by=admin_user_id,
                performed_at=base_date + timedelta(days=10),
            )
            db.add(movement10)
            movements_count += 1

        if "FG-GADGET-001" in items_dict:
            movement11 = StockMovement(
                organization_id=org_id,
                product_id=items_dict["FG-GADGET-001"].id,
                warehouse_id=warehouses_dict["WH-STORE"].id,
                movement_type="out",
                quantity=5,
                unit_cost=Decimal("750.00"),
                reference_type="stock_entry",
                reference_id=entry4.id,
                notes="Sold to customer",
                performed_by=admin_user_id,
                performed_at=base_date + timedelta(days=10),
            )
            db.add(movement11)
            movements_count += 1

        print(f"✓ Created {movements_count} stock movements")

        # ===================================================================
        # 3. CREATE STOCK LEVELS (Current Inventory)
        # ===================================================================
        print("\n3. Creating Stock Levels...")

        stock_levels_data = [
            # Main Warehouse
            {
                "product_code": "RM-STEEL-001",
                "warehouse_code": "WH-MAIN",
                "quantity_on_hand": 500,
                "quantity_reserved": 50,
                "quantity_available": 450,
            },
            {
                "product_code": "RM-PLAST-001",
                "warehouse_code": "WH-MAIN",
                "quantity_on_hand": 125,
                "quantity_reserved": 25,
                "quantity_available": 100,
            },
            {
                "product_code": "FG-WIDGET-001",
                "warehouse_code": "WH-MAIN",
                "quantity_on_hand": 70,  # 100 - 30 transferred
                "quantity_reserved": 10,
                "quantity_available": 60,
            },
            {
                "product_code": "FG-GADGET-001",
                "warehouse_code": "WH-MAIN",
                "quantity_on_hand": 30,  # 50 - 20 transferred
                "quantity_reserved": 5,
                "quantity_available": 25,
            },
            {
                "product_code": "CON-PACK-001",
                "warehouse_code": "WH-MAIN",
                "quantity_on_hand": 1000,
                "quantity_reserved": 100,
                "quantity_available": 900,
            },
            # Retail Store
            {
                "product_code": "FG-WIDGET-001",
                "warehouse_code": "WH-STORE",
                "quantity_on_hand": 20,  # 30 - 10 sold
                "quantity_reserved": 0,
                "quantity_available": 20,
            },
            {
                "product_code": "FG-GADGET-001",
                "warehouse_code": "WH-STORE",
                "quantity_on_hand": 15,  # 20 - 5 sold
                "quantity_reserved": 0,
                "quantity_available": 15,
            },
        ]

        levels_count = 0
        for level_data in stock_levels_data:
            if (
                level_data["product_code"] in items_dict
                and level_data["warehouse_code"] in warehouses_dict
            ):
                stock_level = StockLevel(
                    organization_id=org_id,
                    product_id=items_dict[level_data["product_code"]].id,
                    warehouse_id=warehouses_dict[level_data["warehouse_code"]].id,
                    quantity_on_hand=level_data["quantity_on_hand"],
                    quantity_reserved=level_data["quantity_reserved"],
                    quantity_available=level_data["quantity_available"],
                    last_counted_at=datetime.now(UTC) - timedelta(days=1),
                )
                db.add(stock_level)
                levels_count += 1

        print(f"✓ Created {levels_count} stock levels")

        # ===================================================================
        # 4. CREATE STOCK RECONCILIATIONS (Physical Count Adjustments)
        # ===================================================================
        print("\n4. Creating Stock Reconciliations...")

        # Reconciliation 1: Physical count adjustment
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

        # Add reconciliation items
        recon_items_count = 0

        # Reconciliation item 1: Widget adjustment in Main Warehouse
        if "FG-WIDGET-001" in items_dict:
            recon_item1 = StockReconciliationItem(
                organization_id=org_id,
                reconciliation_id=recon1.id,
                item_id=items_dict["FG-WIDGET-001"].id,
                warehouse_id=warehouses_dict["WH-MAIN"].id,
                current_qty=Decimal("70.00"),
                qty=Decimal("68.00"),  # Found 2 less during count
                qty_difference=Decimal("-2.00"),
                current_valuation_rate=Decimal("350.00"),
                valuation_rate=Decimal("350.00"),
            )
            db.add(recon_item1)
            recon_items_count += 1

        # Reconciliation item 2: Packaging adjustment
        if "CON-PACK-001" in items_dict:
            recon_item2 = StockReconciliationItem(
                organization_id=org_id,
                reconciliation_id=recon1.id,
                item_id=items_dict["CON-PACK-001"].id,
                warehouse_id=warehouses_dict["WH-MAIN"].id,
                current_qty=Decimal("1000.00"),
                qty=Decimal("995.00"),  # Found 5 less (damaged)
                qty_difference=Decimal("-5.00"),
                current_valuation_rate=Decimal("18.00"),
                valuation_rate=Decimal("18.00"),
            )
            db.add(recon_item2)
            recon_items_count += 1

        # Reconciliation item 3: Gadget adjustment in Store
        if "FG-GADGET-001" in items_dict:
            recon_item3 = StockReconciliationItem(
                organization_id=org_id,
                reconciliation_id=recon1.id,
                item_id=items_dict["FG-GADGET-001"].id,
                warehouse_id=warehouses_dict["WH-STORE"].id,
                current_qty=Decimal("15.00"),
                qty=Decimal("16.00"),  # Found 1 extra (miscount earlier)
                qty_difference=Decimal("1.00"),
                current_valuation_rate=Decimal("750.00"),
                valuation_rate=Decimal("750.00"),
            )
            db.add(recon_item3)
            recon_items_count += 1

        print(
            f"✓ Created reconciliation: {recon1.reconciliation_no} with {recon_items_count} items"
        )

        # Reconciliation 2: Damage adjustment
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

        # Reconciliation item for damaged steel
        if "RM-STEEL-001" in items_dict:
            recon_item4 = StockReconciliationItem(
                organization_id=org_id,
                reconciliation_id=recon2.id,
                item_id=items_dict["RM-STEEL-001"].id,
                warehouse_id=warehouses_dict["WH-MAIN"].id,
                current_qty=Decimal("500.00"),
                qty=Decimal("495.00"),  # 5 kg damaged due to rust
                qty_difference=Decimal("-5.00"),
                current_valuation_rate=Decimal("75.00"),
                valuation_rate=Decimal("75.00"),
            )
            db.add(recon_item4)
            recon2_items_count += 1

        print(
            f"✓ Created reconciliation: {recon2.reconciliation_no} with {recon2_items_count} items"
        )

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
        print("\nStock Entry Types:")
        print("  - Material Receipt (STE-2024-001, STE-2024-002)")
        print("  - Material Transfer (STE-2024-003)")
        print("  - Material Issue (STE-2024-004)")
        print("\nStock Levels by Warehouse:")
        print("  Main Warehouse:")
        print("    - RM-STEEL-001: 500 Kg (450 available)")
        print("    - RM-PLAST-001: 125 Kg (100 available)")
        print("    - FG-WIDGET-001: 70 Nos (60 available)")
        print("    - FG-GADGET-001: 30 Nos (25 available)")
        print("    - CON-PACK-001: 1000 Nos (900 available)")
        print("  Retail Store:")
        print("    - FG-WIDGET-001: 20 Nos (20 available)")
        print("    - FG-GADGET-001: 15 Nos (15 available)")
        print("\nReconciliations:")
        print("  - RECON-2024-001: Monthly physical count")
        print("  - RECON-2024-002: Damage write-off")
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
