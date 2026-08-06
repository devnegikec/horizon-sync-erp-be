"""Migration tests for Product-owned serial configuration."""

import importlib.util
from pathlib import Path
from unittest.mock import Mock


migration_path = (
    Path(__file__).parents[1]
    / "alembic"
    / "versions"
    / "042_add_product_serial_configuration.py"
)
spec = importlib.util.spec_from_file_location(
    "product_serial_configuration_migration", migration_path
)
assert spec and spec.loader
migration = importlib.util.module_from_spec(spec)
spec.loader.exec_module(migration)


def test_migration_follows_qr_block_integrity_head():
    assert migration.revision == "042_product_serial_config"
    assert migration.down_revision == "041_qr_block_integrity"


def test_upgrade_adds_serial_prefix_fk_and_normalizes_legacy_types(monkeypatch):
    add_column = Mock()
    create_index = Mock()
    create_foreign_key = Mock()
    execute = Mock()
    monkeypatch.setattr(migration.op, "add_column", add_column)
    monkeypatch.setattr(migration.op, "create_index", create_index)
    monkeypatch.setattr(migration.op, "create_foreign_key", create_foreign_key)
    monkeypatch.setattr(migration.op, "execute", execute)

    migration.upgrade()

    assert add_column.call_args.args[1].name == "serial_prefix_setting_id"
    assert add_column.call_args.args[1].nullable is True
    assert create_index.call_args.args[0] == (
        "ix_qr_products_serial_prefix_setting_id"
    )
    assert create_foreign_key.call_args.kwargs["ondelete"] == "RESTRICT"
    normalization_sql = execute.call_args.args[0]
    assert "random_8_alpha_numeric" in normalization_sql
    assert "R8DAN" in normalization_sql
