# QReach API & RBAC — Implementation Blueprint

> **Date:** 2026-07-16
> **Approach:** APIs built within core-service, existing core-db tables, identity-service for auth/RBAC
> **Status:** DRAFT — For Review

---

## Table of Contents

1. [Architecture Decisions](#1-architecture-decisions)
2. [Current State: What Already Exists](#2-current-state-what-already-exists)
3. [Database Schema Changes Needed](#3-database-schema-changes-needed)
4. [REST API Blueprint (Gap Analysis)](#4-rest-api-blueprint-gap-analysis)
5. [RBAC Permissions — Complete List](#5-rbac-permissions--complete-list)
6. [Implementation Phases](#6-implementation-phases)
7. [Open Questions for Review](#7-open-questions-for-review)

---

## 1. Architecture Decisions

| Decision                 | Choice                                                 | Rationale                                          |
| ------------------------ | ------------------------------------------------------ | -------------------------------------------------- |
| **Service location**     | APIs built inside existing `core-service`              | No new microservice; keep QReach alongside WMS/ERP |
| **Database**             | Keep tables in existing `core-db` (PostgreSQL)         | Tables already exist; no migration needed          |
| **Authentication**       | Validate JWT locally + call identity-service `/me`     | Same pattern as existing core-service endpoints    |
| **Authorization**        | RBAC via identity-service `roles`/`permissions` tables | Same `require_permission()` dependency pattern     |
| **Tenant isolation**     | `organization_id` FK on all tables (already exists)    | Consistent with rest of core-service               |
| **Consumer pages**       | Separate frontend app (already exists)                 | Not in scope for this API build                    |
| **"Tenant" terminology** | Use `organization` (from `identity_db.organizations`)  | Matches existing codebase convention               |

---

## 2. Current State: What Already Exists

### 2.1 Database Tables (All in `core-db`)

| Module                  | Tables                                                                                                                                                                                      | Migration |
| ----------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | --------- |
| **Campaigns & Coupons** | `campaigns`, `play2win_prizes`, `web_campaigns`, `campaign_tags`, `lead_tags`, `campaign_leads`, `coupons`, `coupon_unlock_logs`, `external_coupons`, `coupon_durations`, `shopify_configs` | 025       |
| **QR Products**         | `qr_products`, `qr_blocks`, `product_items`, `qr_scan_events`, `qr_activation_parameters`, `qr_activation_tracks`                                                                           | 024, 038  |
| **QR Credits**          | `qr_credit_balance`, `qr_credit_usage`, `qr_credit_ledger`                                                                                                                                  | 038       |
| **QR Product Settings** | `qr_product_settings`                                                                                                                                                                       | 033       |
| **Brands**              | `brands`                                                                                                                                                                                    | 038       |
| **Brand Trust**         | `brand_industries`, `brand_trust_questions`, `brand_trust_assessments`, `brand_trust_answers`                                                                                               | 031       |
| **Messaging**           | `message_templates`, `bulk_message_jobs`, `scheduled_messages`, `sms_reports`, `whatsapp_reports`, `rcs_reports`, `rcs_credentials`, `rcs_templates`, `message_credits`                     | 027       |
| **Warranties**          | `warranty_periods`, `warranties`                                                                                                                                                            | 026       |
| **Analytics**           | `meta_campaigns`                                                                                                                                                                            | 028       |
| **URL Shortener**       | `short_urls`                                                                                                                                                                                | 029       |
| **Destinations**        | `destination_markets`                                                                                                                                                                       | 030       |
| **Public Submissions**  | `public_submissions`                                                                                                                                                                        | 032       |

### 2.2 Existing API Endpoints

| Prefix                 | Module                   | Auth Required                       | Status                                                                |
| ---------------------- | ------------------------ | ----------------------------------- | --------------------------------------------------------------------- |
| `/campaigns`           | `campaigns.py`           | Yes (with `require_permission`)     | **Partial** — 14 routes, covers basic CRUD + prizes + leads + coupons |
| `/qr-products`         | `qr_products.py`         | Yes                                 | **Partial** — covers CRUD + blocks + scanning                         |
| `/qr-product-settings` | `qr_product_settings.py` | Yes                                 | **Partial** — CRUD                                                    |
| `/warranties`          | `warranties.py`          | Mixed (register/check public)       | **Partial**                                                           |
| `/messaging`           | `messaging.py`           | Yes                                 | **Partial** — templates, jobs, reports                                |
| `/analytics`           | `analytics.py`           | Yes                                 | **Minimal** — 10 routes, mostly Meta campaigns                        |
| `/cascade-qr`          | `cascade_qr.py`          | Yes                                 | **Exists**                                                            |
| `/short-urls`          | `short_urls.py`          | Mixed (resolve is public)           | **Exists**                                                            |
| `/destinations`        | `destinations.py`        | Yes                                 | **Exists**                                                            |
| `/brand-trust`         | `brand_trust.py`         | Mixed (industries/questions public) | **Exists**                                                            |
| `/brands`              | `brands.py`              | Yes                                 | **Partial** — only basic CRUD                                         |
| `/public`              | `public_marketing.py`    | No                                  | **Exists** — contact forms                                            |
| `/scan-events`         | `scan_events.py`         | Yes                                 | **Exists**                                                            |

### 2.3 Existing RBAC Permissions (Used in Code)

```
campaign.create    campaign.read    campaign.update    campaign.delete
brand.create       brand.read       brand.update
qr_product.create  qr_product.read  qr_product.update  qr_product.delete
warranty.create    warranty.read
```

> **Note:** These permission codes are used in `require_permission()` calls but may NOT be seeded in the identity-service `permissions` table yet. This needs verification.

### 2.4 Identity Service — ResourceType Enum (Missing QReach Resources)

The `ResourceType` enum in `identity-service/app/models/base.py` has NO QReach-specific resources. Current resources: `user`, `organization`, `team`, `role`, `permission`, `invitation`, `customer`, `sales_order`, `invoice`, `supplier`, `purchase_order`, `item`, `item_group`, `warehouse`, `stock_entry`, `batch`, `serial`, `asn_order`, `pick_list`, `receiving_slip`, `chart_of_account`, `payment`, `billing`, `report`, `reporting`, `setting`.

---

## 3. Database Schema Changes Needed

### 3.1 Tables to CREATE (Missing)

| #   | Table                    | Purpose                                                     | Priority |
| --- | ------------------------ | ----------------------------------------------------------- | -------- |
| 1   | `stores`                 | POS/store locations for business analytics dashboard        | High     |
| 2   | `schedule_reports`       | Scheduled report configurations (daily/weekly/monthly)      | Medium   |
| 3   | `qreach_api_keys`        | API keys for QReach developer portal (QSeal + QReach)       | Medium   |
| 4   | `landing_customizations` | Campaign landing page custom form configurations            | Medium   |
| 5   | `lead_notes`             | Notes/comments on leads (currently no dedicated table)      | Medium   |
| 6   | `lead_actions`           | Activity log for lead operations (archive, blocklist, etc.) | Low      |

### 3.2 Columns to ADD to Existing Tables

| Table               | New Column              | Type                     | Purpose                                                       |
| ------------------- | ----------------------- | ------------------------ | ------------------------------------------------------------- |
| `campaigns`         | `firebase_url`          | `Text`                   | QR sheet download URL (already in model but verify migration) |
| `campaigns`         | `promotional_video_url` | `Text`                   | Promotional video URL (may already exist as `media_link`)     |
| `campaign_leads`    | `marital_status`        | `String(30)`             | Marital status field                                          |
| `campaign_leads`    | `lead_owner_id`         | `UUID FK → users.id`     | Lead assignment to user                                       |
| `campaign_leads`    | `is_archived`           | `Boolean, default=False` | Soft archive for leads                                        |
| `campaign_leads`    | `is_blocklisted`        | `Boolean, default=False` | Blocklist flag                                                |
| `message_templates` | `headers`               | `JSONB`                  | WhatsApp template header configuration                        |
| `message_templates` | `footer`                | `String(256)`            | WhatsApp template footer                                      |

### 3.3 Identity Service — ResourceType Enum Additions

```python
# Add to ResourceType enum in identity-service/app/models/base.py:
CAMPAIGN = "campaign"
LEAD = "lead"
COUPON = "coupon"
BRAND = "brand"
QR_PRODUCT = "qr_product"
WARRANTY = "warranty"
MESSAGING = "messaging"
SMS = "sms"
WHATSAPP = "whatsapp"
RCS = "rcs"
ANALYTICS = "analytics"
SHORT_URL = "short_url"
DESTINATION = "destination"
STORE = "store"
PUBLIC_SUBMISSION = "public_submission"
API_KEY = "api_key"
```

### 3.4 ActionType Enum Additions

```python
# Add to ActionType enum:
EXPORT = "export"     # For downloading reports
SEND = "send"         # For SMS/WhatsApp/RCS send actions
SCHEDULE = "schedule" # For scheduling messages
IMPORT = "import"     # For lead imports
ARCHIVE = "archive"   # For archiving/unarchiving
ASSIGN = "assign"     # For tag assignment
```

---

## 4. REST API Blueprint (Gap Analysis)

### Legend

- ✅ **Done** — Already implemented
- 🔶 **Partial** — Partially implemented, needs enhancement
- ❌ **Missing** — Not yet implemented

### 4.1 Campaigns

```
✅ POST   /campaigns/                          # Create campaign
✅ GET    /campaigns/                          # List campaigns (paginated, filtered)
✅ GET    /campaigns/{id}/                     # Campaign detail
✅ PATCH  /campaigns/{id}/                     # Update campaign
✅ DELETE /campaigns/{id}/                     # Delete campaign
❌ POST   /campaigns/{id}/clone/              # Clone campaign
❌ PATCH  /campaigns/{id}/status/             # Activate/Pause/End status change
❌ GET    /campaigns/{id}/qr-preview/         # QR design preview (color, logo)
❌ GET    /campaigns/{id}/qr-download/        # Download QR sheets (.xlsx)
✅ POST   /campaigns/{id}/prizes/             # Add Play2Win prize
✅ GET    /campaigns/{id}/prizes/             # List prizes
❌ PUT    /campaigns/{id}/prizes/{prize_id}/  # Update prize
❌ DELETE /campaigns/{id}/prizes/{prize_id}/  # Delete prize
```

### 4.2 Web Campaigns (Click2Win)

```
❌ POST   /web-campaigns/                     # Create web campaign
❌ GET    /web-campaigns/                     # List web campaigns
❌ GET    /web-campaigns/{id}/                # Web campaign detail
❌ PUT    /web-campaigns/{id}/                # Update web campaign
❌ DELETE /web-campaigns/{id}/                # Delete web campaign
❌ GET    /web-campaigns/{id}/external-coupons/ # List external coupons
❌ POST   /web-campaigns/{id}/external-coupons/ # Upload external coupons
```

### 4.3 Leads

```
✅ GET    /campaigns/leads/                   # List leads (paginated, filtered)
✅ POST   /campaigns/leads/                   # Create lead manually
❌ GET    /campaigns/leads/{id}/              # Lead detail
❌ PUT    /campaigns/leads/{id}/              # Update lead
❌ DELETE /campaigns/leads/{id}/              # Delete lead
❌ POST   /campaigns/leads/bulk-delete/       # Bulk delete leads
❌ POST   /campaigns/leads/{id}/archive/      # Archive lead
❌ POST   /campaigns/leads/{id}/unarchive/    # Unarchive lead
❌ POST   /campaigns/leads/{id}/notes/        # Add note to lead
❌ PUT    /campaigns/leads/{id}/notes/{note_id}/ # Update note
❌ DELETE /campaigns/leads/{id}/notes/{note_id}/ # Delete note
❌ POST   /campaigns/leads/{id}/send-sms/     # Send SMS to single lead
❌ POST   /campaigns/leads/{id}/send-email/   # Email share lead info
❌ POST   /campaigns/leads/import/            # Import leads from file
❌ GET    /campaigns/leads/export/            # Export leads to XLS/CSV
❌ POST   /campaigns/leads/{id}/blocklist/    # Blocklist phone number
❌ DELETE /campaigns/leads/{id}/blocklist/    # Remove from blocklist
```

### 4.4 Tags

```
❌ POST   /tags/                              # Create tag
❌ GET    /tags/                              # List tags
❌ PUT    /tags/{id}/                         # Update tag
❌ DELETE /tags/{id}/                         # Delete tag
❌ POST   /tags/assign/                       # Assign tag(s) to leads
❌ POST   /tags/unassign/                     # Unassign tag(s) from leads
❌ POST   /tags/optimize/                     # Optimize/merge tags
❌ POST   /tags/{id}/clear/                   # Clear tag from all leads
```

### 4.5 SMS

```
❌ POST   /sms/templates/                     # Create SMS template
❌ GET    /sms/templates/                     # List SMS templates
❌ GET    /sms/templates/{id}/                # Template detail
❌ PUT    /sms/templates/{id}/                # Update template
❌ DELETE /sms/templates/{id}/                # Delete template
🔶 GET    /messaging/credits/                 # View credits (exists in messaging)
🔶 POST   /messaging/credits/                 # Add credits (exists in messaging)
❌ POST   /sms/send/                          # Send bulk SMS
❌ POST   /sms/schedule/                      # Schedule SMS
❌ GET    /sms/summary/                       # SMS campaign summary
❌ GET    /sms/reports/                       # SMS delivery reports
❌ GET    /sms/reports/{id}/                  # Report detail
❌ GET    /sms/reports/download/              # Download reports
```

### 4.6 WhatsApp

```
❌ POST   /whatsapp/templates/                # Create WhatsApp template
❌ GET    /whatsapp/templates/                # List WhatsApp templates
❌ GET    /whatsapp/templates/{id}/           # Template detail
❌ PUT    /whatsapp/templates/{id}/           # Update template
❌ DELETE /whatsapp/templates/{id}/           # Delete template
❌ POST   /whatsapp/media/upload/             # Upload media file
🔶 GET    /messaging/credits/                 # View credits (exists)
🔶 POST   /messaging/credits/                 # Add credits (exists)
❌ POST   /whatsapp/send/                     # Send bulk WhatsApp
❌ POST   /whatsapp/schedule/                 # Schedule WhatsApp
❌ GET    /whatsapp/summary/                  # Summary dashboard
❌ GET    /whatsapp/reports/                  # Reports
❌ POST   /whatsapp/test/                     # Send test message
❌ POST   /whatsapp/templates/download/       # Download template data
❌ POST   /whatsapp/{id}/suspend/             # Suspend running campaign
```

### 4.7 RCS

```
❌ POST   /rcs/templates/                     # Create RCS template
❌ GET    /rcs/templates/                     # List RCS templates
❌ GET    /rcs/templates/{id}/                # Template detail
❌ PUT    /rcs/templates/{id}/                # Update template
❌ DELETE /rcs/templates/{id}/                # Delete template
❌ GET    /rcs/credits/                       # View RCS credits
❌ POST   /rcs/credits/                       # Add RCS credits
❌ POST   /rcs/send/                          # Send bulk RCS
❌ POST   /rcs/test/                          # Test RCS message
❌ GET    /rcs/summary/                       # Summary dashboard
❌ GET    /rcs/reports/                       # Reports
❌ GET    /rcs/reports/download/              # Download reports
```

### 4.8 Analytics (QReach-specific)

```
❌ GET    /analytics/scans/                   # Scan analytics with filters
❌ GET    /analytics/scans/daily/             # Daily scan trends
❌ GET    /analytics/scans/hourly/            # Hourly distribution
❌ GET    /analytics/scans/weekly/            # Day-of-week distribution
❌ GET    /analytics/scans/geo/               # Geographic distribution (state/city)
❌ GET    /analytics/scans/isp/               # ISP distribution
❌ GET    /analytics/scans/device/            # Device/OS distribution
❌ GET    /analytics/insights/                # Coupons sent vs redeemed
❌ GET    /analytics/insights/redemption/     # Per-campaign redemption rates
❌ GET    /analytics/business/                # Business/POS dashboard
❌ GET    /analytics/product-scans/           # Product-level scan analytics
❌ GET    /analytics/real-time/               # Real-time scan feed (SSE)
✅ GET    /analytics/campaigns-by-type/       # Get campaigns by type (exists)
❌ GET    /analytics/geo/                     # Geo distribution endpoint
❌ GET    /analytics/time-trends/              # Hourly/weekly trends
```

### 4.9 Brands

```
✅ POST   /brands/                            # Create brand
✅ GET    /brands/                            # List brands
✅ GET    /brands/{id}/                       # Brand detail
✅ PATCH  /brands/{id}/                       # Update brand
❌ DELETE /brands/{id}/                       # Delete brand
```

### 4.10 QR Products & QR Management

```
🔶 POST   /qr-products/                       # Create product (exists)
🔶 GET    /qr-products/                       # List products (exists)
🔶 GET    /qr-products/{id}/                  # Product detail (exists)
🔶 PATCH  /qr-products/{id}/                  # Update product (exists)
🔶 DELETE /qr-products/{id}/                  # Delete product (exists)
🔶 POST   /qr-products/{id}/blocks/           # Create QR block/batch (exists)
🔶 GET    /qr-products/{id}/blocks/           # List blocks (exists)
🔶 GET    /qr-products/{id}/blocks/{block_id}/ # Block detail (exists)
❌ GET    /qr-products/{id}/blocks/{block_id}/items/ # List product items in block
❌ GET    /qr-products/{id}/blocks/{block_id}/download/ # Download QR sheets (verify)
❌ POST   /qr-products/{id}/activation/       # Configure activation parameters
❌ GET    /qr-products/{id}/activation/       # Get activation parameters
❌ GET    /qr-products/{id}/scan-events/      # Product scan events
```

### 4.11 QR Product Settings

```
🔶 POST   /qr-product-settings/               # Create setting (exists)
🔶 GET    /qr-product-settings/               # List settings (exists)
🔶 GET    /qr-product-settings/{id}/          # Setting detail (exists)
🔶 PATCH  /qr-product-settings/{id}/          # Update setting (exists)
🔶 DELETE /qr-product-settings/{id}/          # Delete setting (exists)
```

### 4.12 Warranty

```
🔶 POST   /warranties/register/              # Register warranty (exists, public)
🔶 GET    /warranties/check/                  # Check warranty (exists, public)
❌ POST   /warranties/                        # Create warranty (admin)
❌ GET    /warranties/                        # List warranties
❌ GET    /warranties/{id}/                   # Warranty detail
❌ PATCH  /warranties/{id}/                   # Update warranty
❌ GET    /warranties/periods/                # List warranty period options
❌ POST   /warranties/periods/                # Create warranty period option
❌ DELETE /warranties/periods/{id}/           # Delete warranty period option
```

### 4.13 Destinations

```
🔶 POST   /destinations/                      # Create destination (exists)
🔶 GET    /destinations/                      # List destinations (exists)
🔶 GET    /destinations/{id}/                 # Destination detail (exists)
🔶 PATCH  /destinations/{id}/                 # Update destination (exists)
🔶 DELETE /destinations/{id}/                 # Delete destination (exists)
```

### 4.14 Short URLs

```
🔶 POST   /short-urls/                        # Create short URL (exists)
🔶 GET    /short-urls/                        # List short URLs (exists)
🔶 GET    /short-urls/{slug}/                 # Resolve (exists, public)
🔶 PATCH  /short-urls/{id}/                   # Update (exists)
🔶 DELETE /short-urls/{id}/                   # Delete (exists)
```

### 4.15 Brand Trust

```
🔶 GET    /brand-trust/industries/            # List industries (exists, public)
🔶 GET    /brand-trust/questions/             # List questions (exists, public)
🔶 POST   /brand-trust/assessments/           # Create assessment (exists)
🔶 GET    /brand-trust/assessments/           # List assessments (exists)
🔶 GET    /brand-trust/assessments/{id}/      # Assessment detail (exists)
❌ POST   /brand-trust/assessments/{id}/submit/ # Submit assessment
❌ GET    /brand-trust/assessments/{id}/report/ # Get assessment report
```

### 4.16 Facebook/Meta Campaigns

```
❌ POST   /meta/customer-segments/            # Create customer segment
❌ GET    /meta/customer-segments/            # List segments
❌ GET    /meta/customer-segments/{id}/       # Segment detail
❌ DELETE /meta/customer-segments/{id}/       # Delete segment
❌ POST   /meta/credentials/                  # Save Meta API credentials
❌ GET    /meta/credentials/                  # Get Meta credentials
❌ POST   /meta/custom-audiences/             # Create custom audience
❌ POST   /meta/ad-sets/                      # Create ad set
❌ POST   /meta/ads/                          # Submit ad
❌ GET    /meta/ads/{id}/preview/             # Preview ad creative
❌ GET    /meta/targeting/search/             # Search country/market targeting
```

### 4.17 Developer Portal (API Keys)

```
❌ POST   /developer/api-keys/                # Generate API key (QSeal + QReach)
❌ GET    /developer/api-keys/                # List API keys
❌ DELETE /developer/api-keys/{id}/           # Revoke API key
```

### 4.18 Stores

```
❌ POST   /stores/                            # Create store
❌ GET    /stores/                            # List stores
❌ GET    /stores/{id}/                       # Store detail
❌ PATCH  /stores/{id}/                       # Update store
❌ DELETE /stores/{id}/                       # Delete store
❌ POST   /stores/{id}/archive/              # Archive store
❌ POST   /stores/{id}/unarchive/            # Unarchive store
```

### 4.19 Consumer API (Public Endpoints)

```
❌ POST   /consumer/scan/                     # Record QR scan event
❌ POST   /consumer/verify-otp/               # Verify OTP
❌ POST   /consumer/generate-coupon/          # Generate coupon (denomination shuffle)
❌ GET    /consumer/campaign/{id}/            # Get campaign landing page data
✅ POST   /campaigns/coupons/verify/          # Verify coupon (exists, public)
✅ POST   /campaigns/coupons/redeem/          # Redeem coupon (exists, public)
✅ POST   /campaigns/coupons/unlock/          # Unlock coupon (exists, public)
❌ POST   /consumer/feedback/                 # Submit feedback (FW campaigns)
❌ POST   /consumer/play2win/spin/            # Spin the wheel (PW campaigns)
```

---

## 5. RBAC Permissions — Complete List

### 5.1 Permission Naming Convention

**Format:** `{resource}.{action}`
**Examples:** `campaign.create`, `lead.read`, `sms.send`

### 5.2 Master Permission List

#### Campaign Management

| Code                     | Description                        | ResourceType |
| ------------------------ | ---------------------------------- | ------------ |
| `campaign.create`        | Create new campaigns               | `CAMPAIGN`   |
| `campaign.read`          | View campaign list and details     | `CAMPAIGN`   |
| `campaign.update`        | Update campaign configuration      | `CAMPAIGN`   |
| `campaign.delete`        | Delete/soft-delete campaigns       | `CAMPAIGN`   |
| `campaign.clone`         | Clone existing campaigns           | `CAMPAIGN`   |
| `campaign.manage_status` | Activate/Pause/End campaign status | `CAMPAIGN`   |
| `campaign.qr_preview`    | Generate QR design preview         | `CAMPAIGN`   |
| `campaign.qr_download`   | Download QR code sheets            | `CAMPAIGN`   |

#### Prize Management (Play2Win)

| Code           | Description                | ResourceType |
| -------------- | -------------------------- | ------------ |
| `prize.create` | Add prize to campaign      | `CAMPAIGN`   |
| `prize.read`   | View campaign prizes       | `CAMPAIGN`   |
| `prize.update` | Update prize configuration | `CAMPAIGN`   |
| `prize.delete` | Remove prize from campaign | `CAMPAIGN`   |

#### Lead Management

| Code              | Description                 | ResourceType |
| ----------------- | --------------------------- | ------------ |
| `lead.create`     | Create leads manually       | `LEAD`       |
| `lead.read`       | View lead list and details  | `LEAD`       |
| `lead.update`     | Update lead information     | `LEAD`       |
| `lead.delete`     | Delete leads                | `LEAD`       |
| `lead.archive`    | Archive/unarchive leads     | `LEAD`       |
| `lead.import`     | Import leads from file      | `LEAD`       |
| `lead.export`     | Export leads to file        | `LEAD`       |
| `lead.send_sms`   | Send SMS to individual lead | `LEAD`       |
| `lead.send_email` | Email share lead info       | `LEAD`       |
| `lead.blocklist`  | Manage blocklisted numbers  | `LEAD`       |
| `lead.note`       | Add/edit/delete lead notes  | `LEAD`       |

#### Tag Management

| Code           | Description              | ResourceType |
| -------------- | ------------------------ | ------------ |
| `tag.create`   | Create tags              | `LEAD`       |
| `tag.read`     | View tags                | `LEAD`       |
| `tag.update`   | Update tag details       | `LEAD`       |
| `tag.delete`   | Delete tags              | `LEAD`       |
| `tag.assign`   | Assign tags to leads     | `LEAD`       |
| `tag.unassign` | Unassign tags from leads | `LEAD`       |

#### Coupon Management

| Code              | Description                     | ResourceType |
| ----------------- | ------------------------------- | ------------ |
| `coupon.read`     | View coupon list and details    | `COUPON`     |
| `coupon.verify`   | Verify coupon validity          | `COUPON`     |
| `coupon.redeem`   | Redeem a coupon                 | `COUPON`     |
| `coupon.generate` | Generate coupons (consumer API) | `COUPON`     |

#### SMS Management

| Code                  | Description               | ResourceType |
| --------------------- | ------------------------- | ------------ |
| `sms.template_create` | Create SMS templates      | `SMS`        |
| `sms.template_read`   | View SMS templates        | `SMS`        |
| `sms.template_update` | Update SMS templates      | `SMS`        |
| `sms.template_delete` | Delete SMS templates      | `SMS`        |
| `sms.credit_read`     | View SMS credit balance   | `SMS`        |
| `sms.credit_add`      | Add SMS credits           | `SMS`        |
| `sms.send`            | Send bulk SMS             | `SMS`        |
| `sms.schedule`        | Schedule SMS delivery     | `SMS`        |
| `sms.report_read`     | View SMS delivery reports | `SMS`        |
| `sms.report_download` | Download SMS reports      | `SMS`        |

#### WhatsApp Management

| Code                       | Description                       | ResourceType |
| -------------------------- | --------------------------------- | ------------ |
| `whatsapp.template_create` | Create WhatsApp templates         | `WHATSAPP`   |
| `whatsapp.template_read`   | View WhatsApp templates           | `WHATSAPP`   |
| `whatsapp.template_update` | Update WhatsApp templates         | `WHATSAPP`   |
| `whatsapp.template_delete` | Delete WhatsApp templates         | `WHATSAPP`   |
| `whatsapp.media_upload`    | Upload media for templates        | `WHATSAPP`   |
| `whatsapp.credit_read`     | View WhatsApp credit balance      | `WHATSAPP`   |
| `whatsapp.credit_add`      | Add WhatsApp credits              | `WHATSAPP`   |
| `whatsapp.send`            | Send bulk WhatsApp messages       | `WHATSAPP`   |
| `whatsapp.schedule`        | Schedule WhatsApp delivery        | `WHATSAPP`   |
| `whatsapp.test`            | Send test WhatsApp messages       | `WHATSAPP`   |
| `whatsapp.report_read`     | View WhatsApp reports             | `WHATSAPP`   |
| `whatsapp.report_download` | Download WhatsApp reports         | `WHATSAPP`   |
| `whatsapp.suspend`         | Suspend running WhatsApp campaign | `WHATSAPP`   |

#### RCS Management

| Code                  | Description               | ResourceType |
| --------------------- | ------------------------- | ------------ |
| `rcs.template_create` | Create RCS templates      | `RCS`        |
| `rcs.template_read`   | View RCS templates        | `RCS`        |
| `rcs.template_update` | Update RCS templates      | `RCS`        |
| `rcs.template_delete` | Delete RCS templates      | `RCS`        |
| `rcs.credit_read`     | View RCS credit balance   | `RCS`        |
| `rcs.credit_add`      | Add RCS credits           | `RCS`        |
| `rcs.send`            | Send bulk RCS messages    | `RCS`        |
| `rcs.test`            | Send test RCS messages    | `RCS`        |
| `rcs.report_read`     | View RCS delivery reports | `RCS`        |
| `rcs.report_download` | Download RCS reports      | `RCS`        |

#### Analytics

| Code                      | Description                            | ResourceType |
| ------------------------- | -------------------------------------- | ------------ |
| `analytics.scan_read`     | View scan analytics                    | `ANALYTICS`  |
| `analytics.insight_read`  | View coupon/sent vs redeemed analytics | `ANALYTICS`  |
| `analytics.business_read` | View business/POS dashboard            | `ANALYTICS`  |
| `analytics.product_read`  | View product-level scan analytics      | `ANALYTICS`  |
| `analytics.realtime_read` | View real-time scan feed               | `ANALYTICS`  |
| `analytics.export`        | Export analytics reports               | `ANALYTICS`  |

#### Brand Management

| Code           | Description          | ResourceType |
| -------------- | -------------------- | ------------ |
| `brand.create` | Create brands        | `BRAND`      |
| `brand.read`   | View brands          | `BRAND`      |
| `brand.update` | Update brand details | `BRAND`      |
| `brand.delete` | Delete brands        | `BRAND`      |

#### QR Product Management

| Code                        | Description                                     | ResourceType |
| --------------------------- | ----------------------------------------------- | ------------ |
| `qr_product.create`         | Create QR products                              | `QR_PRODUCT` |
| `qr_product.read`           | View QR products                                | `QR_PRODUCT` |
| `qr_product.update`         | Update QR products                              | `QR_PRODUCT` |
| `qr_product.delete`         | Delete QR products                              | `QR_PRODUCT` |
| `qr_product.block_create`   | Create QR code blocks/batches                   | `QR_PRODUCT` |
| `qr_product.block_download` | Download QR code sheets                         | `QR_PRODUCT` |
| `qr_product.activation`     | Configure activation parameters                 | `QR_PRODUCT` |
| `qr_product.setting_manage` | Manage product settings (prefix, channel, etc.) | `QR_PRODUCT` |

#### Warranty Management

| Code                     | Description                    | ResourceType |
| ------------------------ | ------------------------------ | ------------ |
| `warranty.create`        | Create warranty records        | `WARRANTY`   |
| `warranty.read`          | View warranty records          | `WARRANTY`   |
| `warranty.update`        | Update warranty records        | `WARRANTY`   |
| `warranty.period_manage` | Manage warranty period options | `WARRANTY`   |

#### Store Management

| Code            | Description              | ResourceType |
| --------------- | ------------------------ | ------------ |
| `store.create`  | Create store locations   | `STORE`      |
| `store.read`    | View store locations     | `STORE`      |
| `store.update`  | Update store details     | `STORE`      |
| `store.delete`  | Delete store locations   | `STORE`      |
| `store.archive` | Archive/unarchive stores | `STORE`      |

#### Developer Portal

| Code             | Description       | ResourceType |
| ---------------- | ----------------- | ------------ |
| `api_key.create` | Generate API keys | `API_KEY`    |
| `api_key.read`   | View API keys     | `API_KEY`    |
| `api_key.revoke` | Revoke API keys   | `API_KEY`    |

#### Other

| Code                 | Description                | ResourceType  |
| -------------------- | -------------------------- | ------------- |
| `destination.create` | Create destination markets | `DESTINATION` |
| `destination.read`   | View destination markets   | `DESTINATION` |
| `destination.update` | Update destination markets | `DESTINATION` |
| `destination.delete` | Delete destination markets | `DESTINATION` |
| `short_url.create`   | Create short URLs          | `SHORT_URL`   |
| `short_url.read`     | View short URLs            | `SHORT_URL`   |
| `short_url.update`   | Update short URLs          | `SHORT_URL`   |
| `short_url.delete`   | Delete short URLs          | `SHORT_URL`   |

### 5.3 Suggested Roles

| Role                   | Code                 | Permissions Included                                                                                                                                            | Description                      |
| ---------------------- | -------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------- | -------------------------------- |
| **QReach Admin**       | `qreach_admin`       | All `campaign.*`, `lead.*`, `tag.*`, `coupon.*`, `sms.*`, `whatsapp.*`, `rcs.*`, `analytics.*`, `brand.*`, `qr_product.*`, `warranty.*`, `store.*`, `api_key.*` | Full QReach access               |
| **Campaign Manager**   | `campaign_manager`   | `campaign.*`, `lead.*`, `tag.*`, `coupon.*`, `sms.*`, `whatsapp.*`, `rcs.*`, `analytics.*`                                                                      | Campaign + messaging management  |
| **Lead Manager**       | `lead_manager`       | `lead.*`, `tag.*`, `coupon.read`, `sms.send`, `whatsapp.send`                                                                                                   | Lead CRM operations              |
| **Analytics Viewer**   | `analytics_viewer`   | `analytics.*`, `campaign.read`, `lead.read`, `coupon.read`                                                                                                      | Read-only analytics access       |
| **QR Product Manager** | `qr_product_manager` | `qr_product.*`, `brand.read`, `warranty.*`, `destination.*`                                                                                                     | Product and QR code management   |
| **Developer**          | `qreach_developer`   | `api_key.*`, `short_url.*`, `campaign.read`, `analytics.read`                                                                                                   | API key management + read access |

### 5.4 System Admin Override

System admins (`user_type = "system_admin"` with `*.*` wildcard permission) bypass all QReach permission checks — they have full access to all QReach resources across all organizations.

---

## 6. Implementation Phases

### Phase 1: Foundation (DB + Core CRUD)

- Add missing tables: `stores`, `schedule_reports`, `qreach_api_keys`, `landing_customizations`, `lead_notes`
- Add missing columns to existing tables
- Seed all QReach permissions in identity-service `permissions` table
- Add QReach resources to `ResourceType` enum + migration
- Create default QReach roles in identity-service
- Complete Campaign CRUD (clone, status)
- Complete Brand CRUD (delete)
- Complete Lead CRUD (detail, update, delete, archive, notes, import/export)
- Complete Tag CRUD + assignment endpoints

### Phase 2: Messaging (SMS + WhatsApp + RCS)

- Complete SMS template CRUD + credit management
- Complete WhatsApp template CRUD + media upload + credit management
- Complete RCS template CRUD + credit management
- Bulk send + schedule endpoints for all channels
- Delivery reports + summary dashboards
- Test message endpoints

### Phase 3: Analytics & Consumer API

- QReach scan analytics (daily, hourly, weekly, geo, device)
- Insights dashboard (coupons sent vs redeemed)
- Business/POS dashboard
- Consumer scan/coupon generation/spin endpoints
- Real-time scan feed (SSE)

### Phase 4: Advanced Features

- Facebook/Meta campaign integration
- Brand trust assessment completion + reports
- Store management
- Scheduled reports
- QR design preview + download

---

## 7. Open Questions for Review

Please review and provide feedback on the following:

1. **Permission granularity**: Is the permission list too granular? Should we combine some (e.g., `sms.send` + `sms.schedule` into `sms.manage`)?

2. **SMS vs WhatsApp vs RCS**: Should all messaging be under a single `messaging.*` permission set, or keep them separate as proposed?

3. **Consumer API auth**: Consumer endpoints (scan, generate coupon, spin) should be public with API key auth or organization_id parameter. How should this work?

4. **Matomo dependency**: The original migration doc mentions QReach Analytics depends on Matomo. Should we build analytics by tracking events directly in `qr_scan_events` + `coupons` tables instead?

5. **Firebase Storage**: QR sheets are stored in Firebase/GCS. Should we migrate to S3 or keep GCS?

6. **Existing `coupon_durations` and `shopify_configs` tables**: These exist but have no API endpoints. Should they be included?

7. **`web_campaigns` (Click2Win)**: Should these be merged with the `campaigns` table since they share most columns, or kept separate?

8. **Role hierarchy**: Should `qreach_admin` inherit from `campaign_manager` and `qr_product_manager`, or should roles be flat as proposed?
