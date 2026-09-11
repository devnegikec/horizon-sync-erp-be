"""Organization Onboarding Service

Seeds default data for a newly created organization:
  1. Default currency (base currency from org settings)
  2. Default UOMs (standard units of measure)
  3. Default tax templates (Input/Output with 0% placeholder)
  4. Default item groups (top-level categories)

All operations are idempotent — safe to call multiple times.
"""

import logging
import uuid
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy.orm import Session

from app.models.currency_master import CurrencyMaster
from app.models.item_group import ItemGroup
from app.models.tax_template import TaxRule, TaxTemplate
from app.models.uom import UOM
from app.repositories.currency_master_repository import CurrencyMasterRepository
from app.repositories.uom_repository import UOMRepository

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Default data definitions
# ---------------------------------------------------------------------------

DEFAULT_UOMS = [
    # Quantity
    {"name": "Piece", "abbreviation": "PCS", "uom_type": "count", "description": "Individual unit or piece"},
    {"name": "Dozen", "abbreviation": "DOZ", "uom_type": "count", "description": "12 pieces"},
    {"name": "Pair", "abbreviation": "PR", "uom_type": "count", "description": "Set of two"},
    {
        "name": "Set",
        "abbreviation": "SET",
        "uom_type": "count",
        "description": "Group of items sold together",
    },
    {"name": "Box", "abbreviation": "BOX", "uom_type": "count", "description": "Standard box packaging"},
    {"name": "Carton", "abbreviation": "CTN", "uom_type": "count", "description": "Carton packaging"},
    {"name": "Pack", "abbreviation": "PCK", "uom_type": "count", "description": "Packaged bundle"},
    {"name": "Roll", "abbreviation": "ROL", "uom_type": "count", "description": "Roll of material"},
    {"name": "Sheet", "abbreviation": "SHT", "uom_type": "count", "description": "Flat sheet"},
    {"name": "Bundle", "abbreviation": "BDL", "uom_type": "count", "description": "Bundled items"},
    # Weight
    {"name": "Kilogram", "abbreviation": "KG", "uom_type": "weight", "description": "Metric unit of weight"},
    {
        "name": "Gram",
        "abbreviation": "GM",
        "uom_type": "weight",
        "description": "Metric unit of weight (1/1000 kg)",
    },
    {
        "name": "Milligram",
        "abbreviation": "MG",
        "uom_type": "weight",
        "description": "Metric unit of weight (1/1000 g)",
    },
    {"name": "Metric Ton", "abbreviation": "MT", "uom_type": "weight", "description": "1000 kilograms"},
    {"name": "Pound", "abbreviation": "LB", "uom_type": "weight", "description": "Imperial unit of weight"},
    {
        "name": "Ounce",
        "abbreviation": "OZ",
        "uom_type": "weight",
        "description": "Imperial unit of weight (1/16 lb)",
    },
    # Volume
    {"name": "Liter", "abbreviation": "LTR", "uom_type": "volume", "description": "Metric unit of volume"},
    {
        "name": "Milliliter",
        "abbreviation": "ML",
        "uom_type": "volume",
        "description": "Metric unit of volume (1/1000 L)",
    },
    {
        "name": "Cubic Meter",
        "abbreviation": "CBM",
        "uom_type": "volume",
        "description": "Metric unit of volume",
    },
    {"name": "Gallon", "abbreviation": "GAL", "uom_type": "volume", "description": "Imperial unit of volume"},
    # Length
    {"name": "Meter", "abbreviation": "MTR", "uom_type": "length", "description": "Metric unit of length"},
    {
        "name": "Centimeter",
        "abbreviation": "CM",
        "uom_type": "length",
        "description": "Metric unit of length (1/100 m)",
    },
    {
        "name": "Millimeter",
        "abbreviation": "MM",
        "uom_type": "length",
        "description": "Metric unit of length (1/1000 m)",
    },
    {
        "name": "Kilometer",
        "abbreviation": "KM",
        "uom_type": "length",
        "description": "Metric unit of length (1000 m)",
    },
    {"name": "Inch", "abbreviation": "IN", "uom_type": "length", "description": "Imperial unit of length"},
    {
        "name": "Foot",
        "abbreviation": "FT",
        "uom_type": "length",
        "description": "Imperial unit of length (12 inches)",
    },
    {
        "name": "Yard",
        "abbreviation": "YD",
        "uom_type": "length",
        "description": "Imperial unit of length (3 feet)",
    },
    # Area
    {
        "name": "Square Meter",
        "abbreviation": "SQM",
        "uom_type": "area",
        "description": "Metric unit of area",
    },
    {
        "name": "Square Foot",
        "abbreviation": "SQF",
        "uom_type": "area",
        "description": "Imperial unit of area",
    },
    # Time / Service
    {"name": "Hour", "abbreviation": "HR", "uom_type": "time", "description": "Unit of time"},
    {"name": "Day", "abbreviation": "DAY", "uom_type": "time", "description": "Unit of time (24 hours)"},
    {"name": "Month", "abbreviation": "MON", "uom_type": "time", "description": "Unit of time"},
    {"name": "Year", "abbreviation": "YR", "uom_type": "time", "description": "Unit of time (12 months)"},
    # Other
    {"name": "Unit", "abbreviation": "UNIT", "uom_type": "other", "description": "Generic unit"},
    {"name": "Lot", "abbreviation": "LOT", "uom_type": "other", "description": "Batch or lot of items"},
    {"name": "Pallet", "abbreviation": "PLT", "uom_type": "other", "description": "Pallet load"},
    {"name": "Container", "abbreviation": "CNT", "uom_type": "other", "description": "Shipping container"},
    {"name": "Bag", "abbreviation": "BAG", "uom_type": "other", "description": "Bag packaging"},
    {"name": "Drum", "abbreviation": "DRM", "uom_type": "other", "description": "Drum container"},
    {"name": "Bottle", "abbreviation": "BTL", "uom_type": "other", "description": "Bottle packaging"},
]

# Tax templates: code, name, category, description
# Rules are placeholder 0% — org can configure real rates later.
DEFAULT_TAX_TEMPLATES = [
    {
        "template_code": "TAX-OUT-STD",
        "template_name": "Standard Output Tax",
        "tax_category": "Output",
        "description": "Default output tax template for sales transactions",
        "is_default": True,
        "rules": [
            {
                "rule_name": "Output Tax",
                "tax_type": "VAT",
                "tax_rate": 0.00,
                "sequence": 1,
                "is_compound": False,
                "description": "Configure rate as required",
            }
        ],
    },
    {
        "template_code": "TAX-IN-STD",
        "template_name": "Standard Input Tax",
        "tax_category": "Input",
        "description": "Default input tax template for purchase transactions",
        "is_default": True,
        "rules": [
            {
                "rule_name": "Input Tax",
                "tax_type": "VAT",
                "tax_rate": 0.00,
                "sequence": 1,
                "is_compound": False,
                "description": "Configure rate as required",
            }
        ],
    },
]

