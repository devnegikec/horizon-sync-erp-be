"""Migration tests for durable QR Block artifacts."""

import importlib.util
from pathlib import Path
from unittest.mock import Mock

migration_path = (
    Path(__file__).parents[1]
    / "alembic"
    / "versions"
    / "044_add_qr_block_artifacts.py"
)
spec = importlib.util.spec_from_file_location(
    "qr_block_artifacts_migration", migration_path
)
assert spec and spec.loader
migration = importlib.util.module_from_spec(spec)
spec.loader.exec_module(migration)


def test_migration_follows_credit_management():
    assert migration.revision == "044_qr_block_artifacts"
    assert migration.down_revision == "043_qr_credit_management"


def test_upgrade_adds_artifact_metadata(monkeypatch):
    add_column = Mock()
    monkeypatch.setattr(migration.op, "add_column", add_column)

    migration.upgrade()

    assert [call.args[1].name for call in add_column.call_args_list] == [
        "artifact_object_key",
        "artifact_size_bytes",
        "artifact_checksum_sha256",
        "artifact_generated_at",
    ]


def test_downgrade_removes_artifact_metadata(monkeypatch):
    drop_column = Mock()
    monkeypatch.setattr(migration.op, "drop_column", drop_column)

    migration.downgrade()

    assert [call.args[1] for call in drop_column.call_args_list] == [
        "artifact_generated_at",
        "artifact_checksum_sha256",
        "artifact_size_bytes",
        "artifact_object_key",
    ]
