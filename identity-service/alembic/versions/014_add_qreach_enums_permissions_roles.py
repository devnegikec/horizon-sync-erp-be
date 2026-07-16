"""Add QReach enum values + seed permissions and default roles

Revision ID: 014
Revises: 013
Create Date: 2026-07-16

1. Adds QReach-specific values to resourcetype and actiontype PostgreSQL enums
2. Seeds 87 QReach RBAC permissions across 14 resource types
3. Creates 6 default QReach roles in the master organization
"""

import uuid
from datetime import UTC, datetime

from sqlalchemy import text

from alembic import op

revision = "014"
down_revision = "013"
branch_labels = None
depends_on = None

# ── Permission definitions ────────────────────────────────────────────────────

PERMISSION_DEFS = [
    # Campaign Management (8)
    (
        "campaign.create",
        "Create Campaign",
        "Create new campaigns",
        "campaign",
        "create",
        "qreach",
        "campaign",
    ),
    (
        "campaign.read",
        "View Campaigns",
        "View campaign list and details",
        "campaign",
        "read",
        "qreach",
        "campaign",
    ),
    (
        "campaign.update",
        "Update Campaign",
        "Update campaign configuration",
        "campaign",
        "update",
        "qreach",
        "campaign",
    ),
    (
        "campaign.delete",
        "Delete Campaign",
        "Delete/soft-delete campaigns",
        "campaign",
        "delete",
        "qreach",
        "campaign",
    ),
    (
        "campaign.clone",
        "Clone Campaign",
        "Clone existing campaigns",
        "campaign",
        "manage",
        "qreach",
        "campaign",
    ),
    (
        "campaign.manage_status",
        "Manage Campaign Status",
        "Activate/Pause/End campaign",
        "campaign",
        "manage",
        "qreach",
        "campaign",
    ),
    (
        "campaign.qr_preview",
        "QR Design Preview",
        "Generate QR design preview",
        "campaign",
        "read",
        "qreach",
        "campaign",
    ),
    (
        "campaign.qr_download",
        "Download QR Sheets",
        "Download QR code sheets",
        "campaign",
        "export",
        "qreach",
        "campaign",
    ),
    # Prize Management (4)
    (
        "prize.create",
        "Create Prize",
        "Add prize to campaign",
        "campaign",
        "create",
        "qreach",
        "prize",
    ),
    (
        "prize.read",
        "View Prizes",
        "View campaign prizes",
        "campaign",
        "read",
        "qreach",
        "prize",
    ),
    (
        "prize.update",
        "Update Prize",
        "Update prize configuration",
        "campaign",
        "update",
        "qreach",
        "prize",
    ),
    (
        "prize.delete",
        "Delete Prize",
        "Remove prize from campaign",
        "campaign",
        "delete",
        "qreach",
        "prize",
    ),
    # Lead Management (11)
    (
        "lead.create",
        "Create Lead",
        "Create leads manually",
        "lead",
        "create",
        "qreach",
        "lead",
    ),
    (
        "lead.read",
        "View Leads",
        "View lead list and details",
        "lead",
        "read",
        "qreach",
        "lead",
    ),
    (
        "lead.update",
        "Update Lead",
        "Update lead information",
        "lead",
        "update",
        "qreach",
        "lead",
    ),
    ("lead.delete", "Delete Lead", "Delete leads", "lead", "delete", "qreach", "lead"),
    (
        "lead.archive",
        "Archive Lead",
        "Archive/unarchive leads",
        "lead",
        "archive",
        "qreach",
        "lead",
    ),
    (
        "lead.import",
        "Import Leads",
        "Import leads from file",
        "lead",
        "import",
        "qreach",
        "lead",
    ),
    (
        "lead.export",
        "Export Leads",
        "Export leads to file",
        "lead",
        "export",
        "qreach",
        "lead",
    ),
    (
        "lead.send_sms",
        "Send SMS to Lead",
        "Send SMS to individual lead",
        "lead",
        "send",
        "qreach",
        "lead",
    ),
    (
        "lead.send_email",
        "Email Lead",
        "Email share lead info",
        "lead",
        "send",
        "qreach",
        "lead",
    ),
    (
        "lead.blocklist",
        "Manage Blocklist",
        "Manage blocklisted numbers",
        "lead",
        "manage",
        "qreach",
        "lead",
    ),
    (
        "lead.note",
        "Manage Lead Notes",
        "Add/edit/delete lead notes",
        "lead",
        "manage",
        "qreach",
        "lead",
    ),
    # Tag Management (6)
    ("tag.create", "Create Tag", "Create tags", "lead", "create", "qreach", "tag"),
    ("tag.read", "View Tags", "View tags", "lead", "read", "qreach", "tag"),
    (
        "tag.update",
        "Update Tag",
        "Update tag details",
        "lead",
        "update",
        "qreach",
        "tag",
    ),
    ("tag.delete", "Delete Tag", "Delete tags", "lead", "delete", "qreach", "tag"),
    (
        "tag.assign",
        "Assign Tags",
        "Assign tags to leads",
        "lead",
        "assign",
        "qreach",
        "tag",
    ),
    (
        "tag.unassign",
        "Unassign Tags",
        "Unassign tags from leads",
        "lead",
        "assign",
        "qreach",
        "tag",
    ),
    # Coupon Management (4)
    (
        "coupon.read",
        "View Coupons",
        "View coupon list and details",
        "coupon",
        "read",
        "qreach",
        "coupon",
    ),
    (
        "coupon.verify",
        "Verify Coupon",
        "Verify coupon validity",
        "coupon",
        "read",
        "qreach",
        "coupon",
    ),
    (
        "coupon.redeem",
        "Redeem Coupon",
        "Redeem a coupon",
        "coupon",
        "execute",
        "qreach",
        "coupon",
    ),
    (
        "coupon.generate",
        "Generate Coupon",
        "Generate coupons (consumer API)",
        "coupon",
        "create",
        "qreach",
        "coupon",
    ),
    # SMS Management (10)
    (
        "sms.template_create",
        "Create SMS Template",
        "Create SMS templates",
        "sms",
        "create",
        "qreach",
        "sms",
    ),
    (
        "sms.template_read",
        "View SMS Templates",
        "View SMS templates",
        "sms",
        "read",
        "qreach",
        "sms",
    ),
    (
        "sms.template_update",
        "Update SMS Template",
        "Update SMS templates",
        "sms",
        "update",
        "qreach",
        "sms",
    ),
    (
        "sms.template_delete",
        "Delete SMS Template",
        "Delete SMS templates",
        "sms",
        "delete",
        "qreach",
        "sms",
    ),
    (
        "sms.credit_read",
        "View SMS Credits",
        "View SMS credit balance",
        "sms",
        "read",
        "qreach",
        "sms",
    ),
    (
        "sms.credit_add",
        "Add SMS Credits",
        "Add SMS credits",
        "sms",
        "create",
        "qreach",
        "sms",
    ),
    (
        "sms.send",
        "Send Bulk SMS",
        "Send bulk SMS messages",
        "sms",
        "send",
        "qreach",
        "sms",
    ),
    (
        "sms.schedule",
        "Schedule SMS",
        "Schedule SMS delivery",
        "sms",
        "schedule",
        "qreach",
        "sms",
    ),
    (
        "sms.report_read",
        "View SMS Reports",
        "View SMS delivery reports",
        "sms",
        "read",
        "qreach",
        "sms",
    ),
    (
        "sms.report_download",
        "Download SMS Reports",
        "Download SMS reports",
        "sms",
        "export",
        "qreach",
        "sms",
    ),
    # WhatsApp Management (12)
    (
        "whatsapp.template_create",
        "Create WhatsApp Template",
        "Create WhatsApp templates",
        "whatsapp",
        "create",
        "qreach",
        "whatsapp",
    ),
    (
        "whatsapp.template_read",
        "View WhatsApp Templates",
        "View WhatsApp templates",
        "whatsapp",
        "read",
        "qreach",
        "whatsapp",
    ),
    (
        "whatsapp.template_update",
        "Update WhatsApp Template",
        "Update WhatsApp templates",
        "whatsapp",
        "update",
        "qreach",
        "whatsapp",
    ),
    (
        "whatsapp.template_delete",
        "Delete WhatsApp Template",
        "Delete WhatsApp templates",
        "whatsapp",
        "delete",
        "qreach",
        "whatsapp",
    ),
    (
        "whatsapp.media_upload",
        "Upload WhatsApp Media",
        "Upload media for templates",
        "whatsapp",
        "create",
        "qreach",
        "whatsapp",
    ),
    (
        "whatsapp.credit_read",
        "View WhatsApp Credits",
        "View WhatsApp credit balance",
        "whatsapp",
        "read",
        "qreach",
        "whatsapp",
    ),
    (
        "whatsapp.credit_add",
        "Add WhatsApp Credits",
        "Add WhatsApp credits",
        "whatsapp",
        "create",
        "qreach",
        "whatsapp",
    ),
    (
        "whatsapp.send",
        "Send Bulk WhatsApp",
        "Send bulk WhatsApp messages",
        "whatsapp",
        "send",
        "qreach",
        "whatsapp",
    ),
    (
        "whatsapp.schedule",
        "Schedule WhatsApp",
        "Schedule WhatsApp delivery",
        "whatsapp",
        "schedule",
        "qreach",
        "whatsapp",
    ),
    (
        "whatsapp.test",
        "Test WhatsApp",
        "Send test WhatsApp messages",
        "whatsapp",
        "send",
        "qreach",
        "whatsapp",
    ),
    (
        "whatsapp.report_read",
        "View WhatsApp Reports",
        "View WhatsApp reports",
        "whatsapp",
        "read",
        "qreach",
        "whatsapp",
    ),
    (
        "whatsapp.report_download",
        "Download WhatsApp Reports",
        "Download WhatsApp reports",
        "whatsapp",
        "export",
        "qreach",
        "whatsapp",
    ),
    # RCS Management (10)
    (
        "rcs.template_create",
        "Create RCS Template",
        "Create RCS templates",
        "rcs",
        "create",
        "qreach",
        "rcs",
    ),
    (
        "rcs.template_read",
        "View RCS Templates",
        "View RCS templates",
        "rcs",
        "read",
        "qreach",
        "rcs",
    ),
    (
        "rcs.template_update",
        "Update RCS Template",
        "Update RCS templates",
        "rcs",
        "update",
        "qreach",
        "rcs",
    ),
    (
        "rcs.template_delete",
        "Delete RCS Template",
        "Delete RCS templates",
        "rcs",
        "delete",
        "qreach",
        "rcs",
    ),
    (
        "rcs.credit_read",
        "View RCS Credits",
        "View RCS credit balance",
        "rcs",
        "read",
        "qreach",
        "rcs",
    ),
    (
        "rcs.credit_add",
        "Add RCS Credits",
        "Add RCS credits",
        "rcs",
        "create",
        "qreach",
        "rcs",
    ),
    (
        "rcs.send",
        "Send Bulk RCS",
        "Send bulk RCS messages",
        "rcs",
        "send",
        "qreach",
        "rcs",
    ),
    ("rcs.test", "Test RCS", "Send test RCS messages", "rcs", "send", "qreach", "rcs"),
    (
        "rcs.report_read",
        "View RCS Reports",
        "View RCS delivery reports",
        "rcs",
        "read",
        "qreach",
        "rcs",
    ),
    (
        "rcs.report_download",
        "Download RCS Reports",
        "Download RCS reports",
        "rcs",
        "export",
        "qreach",
        "rcs",
    ),
    # Analytics (6)
    (
        "analytics.scan_read",
        "View Scan Analytics",
        "View scan analytics",
        "analytics",
        "read",
        "qreach",
        "analytics",
    ),
    (
        "analytics.insight_read",
        "View Insights",
        "View coupon sent vs redeemed",
        "analytics",
        "read",
        "qreach",
        "analytics",
    ),
    (
        "analytics.business_read",
        "View Business Dashboard",
        "View business/POS dashboard",
        "analytics",
        "read",
        "qreach",
        "analytics",
    ),
    (
        "analytics.product_read",
        "View Product Analytics",
        "View product-level scans",
        "analytics",
        "read",
        "qreach",
        "analytics",
    ),
    (
        "analytics.realtime_read",
        "View Real-time Feed",
        "View real-time scan feed",
        "analytics",
        "read",
        "qreach",
        "analytics",
    ),
    (
        "analytics.export",
        "Download Analytics",
        "Export analytics reports",
        "analytics",
        "export",
        "qreach",
        "analytics",
    ),
    # Brand Management (4)
    (
        "brand.create",
        "Create Brand",
        "Create brands",
        "brand",
        "create",
        "qreach",
        "brand",
    ),
    ("brand.read", "View Brands", "View brands", "brand", "read", "qreach", "brand"),
    (
        "brand.update",
        "Update Brand",
        "Update brand details",
        "brand",
        "update",
        "qreach",
        "brand",
    ),
    (
        "brand.delete",
        "Delete Brand",
        "Delete brands",
        "brand",
        "delete",
        "qreach",
        "brand",
    ),
    # QR Product Management (8)
    (
        "qr_product.create",
        "Create QR Product",
        "Create QR products",
        "qr_product",
        "create",
        "qreach",
        "qr_product",
    ),
    (
        "qr_product.read",
        "View QR Products",
        "View QR products",
        "qr_product",
        "read",
        "qreach",
        "qr_product",
    ),
    (
        "qr_product.update",
        "Update QR Product",
        "Update QR products",
        "qr_product",
        "update",
        "qreach",
        "qr_product",
    ),
    (
        "qr_product.delete",
        "Delete QR Product",
        "Delete QR products",
        "qr_product",
        "delete",
        "qreach",
        "qr_product",
    ),
    (
        "qr_product.block_create",
        "Create QR Block",
        "Create QR code blocks/batches",
        "qr_product",
        "create",
        "qreach",
        "qr_product",
    ),
    (
        "qr_product.block_download",
        "Download QR Block",
        "Download QR code sheets",
        "qr_product",
        "export",
        "qreach",
        "qr_product",
    ),
    (
        "qr_product.activation",
        "Manage Activation",
        "Configure activation parameters",
        "qr_product",
        "manage",
        "qreach",
        "qr_product",
    ),
    (
        "qr_product.setting_manage",
        "Manage Product Settings",
        "Manage product settings",
        "qr_product",
        "manage",
        "qreach",
        "qr_product",
    ),
    # Warranty Management (4)
    (
        "warranty.create",
        "Create Warranty",
        "Create warranty records",
        "warranty",
        "create",
        "qreach",
        "warranty",
    ),
    (
        "warranty.read",
        "View Warranties",
        "View warranty records",
        "warranty",
        "read",
        "qreach",
        "warranty",
    ),
    (
        "warranty.update",
        "Update Warranty",
        "Update warranty records",
        "warranty",
        "update",
        "qreach",
        "warranty",
    ),
    (
        "warranty.period_manage",
        "Manage Warranty Periods",
        "Manage warranty periods",
        "warranty",
        "manage",
        "qreach",
        "warranty",
    ),
    # Other Resources
    (
        "destination.create",
        "Create Destination",
        "Create destination markets",
        "destination",
        "create",
        "qreach",
        "destination",
    ),
    (
        "destination.read",
        "View Destinations",
        "View destination markets",
        "destination",
        "read",
        "qreach",
        "destination",
    ),
    (
        "destination.update",
        "Update Destination",
        "Update destination markets",
        "destination",
        "update",
        "qreach",
        "destination",
    ),
    (
        "destination.delete",
        "Delete Destination",
        "Delete destination markets",
        "destination",
        "delete",
        "qreach",
        "destination",
    ),
    (
        "short_url.create",
        "Create Short URL",
        "Create short URLs",
        "short_url",
        "create",
        "qreach",
        "short_url",
    ),
    (
        "short_url.read",
        "View Short URLs",
        "View short URLs",
        "short_url",
        "read",
        "qreach",
        "short_url",
    ),
    (
        "short_url.update",
        "Update Short URL",
        "Update short URLs",
        "short_url",
        "update",
        "qreach",
        "short_url",
    ),
    (
        "short_url.delete",
        "Delete Short URL",
        "Delete short URLs",
        "short_url",
        "delete",
        "qreach",
        "short_url",
    ),
    (
        "api_key.create",
        "Generate API Key",
        "Generate API keys",
        "api_key",
        "create",
        "qreach",
        "developer",
    ),
    (
        "api_key.read",
        "View API Keys",
        "View API keys",
        "api_key",
        "read",
        "qreach",
        "developer",
    ),
    (
        "api_key.revoke",
        "Revoke API Key",
        "Revoke API keys",
        "api_key",
        "delete",
        "qreach",
        "developer",
    ),
]

