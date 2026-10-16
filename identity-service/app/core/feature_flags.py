"""Module → feature flag mapping for permission gating.

The Identity Service does not own the ``feature_flags`` table — that lives in
the Core Service. This module defines, for each permission-code prefix (the
part before the first ``.``), which GLOBAL feature flag gates that module.

When a flag is disabled, every permission whose code prefix maps to it is
omitted from:

  * ``GET /roles`` and ``GET /roles/{id}`` (``include_permissions=true``)
  * ``GET /permissions/grouped`` (``modules`` + ``categories`` + ``uncategorized``)
  * ``GET /users/me/permissions``

Prefixes NOT present in this map (e.g. messaging, marketing, bulk, settings)
are never gated — there is no feature flag for them.

Flag names mirror ``core-service/app/core/constants.py`` and the GLOBAL
``feature_flags`` rows seeded in the Core Service.
"""

# ── Flag name constants (mirrors core-service/app/core/constants.py) ────────
INVOICES_ENABLED = "invoices_enabled"
REVENUE_MODULE_ENABLED = "revenue_module_enabled"
SOURCING_MODULE_ENABLED = "sourcing_module_enabled"
INVENTORY_MODULE_ENABLED = "inventory_module_enabled"
BOOK_MODULE_ENABLED = "book_module_enabled"
BOOK_CHART_OF_ACCOUNT_ENABLED = "book_chart_of_account_enabled"
TAXANDCHARGES_MODULE_ENABLED = "taxandcharges_module_enabled"
SUBSCRIPTIONS_MODULE_ENABLED = "subscriptions_module_enabled"
ANALYTICS_MODULE_ENABLED = "analytics_module_enabled"
QSEAL_MODULE_ENABLED = "qseal_module_enabled"
USERS_MODULE_ENABLED = "users_module_enabled"
ROLES_MODULE_ENABLED = "roles_module_enabled"
REPORTS_MODULE_ENABLED = "reports_module_enabled"

# ── Permission code prefix → feature flag name ───────────────────────────────
# The prefix is ``permission.code.split(".")[0]``.
RESOURCE_FLAG_MAP: dict[str, str] = {
    # Revenue / Sales & Orders
    "customer": REVENUE_MODULE_ENABLED,
    "sales_order": REVENUE_MODULE_ENABLED,
    "quotation": REVENUE_MODULE_ENABLED,
    "invoice": INVOICES_ENABLED,
    # Sourcing / Procurement
    "supplier": SOURCING_MODULE_ENABLED,
    "purchase_order": SOURCING_MODULE_ENABLED,
    "rfq": SOURCING_MODULE_ENABLED,
    # Inventory
    "item": INVENTORY_MODULE_ENABLED,
    "item_group": INVENTORY_MODULE_ENABLED,
    "warehouse": INVENTORY_MODULE_ENABLED,
    "stock_entry": INVENTORY_MODULE_ENABLED,
    "stock_level": INVENTORY_MODULE_ENABLED,
    "stock_settings": INVENTORY_MODULE_ENABLED,
    "stock_reconciliation": INVENTORY_MODULE_ENABLED,
    "put_away_rule": INVENTORY_MODULE_ENABLED,
    "batch": INVENTORY_MODULE_ENABLED,
    "serial": INVENTORY_MODULE_ENABLED,
    "pick_list": INVENTORY_MODULE_ENABLED,
    "asn_order": INVENTORY_MODULE_ENABLED,
    # WMS operations live inside the Inventory module, so they follow the
    # inventory flag (``wms_enabled`` is a TENANT-scoped dual-mode flag, not a
    # GLOBAL module toggle).
    "receiving_slip": INVENTORY_MODULE_ENABLED,
    "inbound_exception": INVENTORY_MODULE_ENABLED,
    "return": INVENTORY_MODULE_ENABLED,
    "wms": INVENTORY_MODULE_ENABLED,
    # Books / Accounting (incl. banking)
    "chart_of_account": BOOK_CHART_OF_ACCOUNT_ENABLED,
    "payment": BOOK_MODULE_ENABLED,
    "currency": BOOK_MODULE_ENABLED,
    "exchange_rate": BOOK_MODULE_ENABLED,
    "bank_account": BOOK_MODULE_ENABLED,
    "reconciliation": BOOK_MODULE_ENABLED,
    "journal_entry": BOOK_MODULE_ENABLED,
    # Taxes & Charges
    "charge_template": TAXANDCHARGES_MODULE_ENABLED,
    "tax_template": TAXANDCHARGES_MODULE_ENABLED,
    # Analytics / Reports
    "analytics": ANALYTICS_MODULE_ENABLED,
    "report": REPORTS_MODULE_ENABLED,
    # QSeal
    "qseal": QSEAL_MODULE_ENABLED,
    # Identity
    "user": USERS_MODULE_ENABLED,
    "org": USERS_MODULE_ENABLED,
    "organization": USERS_MODULE_ENABLED,
    "invitation": USERS_MODULE_ENABLED,
    "role": ROLES_MODULE_ENABLED,
    "permission": ROLES_MODULE_ENABLED,
}


def disabled_resource_prefixes(flags: dict[str, bool]) -> set[str]:
    """Return the set of permission-code prefixes whose flag is disabled.

    A prefix is disabled when its mapped flag is absent from ``flags`` or
    explicitly ``False`` (matching Core Service's fail-closed evaluation).
    """
    return {
        prefix
        for prefix, flag_name in RESOURCE_FLAG_MAP.items()
        if not flags.get(flag_name, False)
    }


def permission_code_is_enabled(code: str, disabled: set[str]) -> bool:
    """Return True unless the code's prefix has been disabled by a flag."""
    if not disabled:
        return True
    if "." in code:
        return code.split(".")[0] not in disabled
    # Wildcards and codes without a dot are never module-gated.
    return True


def filter_permission_codes(codes: list[str], disabled: set[str]) -> list[str]:
    """Filter a list of permission codes by disabled module prefixes."""
    if not disabled:
        return codes
    return [c for c in codes if permission_code_is_enabled(c, disabled)]
