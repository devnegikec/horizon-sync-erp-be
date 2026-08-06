"""Migration tests for signed QR URL storage."""

import importlib.util
from pathlib import Path
from unittest.mock import Mock

import sqlalchemy as sa


migration_path = (
    Path(__file__).parents[1]
    / "alembic"
    / "versions"
    / "045_expand_product_item_token_id.py"
)
spec = importlib.util.spec_from_file_location(
    "expand_product_item_token_id", migration_path
)
assert spec and spec.loader
migration = importlib.util.module_from_spec(spec)
spec.loader.exec_module(migration)


def test_migration_follows_qr_block_artifacts():
    assert migration.revision == "045_expand_item_token_id"
    assert migration.down_revision == "044_qr_block_artifacts"


def test_upgrade_changes_token_id_to_text(monkeypatch):
    alter_column = Mock()
    monkeypatch.setattr(migration.op, "alter_column", alter_column)

    migration.upgrade()

    call = alter_column.call_args
    assert call.args == ("product_items", "token_id")
    assert isinstance(call.kwargs["existing_type"], sa.String)
    assert call.kwargs["existing_type"].length == 75
    assert isinstance(call.kwargs["type_"], sa.Text)


def test_downgrade_restores_token_id_limit(monkeypatch):
    alter_column = Mock()
    monkeypatch.setattr(migration.op, "alter_column", alter_column)

    migration.downgrade()

    call = alter_column.call_args
    assert call.args == ("product_items", "token_id")
    assert isinstance(call.kwargs["existing_type"], sa.Text)
    assert isinstance(call.kwargs["type_"], sa.String)
    assert call.kwargs["type_"].length == 75
