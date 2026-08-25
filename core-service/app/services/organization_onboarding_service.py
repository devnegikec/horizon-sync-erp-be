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
    {"name": "Piece", "abbreviation": "PCS", "description": "Individual unit or piece"},
    {"name": "Dozen", "abbreviation": "DOZ", "description": "12 pieces"},
    {"name": "Pair", "abbreviation": "PR", "description": "Set of two"},
    {"name": "Set", "abbreviation": "SET", "description": "Group of items sold together"},
    {"name": "Box", "abbreviation": "BOX", "description": "Standard box packaging"},
    {"name": "Carton", "abbreviation": "CTN", "description": "Carton packaging"},
    {"name": "Pack", "abbreviation": "PCK", "description": "Packaged bundle"},
    {"name": "Roll", "abbreviation": "ROL", "description": "Roll of material"},
    {"name": "Sheet", "abbreviation": "SHT", "description": "Flat sheet"},
    {"name": "Bundle", "abbreviation": "BDL", "description": "Bundled items"},
    # Weight
    {"name": "Kilogram", "abbreviation": "KG", "description": "Metric unit of weight"},
    {"name": "Gram", "abbreviation": "GM", "description": "Metric unit of weight (1/1000 kg)"},
    {"name": "Milligram", "abbreviation": "MG", "description": "Metric unit of weight (1/1000 g)"},
    {"name": "Metric Ton", "abbreviation": "MT", "description": "1000 kilograms"},
    {"name": "Pound", "abbreviation": "LB", "description": "Imperial unit of weight"},
    {"name": "Ounce", "abbreviation": "OZ", "description": "Imperial unit of weight (1/16 lb)"},
    # Volume
    {"name": "Liter", "abbreviation": "LTR", "description": "Metric unit of volume"},
    {"name": "Milliliter", "abbreviation": "ML", "description": "Metric unit of volume (1/1000 L)"},
    {"name": "Cubic Meter", "abbreviation": "CBM", "description": "Metric unit of volume"},
    {"name": "Gallon", "abbreviation": "GAL", "description": "Imperial unit of volume"},
    # Length
    {"name": "Meter", "abbreviation": "MTR", "description": "Metric unit of length"},
    {"name": "Centimeter", "abbreviation": "CM", "description": "Metric unit of length (1/100 m)"},
    {"name": "Millimeter", "abbreviation": "MM", "description": "Metric unit of length (1/1000 m)"},
    {"name": "Kilometer", "abbreviation": "KM", "description": "Metric unit of length (1000 m)"},
    {"name": "Inch", "abbreviation": "IN", "description": "Imperial unit of length"},
    {"name": "Foot", "abbreviation": "FT", "description": "Imperial unit of length (12 inches)"},
    {"name": "Yard", "abbreviation": "YD", "description": "Imperial unit of length (3 feet)"},
    # Area
    {"name": "Square Meter", "abbreviation": "SQM", "description": "Metric unit of area"},
    {"name": "Square Foot", "abbreviation": "SQF", "description": "Imperial unit of area"},
    # Time / Service
    {"name": "Hour", "abbreviation": "HR", "description": "Unit of time"},
    {"name": "Day", "abbreviation": "DAY", "description": "Unit of time (24 hours)"},
    {"name": "Month", "abbreviation": "MON", "description": "Unit of time"},
    {"name": "Year", "abbreviation": "YR", "description": "Unit of time (12 months)"},
    # Other
    {"name": "Unit", "abbreviation": "UNIT", "description": "Generic unit"},
    {"name": "Lot", "abbreviation": "LOT", "description": "Batch or lot of items"},
    {"name": "Pallet", "abbreviation": "PLT", "description": "Pallet load"},
    {"name": "Container", "abbreviation": "CNT", "description": "Shipping container"},
    {"name": "Bag", "abbreviation": "BAG", "description": "Bag packaging"},
    {"name": "Drum", "abbreviation": "DRM", "description": "Drum container"},
    {"name": "Bottle", "abbreviation": "BTL", "description": "Bottle packaging"},
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
            "currency": self._seed_currency(organization_id, base_currency, user_id, now),
            "uoms": self._seed_uoms(organization_id, user_id, now),
            "tax_templates": self._seed_tax_templates(organization_id, user_id, now),
            "item_groups": self._seed_item_groups(organization_id, user_id, now),
            "dual_mode_flags": self._seed_dual_mode_flags(organization_id, user_id, now),
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

        logger.debug(f"Seeded {created} currencies for org {organization_id} (base: {code})")
        return {"created": created, "skipped": skipped}

    # ------------------------------------------------------------------
    # System Config — base currency
    # ------------------------------------------------------------------

    def _seed_system_config_base_currency(self, base_currency: str, updated_by: str) -> None:
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
            existing = (
                self.uom_repo.get_by_abbreviation(
                    uom_data["abbreviation"], organization_id
                )
                or self.uom_repo.get_by_name(uom_data["name"], organization_id)
            )
            if existing:
                skipped += 1
                continue

            uom = UOM(
                id=uuid.uuid4(),
                organization_id=organization_id,
                name=uom_data["name"],
                abbreviation=uom_data["abbreviation"],
                description=uom_data.get("description"),
                created_by=user_id,
                updated_by=user_id,
                created_at=now,
                updated_at=now,
            )
            self.db.add(uom)
            created += 1

        logger.debug(f"UOM seed: {created} created, {skipped} skipped for org {organization_id}")
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
