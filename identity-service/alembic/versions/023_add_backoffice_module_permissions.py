"""Add back-office module permission codes.

Revision ID: 023
Revises: 022
Create Date: 2026-09-25

Back-office modules (banking, analytics, messaging, brand trust, bulk
import/export, charge templates, short URLs, document numbering, pick
settings, QSeal and landing pages) were previously gated only by
authentication (``get_current_user``). Core-service now enforces
``require_permission`` on these endpoints, so the corresponding permission
codes must exist in the ``permissions`` table for regular (non-admin) users
to be granted them.

The new ``resourcetype`` labels are appended to the enum before the insert
statements cast to them (mirrors migrations 020/022).
"""

from sqlalchemy import text
from sqlalchemy.orm import Session

from alembic import op

revision = "023"
down_revision = "022"
branch_labels = None
depends_on = None

# New resourcetype enum values.
NEW_RESOURCE_TYPES = [
    "currency",
    "exchange_rate",
    "stock_level",
    "stock_settings",
    "stock_reconciliation",
    "put_away_rule",
    "analytics",
    "bank_account",
    "reconciliation",
    "messaging",
    "communication",
    "brand_trust",
    "bulk_export",
    "bulk_import",
    "charge_template",
    "short_url",
    "document_numbering",
    "pick_setting",
]

