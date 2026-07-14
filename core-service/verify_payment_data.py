"""Verify payment data seeding"""

import os

from sqlalchemy import create_engine, text

DATABASE_URL = os.getenv(
    "DATABASE_URL", "postgresql://horizon_user:horizon_pass@localhost:5432/core_db"
)
engine = create_engine(DATABASE_URL)
org_id = "b1f71de1-0a19-424e-9580-1d3f871c5b1f"

print("=== PAYMENT DATA VERIFICATION ===\n")

with engine.connect() as conn:
    # Invoice items
    result = conn.execute(
        text("SELECT COUNT(*) FROM invoice_items WHERE organization_id = :org_id"),
        {"org_id": org_id},
    )
    print(f"Invoice Items: {result.scalar()}")

    # Payments by status
    result = conn.execute(
        text(
            "SELECT status, COUNT(*) FROM payment_entries WHERE organization_id = :org_id GROUP BY status"
        ),
        {"org_id": org_id},
    )
    print("\nPayments by Status:")
    for row in result:
        print(f"  {row[0]}: {row[1]}")

    # Payments by type
    result = conn.execute(
        text(
            "SELECT payment_type, COUNT(*) FROM payment_entries WHERE organization_id = :org_id GROUP BY payment_type"
        ),
        {"org_id": org_id},
    )
    print("\nPayments by Type:")
    for row in result:
        print(f"  {row[0]}: {row[1]}")

    # Payment allocations
    result = conn.execute(
        text("SELECT COUNT(*) FROM payment_references WHERE organization_id = :org_id"),
        {"org_id": org_id},
    )
    print(f"\nPayment Allocations: {result.scalar()}")

    # Unpaid invoices
    result = conn.execute(
        text(
            "SELECT invoice_type, COUNT(*) FROM invoices WHERE organization_id = :org_id AND balance_due > 0 GROUP BY invoice_type"
        ),
        {"org_id": org_id},
    )
    print("\nUnpaid Invoices:")
    for row in result:
        print(f"  {row[0]}: {row[1]}")

print("\n=== VERIFICATION COMPLETE ===")
