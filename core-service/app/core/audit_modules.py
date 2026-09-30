"""Module classification for audited core-service tables.

The audit UI groups events by business module. ``table_to_module`` maps a
``table_name`` to one of the modules below; ``tables_for_module`` reverses it
for the ``module`` filter on ``GET /admin/audit-logs``.

Notes:
- Users and Roles activity (login/logout, role assignment) is recorded by the
  identity service, not core-service, so those modules are sparse here
  (``Users`` has only ``warehouse_users``; ``Roles`` is empty).
- ``Other`` is the fallback bucket. It always resolves to every audited table
  that no enabled module claims, so a row labelled ``Other`` is always
  selectable through the ``module`` filter.
- When a new table is added, add it to ``_MODULE_TABLES`` to give it a real
  module; until then it is labelled — and filterable as — ``Other``.
"""

OTHER_MODULE = "Other"

# Every module value ``table_to_module`` can return must be listed here: the
# ``module`` filter on GET /admin/audit-logs rejects anything else with a 400.
# Revenue/Settings stay disabled until their tables are reviewed -- their rows
# fall into ``OTHER_MODULE`` and remain filterable there.
MODULES: list[str] = [
    "Inventory",
    "WMS",
    # "Revenue",
    "QSeal",
    "Users",
    "Roles",
    # "Settings",
    OTHER_MODULE,
]

_MODULE_TABLES: dict[str, list[str]] = {
    "Inventory": [
        "batches",
        "brands",
        "item_groups",
        "item_packaging_units",
        "item_prices",
        "item_suppliers",
        "items",
        "packaging_types",
        "product_items",
        "product_sku_attribute_values",
        "product_skus",
        "products",
        "serial_no_history",
        "serial_nos",
        "stock_entries",
        "stock_entry_items",
        "stock_levels",
        "stock_movements",
        "stock_reconciliation_items",
        "stock_reconciliations",
        "stock_settings",
        "suppliers",
        "uom_conversions",
        "uoms",
        "variant_attribute_values",
        "variant_attributes",
        "warranties",
        "warranty_periods",
    ],
    "WMS": [
        "asn_order_items",
        "asn_order_serial_lines",
        "asn_orders",
        "bin_reservations",
        "bin_stock_levels",
        "delivery_note_items",
        "delivery_notes",
        "dispatch_records",
        "gate_verification_items",
        "gate_verification_sessions",
        "handling_units",
        "location_allocations",
        "location_scans",
        "material_request_lines",
        "material_requests",
        "outbound_order_items",
        "outbound_orders",
        "packing_slip_items",
        "packing_slips",
        "pending_warehouse_assignments",
        "pick_exceptions",
        "pick_idempotency_keys",
        "pick_list_items",
        "pick_lists",
        "purchase_receipt_items",
        "purchase_receipts",
        "put_away_list_items",
        "put_away_lists",
        "put_away_rules",
        "quality_inspection_parameters",
        "quality_inspection_readings",
        "quality_inspection_templates",
        "quality_inspections",
        "receiving_slip_items",
        "receiving_slips",
        "scan_session_items",
        "scan_sessions",
        "vehicle_arrivals",
        "vehicles",
        "warehouse_floor_plans",
        "warehouse_locations",
        "warehouses_extended",
        "wms_devices",
        "worker_sessions",
        "worker_tasks",
    ],
    # "Revenue": [
    #     "account_balances",
    #     "accounts",
    #     "bank_account_history",
    #     "bank_accounts",
    #     "bank_reconciliations",
    #     "bank_transactions",
    #     "charge_templates",
    #     "currency_masters",
    #     "customers",
    #     "default_accounts",
    #     "exchange_rates",
    #     "invoice_items",
    #     "invoices",
    #     "journal_entries",
    #     "journal_entry_lines",
    #     "landed_cost_vouchers",
    #     "payment_entries",
    #     "payment_references",
    #     "payments",
    #     "purchase_order_lines",
    #     "purchase_orders",
    #     "quotation_items",
    #     "quotations",
    #     "reminder_configs",
    #     "reminder_logs",
    #     "return_receipt_note_events",
    #     "return_receipt_note_items",
    #     "return_receipt_notes",
    #     "return_registration_items",
    #     "return_registrations",
    #     "return_session_items",
    #     "return_sessions",
    #     "rfq_lines",
    #     "rfq_suppliers",
    #     "rfqs",
    #     "sales_order_items",
    #     "sales_orders",
    #     "supplier_quotes",
    #     "tax_rules",
    #     "tax_templates",
    #     "transaction_charge_breakdown",
    #     "transaction_tax_breakdown",
    # ],
    "QSeal": [
        "qr_activation_parameters",
        "qr_activation_tracks",
        "qr_blocks",
        "qr_credit_balance",
        "qr_credit_ledger",
        "qr_credit_reservations",
        "qr_credit_usage",
        "qr_cta_configs",
        "qr_product_settings",
        "qr_products",
        "qr_scan_events",
        "qr_scan_interactions",
        "qseal_activation_requests",
        "qseal_parameters",
        "qseal_tracks",
    ],
    "Users": [
        "warehouse_users",
    ],
    "Roles": [],
    # "Settings": [
    #     "admin_notifications",
    #     "bulk_export_jobs",
    #     "bulk_import_jobs",
    #     "destination_markets",
    #     "document_numbering_config",
    #     "document_sequence_counter",
    #     "erp_sync_messages",
    #     "feature_flags",
    #     "message_templates",
    #     "notifications",
    #     "shopify_configs",
    #     "system_config",
    # ],
    # "Other": [
    #     "brand_industries",
    #     "brand_trust_answers",
    #     "brand_trust_assessments",
    #     "brand_trust_questions",
    #     "bulk_message_jobs",
    #     "campaign_leads",
    #     "campaign_tags",
    #     "campaigns",
    #     "communication_logs",
    #     "coupon_durations",
    #     "coupon_unlock_logs",
    #     "coupons",
    #     "external_coupons",
    #     "landing_page_configs",
    #     "message_credits",
    #     "meta_campaigns",
    #     "play2win_prizes",
    #     "public_submissions",
    #     "rcs_credentials",
    #     "rcs_reports",
    #     "rcs_templates",
    #     "scheduled_messages",
    #     "short_urls",
    #     "sms_reports",
    #     "web_campaigns",
    #     "whatsapp_reports",
    # ],
}