# Item groups: code, name, description, parent_code (None = root)
DEFAULT_ITEM_GROUPS = [
    {
        "code": "ALL",
        "name": "All Items",
        "description": "Root item group — parent of all categories",
        "parent_code": None,
    },
    {
        "code": "PRODUCTS",
        "name": "Products",
        "description": "Physical goods and manufactured products",
        "parent_code": "ALL",
    },
    {
        "code": "SERVICES",
        "name": "Services",
        "description": "Service items and labour",
        "parent_code": "ALL",
    },
    {
        "code": "RAW-MATERIALS",
        "name": "Raw Materials",
        "description": "Raw materials used in production",
        "parent_code": "ALL",
    },
    {
        "code": "CONSUMABLES",
        "name": "Consumables",
        "description": "Consumable supplies and office materials",
        "parent_code": "ALL",
    },
    {
        "code": "FINISHED-GOODS",
        "name": "Finished Goods",
        "description": "Completed products ready for sale",
        "parent_code": "PRODUCTS",
    },
    {
        "code": "SEMI-FINISHED",
        "name": "Semi-Finished Goods",
        "description": "Work-in-progress and sub-assemblies",
        "parent_code": "PRODUCTS",
    },
]

# ---------------------------------------------------------------------------
# On-demand data sync catalog (Settings → Data Sync tab)
# ---------------------------------------------------------------------------

# Each entry maps a stable API key to the matching idempotent seed routine.
# `label`/`description` are surfaced by the GET /data-sync/features endpoint.
SYNCABLE_FEATURES = [
    {
        "key": "currencies",
        "label": "Currencies",
        "description": "Base currency plus common international currencies",
    },
    {
        "key": "uoms",
        "label": "Units of Measure (UOM)",
        "description": "Standard units of measure (PCS, KG, LTR, MTR, HR, ...)",
    },
    {
        "key": "tax_templates",
        "label": "Tax Templates",
        "description": "Default Input and Output tax templates (0% placeholder)",
    },
    {
        "key": "item_groups",
        "label": "Item Groups",
        "description": "Default item group hierarchy (All Items → Products, Services, ...)",
    },
    {
        "key": "feature_flags",
        "label": "Tenant Feature Flags",
        "description": "Product/item dual-mode feature flags with safe defaults",
    },
    {
        "key": "items",
        "label": "Sample Items",
        "description": "Sample items (incl. serialized units) for testing transfers",
    },
    {
        "key": "stock",
        "label": "Sample Stock",
        "description": "Seed stock for sample items into a selected warehouse",
    },
    {
        "key": "stock_boost",
        "label": "Increase Item Stock",
        "description": "Add a fixed quantity to every item's stock level (test helper)",
    },
    {
        "key": "receive_asn",
        "label": "Inbound Automation",
        "description": (
            "Multi-step inbound flow: QR blocks → ASN → receiving slip → put-away. "
            "Run one step or the whole chain."
        ),
    },
]

SYNCABLE_FEATURE_KEYS = {feature["key"] for feature in SYNCABLE_FEATURES}

# Canonical sample items seeded by the ``items`` data-sync feature. Idempotent
# on ``item_code`` then ``sku`` (skips rows that already exist).
SAMPLE_ITEMS = [
    {
        "item_code": "SMPL-SMART-X1",
        "name": "Smartphone X1 (serialized)",
        "sku": "SMART-X1",
        "gtin": "8900000000012",
        "uom": "Nos",
        "item_type": "stock",
        "has_serial_no": True,
    },
    {
        "item_code": "SMPL-LAPTOP-14",
        "name": "Laptop Pro 14 (serialized)",
        "sku": "LAPTOP-PRO-14",
        "gtin": "8900000000029",
        "uom": "Nos",
        "item_type": "stock",
        "has_serial_no": True,
    },
    {
        "item_code": "SMPL-COOKER",
        "name": "Cooker",
        "sku": "COOKER-001",
        "gtin": None,
        "uom": "Unit",
        "item_type": "stock",
        "has_serial_no": False,
    },
    {
        "item_code": "SMPL-GRINDER",
        "name": "Grinder",
        "sku": "GRINDER-002",
        "gtin": None,
        "uom": "Piece",
        "item_type": "stock",
        "has_serial_no": False,
    },
    {
        "item_code": "SMPL-INDUCTION",
        "name": "Induction Cooktop 2000W",
        "sku": "PIC-2000-BK",
        "gtin": None,
        "uom": "Piece",
        "item_type": "stock",
        "has_serial_no": False,
    },
    {
        "item_code": "SMPL-KETTLE",
        "name": "Prestige Digi Kettle 2.0 Litre with 6 Preset Modes",
        "sku": "PPI-SKO-89",
        "gtin": "234234237",
        "uom": "PC",
        "item_type": "stock",
        "has_serial_no": False,
    },
]


