"""Unit tests for the pick configuration layer (PR-02 / T-17)."""

import pytest

from app.core import pick_config
from app.core.pick_config import (
    BOOL,
    ENUM,
    INT,
    LIST,
    NUMERIC,
    PICK_CONFIG_CATALOG,
    catalog_entries,
    default_value,
    full_key,
    is_valid_key,
    normalize_key,
    validate_value,
)
from app.models.pick_setting import PickSetting
from app.services.pick_settings_service import PickConfigResolver, PickSettingsService


# ---------------------------------------------------------------------------
# Catalog + validation (pure, no DB)
# ---------------------------------------------------------------------------

class TestCatalog:
    def test_all_plan_keys_present(self):
        expected = {
            "allocation_strategy",
            "require_bin_scan",
            "require_sku_scan",
            "require_serial",
            "over_pick_tolerance",
            "allow_short_pick",
            "short_pick_approval_threshold",
            "require_stage_scan",
            "enable_handling_unit",
            "aging_threshold_minutes",
            "login_lockout_attempts",
            "session_timeout_minutes",
            "reason_codes",
            "priority_fields",
            "backorder_rule",
            "inventory_statuses_pickable",
        }
        assert set(PICK_CONFIG_CATALOG) == expected

    def test_every_entry_has_type_and_default(self):
        for entry in catalog_entries():
            assert entry["type"] in {BOOL, INT, NUMERIC, ENUM, LIST}
            assert entry["label"]
            assert entry["description"]

    def test_key_helpers(self):
        assert normalize_key("require_bin_scan") == "require_bin_scan"
        assert normalize_key("pick.require_bin_scan") == "require_bin_scan"
        assert full_key("require_bin_scan") == "pick.require_bin_scan"
        assert full_key("pick.require_bin_scan") == "pick.require_bin_scan"
        assert is_valid_key("pick.require_bin_scan") is True
        assert is_valid_key("not_a_key") is False

    def test_defaults(self):
        assert default_value("allocation_strategy") == "fefo_fifo"
        assert default_value("require_bin_scan") is True
        assert default_value("require_serial") == "per_item"
        assert default_value("inventory_statuses_pickable") == ["available"]
        assert default_value("priority_fields") == []
        assert default_value("aging_threshold_minutes") == 120


class TestValidateValue:
    def test_valid_values_accepted(self):
        assert validate_value("require_bin_scan", True) is True
        assert validate_value("require_bin_scan", False) is False
        assert validate_value("aging_threshold_minutes", 30) == 30
        assert validate_value("over_pick_tolerance", 0.5) == 0.5
        assert validate_value("allocation_strategy", "fifo") == "fifo"
        assert validate_value("inventory_statuses_pickable", ["available"]) == [
            "available"
        ]

    def test_unknown_key_rejected(self):
        with pytest.raises(ValueError, match="Unknown pick config key"):
            validate_value("nope", True)

    def test_wrong_type_rejected(self):
        with pytest.raises(ValueError, match="must be a boolean"):
            validate_value("require_bin_scan", "true")
        with pytest.raises(ValueError, match="must be an integer"):
            validate_value("aging_threshold_minutes", "120")
        with pytest.raises(ValueError, match="must be a number"):
            validate_value("over_pick_tolerance", "0.5")
        with pytest.raises(ValueError, match="must be a list of strings"):
            validate_value("priority_fields", "cutoff")

    def test_invalid_enum_rejected(self):
        with pytest.raises(ValueError, match="must be one of"):
            validate_value("allocation_strategy", "lifo")


# ---------------------------------------------------------------------------
# Resolver (read-once snapshot, no DB)
# ---------------------------------------------------------------------------

