"""Migration tests for QR block Phase 1 integrity changes."""

import importlib.util
from pathlib import Path
from unittest.mock import Mock

import pytest


migration_path = (
    Path(__file__).parents[1]
    / "alembic"
    / "versions"
    / "041_add_qr_block_generation_integrity.py"
)
spec = importlib.util.spec_from_file_location("qr_block_phase1_migration", migration_path)
assert spec and spec.loader
migration = importlib.util.module_from_spec(spec)
spec.loader.exec_module(migration)


def test_migration_follows_current_qr_head():
    assert migration.revision == "041_qr_block_integrity"
    assert migration.down_revision == "040_add_product_shelf_life"


def test_migration_stops_when_duplicate_batches_exist(monkeypatch):
    bind = Mock()
    bind.execute.return_value.first.return_value = ("org", "batch")
    monkeypatch.setattr(migration.op, "get_bind", lambda: bind)

    with pytest.raises(RuntimeError, match="active duplicate batches"):
        migration._assert_no_active_duplicates()


def test_migration_stops_when_duplicate_serials_exist(monkeypatch):
    bind = Mock()
    first_result = Mock()
    first_result.first.return_value = None
    second_result = Mock()
    second_result.first.return_value = ("org", "serial")
    bind.execute.side_effect = [first_result, second_result]
    monkeypatch.setattr(migration.op, "get_bind", lambda: bind)

    with pytest.raises(RuntimeError, match="active duplicate serial"):
        migration._assert_no_active_duplicates()


def test_upgrade_creates_active_unique_indexes(monkeypatch):
    bind = Mock()
    result = Mock()
    result.first.return_value = None
    bind.execute.return_value = result
    monkeypatch.setattr(migration.op, "get_bind", lambda: bind)

    create_index = Mock()
    monkeypatch.setattr(migration.op, "add_column", Mock())
    monkeypatch.setattr(migration.op, "execute", Mock())
    monkeypatch.setattr(migration.op, "create_check_constraint", Mock())
    monkeypatch.setattr(migration.op, "create_index", create_index)

    migration.upgrade()

    index_names = [call.args[0] for call in create_index.call_args_list]
    assert index_names == [
        "uq_qr_blocks_org_batch_active",
        "uq_product_items_org_serial_active",
    ]
    assert all(
        call.kwargs["postgresql_where"] is not None
        for call in create_index.call_args_list
    )
