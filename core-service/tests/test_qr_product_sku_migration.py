"""Regression coverage for QRProduct schema parity."""

from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path


def test_qr_product_sku_migration_exists():
    migration_path = (
        Path(__file__).parents[1]
        / "alembic"
        / "versions"
        / "048_add_sku_to_qr_products.py"
    )
    spec = spec_from_file_location("qr_product_sku_migration", migration_path)
    assert spec is not None and spec.loader is not None
    migration = module_from_spec(spec)
    spec.loader.exec_module(migration)

    assert migration.down_revision == "047_global_item_serial"
    assert migration.revision == "048_add_qr_products_sku"