# (code, name, description, resource, action, category)
# Actions reuse existing actiontype labels only (read/create/update/delete/
# manage). "send"-style permissions map to "create".
PERMISSIONS = [
    # Currency & exchange rates
    ("currency.read", "Read Currencies", "View currencies", "currency", "read", "accounting"),
    ("currency.create", "Create Currency", "Add a currency", "currency", "create", "accounting"),
    ("currency.update", "Update Currency", "Edit a currency", "currency", "update", "accounting"),
    ("currency.delete", "Delete Currency", "Remove a currency", "currency", "delete", "accounting"),
    ("exchange_rate.read", "Read Exchange Rates", "View exchange rates", "exchange_rate", "read", "accounting"),
    ("exchange_rate.create", "Create Exchange Rate", "Add an exchange rate", "exchange_rate", "create", "accounting"),
    ("exchange_rate.update", "Update Exchange Rate", "Edit an exchange rate", "exchange_rate", "update", "accounting"),
    ("exchange_rate.delete", "Delete Exchange Rate", "Remove an exchange rate", "exchange_rate", "delete", "accounting"),
    # Stock
    ("stock_level.read", "Read Stock Levels", "View stock levels", "stock_level", "read", "inventory"),
    ("stock_level.create", "Create Stock Level", "Create a stock level", "stock_level", "create", "inventory"),
    ("stock_level.update", "Update Stock Level", "Edit a stock level", "stock_level", "update", "inventory"),
    ("stock_settings.read", "Read Stock Settings", "View stock settings", "stock_settings", "read", "inventory"),
    ("stock_settings.update", "Update Stock Settings", "Edit stock settings", "stock_settings", "update", "inventory"),
    ("stock_reconciliation.read", "Read Stock Reconciliations", "View stock reconciliations", "stock_reconciliation", "read", "inventory"),
    ("stock_reconciliation.create", "Create Stock Reconciliation", "Create a stock reconciliation", "stock_reconciliation", "create", "inventory"),
    ("stock_reconciliation.update", "Update Stock Reconciliation", "Edit a stock reconciliation", "stock_reconciliation", "update", "inventory"),
    ("stock_reconciliation.delete", "Delete Stock Reconciliation", "Remove a stock reconciliation", "stock_reconciliation", "delete", "inventory"),
    ("put_away_rule.read", "Read Put-Away Rules", "View put-away rules", "put_away_rule", "read", "inventory"),
    ("put_away_rule.create", "Create Put-Away Rule", "Add a put-away rule", "put_away_rule", "create", "inventory"),
    ("put_away_rule.update", "Update Put-Away Rule", "Edit a put-away rule", "put_away_rule", "update", "inventory"),
    ("put_away_rule.delete", "Delete Put-Away Rule", "Remove a put-away rule", "put_away_rule", "delete", "inventory"),
    # Banking
    ("bank_account.read", "Read Bank Accounts", "View bank accounts and their masked identifiers", "bank_account", "read", "banking"),
    ("bank_account.create", "Create Bank Account", "Add a new bank account", "bank_account", "create", "banking"),
    ("bank_account.update", "Update Bank Account", "Edit an existing bank account", "bank_account", "update", "banking"),
    ("bank_account.delete", "Delete Bank Account", "Remove a bank account", "bank_account", "delete", "banking"),
    ("bank_account.manage", "Manage Bank Accounts", "Full bank account administration", "bank_account", "manage", "banking"),
    ("reconciliation.read", "Read Reconciliations", "View account/bank reconciliations", "reconciliation", "read", "banking"),
    ("reconciliation.create", "Create Reconciliation", "Start a new reconciliation", "reconciliation", "create", "banking"),
    ("reconciliation.update", "Update Reconciliation", "Edit a reconciliation", "reconciliation", "update", "banking"),
    ("reconciliation.delete", "Delete Reconciliation", "Remove a reconciliation", "reconciliation", "delete", "banking"),
    # Analytics
    ("analytics.read", "Read Analytics", "View analytics dashboards and reports", "analytics", "read", "reporting"),
    # Messaging / Communications
    ("messaging.read", "Read Messaging", "View messaging channels and history", "messaging", "read", "messaging"),
    ("messaging.create", "Create Messaging", "Create message templates", "messaging", "create", "messaging"),
    ("messaging.update", "Update Messaging", "Edit message templates and settings", "messaging", "update", "messaging"),
    ("messaging.delete", "Delete Messaging", "Remove message templates", "messaging", "delete", "messaging"),
    ("messaging.send", "Send Message", "Send messages via configured channels", "messaging", "create", "messaging"),
    ("communication.read", "Read Communications", "View communication templates and logs", "communication", "read", "messaging"),
    ("communication.create", "Create Communication", "Create communications", "communication", "create", "messaging"),
    ("communication.update", "Update Communication", "Edit communication records", "communication", "update", "messaging"),
    ("communication.delete", "Delete Communication", "Remove communication records", "communication", "delete", "messaging"),
    ("communication.send", "Send Communication", "Send communications (email/SMS/WhatsApp)", "communication", "create", "messaging"),
    # Brand trust
    ("brand_trust.read", "Read Brand Trust", "View brand-trust industries and questions", "brand_trust", "read", "marketing"),
    ("brand_trust.create", "Create Brand Trust", "Create brand-trust questions", "brand_trust", "create", "marketing"),
    ("brand_trust.update", "Update Brand Trust", "Edit brand-trust questions", "brand_trust", "update", "marketing"),
    # Bulk import / export
    ("bulk_export.read", "Read Bulk Exports", "View bulk export jobs and templates", "bulk_export", "read", "data"),
    ("bulk_export.create", "Create Bulk Export", "Trigger a bulk export", "bulk_export", "create", "data"),
    ("bulk_import.read", "Read Bulk Imports", "View bulk import jobs and templates", "bulk_import", "read", "data"),
    ("bulk_import.create", "Create Bulk Import", "Upload and run a bulk import", "bulk_import", "create", "data"),
    # Tax & charges
    ("charge_template.read", "Read Charge Templates", "View tax/charge templates", "charge_template", "read", "taxes"),
    ("charge_template.create", "Create Charge Template", "Create a tax/charge template", "charge_template", "create", "taxes"),
    ("charge_template.update", "Update Charge Template", "Edit a tax/charge template", "charge_template", "update", "taxes"),
    ("charge_template.delete", "Delete Charge Template", "Remove a tax/charge template", "charge_template", "delete", "taxes"),
    # Short URLs
    ("short_url.read", "Read Short URLs", "View short URL records", "short_url", "read", "marketing"),
    ("short_url.create", "Create Short URL", "Create a short URL", "short_url", "create", "marketing"),
    ("short_url.update", "Update Short URL", "Edit a short URL", "short_url", "update", "marketing"),
    ("short_url.delete", "Delete Short URL", "Remove a short URL", "short_url", "delete", "marketing"),
    # Document numbering
    ("document_numbering.read", "Read Document Numbering", "View document numbering sequences", "document_numbering", "read", "settings"),
    ("document_numbering.update", "Update Document Numbering", "Edit document numbering sequences", "document_numbering", "update", "settings"),
    # Pick settings
    ("pick_setting.read", "Read Pick Settings", "View pick-list configuration", "pick_setting", "read", "settings"),
    ("pick_setting.update", "Update Pick Settings", "Edit pick-list configuration", "pick_setting", "update", "settings"),
    # QSeal / landing pages (referenced by seed templates; ensure they exist)
    ("qseal.read", "Read QSeal", "View QSeal parameters and tracks", "qseal", "read", "wms"),
    ("qseal.create", "Create QSeal", "Create QSeal parameters", "qseal", "create", "wms"),
    ("qseal.update", "Update QSeal", "Edit QSeal parameters", "qseal", "update", "wms"),
    ("qseal.delete", "Delete QSeal", "Remove QSeal parameters", "qseal", "delete", "wms"),
    ("qseal.manage", "Manage QSeal", "Full QSeal administration", "qseal", "manage", "wms"),
    ("landing_page.read", "Read Landing Pages", "View landing page configs", "landing_page", "read", "marketing"),
    ("landing_page.create", "Create Landing Page", "Create a landing page config", "landing_page", "create", "marketing"),
    ("landing_page.update", "Update Landing Page", "Edit a landing page config", "landing_page", "update", "marketing"),
    ("landing_page.delete", "Delete Landing Page", "Remove a landing page config", "landing_page", "delete", "marketing"),
    ("landing_page.manage", "Manage Landing Pages", "Full landing page administration", "landing_page", "manage", "marketing"),
]

