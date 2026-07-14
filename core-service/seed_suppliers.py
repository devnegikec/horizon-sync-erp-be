"""Seed suppliers data for testing"""

import uuid
from datetime import UTC, datetime

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.models.base import SupplierStatus
from app.models.supplier import Supplier

# Database URL
DATABASE_URL = "postgresql://horizon_user:horizon_pass@localhost:5432/core_db"

# Organization ID
ORG_ID = uuid.UUID("b1f71de1-0a19-424e-9580-1d3f871c5b1f")

# Supplier data
suppliers_data = [
    {
        "supplier_name": "Acme Corporation1",
        "supplier_code": "ACME001",
        "email": "contact@acmecorp1.com",
        "phone": "+1-555-0101",
        "address_line1": "123 Industrial Blvd",
        "city": "New York",
        "country": "USA",
        "payment_terms": 30,
    },
    {
        "supplier_name": "Global Suppliers1",
        "supplier_code": "GLOBAL001",
        "email": "info@globalsuppliers1.com",
        "phone": "+1-555-0102",
        "address_line1": "456 Trade Street",
        "city": "Los Angeles",
        "country": "USA",
        "payment_terms": 45,
    },
    {
        "supplier_name": "Tech Parts Ltd",
        "supplier_code": "TECH001",
        "email": "sales@techparts.com",
        "phone": "+1-555-0103",
        "address_line1": "789 Tech Avenue",
        "city": "San Francisco",
        "country": "USA",
        "payment_terms": 30,
    },
    {
        "supplier_name": "Industrial Materials Co",
        "supplier_code": "INDMAT001",
        "email": "orders@indmaterials.com",
        "phone": "+1-555-0104",
        "address_line1": "321 Materials Way",
        "city": "Chicago",
        "country": "USA",
        "payment_terms": 60,
    },
]


def seed_suppliers():
    """Insert supplier seed data"""
    engine = create_engine(DATABASE_URL)
    SessionLocal = sessionmaker(bind=engine)
    db = SessionLocal()

    try:
        for supplier_data in suppliers_data:
            # Check if supplier already exists
            existing = (
                db.query(Supplier)
                .filter(
                    Supplier.organization_id == ORG_ID,
                    Supplier.supplier_code == supplier_data["supplier_code"],
                )
                .first()
            )

            if existing:
                print(
                    f"Supplier {supplier_data['supplier_code']} already exists, skipping..."
                )
                continue

            # Create new supplier
            supplier = Supplier(
                id=uuid.uuid4(),
                organization_id=ORG_ID,
                supplier_name=supplier_data["supplier_name"],
                supplier_code=supplier_data["supplier_code"],
                email=supplier_data["email"],
                phone=supplier_data["phone"],
                address_line1=supplier_data["address_line1"],
                city=supplier_data["city"],
                country=supplier_data["country"],
                status=SupplierStatus.ACTIVE,
                payment_terms=supplier_data["payment_terms"],
                created_at=datetime.now(UTC),
                updated_at=datetime.now(UTC),
            )

            db.add(supplier)
            print(
                f"Created supplier: {supplier.supplier_name} ({supplier.supplier_code})"
            )

        db.commit()
        print("\n✓ Supplier seed data inserted successfully!")

        # Display inserted suppliers
        suppliers = (
            db.query(Supplier)
            .filter(Supplier.organization_id == ORG_ID)
            .order_by(Supplier.supplier_code)
            .all()
        )

        print(f"\nTotal suppliers for organization: {len(suppliers)}")
        for s in suppliers:
            print(f"  - {s.supplier_code}: {s.supplier_name} (ID: {s.id})")

    except Exception as e:
        db.rollback()
        print(f"Error: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    seed_suppliers()