class OrganizationOnboardingService:
    """Seeds default master data for a newly created organization.

    All seed methods are idempotent — they check for existing records
    before inserting and skip duplicates gracefully.
    """

    def __init__(self, db: Session):
        self.db = db
        self.currency_repo = CurrencyMasterRepository(db)
        self.uom_repo = UOMRepository(db)

    # ------------------------------------------------------------------
    # Public entry point
    # ------------------------------------------------------------------

    def seed_defaults(
        self,
        organization_id: UUID,
        base_currency: str,
        created_by: str,
    ) -> dict:
        """Seed all default data for a new organization.

        Args:
            organization_id: UUID of the organization
            base_currency: ISO currency code (e.g. "USD")
            created_by: User identifier (UUID string)

        Returns:
            Summary dict with counts of created/skipped records per category.
        """
        now = datetime.now(UTC)
        user_id = self._parse_user_id(created_by, organization_id)

        logger.info(
            "Starting organization onboarding seed",
            extra={
                "organization_id": str(organization_id),
                "base_currency": base_currency,
                "created_by": created_by,
                "event": "onboarding_seed_started",
            },
        )

        summary = {
            "organization_id": str(organization_id),
            "currency": self._seed_currency(
                organization_id, base_currency, user_id, now
            ),
            "uoms": self._seed_uoms(organization_id, user_id, now),
            "tax_templates": self._seed_tax_templates(organization_id, user_id, now),
            "item_groups": self._seed_item_groups(organization_id, user_id, now),
            "dual_mode_flags": self._seed_dual_mode_flags(
                organization_id, user_id, now
            ),
        }

        # Also set the system_config base_currency so the UI picks it up immediately
        self._seed_system_config_base_currency(base_currency, str(user_id))

        self.db.commit()

        logger.info(
            "Organization onboarding seed completed",
            extra={
                "organization_id": str(organization_id),
                "summary": summary,
                "event": "onboarding_seed_completed",
            },
        )

        return summary

    # ------------------------------------------------------------------
    # On-demand data sync (Settings → Data Sync tab)
    # ------------------------------------------------------------------

    def sync_features(
        self,
        organization_id: UUID,
        features: list[str],
        created_by: str,
        base_currency: str = "USD",
        warehouse_id: UUID | None = None,
        stock_boost_qty: int | None = None,
        receive_asn_options: dict | None = None,
    ) -> dict:
        """Seed the requested default data categories on demand.

        Each feature key is dispatched to the matching idempotent seed method.
        Unknown keys are ignored here (the API layer validates them upstream).

        Args:
            organization_id: UUID of the organization
            features: List of feature keys (see ``SYNCABLE_FEATURES``)
            created_by: User identifier (UUID string)
            base_currency: ISO currency code used when seeding currencies
            warehouse_id: Optional target warehouse for stock seeding

        Returns:
            Per-feature summary dict with created/skipped counts.
        """
        now = datetime.now(UTC)
        user_id = self._parse_user_id(created_by, organization_id)

        # Seed order matters: stock depends on sample items existing, so run
        # items (and its item_groups dependency) before stock regardless of the
        # order the client requested them in.
        _dependency_rank = {"item_groups": 0, "items": 1, "stock": 2, "receive_asn": 3}
        ordered_features = sorted(features, key=lambda k: _dependency_rank.get(k, 10))

        summary: dict = {"organization_id": str(organization_id)}
        for key in ordered_features:
            summary[key] = self._sync_feature(
                key, organization_id, user_id, now, base_currency, warehouse_id,
                stock_boost_qty, receive_asn_options,
            )

        self.db.commit()

        logger.info(
            "On-demand data sync completed",
            extra={
                "organization_id": str(organization_id),
                "features": features,
                "event": "data_sync_completed",
            },
        )

        return summary

    def _sync_feature(
        self,
        key: str,
        organization_id: UUID,
        user_id: UUID,
        now: datetime,
        base_currency: str,
        warehouse_id: UUID | None = None,
        stock_boost_qty: int | None = None,
        receive_asn_options: dict | None = None,
    ) -> dict:
        """Dispatch a single feature key to its idempotent seed routine."""
        if key == "currencies":
            return self._seed_currency(organization_id, base_currency, user_id, now)
        if key == "uoms":
            return self._seed_uoms(organization_id, user_id, now)
        if key == "tax_templates":
            return self._seed_tax_templates(organization_id, user_id, now)
        if key == "item_groups":
            return self._seed_item_groups(organization_id, user_id, now)
        if key == "feature_flags":
            return self._seed_dual_mode_flags(organization_id, user_id, now)
        if key == "items":
            return self._seed_items(organization_id, user_id, now)
        if key == "stock":
            return self._seed_stock(organization_id, user_id, now, warehouse_id)
        if key == "stock_boost":
            return self._seed_stock_boost(
                organization_id, user_id, now, stock_boost_qty or 0
            )
        if key == "receive_asn":
            return self._seed_receive_asn(
                organization_id, user_id, now, warehouse_id, receive_asn_options
            )
        return {"created": 0, "skipped": 0, "error": f"unknown feature '{key}'"}

    # ------------------------------------------------------------------
    # Product/Item dual-mode feature flags (catalog vs WMS)
    # ------------------------------------------------------------------

    def _seed_dual_mode_flags(
        self,
        organization_id: UUID,
        user_id: UUID,
        now: datetime,
    ) -> dict:
        """Seed tenant-scoped product/item dual-mode flags with safe defaults."""
        from app.core.constants import (
            AUTO_APPROVE_SINGLE_CREATE,
            AUTO_CREATE_SKU_ON_ITEM,
            AUTO_CREATE_VARIANT_AXES,
            ITEM_AUTO_CREATE_PRODUCT,
            PRODUCT_EDITABLE_MANUALLY,
            QR_AUTO_LINK_PARENT_CHILD,
            QSEAL_ENABLED,
            REQUIRE_ITEM_APPROVAL,
            TENANT_SCOPE,
            VARIANT_STRUCTURED_ENABLED,
            WMS_ENABLED,
        )
        from app.models.feature_flag import FeatureFlag

        defaults = {
            WMS_ENABLED: True,
            QSEAL_ENABLED: True,
            PRODUCT_EDITABLE_MANUALLY: False,
            ITEM_AUTO_CREATE_PRODUCT: True,
            VARIANT_STRUCTURED_ENABLED: True,
            AUTO_CREATE_SKU_ON_ITEM: False,
            AUTO_CREATE_VARIANT_AXES: False,
            REQUIRE_ITEM_APPROVAL: False,
            AUTO_APPROVE_SINGLE_CREATE: True,
            QR_AUTO_LINK_PARENT_CHILD: True,
        }
        created = 0
        skipped = 0
        for name, enabled in defaults.items():
            existing = (
                self.db.query(FeatureFlag)
                .filter(
                    FeatureFlag.name == name,
                    FeatureFlag.scope == TENANT_SCOPE,
                    FeatureFlag.tenant_id == organization_id,
                )
                .first()
            )
            if existing:
                skipped += 1
                continue
            self.db.add(
                FeatureFlag(
                    name=name,
                    description=f"Tenant-scoped product/item dual-mode flag ({name})",
                    enabled=enabled,
                    visible=True,
                    scope=TENANT_SCOPE,
                    tenant_id=organization_id,
                    user_id=None,
                    created_at=now,
                    updated_at=now,
                )
            )
            created += 1
        logger.debug(
            "Dual-mode flags: %s created, %s skipped for org %s",
            created,
            skipped,
            organization_id,
        )
        return {"created": created, "skipped": skipped}

    # ------------------------------------------------------------------
    # Currency
    # ------------------------------------------------------------------

    def _seed_currency(
        self,
        organization_id: UUID,
        base_currency: str,
        user_id: UUID,
        now: datetime,
    ) -> dict:
        """Seed the base currency and common additional currencies for the organization."""
        code = (base_currency or "USD").upper()[:3]
        created = 0
        skipped = 0

        # Define currencies to seed: base currency + common international currencies
        currencies_to_seed = [
            {"code": code, "is_base": True},
            {"code": "USD", "is_base": False},
            {"code": "EUR", "is_base": False},
            {"code": "GBP", "is_base": False},
            {"code": "INR", "is_base": False},
            {"code": "AED", "is_base": False},
            {"code": "SAR", "is_base": False},
            {"code": "CAD", "is_base": False},
            {"code": "AUD", "is_base": False},
            {"code": "JPY", "is_base": False},
            {"code": "CNY", "is_base": False},
            {"code": "SGD", "is_base": False},
            {"code": "CHF", "is_base": False},
        ]

        # Remove duplicates (if base currency is already in the list)
        seen_codes: set[str] = set()
        unique_currencies = []
        for c in currencies_to_seed:
            if c["code"] not in seen_codes:
                seen_codes.add(c["code"])
                unique_currencies.append(c)

        # Clear any existing base currency flag (shouldn't exist for new org, but be safe)
        self.currency_repo.clear_base_currency(organization_id)

        for curr in unique_currencies:
            curr_code = curr["code"]
            existing = self.currency_repo.get_by_code(curr_code, organization_id)
            if existing:
                skipped += 1
                # Ensure base currency flag is set correctly
                if curr_code == code and not existing.is_base_currency:
                    existing.is_base_currency = True
                continue

            currency = CurrencyMaster(
                id=uuid.uuid4(),
                organization_id=organization_id,
                code=curr_code,
                name=self._currency_name(curr_code),
                symbol=self._currency_symbol(curr_code),
                is_base_currency=(curr_code == code),
                created_by=user_id,
                updated_by=user_id,
                created_at=now,
                updated_at=now,
            )
            self.db.add(currency)
            created += 1

        logger.debug(
            f"Seeded {created} currencies for org {organization_id} (base: {code})"
        )
        return {"created": created, "skipped": skipped}

    # ------------------------------------------------------------------
    # System Config — base currency
    # ------------------------------------------------------------------

    def _seed_system_config_base_currency(
        self, base_currency: str, updated_by: str
    ) -> None:
        """Write the base currency into system_config so the /currency/base-currency
        endpoint returns the correct value immediately after onboarding."""
        try:
            from app.services.currency_service import CurrencyService

            svc = CurrencyService(self.db)
            svc.set_base_currency(base_currency.upper()[:3], updated_by)
            logger.debug(f"system_config base_currency set to {base_currency}")
        except Exception as exc:
            logger.warning(f"Could not set system_config base_currency: {exc}")

    # ------------------------------------------------------------------
    # UOMs
    # ------------------------------------------------------------------

    def _seed_uoms(
        self,
        organization_id: UUID,
        user_id: UUID,
        now: datetime,
    ) -> dict:
        """Seed standard UOMs for the organization."""
        created = 0
        skipped = 0

        for uom_data in DEFAULT_UOMS:
            existing = self.uom_repo.get_by_abbreviation(
                uom_data["abbreviation"], organization_id
            ) or self.uom_repo.get_by_name(uom_data["name"], organization_id)
            if existing:
                # Backfill uom_type for pre-existing UOMs (idempotent).
                if not existing.uom_type and uom_data.get("uom_type"):
                    existing.uom_type = uom_data["uom_type"]
                    self.db.add(existing)
                skipped += 1
                continue

            uom = UOM(
                id=uuid.uuid4(),
                organization_id=organization_id,
                name=uom_data["name"],
                abbreviation=uom_data["abbreviation"],
                uom_type=uom_data.get("uom_type"),
                description=uom_data.get("description"),
                created_by=user_id,
                updated_by=user_id,
                created_at=now,
                updated_at=now,
            )
            self.db.add(uom)
            created += 1

        logger.debug(
            f"UOM seed: {created} created, {skipped} skipped for org {organization_id}"
        )
        return {"created": created, "skipped": skipped}

    # ------------------------------------------------------------------
    # Tax Templates
    # ------------------------------------------------------------------

    def _seed_tax_templates(
        self,
        organization_id: UUID,
        user_id: UUID,
        now: datetime,
    ) -> dict:
        """Seed default tax templates with real GL account references.

        Looks up the seeded GL accounts by code when chart_of_accounts is enabled:
          - Output tax rules → account 2300 (Sales Tax Payable)
          - Input tax rules  → account 1400 (Prepaid Expenses / Tax Receivable)

        If the chart_of_accounts feature is disabled globally, tax templates are
        still seeded but rules use organization_id as a sentinel account_head_id.
        The user can update the account head later from the Tax Templates UI.
        """
        created = 0
        skipped = 0

        # Check if chart_of_accounts feature is enabled
        from app.core.constants import BOOK_CHART_OF_ACCOUNT_ENABLED
        from app.services.feature_flag_service import is_feature_enabled

        chart_enabled = is_feature_enabled(BOOK_CHART_OF_ACCOUNT_ENABLED, self.db)

        # Look up tax-related GL accounts only when chart feature is enabled
        from app.models.chart_of_account import Account as GLAccount

        def _get_account_id(code: str) -> UUID:
            """Return the GL account UUID for the given code, or org_id as fallback."""
            if not chart_enabled:
                logger.info(
                    f"chart_of_accounts feature is disabled; using org_id as placeholder "
                    f"for account_head_id in tax rules (code: {code})"
                )
                return organization_id

            acct = (
                self.db.query(GLAccount)
                .filter(
                    GLAccount.organization_id == organization_id,
                    GLAccount.account_code == code,
                )
                .first()
            )
            if acct:
                return acct.id

            logger.warning(
                f"GL account {code} not found for org {organization_id} during tax template seed; "
                "using org_id as placeholder — update account_head_id after chart is seeded."
            )
            return organization_id  # sentinel — user must update

        # Account code mapping per tax category
        # 2300 = Sales Tax Payable  (Output / collected from customers)
        # 1400 = Prepaid Expenses   (Input / paid to suppliers, closest available)
        output_account_id = _get_account_id("2300")
        input_account_id = _get_account_id("1400")

        category_account_map = {
            "Output": output_account_id,
            "Input": input_account_id,
            "Both": output_account_id,  # Both templates use output account as primary
        }

        for tmpl_data in DEFAULT_TAX_TEMPLATES:
            existing = (
                self.db.query(TaxTemplate)
                .filter(
                    TaxTemplate.organization_id == organization_id,
                    TaxTemplate.template_code == tmpl_data["template_code"],
                    TaxTemplate.deleted_at.is_(None),
                )
                .first()
            )
            if existing:
                skipped += 1
                continue

            template = TaxTemplate(
                id=uuid.uuid4(),
                organization_id=organization_id,
                template_code=tmpl_data["template_code"],
                template_name=tmpl_data["template_name"],
                description=tmpl_data.get("description"),
                tax_category=tmpl_data["tax_category"],
                is_default=tmpl_data.get("is_default", False),
                is_active=True,
                created_by=user_id,
                updated_by=user_id,
                created_at=now,
                updated_at=now,
            )
            self.db.add(template)
            self.db.flush()  # get template.id for rules

            # Determine the account head for this template's category
            account_head_id = category_account_map.get(
                tmpl_data["tax_category"], output_account_id
            )

            for rule_data in tmpl_data.get("rules", []):
                # Input tax rules use the input account; output/both use output account
                if tmpl_data["tax_category"] == "Input":
                    rule_account_id = input_account_id
                else:
                    rule_account_id = account_head_id

                rule = TaxRule(
                    id=uuid.uuid4(),
                    tax_template_id=template.id,
                    rule_name=rule_data["rule_name"],
                    tax_type=rule_data["tax_type"],
                    description=rule_data.get("description"),
                    tax_rate=rule_data["tax_rate"],
                    account_head_id=rule_account_id,
                    is_compound=rule_data.get("is_compound", False),
                    sequence=rule_data["sequence"],
                    created_at=now,
                    updated_at=now,
                )
                self.db.add(rule)

            created += 1

        logger.debug(
            f"Tax template seed: {created} created, {skipped} skipped for org {organization_id}"
        )
        return {"created": created, "skipped": skipped}

    # ------------------------------------------------------------------
    # Item Groups
    # ------------------------------------------------------------------

    def _seed_items(
        self,
        organization_id: UUID,
        user_id: UUID,
        now: datetime,
    ) -> dict:
        """Seed a canonical set of sample items (incl. serialized units).

        Idempotent on ``item_code`` then ``sku`` — items that already exist are
        skipped so the data-sync button can be pressed repeatedly.
        """
        from app.models.base import ItemStatus, ItemType, ValuationMethod
        from app.models.item import Item

        created = 0
        skipped = 0

        existing_codes = {
            c
            for (c,) in self.db.query(Item.item_code)
            .filter(
                Item.organization_id == organization_id,
                Item.deleted_at.is_(None),
            )
            .all()
        }
        existing_skus = {
            s
            for (s,) in self.db.query(Item.sku)
            .filter(
                Item.organization_id == organization_id,
                Item.deleted_at.is_(None),
                Item.sku.isnot(None),
            )
            .all()
        }

        for item_data in SAMPLE_ITEMS:
            code = item_data["item_code"]
            sku = item_data.get("sku")
            if (code and code in existing_codes) or (sku and sku in existing_skus):
                skipped += 1
                continue

            item = Item(
                id=uuid.uuid4(),
                organization_id=organization_id,
                item_code=code,
                item_name=item_data["name"],
                sku=sku,
                gtin=item_data.get("gtin"),
                uom=item_data.get("uom", "Nos"),
                item_type=ItemType(item_data.get("item_type", "stock")),
                status=ItemStatus.ACTIVE,
                maintain_stock=True,
                valuation_method=ValuationMethod.FIFO,
                has_serial_no=item_data.get("has_serial_no", False),
                has_batch_no=item_data.get("has_batch_no", False),
                created_by=user_id,
                updated_by=user_id,
                created_at=now,
                updated_at=now,
            )
            self.db.add(item)
            self.db.flush()
            existing_codes.add(code)
            if sku:
                existing_skus.add(sku)
            created += 1

        logger.debug(
            "Sample item seed: %s created, %s skipped for org %s",
            created,
            skipped,
            organization_id,
        )
        return {"created": created, "skipped": skipped}

    def _seed_stock(
        self,
        organization_id: UUID,
        user_id: UUID,
        now: datetime,
        warehouse_id: UUID | None,
    ) -> dict:
        """Seed stock for the sample items into the selected warehouse.

        Idempotent: creates missing ``stock_levels`` rows and tops up existing
        rows that are below the target quantity (50 regular / 20 serialized).
        """
        from app.models.item import Item
        from app.models.stock_level import StockLevel
        from app.models.warehouse import Warehouse

        if warehouse_id is None:
            return {
                "created": 0,
                "skipped": 0,
                "error": "warehouse_id is required for stock seeding",
            }

        warehouse = (
            self.db.query(Warehouse)
            .filter(
                Warehouse.id == warehouse_id,
                Warehouse.organization_id == organization_id,
            )
            .first()
        )
        if warehouse is None:
            return {
                "created": 0,
                "skipped": 0,
                "error": "Warehouse not found in organization",
            }

        skus = [item_data["sku"] for item_data in SAMPLE_ITEMS if item_data.get("sku")]
        items = (
            self.db.query(Item)
            .filter(
                Item.organization_id == organization_id,
                Item.sku.in_(skus),
                Item.deleted_at.is_(None),
            )
            .all()
        )

        created = 0
        skipped = 0
        for item in items:
            target_qty = 20 if item.has_serial_no else 50
            level = (
                self.db.query(StockLevel)
                .filter(
                    StockLevel.organization_id == organization_id,
                    StockLevel.product_id == item.id,
                    StockLevel.warehouse_id == warehouse_id,
                )
                .first()
            )
            if level is None:
                self.db.add(
                    StockLevel(
                        id=uuid.uuid4(),
                        organization_id=organization_id,
                        product_id=item.id,
                        warehouse_id=warehouse_id,
                        quantity_on_hand=target_qty,
                        quantity_reserved=0,
                        quantity_available=target_qty,
                        created_at=now,
                        updated_at=now,
                    )
                )
                created += 1
            else:
                if (level.quantity_on_hand or 0) < target_qty:
                    reserved = level.quantity_reserved or 0
                    level.quantity_on_hand = target_qty
                    level.quantity_available = target_qty - reserved
                    level.updated_at = now
                skipped += 1

        logger.debug(
            "Sample stock seed: %s created, %s skipped for org %s warehouse %s",
            created,
            skipped,
            organization_id,
            warehouse_id,
        )
        return {"created": created, "skipped": skipped}

    def _seed_stock_boost(
        self,
        organization_id: UUID,
        user_id: UUID,
        now: datetime,
        qty: int,
    ) -> dict:
        """Increase item stock levels by a fixed amount (test helper).

        Adds ``qty`` to the warehouse-level ``stock_levels`` aggregate and, for
        per-bin ``bin_stock_levels``, adds up to ``qty`` per bin but never past
        the bin's capacity, so the capacity model stays consistent and later
        put-away/pick flows don't fail on over-full bins.
        """
        from collections import defaultdict
        from decimal import Decimal

        from app.models.bin_stock_level import BinStockLevel
        from app.models.stock_level import StockLevel
        from app.models.warehouse_location import WarehouseLocation

        if qty <= 0:
            return {
                "created": 0,
                "skipped": 0,
                "error": "Quantity must be a positive integer",
            }

        stock_updated = 0
        for level in (
            self.db.query(StockLevel)
            .filter(StockLevel.organization_id == organization_id)
            .all()
        ):
            level.quantity_on_hand = (level.quantity_on_hand or 0) + qty
            level.quantity_available = (level.quantity_available or 0) + qty
            level.updated_at = now
            stock_updated += 1

        bin_updated = 0
        bin_levels = (
            self.db.query(BinStockLevel)
            .filter(BinStockLevel.organization_id == organization_id)
            .all()
        )
        if bin_levels:
            bin_ids = {level.bin_location_id for level in bin_levels}
            capacities = {
                wl.id: Decimal(str(wl.capacity or 0))
                for wl in self.db.query(WarehouseLocation)
                .filter(WarehouseLocation.id.in_(bin_ids))
                .all()
            }
            bin_totals: dict = defaultdict(lambda: Decimal("0"))
            for level in bin_levels:
                bin_totals[level.bin_location_id] += Decimal(
                    str(level.quantity_on_hand or 0)
                )

            qty_dec = Decimal(str(qty))
            for level in bin_levels:
                capacity = capacities.get(level.bin_location_id, Decimal("0"))
                if capacity <= 0:
                    # Unlimited capacity — add the full amount.
                    level.quantity_on_hand = (level.quantity_on_hand or 0) + qty
                    bin_totals[level.bin_location_id] += qty_dec
                    bin_updated += 1
                    continue
                available = capacity - bin_totals[level.bin_location_id]
                if available <= 0:
                    continue  # bin already at/over capacity — leave it alone
                add = min(qty_dec, available)
                level.quantity_on_hand = (level.quantity_on_hand or 0) + add
                bin_totals[level.bin_location_id] += add
                bin_updated += 1

        logger.info(
            "Stock boost: +%s on %s stock_levels and %s bin_stock_levels for org %s",
            qty,
            stock_updated,
            bin_updated,
            organization_id,
        )
        return {"created": stock_updated + bin_updated, "skipped": 0, "quantity": qty}

    # Ordered Inbound Automation steps. Each step depends on the previous one.
    INBOUND_AUTOMATION_STEPS = ("qr_blocks", "asn", "receiving_slip", "put_away")

    def _seed_receive_asn(
        self,
        organization_id: UUID,
        user_id: UUID,
        now: datetime,
        warehouse_id: UUID | None,
        options: dict | None,
    ) -> dict:
        """Multi-step "Inbound Automation" flow (Settings → Data Sync).

        Runs the requested steps in dependency order so a tenant can execute
        just one step or the whole chain:

          1. ``qr_blocks``      — create QR blocks (+ batch) from item lines
          2. ``asn``            — create + confirm ONE ASN from block children
          3. ``receiving_slip`` — inbound scan session → ONE receiving slip
          4. ``put_away``       — put-away list from the slip (auto mode,
                                  auto-assigned worker for the inbound warehouse)

        ``steps`` must be an ordered prefix of the sequence above (a later step
        cannot run without its predecessor). When omitted, the original
        qr_blocks → asn → receiving_slip behaviour is preserved.
        """
        from uuid import uuid4

        from app.schemas.qr_product import QRBlockCreate
        from app.services.asn_order_service import AsnOrderService
        from app.services.inbound_service import InboundService
        from app.services.put_away_service import PutAwayService
        from app.services.qr_block_queue import enqueue_qr_block
        from app.services.qr_product_service import QRProductService

        options = options or {}
        mode = options.get("mode") or "items"
        qr_type = options.get("qr_type") or "dynamic"
        qr_image = bool(options.get("qr_image", True))
        item_configs = options.get("items") or []
        block_ids = [b for b in (options.get("block_ids") or []) if b]
        asn_type = options.get("asn_type") or "purchase"
        target_warehouse_id = options.get("target_warehouse_id") or warehouse_id
        source_warehouse_id = options.get("source_warehouse_id")

        steps = self._normalize_inbound_automation_steps(
            options.get("steps")
            or list(self.INBOUND_AUTOMATION_STEPS[:3])
        )
        if isinstance(steps, dict):  # validation error
            return steps

        if target_warehouse_id is None:
            return {"created": 0, "skipped": 0, "error": "target_warehouse_id is required"}
        if asn_type == "internal_transfer" and source_warehouse_id is None:
            return {
                "created": 0,
                "skipped": 0,
                "error": "source_warehouse_id is required for an internal transfer ASN",
            }

        qr_svc = QRProductService(self.db)

        # ── Step 1: QR blocks ──────────────────────────────────────────
        blocks: list = []
        if "qr_blocks" in steps:
            if mode == "block_ids":
                for raw_id in block_ids:
                    try:
                        block_id = UUID(raw_id)
                    except ValueError:
                        return {
                            "created": 0,
                            "skipped": 0,
                            "error": f"Invalid block id: {raw_id}",
                        }
                    block = qr_svc.get_block(block_id, organization_id)
                    if block.status != "completed":
                        return {
                            "created": 0,
                            "skipped": 0,
                            "error": f"Block {raw_id} is not completed (status={block.status})",
                        }
                    blocks.append(block)
            else:
                is_auto_link_enabled = self._qr_auto_link_enabled(organization_id)
                for cfg in item_configs:
                    item = self._resolve_receive_item(cfg, organization_id)
                    if item is None or not getattr(item, "qr_product_id", None):
                        continue
                    base_batch = (cfg.get("batch") or "").strip()
                    if not base_batch:
                        base_batch = f"BATCH-{now.strftime('%Y%m%d')}"
                    batch = self._next_batch_number(base_batch, organization_id)
                    quantity = max(1, int(cfg.get("quantity") or 10))
                    master_pack_size = self._resolve_item_master_pack_size(
                        item, cfg, organization_id
                    )
                    # Parent/child auto-linking is gated by the tenant feature
                    # flag; the master-pack size itself always comes from the
                    # item's base packaging unit (never hardcoded).
                    master_pack_enabled = is_auto_link_enabled and master_pack_size is not None
                    try:
                        block = qr_svc.create_block_job(
                            item.qr_product_id,
                            QRBlockCreate(
                                batch=batch,
                                quantity=quantity,
                                qr_type=qr_type,
                                qr_image=qr_image,
                                master_pack_enabled=master_pack_enabled,
                                master_pack_size=(
                                    master_pack_size if master_pack_enabled else None
                                ),
                            ),
                            organization_id,
                            user_id,
                        )
                        task_id = str(uuid4())
                        block = qr_svc.assign_block_task(
                            block.id, organization_id, task_id
                        )
                        enqueue_qr_block(block.id, organization_id, task_id)
                    except Exception:
                        continue
                    try:
                        block = self._wait_for_receive_block(block.id, organization_id)
                    except (RuntimeError, TimeoutError):
                        continue
                    blocks.append(block)
            if not blocks:
                return {
                    "created": 0,
                    "skipped": 0,
                    "steps": steps,
                    "error": "No QR blocks available",
                }

        # ── Resolve child serials (needed by steps 2/3/4) ──────────────
        aggregated: dict = {}
        all_serials: list[str] = []
        if any(s in steps for s in ("asn", "receiving_slip", "put_away")):
            for block in blocks:
                item_id, serials = self._resolve_receive_block_children(
                    block, organization_id
                )
                if item_id is None:
                    continue
                bucket = aggregated.setdefault(
                    str(item_id), {"item_id": item_id, "serials": []}
                )
                bucket["serials"].extend(serials)
                bucket["serials"] = list(dict.fromkeys(bucket["serials"]))
            if not aggregated:
                return {
                    "created": 0,
                    "skipped": 0,
                    "steps": steps,
                    "error": "No child serials resolved from blocks",
                }
            all_serials = [
                s for bucket in aggregated.values() for s in bucket["serials"]
            ]

        asn = None
        slip = None
        put_away = None

        # ── Step 2: ASN ────────────────────────────────────────────────
        if "asn" in steps:
            asn_svc = AsnOrderService(self.db)
            asn_payload = {
                "order_date": now,
                "delivery_date": now,
                "warehouse_id_to": target_warehouse_id,
                "asn_type": asn_type,
                "items": [
                    {
                        "item_id": bucket["item_id"],
                        "qty": len(bucket["serials"]),
                        "uom": "pcs",
                        "serial_nos": bucket["serials"],
                    }
                    for bucket in aggregated.values()
                ],
            }
            if asn_type == "internal_transfer":
                asn_payload["warehouse_id_from"] = source_warehouse_id
            asn = asn_svc.create(asn_payload, organization_id, user_id)
            asn_id = UUID(str(asn["id"]))
            asn_svc.update_status(asn_id, "confirmed", organization_id, user_id)

        # ── Step 3: Receiving slip ─────────────────────────────────────
        if "receiving_slip" in steps:
            inbound = InboundService(self.db)
            session = inbound.start_session(
                worker_id=user_id,
                organization_id=organization_id,
                warehouse_id=target_warehouse_id,
                dock_location="DOCK-A",
                asn_order_id=asn_id,
            )
            session_id = UUID(session["id"])
            for serial in all_serials:
                inbound.record_scan(session_id, serial, user_id, organization_id)
            slip = inbound.end_session(session_id, user_id, organization_id)

        # ── Step 4: Put-away ───────────────────────────────────────────
        if "put_away" in steps:
            slip_id = UUID(str(slip["id"]))
            # The receiving slip is generated in pending_review; put-away list
            # generation requires an approved (pending_putaway) slip, so
            # approve it first when running the put-away step.
            if slip.get("status") == "pending_review":
                inbound = InboundService(self.db)
                slip = inbound.approve_slip(slip_id, organization_id, user_id)
            put_away_svc = PutAwayService(self.db)
            put_away_worker_ids = [
                UUID(str(w)) for w in (options.get("put_away_worker_ids") or []) if w
            ]
            if put_away_worker_ids:
                # One put-away list per selected worker; items are split
                # round-robin (master-pack children kept together).
                put_away = put_away_svc.generate_from_slip_for_workers(
                    slip_id=slip_id,
                    org_id=organization_id,
                    worker_ids=put_away_worker_ids,
                    mode="auto",
                )
            else:
                # No workers selected → single unassigned put-away list.
                raise RuntimeError("Put-away step requires at least one worker ID in options.put_away_worker_ids")

        result: dict = {
            "created": len(blocks) if blocks else len(aggregated),
            "skipped": 0,
            "steps": steps,
        }
        if blocks:
            result["block_count"] = len(blocks)
        if asn is not None:
            result["asn_no"] = asn.get("asn_order_no")
        if slip is not None:
            result["slip_number"] = slip.get("slip_number")
            result["received_serial_count"] = len(all_serials)
        if put_away is not None:
            put_away_lists = put_away if isinstance(put_away, list) else [put_away]
            result["put_away_count"] = len(put_away_lists)
            result["put_away_list_nos"] = [
                getattr(pl, "put_away_list_no", None) for pl in put_away_lists
            ]
            if put_away_lists:
                result["put_away_list_no"] = getattr(
                    put_away_lists[0], "put_away_list_no", None
                )
                result["put_away_status"] = getattr(put_away_lists[0], "status", None)
        return result

    def _normalize_inbound_automation_steps(self, requested_steps) -> list | dict:
        """Validate/order the requested Inbound Automation steps.

        Returns an ordered, de-duplicated list of valid step keys, or an error
        dict when a step is unknown or a later step is requested without its
        predecessor (the steps are sequentially dependent).
        """
        valid = self.INBOUND_AUTOMATION_STEPS
        ordered: list[str] = []
        for step in requested_steps:
            if step not in valid:
                return {
                    "created": 0,
                    "skipped": 0,
                    "error": f"Unknown inbound automation step: {step}",
                }
            if step not in ordered:
                ordered.append(step)
        ordered.sort(key=lambda s: valid.index(s))
        for step in ordered:
            idx = valid.index(step)
            if idx > 0 and valid[idx - 1] not in ordered:
                return {
                    "created": 0,
                    "skipped": 0,
                    "error": (
                        f"Step '{step}' requires previous step '{valid[idx - 1]}'"
                    ),
                }
        return ordered

    def _qr_auto_link_enabled(self, organization_id: UUID) -> bool:
        """Evaluate the ``qr_auto_link_parent_child`` tenant feature flag.

        Defaults to enabled when the flag has never been configured, preserving
        the previous always-on behaviour.
        """
        from app.core.constants import QR_AUTO_LINK_PARENT_CHILD
        from app.repositories.feature_flag_repository import FeatureFlagRepository

        repo = FeatureFlagRepository(self.db)
        flag = repo.get_by_name_for_tenant(
            QR_AUTO_LINK_PARENT_CHILD, organization_id
        )
        if flag is None:
            flag = repo.get_by_name(QR_AUTO_LINK_PARENT_CHILD, scope="GLOBAL")
        if flag is None:
            return True
        return bool(flag.enabled)

    def _resolve_item_master_pack_size(
        self, item, cfg: dict, organization_id: UUID
    ) -> int | None:
        """Resolve a line's master-pack size: explicit value first, else the
        item's base packaging unit (``items_per_master_pack``)."""
        raw = cfg.get("master_pack_size")
        if raw is not None:
            try:
                value = int(raw)
                if value > 0:
                    return value
            except (TypeError, ValueError):
                pass

        from app.models.item_packaging_unit import ItemPackagingUnit

        row = (
            self.db.query(ItemPackagingUnit.items_per_master_pack)
            .filter(
                ItemPackagingUnit.item_id == item.id,
                ItemPackagingUnit.organization_id == organization_id,
                ItemPackagingUnit.is_base_unit.is_(True),
                ItemPackagingUnit.is_active.is_(True),
            )
            .first()
        )
        if row and row[0] is not None:
            try:
                value = int(row[0])
                if value > 0:
                    return value
            except (TypeError, ValueError):
                pass
        return None

    def _wait_for_receive_block(
        self, block_id: UUID, organization_id: UUID, timeout_s: int = 180
    ):
        """Poll a queued QR block until it completes or fails."""
        import time

        from app.services.qr_product_service import QRProductService

        svc = QRProductService(self.db)
        deadline = time.time() + timeout_s
        while time.time() < deadline:
            self.db.expire_all()
            block = svc.get_block(block_id, organization_id)
            if block.status == "completed":
                return block
            if block.status == "failed":
                raise RuntimeError(
                    f"Block {block_id} failed: {getattr(block, 'error_message', None)}"
                )
            time.sleep(3)
        raise TimeoutError(f"Block {block_id} did not complete within {timeout_s}s")

    def _resolve_receive_block_children(self, block, organization_id):
        """Return (item_id, child_serials) for a completed QR block."""
        from app.models.item import Item
        from app.services.qseal_service import QSealService

        qseal = QSealService(self.db)
        item = (
            self.db.query(Item)
            .filter(
                Item.organization_id == organization_id,
                Item.qr_product_id == block.product_id,
                Item.deleted_at.is_(None),
            )
            .first()
        )
        if item is None:
            return None, []

        parents = qseal.get_parents_by_block(block.id, organization_id, 1, 100)
        serials: list[str] = []
        for node in (parents or {}).get("nodes", []):
            # _to_response_dict may return node ids as UUID objects — normalize.
            parent_id = UUID(str(node["id"]))
            detail = qseal.get_parent_with_linked_units(parent_id, organization_id)
            for unit in detail.get("linked_units", []):
                serial = unit.get("serial_number")
                if serial:
                    serials.append(serial)
        return item.id, list(dict.fromkeys(serials))

    def _resolve_receive_item(self, cfg: dict, organization_id: UUID):
        """Resolve a configured item line to an Item (by id, then sku/code)."""
        from sqlalchemy import or_

        from app.models.item import Item

        item = None
        if cfg.get("item_id"):
            try:
                # model_dump() keeps item_id as a UUID, but it may also arrive
                # as a string — normalize before constructing the UUID.
                item_id = UUID(str(cfg["item_id"]))
                item = (
                    self.db.query(Item)
                    .filter(
                        Item.organization_id == organization_id,
                        Item.deleted_at.is_(None),
                        Item.id == item_id,
                    )
                    .first()
                )
            except (ValueError, AttributeError, TypeError):
                item = None
        if item is None and cfg.get("sku"):
            sku = str(cfg["sku"]).strip()
            item = (
                self.db.query(Item)
                .filter(
                    Item.organization_id == organization_id,
                    Item.deleted_at.is_(None),
                    or_(Item.sku == sku, Item.item_code == sku),
                )
                .first()
            )
        return item

    def _next_batch_number(self, base: str, organization_id: UUID) -> str:
        """Append the next sequence to a base batch (e.g. BASE-1, BASE-2)."""
        from app.models.qr_block import QRBlock

        prefix = f"{base}-"
        rows = (
            self.db.query(QRBlock.batch)
            .filter(
                QRBlock.organization_id == organization_id,
                QRBlock.batch.like(f"{prefix}%"),
            )
            .all()
        )
        max_seq = 0
        for (batch,) in rows:
            suffix = (batch or "").removeprefix(prefix)
            if suffix.isdigit():
                max_seq = max(max_seq, int(suffix))
        return f"{base}-{max_seq + 1}"

    def _seed_item_groups(
        self,
        organization_id: UUID,
        user_id: UUID,
        now: datetime,
    ) -> dict:
        """Seed default item group hierarchy for the organization."""
        created = 0
        skipped = 0

        # Track code -> id for parent resolution
        code_to_id: dict[str, UUID] = {}

        # Pre-load existing groups for this org
        existing_groups = (
            self.db.query(ItemGroup)
            .filter(
                ItemGroup.organization_id == organization_id,
                ItemGroup.deleted_at.is_(None),
            )
            .all()
        )
        for g in existing_groups:
            code_to_id[g.code] = g.id

        for grp_data in DEFAULT_ITEM_GROUPS:
            if grp_data["code"] in code_to_id:
                skipped += 1
                continue

            parent_id = None
            if grp_data["parent_code"]:
                parent_id = code_to_id.get(grp_data["parent_code"])
                if parent_id is None:
                    logger.warning(
                        f"Parent group '{grp_data['parent_code']}' not found for "
                        f"'{grp_data['code']}', creating as root"
                    )

            group = ItemGroup(
                id=uuid.uuid4(),
                organization_id=organization_id,
                code=grp_data["code"],
                name=grp_data["name"],
                description=grp_data.get("description"),
                parent_id=parent_id,
                is_active=True,
                created_by=user_id,
                updated_by=user_id,
                created_at=now,
                updated_at=now,
            )
            self.db.add(group)
            self.db.flush()  # get group.id for children
            code_to_id[grp_data["code"]] = group.id
            created += 1

        logger.debug(
            f"Item group seed: {created} created, {skipped} skipped for org {organization_id}"
        )
        return {"created": created, "skipped": skipped}

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _parse_user_id(created_by: str, fallback: UUID) -> UUID:
        """Parse created_by string to UUID, falling back to org ID."""
        try:
            return UUID(created_by)
        except (ValueError, AttributeError):
            return fallback

    @staticmethod
    def _currency_name(code: str) -> str:
        """Return a human-readable name for common currency codes."""
        names = {
            "USD": "US Dollar",
            "EUR": "Euro",
            "GBP": "British Pound",
            "AED": "UAE Dirham",
            "SAR": "Saudi Riyal",
            "INR": "Indian Rupee",
            "PKR": "Pakistani Rupee",
            "BDT": "Bangladeshi Taka",
            "CAD": "Canadian Dollar",
            "AUD": "Australian Dollar",
            "JPY": "Japanese Yen",
            "CNY": "Chinese Yuan",
            "SGD": "Singapore Dollar",
            "MYR": "Malaysian Ringgit",
            "NGN": "Nigerian Naira",
            "KES": "Kenyan Shilling",
            "ZAR": "South African Rand",
            "BRL": "Brazilian Real",
            "MXN": "Mexican Peso",
            "CHF": "Swiss Franc",
        }
        return names.get(code, f"{code} Currency")

    @staticmethod
    def _currency_symbol(code: str) -> str:
        """Return the symbol for common currency codes."""
        symbols = {
            "USD": "$",
            "EUR": "€",
            "GBP": "£",
            "AED": "د.إ",
            "SAR": "﷼",
            "INR": "₹",
            "PKR": "₨",
            "BDT": "৳",
            "CAD": "CA$",
            "AUD": "A$",
            "JPY": "¥",
            "CNY": "¥",
            "SGD": "S$",
            "MYR": "RM",
            "NGN": "₦",
            "KES": "KSh",
            "ZAR": "R",
            "BRL": "R$",
            "MXN": "MX$",
            "CHF": "Fr",
        }
        return symbols.get(code, code)
