"""Feature flag name constants and error codes.

Central registry of all feature flag names and related constants
used across the application. Add new flags here instead of using
raw strings in code.
"""

# ── Feature flag names ──────────────────────────────────────────────
# Invoice module
INVOICES_ENABLED = "invoices_enabled"
INVOICE_AUTO_JOURNAL_POSTING = "invoice_auto_journal_posting"

# Sidebar modules (platform app)
INVENTORY_MODULE_ENABLED = "inventory_module_enabled"

# Revenue module
REVENUE_MODULE_ENABLED = "revenue_module_enabled"

# Sourcing module
SOURCING_MODULE_ENABLED = "sourcing_module_enabled"

# Banking module
BOOK_MODULE_ENABLED = "book_module_enabled"
BOOK_CHART_OF_ACCOUNT_ENABLED = "book_chart_of_account_enabled"

# Tax module
TAXANDCHARGES_MODULE_ENABLED = "taxandcharges_module_enabled"

# Subscription module
SUBSCRIPTIONS_MODULE_ENABLED = "subscriptions_module_enabled"

# Analystics module
ANALYTICS_MODULE_ENABLED = "analytics_module_enabled"

# QSeal module
QSEAL_MODULE_ENABLED = "qseal_module_enabled"

# User module
USERS_MODULE_ENABLED = "users_module_enabled"

# Roles module
ROLES_MODULE_ENABLED = "roles_module_enabled"

# Report module
REPORTS_MODULE_ENABLED = "reports_module_enabled"

# ── Error codes ─────────────────────────────────────────────────────
FEATURE_DISABLED_CODE = "FEATURE_DISABLED"

# ── HTTP status codes ───────────────────────────────────────────────
HTTP_FEATURE_DISABLED = 423  # Locked – feature administratively disabled

# ── Default scope ───────────────────────────────────────────────────
DEFAULT_SCOPE = "GLOBAL"