# table_name -> module (flattened, for row-level lookup)
TABLE_MODULE_MAP: dict[str, str] = {
    table: module for module, tables in _MODULE_TABLES.items() for table in tables
}


def table_to_module(table_name: str) -> str:
    """Return the business module for a table, defaulting to ``Other``.

    The result is always a member of ``MODULES``, so a module taken from a
    response row can be fed straight back into the ``module`` filter.
    """
    module = TABLE_MODULE_MAP.get(table_name)
    if module is None or module not in MODULES:
        return OTHER_MODULE
    return module


def _tables_owned_by_enabled_modules() -> set[str]:
    """Table names claimed by a module that is actually selectable."""
    return {
        table
        for module, tables in _MODULE_TABLES.items()
        if module in MODULES
        for table in tables
    }


def _audited_table_names() -> set[str]:
    """Table names of every model that emits audit entries.

    Mirrors ``register_audit_listeners`` so the fallback bucket contains
    exactly the tables whose rows can appear in the audit log.
    """
    from app.core.audit_listener import AUDIT_EXCLUDE_TABLES
    from app.database import Base

    names: set[str] = set()
    for mapper in Base.registry.mappers:
        cls = mapper.class_
        if getattr(cls, "__audited__", None) is False:
            continue
        table = getattr(cls, "__tablename__", None)
        if table and table not in AUDIT_EXCLUDE_TABLES:
            names.add(table)
    return names


def tables_for_module(module: str) -> list[str]:
    """Return the core tables belonging to *module* (empty for unknown).

    ``Other`` is the fallback bucket, so it resolves to every audited table
    that no enabled module claims. That keeps the set of filterable modules in
    step with the set of module values the API can emit.
    """
    if module == OTHER_MODULE:
        return sorted(_audited_table_names() - _tables_owned_by_enabled_modules())
    return list(_MODULE_TABLES.get(module, []))
