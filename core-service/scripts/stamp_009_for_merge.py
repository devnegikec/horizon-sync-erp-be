"""One-off: apply 009 DDL and ensure only f6g7h8i9j0k1 in alembic_version.

Use when DB is at f6g7h8i9j0k1 (accounts branch) and never applied 009.
Ensures 009's schema (item discount columns) exists and removes 009 from
alembic_version if present so 'alembic upgrade head' can run (single path).

Run from core-service: python scripts/stamp_009_for_merge.py
Then: alembic upgrade head
"""

import os
import sys

from sqlalchemy import create_engine, inspect, text

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.config import settings  # noqa: E402


def _ensure_discount_columns(conn, table_name: str) -> None:
    inspector = inspect(conn)
    columns = [c["name"] for c in inspector.get_columns(table_name)]
    for col_name, col_type, default in (
        ("discount_type", "VARCHAR(20)", "'percentage'"),
        ("discount_value", "NUMERIC(15, 2)", "0"),
        ("discount_amount", "NUMERIC(15, 2)", "0"),
    ):
        if col_name not in columns:
            conn.execute(
                text(
                    f"ALTER TABLE {table_name} ADD COLUMN {col_name} {col_type} "
                    f"DEFAULT {default}"
                )
            )
            print(f"  Added {table_name}.{col_name}")


def main() -> int:
    engine = create_engine(settings.database_url)
    with engine.begin() as conn:
        print("Applying 009 DDL (item discount columns)...")
        _ensure_discount_columns(conn, "quotation_items")
        _ensure_discount_columns(conn, "sales_order_items")
        # Remove 009 from alembic_version so only f6g7h8i9j0k1 remains (single path to head)
        r = conn.execute(text("DELETE FROM alembic_version WHERE version_num = '009'"))
        if r.rowcount:
            print("Removed 009 from alembic_version (so upgrade head has a single path).")
        else:
            print("009 not in alembic_version.")
    print("Done. Run: alembic upgrade head")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