# Which preloaded role codes receive each permission. Admin-type roles get
# everything (they bypass RBAC anyway, but keeping the role templates complete
# lets admins clone/derive roles). WMS roles get only the QSeal codes.
ADMIN_ROLES = ["super_admin", "org_admin", "organization_admin", "owner"]
WMS_ROLES = ["wms_admin", "wms_manager"]

ASSIGNMENTS: dict[str, list[str]] = {
    code: (ADMIN_ROLES + (WMS_ROLES if code.startswith("qseal.") else []))
    for code, *_ in PERMISSIONS
}

_INSERT_PERMISSION = text(
    """
    INSERT INTO permissions (
        id, code, name, description, resource, action, module, category,
        is_active, extra_data, created_at, updated_at
    )
    SELECT gen_random_uuid(), :code, :name, :description,
           CAST(:resource AS resourcetype),
           CAST(:action AS actiontype),
           'core', :category, true, '{}', now(), now()
    WHERE NOT EXISTS (SELECT 1 FROM permissions WHERE code = :code)
    """
)

_INSERT_ROLE_PERMISSION = text(
    """
    INSERT INTO role_permissions (id, role_id, permission_id)
    SELECT gen_random_uuid(), roles.id, permissions.id
    FROM roles, permissions
    WHERE roles.code = :role_code AND permissions.code = :permission_code
    AND NOT EXISTS (
        SELECT 1 FROM role_permissions
        WHERE role_permissions.role_id = roles.id
          AND role_permissions.permission_id = permissions.id
    )
    """
)


def _bind_engine(bind):
    """Return a raw Engine from an Alembic bind (Connection or Engine)."""
    return getattr(bind, "engine", bind)


def upgrade():
    bind = op.get_bind()
    engine = _bind_engine(bind)

    # ``ALTER TYPE ... ADD VALUE`` cannot run in the same transaction that
    # later casts to the new label (same split as migrations 020/022).
    with engine.connect() as probe:
        type_exists = (
            probe.execute(
                text("SELECT 1 FROM pg_type WHERE typname = 'resourcetype'")
            ).scalar()
            is not None
        )

    add_value_sql = " ".join(
        f"ALTER TYPE resourcetype ADD VALUE IF NOT EXISTS '{value}';"
        for value in NEW_RESOURCE_TYPES
    )
    if type_exists:
        with engine.execution_options(isolation_level="AUTOCOMMIT").connect() as conn:
            conn.execute(text(add_value_sql))
    else:
        op.execute(text(add_value_sql))

    session = Session(bind=bind)
    try:
        for code, name, description, resource, action, category in PERMISSIONS:
            session.execute(
                _INSERT_PERMISSION,
                {
                    "code": code,
                    "name": name,
                    "description": description,
                    "resource": resource,
                    "action": action,
                    "category": category,
                },
            )

        for permission_code, role_codes in ASSIGNMENTS.items():
            for role_code in role_codes:
                session.execute(
                    _INSERT_ROLE_PERMISSION,
                    {"role_code": role_code, "permission_code": permission_code},
                )
        session.commit()
    finally:
        session.close()


def downgrade():
    session = Session(bind=op.get_bind())
    try:
        codes = [row[0] for row in PERMISSIONS]
        # Do not delete role_permissions: seed data may have granted these to
        # the same roles independently (mirrors migrations 019/022).
        session.execute(
            text(
                "DELETE FROM permissions WHERE code = ANY(:codes) "
                "AND NOT EXISTS ("
                "  SELECT 1 FROM role_permissions rp "
                "  WHERE rp.permission_id = permissions.id"
                ")"
            ),
            {"codes": codes},
        )
        session.commit()
    finally:
        session.close()