class TestResolver:
    def test_default_fallback_when_unset(self):
        resolver = PickConfigResolver({})
        assert resolver.resolve("require_bin_scan") is True
        assert resolver.get_int("aging_threshold_minutes") == 120
        assert resolver.get_enum("allocation_strategy") == "fefo_fifo"
        assert resolver.get_list("inventory_statuses_pickable") == ["available"]

    def test_override_takes_precedence(self):
        # Simulates a per-organization override merged over defaults.
        resolver = PickConfigResolver({"require_bin_scan": False})
        assert resolver.get_bool("require_bin_scan") is False
        # Untouched keys still fall back to defaults.
        assert resolver.get_bool("allow_short_pick") is True

    def test_typed_getters(self):
        resolver = PickConfigResolver(
            {
                "aging_threshold_minutes": 15,
                "over_pick_tolerance": 2.5,
                "reason_codes": ["bin_empty", "damaged"],
                "allocation_strategy": "zone",
            }
        )
        assert resolver.get_int("aging_threshold_minutes") == 15
        assert resolver.get_numeric("over_pick_tolerance") == 2.5
        assert resolver.get_list("reason_codes") == ["bin_empty", "damaged"]
        assert resolver.get_enum("allocation_strategy") == "zone"

    def test_snapshot_returns_copy(self):
        resolver = PickConfigResolver({"require_bin_scan": False})
        snap = resolver.snapshot()
        snap["require_bin_scan"] = True
        assert resolver.get_bool("require_bin_scan") is False


# ---------------------------------------------------------------------------
# Service merge/upsert logic (fake session, no DB fixture)
# ---------------------------------------------------------------------------

class _FakeQuery:
    def __init__(self, rows):
        self._rows = rows

    def filter(self, *args):
        return self

    def all(self):
        return list(self._rows)

    def first(self):
        return self._rows[0] if self._rows else None

    def delete(self, synchronize_session=False):
        deleted = len(self._rows)
        self._rows.clear()
        return deleted


class _FakeDb:
    def __init__(self, rows=None):
        self._rows = list(rows or [])
        self.added = []

    def query(self, model):
        return _FakeQuery([r for r in self._rows if isinstance(r, model)])

    def add(self, obj):
        self.added.append(obj)

    def commit(self):
        pass


class TestPickSettingsService:
    def _row(self, key, value, org):
        return PickSetting(organization_id=org, key=key, value=value)

    def test_get_settings_merges_override(self):
        org = __import__("uuid").uuid4()
        db = _FakeDb([self._row("require_bin_scan", False, org)])
        settings = PickSettingsService(db).get_settings(org)
        assert settings["require_bin_scan"] is False
        assert settings["allocation_strategy"] == "fefo_fifo"  # default
        assert settings["aging_threshold_minutes"] == 120  # default

    def test_get_settings_all_defaults_when_no_rows(self):
        org = __import__("uuid").uuid4()
        settings = PickSettingsService(_FakeDb()).get_settings(org)
        assert settings["require_bin_scan"] is True
        assert len(settings) == len(PICK_CONFIG_CATALOG)

    def test_update_settings_rejects_bad_value_without_writes(self):
        org = __import__("uuid").uuid4()
        db = _FakeDb()
        svc = PickSettingsService(db)
        with pytest.raises(ValueError):
            svc.update_settings(org, {"require_bin_scan": "yes"})
        assert db.added == []

    def test_update_settings_creates_new_row(self):
        org = __import__("uuid").uuid4()
        db = _FakeDb()
        svc = PickSettingsService(db)
        svc.update_settings(org, {"require_bin_scan": False})
        assert len(db.added) == 1
        assert db.added[0].key == "require_bin_scan"
        assert db.added[0].value is False

    def test_update_settings_updates_existing_row(self):
        org = __import__("uuid").uuid4()
        row = self._row("require_bin_scan", True, org)
        db = _FakeDb([row])
        svc = PickSettingsService(db)
        svc.update_settings(org, {"require_bin_scan": False})
        assert row.value is False
        assert db.added == []


def test_pick_config_type_constants():
    assert pick_config.BOOL == "bool"
    assert pick_config.INT == "int"
    assert pick_config.NUMERIC == "numeric"
    assert pick_config.ENUM == "enum"
    assert pick_config.LIST == "list"