# ── Default QReach Roles ──────────────────────────────────────────────────────

ROLE_DEFS = [
    (
        "qreach_admin",
        "QReach Admin",
        "Full access to all QReach features: campaigns, leads, messaging, analytics, products, brands",
        90,
        [
            "campaign.create",
            "campaign.read",
            "campaign.update",
            "campaign.delete",
            "campaign.clone",
            "campaign.manage_status",
            "campaign.qr_preview",
            "campaign.qr_download",
            "prize.create",
            "prize.read",
            "prize.update",
            "prize.delete",
            "lead.create",
            "lead.read",
            "lead.update",
            "lead.delete",
            "lead.archive",
            "lead.import",
            "lead.export",
            "lead.send_sms",
            "lead.send_email",
            "lead.blocklist",
            "lead.note",
            "tag.create",
            "tag.read",
            "tag.update",
            "tag.delete",
            "tag.assign",
            "tag.unassign",
            "coupon.read",
            "coupon.verify",
            "coupon.redeem",
            "coupon.generate",
            "sms.template_create",
            "sms.template_read",
            "sms.template_update",
            "sms.template_delete",
            "sms.credit_read",
            "sms.credit_add",
            "sms.send",
            "sms.schedule",
            "sms.report_read",
            "sms.report_download",
            "whatsapp.template_create",
            "whatsapp.template_read",
            "whatsapp.template_update",
            "whatsapp.template_delete",
            "whatsapp.media_upload",
            "whatsapp.credit_read",
            "whatsapp.credit_add",
            "whatsapp.send",
            "whatsapp.schedule",
            "whatsapp.test",
            "whatsapp.report_read",
            "whatsapp.report_download",
            "rcs.template_create",
            "rcs.template_read",
            "rcs.template_update",
            "rcs.template_delete",
            "rcs.credit_read",
            "rcs.credit_add",
            "rcs.send",
            "rcs.test",
            "rcs.report_read",
            "rcs.report_download",
            "analytics.scan_read",
            "analytics.insight_read",
            "analytics.business_read",
            "analytics.product_read",
            "analytics.realtime_read",
            "analytics.export",
            "brand.create",
            "brand.read",
            "brand.update",
            "brand.delete",
            "qr_product.create",
            "qr_product.read",
            "qr_product.update",
            "qr_product.delete",
            "qr_product.block_create",
            "qr_product.block_download",
            "qr_product.activation",
            "qr_product.setting_manage",
            "warranty.create",
            "warranty.read",
            "warranty.update",
            "warranty.period_manage",
            "destination.create",
            "destination.read",
            "destination.update",
            "destination.delete",
            "short_url.create",
            "short_url.read",
            "short_url.update",
            "short_url.delete",
            "api_key.create",
            "api_key.read",
            "api_key.revoke",
        ],
    ),
    (
        "campaign_manager",
        "Campaign Manager",
        "Manage campaigns, leads, messaging, and view analytics",
        70,
        [
            "campaign.create",
            "campaign.read",
            "campaign.update",
            "campaign.delete",
            "campaign.clone",
            "campaign.manage_status",
            "prize.create",
            "prize.read",
            "prize.update",
            "prize.delete",
            "lead.create",
            "lead.read",
            "lead.update",
            "lead.delete",
            "lead.archive",
            "lead.import",
            "lead.export",
            "lead.send_sms",
            "lead.send_email",
            "lead.blocklist",
            "lead.note",
            "tag.create",
            "tag.read",
            "tag.update",
            "tag.delete",
            "tag.assign",
            "tag.unassign",
            "coupon.read",
            "coupon.verify",
            "coupon.redeem",
            "coupon.generate",
            "sms.template_create",
            "sms.template_read",
            "sms.template_update",
            "sms.template_delete",
            "sms.credit_read",
            "sms.credit_add",
            "sms.send",
            "sms.schedule",
            "sms.report_read",
            "sms.report_download",
            "whatsapp.template_create",
            "whatsapp.template_read",
            "whatsapp.template_update",
            "whatsapp.template_delete",
            "whatsapp.media_upload",
            "whatsapp.credit_read",
            "whatsapp.credit_add",
            "whatsapp.send",
            "whatsapp.schedule",
            "whatsapp.test",
            "whatsapp.report_read",
            "whatsapp.report_download",
            "rcs.template_create",
            "rcs.template_read",
            "rcs.template_update",
            "rcs.template_delete",
            "rcs.credit_read",
            "rcs.credit_add",
            "rcs.send",
            "rcs.test",
            "rcs.report_read",
            "rcs.report_download",
            "analytics.scan_read",
            "analytics.insight_read",
            "analytics.business_read",
            "analytics.product_read",
            "analytics.realtime_read",
            "analytics.export",
            "short_url.create",
            "short_url.read",
            "short_url.update",
            "short_url.delete",
        ],
    ),
    (
        "lead_manager",
        "Lead Manager",
        "Manage leads, tags, and send individual messages",
        50,
        [
            "campaign.read",
            "lead.create",
            "lead.read",
            "lead.update",
            "lead.delete",
            "lead.archive",
            "lead.import",
            "lead.export",
            "lead.send_sms",
            "lead.send_email",
            "lead.blocklist",
            "lead.note",
            "tag.create",
            "tag.read",
            "tag.update",
            "tag.delete",
            "tag.assign",
            "tag.unassign",
            "coupon.read",
            "sms.send",
            "whatsapp.send",
        ],
    ),
    (
        "analytics_viewer",
        "Analytics Viewer",
        "Read-only access to analytics and campaign data",
        40,
        [
            "campaign.read",
            "lead.read",
            "coupon.read",
            "analytics.scan_read",
            "analytics.insight_read",
            "analytics.business_read",
            "analytics.product_read",
            "analytics.realtime_read",
            "analytics.export",
        ],
    ),
    (
        "qr_product_manager",
        "QR Product Manager",
        "Manage QR products, blocks, brands, warranties, destinations",
        60,
        [
            "qr_product.create",
            "qr_product.read",
            "qr_product.update",
            "qr_product.delete",
            "qr_product.block_create",
            "qr_product.block_download",
            "qr_product.activation",
            "qr_product.setting_manage",
            "brand.read",
            "brand.create",
            "brand.update",
            "brand.delete",
            "warranty.create",
            "warranty.read",
            "warranty.update",
            "warranty.period_manage",
            "destination.create",
            "destination.read",
            "destination.update",
            "destination.delete",
            "short_url.create",
            "short_url.read",
            "short_url.update",
            "short_url.delete",
        ],
    ),
    (
        "qreach_developer",
        "QReach Developer",
        "API key management and read-only access to campaigns and analytics",
        30,
        [
            "api_key.create",
            "api_key.read",
            "api_key.revoke",
            "campaign.read",
            "analytics.scan_read",
            "analytics.insight_read",
            "short_url.create",
            "short_url.read",
        ],
    ),
]


