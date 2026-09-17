"""Migration tests for durable QR generation credit reservations."""

import importlib.util
from pathlib import Path
from unittest.mock import Mock

migration_path = (
    Path(__file__).parents[1]
    / "alembic"
    / "versions"
    / "046_add_qr_credit_reservations.py"
)
spec = importlib.util.spec_from_file_location(
    "qr_credit_reservations_migration",
    migration_path,
)
assert spec and spec.loader
migration = importlib.util.module_from_spec(spec)
spec.loader.exec_module(migration)


def test_migration_follows_product_item_url_expansion():
    assert migration.revision == "046_qr_credit_reservations"
    assert migration.down_revision == "045_expand_item_token_id"


def test_upgrade_adds_reserved_balance_and_reservation_table(monkeypatch):
    add_column = Mock()
    create_table = Mock()
    create_index = Mock()
    create_check_constraint = Mock()
    monkeypatch.setattr(migration.op, "add_column", add_column)
    monkeypatch.setattr(migration.op, "create_table", create_table)
    monkeypatch.setattr(migration.op, "create_index", create_index)
    monkeypatch.setattr(
        migration.op,
        "create_check_constraint",
        create_check_constraint,
    )

    migration.upgrade()

    assert add_column.call_args.args[0] == "qr_credit_balance"
    assert add_column.call_args.args[1].name == "reserved_credits"
    assert create_table.call_args.args[0] == "qr_credit_reservations"
    column_names = {
        value.name
        for value in create_table.call_args.args[1:]
        if hasattr(value, "name")
    }
    assert {
        "organization_id",
        "block_id",
        "quantity",
        "status",
    }.issubset(column_names)
    assert any(
        call.args[0] == "ix_qr_credit_reservations_org_status"
        for call in create_index.call_args_list
    )


def test_downgrade_removes_reservations_before_balance_column(monkeypatch):
    drop_index = Mock()
    drop_table = Mock()
    drop_constraint = Mock()
    drop_column = Mock()
    monkeypatch.setattr(migration.op, "drop_index", drop_index)
    monkeypatch.setattr(migration.op, "drop_table", drop_table)
    monkeypatch.setattr(migration.op, "drop_constraint", drop_constraint)
    monkeypatch.setattr(migration.op, "drop_column", drop_column)

    migration.downgrade()

    drop_table.assert_called_once_with("qr_credit_reservations")
    drop_column.assert_called_once_with(
        "qr_credit_balance",
        "reserved_credits",
    )
