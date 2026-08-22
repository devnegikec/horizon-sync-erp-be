"""Migration tests for Phase 2 QR-credit management."""

import importlib.util
from pathlib import Path
from unittest.mock import Mock

migration_path = (
    Path(__file__).parents[1]
    / "alembic"
    / "versions"
    / "043_add_qr_credit_management.py"
)
spec = importlib.util.spec_from_file_location(
    "qr_credit_management_migration", migration_path
)
assert spec and spec.loader
migration = importlib.util.module_from_spec(spec)
spec.loader.exec_module(migration)


def test_migration_follows_product_serial_configuration():
    assert migration.revision == "043_qr_credit_management"
    assert migration.down_revision == "042_product_serial_config"


def test_upgrade_adds_setting_fks_and_credit_idempotency(monkeypatch):
    add_column = Mock()
    create_index = Mock()
    create_foreign_key = Mock()
    monkeypatch.setattr(migration.op, "add_column", add_column)
    monkeypatch.setattr(migration.op, "create_index", create_index)
    monkeypatch.setattr(migration.op, "create_foreign_key", create_foreign_key)
    monkeypatch.setattr(migration.op, "alter_column", Mock())
    monkeypatch.setattr(migration.op, "execute", Mock())
    monkeypatch.setattr(migration.op, "create_check_constraint", Mock())

    migration.upgrade()

    added_columns = [call.args[1].name for call in add_column.call_args_list]
    assert added_columns[:2] == [
        "channel_setting_id",
        "destination_setting_id",
    ]
    assert "transaction_type" in added_columns
    assert "reference_id" in added_columns
    foreign_keys = [call.args[0] for call in create_foreign_key.call_args_list]
    assert foreign_keys == [
        "fk_qr_blocks_channel_setting_id",
        "fk_qr_blocks_destination_setting_id",
    ]
    index_names = [call.args[0] for call in create_index.call_args_list]
    assert "uq_qr_credit_ledger_org_reference" in index_names
    assert "uq_qr_credit_ledger_block_consumption" in index_names