def upgrade():
    conn = op.get_bind()

    # ── Step 1: Add enum values ──────────────────────────────────────────
    for val in [
        "campaign",
        "lead",
        "coupon",
        "brand",
        "qr_product",
        "warranty",
        "sms",
        "whatsapp",
        "rcs",
        "analytics",
        "short_url",
        "destination",
        "store",
        "public_submission",
        "api_key",
    ]:
        conn.execute(text(f"ALTER TYPE resourcetype ADD VALUE IF NOT EXISTS '{val}'"))

    for val in ["export", "send", "schedule", "import", "archive", "assign"]:
        conn.execute(text(f"ALTER TYPE actiontype ADD VALUE IF NOT EXISTS '{val}'"))

    # Commit so new enum values are visible to subsequent INSERTs
    conn.execute(text("COMMIT"))

    # ── Step 2: Seed permissions ─────────────────────────────────────────
    now = datetime.now(UTC).isoformat()
    created = 0
    skipped = 0
    for code, name, desc, resource, action, module, category in PERMISSION_DEFS:
        existing = conn.execute(
            text("SELECT id FROM permissions WHERE code = :code"),
            {"code": code},
        ).fetchone()
        if existing:
            skipped += 1
            continue
        conn.execute(
            text(
                """
                INSERT INTO permissions (id, code, name, description, resource, action,
                    module, category, is_active, extra_data, created_at, updated_at)
                VALUES (gen_random_uuid(), :code, :name, :desc, :resource, :action,
                    :module, :category, true, '{}', :now, :now)
            """
            ),
            {
                "code": code,
                "name": name,
                "desc": desc,
                "resource": resource,
                "action": action,
                "module": module,
                "category": category,
                "now": now,
            },
        )
        created += 1

    print(f"  QReach Permissions: {created} created, {skipped} already existed")

    # ── Step 3: Load permission ID map ───────────────────────────────────
    rows = conn.execute(
        text("SELECT code, id FROM permissions WHERE module = 'qreach'")
    ).fetchall()
    perm_id_map = {row[0]: row[1] for row in rows}

    # ── Step 4: Find master organization ────────────────────────────────
    master_org = conn.execute(
        text("SELECT id FROM organizations WHERE organization_type = 'master' LIMIT 1")
    ).fetchone()
    if not master_org:
        print("  WARNING: No master organization found — skipping role creation")
        return
    master_org_id = master_org[0]

    # ── Step 5: Seed roles ──────────────────────────────────────────────
    roles_created = 0
    roles_skipped = 0
    links_created = 0
    links_skipped = 0

    for code, name, desc, hierarchy, perm_codes in ROLE_DEFS:
        existing_role = conn.execute(
            text(
                "SELECT id FROM roles WHERE code = :code AND organization_id = :org_id"
            ),
            {"code": code, "org_id": master_org_id},
        ).fetchone()

        if existing_role:
            role_id = existing_role[0]
            roles_skipped += 1
        else:
            role_id = str(uuid.uuid4())
            conn.execute(
                text(
                    """
                    INSERT INTO roles (id, organization_id, name, code, description,
                        is_system, is_default, hierarchy_level, is_active, created_at, updated_at)
                    VALUES (:id, :org_id, :name, :code, :desc,
                        true, false, :hierarchy, true, :now, :now)
                """
                ),
                {
                    "id": role_id,
                    "org_id": master_org_id,
                    "name": name,
                    "code": code,
                    "desc": desc,
                    "hierarchy": hierarchy,
                    "now": now,
                },
            )
            roles_created += 1

        for pcode in perm_codes:
            perm_id = perm_id_map.get(pcode)
            if not perm_id:
                print(
                    f"    WARNING: permission '{pcode}' not found — skipping link for role '{code}'"
                )
                continue

            existing_link = conn.execute(
                text(
                    "SELECT 1 FROM role_permissions WHERE role_id = :rid AND permission_id = :pid"
                ),
                {"rid": role_id, "pid": perm_id},
            ).fetchone()

            if existing_link:
                links_skipped += 1
                continue

            conn.execute(
                text(
                    "INSERT INTO role_permissions (id, role_id, permission_id) VALUES (gen_random_uuid(), :rid, :pid)"
                ),
                {"rid": role_id, "pid": str(perm_id)},
            )
            links_created += 1

    print(f"  QReach Roles: {roles_created} created, {roles_skipped} already existed")
    print(
        f"  RolePermission links: {links_created} created, {links_skipped} already existed"
    )


def downgrade():
    conn = op.get_bind()

    conn.execute(
        text(
            """
            DELETE FROM role_permissions WHERE role_id IN (
                SELECT id FROM roles WHERE code IN (
                    'qreach_admin', 'campaign_manager', 'lead_manager',
                    'analytics_viewer', 'qr_product_manager', 'qreach_developer'
                )
            )
        """
        )
    )
    conn.execute(
        text(
            """
            DELETE FROM roles WHERE code IN (
                'qreach_admin', 'campaign_manager', 'lead_manager',
                'analytics_viewer', 'qr_product_manager', 'qreach_developer'
            )
        """
        )
    )
    conn.execute(text("DELETE FROM permissions WHERE module = 'qreach'"))
