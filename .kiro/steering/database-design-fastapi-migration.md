# QSeal FastAPI PostgreSQL Database Design

Multi-tenancy moves from schema-per-tenant to `tenant_id` column on every table.
The old `Brand` entity is removed — key pairs move to `organizations`.

---

## Service 1: Auth & Tenant/Org Service

### `organizations` (replaces `Client` + `Brand`)

```sql
CREATE TABLE organizations (
    id               UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name             VARCHAR(256) NOT NULL,
    short_code       VARCHAR(256),
    public_key       VARCHAR(255),
    private_key      VARCHAR(255),
    schema_name      VARCHAR(100),
    domain_url       VARCHAR(255),
    industry         VARCHAR(100),
    paid_until       DATE,
    on_trial         BOOLEAN DEFAULT TRUE,
    trial_expiry     DATE,
    status           VARCHAR(20) DEFAULT 'ACTIVE',
    timezone         VARCHAR(50) DEFAULT 'UTC',
    qr_credit_limit  INTEGER DEFAULT 0,
    qr_credit_used   INTEGER DEFAULT 0,
    created_at       TIMESTAMPTZ DEFAULT now(),
    updated_at       TIMESTAMPTZ DEFAULT now()
);
```

### `users`

```sql
CREATE TABLE users (
    id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id     UUID NOT NULL REFERENCES organizations(id),
    email         VARCHAR(255) UNIQUE NOT NULL,
    mobile        VARCHAR(20),
    password_hash VARCHAR(255),
    roles         TEXT[],
    is_active     BOOLEAN DEFAULT TRUE,
    created_at    TIMESTAMPTZ DEFAULT now(),
    updated_at    TIMESTAMPTZ DEFAULT now()
);
CREATE INDEX idx_users_tenant ON users(tenant_id);
```

### `otp_verifications` (from `OTP`)

```sql
CREATE TABLE otp_verifications (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id   UUID NOT NULL,
    otp         VARCHAR(10) NOT NULL,
    otp_type    VARCHAR(20),
    email       VARCHAR(120),
    mobile      VARCHAR(20),
    location    VARCHAR(56),
    order_id    VARCHAR(24),
    is_verified BOOLEAN DEFAULT FALSE,
    created_at  TIMESTAMPTZ DEFAULT now()
);
```

---

## Service 2: Product & QR Service

### `products` (from `Product`)

```sql
CREATE TABLE products (
    id                      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id               UUID NOT NULL,
    name                    VARCHAR(100) NOT NULL,
    generic_name            VARCHAR(100),
    gtin                    VARCHAR(20),
    industry                VARCHAR(100),
    landing_page            TEXT,
    image_url               TEXT,
    banner_image_url        TEXT,
    email                   VARCHAR(255),
    phone_number            VARCHAR(15),
    client_product_auth_url TEXT,
    activation_method       VARCHAR(4) DEFAULT 'pre',
    sr_number_type          VARCHAR(12),
    redirect_to_client      BOOLEAN DEFAULT FALSE,
    warranty_period_months  INTEGER,
    qr_type                 VARCHAR(30),
    created_at              TIMESTAMPTZ DEFAULT now(),
    updated_at              TIMESTAMPTZ DEFAULT now()
);
CREATE INDEX idx_products_tenant ON products(tenant_id);
```

### `qr_blocks` (from `Order`)

```sql
CREATE TABLE qr_blocks (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id       UUID NOT NULL,
    product_id      UUID NOT NULL REFERENCES products(id),
    batch           VARCHAR(50) NOT NULL,
    serial_prefix   VARCHAR(20),
    sr_number       VARCHAR(256),
    sr_number_type  VARCHAR(256),
    quantity        INTEGER NOT NULL,
    cert_type       VARCHAR(1),
    size            VARCHAR(4),
    colour_desc     VARCHAR(50),
    price           INTEGER,
    style           VARCHAR(20),
    task_status     VARCHAR(20),
    qr_image        BOOLEAN DEFAULT FALSE,
    manufacture_date DATE,
    expiry_date     DATE,
    gcs_url         TEXT,
    created_at      TIMESTAMPTZ DEFAULT now(),
    updated_at      TIMESTAMPTZ DEFAULT now()
);
CREATE INDEX idx_qr_blocks_tenant ON qr_blocks(tenant_id);
CREATE INDEX idx_qr_blocks_product ON qr_blocks(product_id);
```

### `product_items` (from `ProductItem`)

```sql
CREATE TABLE product_items (
    id               UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id        UUID NOT NULL,
    product_id       UUID NOT NULL REFERENCES products(id),
    block_id         UUID REFERENCES qr_blocks(id),
    serial_number    VARCHAR(75) NOT NULL,
    secrete_code     VARCHAR(50),
    token_id         VARCHAR(75),
    is_unit          BOOLEAN DEFAULT FALSE,
    is_suspicious    BOOLEAN DEFAULT FALSE,
    is_verify        BOOLEAN DEFAULT FALSE,
    is_auth          BOOLEAN DEFAULT FALSE,
    qr_deactive      BOOLEAN DEFAULT TRUE,
    qr_deactive_unit BOOLEAN DEFAULT TRUE,
    scan_date        TIMESTAMPTZ,
    scans            INTEGER DEFAULT 0,
    destination_market VARCHAR(100),
    created_at       TIMESTAMPTZ DEFAULT now(),
    updated_at       TIMESTAMPTZ DEFAULT now()
);
CREATE INDEX idx_product_items_tenant ON product_items(tenant_id);
CREATE INDEX idx_product_items_serial ON product_items(serial_number);
```

### `qr_activation_parameters` (from `QRActivationParameters`)

```sql
CREATE TABLE qr_activation_parameters (
    id                 UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id          UUID NOT NULL,
    product_id         UUID REFERENCES products(id),
    block_id           UUID REFERENCES qr_blocks(id),
    serial_number      VARCHAR(75),
    manufacturing_date DATE NOT NULL,
    expiry_date        DATE NOT NULL,
    manufacturing_unit VARCHAR(100) NOT NULL,
    dispatch_batch     VARCHAR(100),
    destination_market VARCHAR(100),
    mrp                NUMERIC(10,2),
    currency           VARCHAR(10),
    batch_size         INTEGER,
    qr_settings        BOOLEAN DEFAULT FALSE,
    qr_cascade         BOOLEAN DEFAULT FALSE,
    created_at         TIMESTAMPTZ DEFAULT now()
);
CREATE INDEX idx_qr_activation_tenant ON qr_activation_parameters(tenant_id);
```

### `qr_activation_tracks` (from `QRActivationTrack`)

```sql
CREATE TABLE qr_activation_tracks (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id       UUID NOT NULL,
    qr_type         VARCHAR(25),
    name            VARCHAR(20),
    capacity        INTEGER,
    serial_number   VARCHAR(10),
    qr_code_link    TEXT,
    app_cascade_map BOOLEAN DEFAULT FALSE,
    parent_id       UUID REFERENCES qr_activation_tracks(id),
    parent_app_id   UUID REFERENCES qr_activation_tracks(id),
    created_at      TIMESTAMPTZ DEFAULT now()
);
```

### `qr_credit_usage` (NEW)

```sql
CREATE TABLE qr_credit_usage (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id   UUID NOT NULL,
    block_id    UUID REFERENCES qr_blocks(id),
    quantity    INTEGER NOT NULL,
    used_at     TIMESTAMPTZ DEFAULT now()
);
CREATE INDEX idx_qr_credit_tenant ON qr_credit_usage(tenant_id);
```

---

## Service 3: Campaign & Coupon Service

### `campaigns` (from `Campaign`)

```sql
CREATE TABLE campaigns (
    id                        UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id                 UUID NOT NULL,
    name                      VARCHAR(256) NOT NULL,
    campaign_type             VARCHAR(3) NOT NULL,
    campaign_status           VARCHAR(1) DEFAULT 'A',
    location                  VARCHAR(256),
    from_date                 DATE NOT NULL,
    to_date                   DATE NOT NULL,
    coupon_deliver            VARCHAR(50) DEFAULT 'Nothing',
    denominations             TEXT,
    denominations_value       TEXT,
    denominations_list        JSONB,
    sms_senderid              VARCHAR(10),
    sms_template              VARCHAR(256),
    sms_variable              JSONB,
    whatsapp_template_name    VARCHAR(256),
    whatsapp_template_type    VARCHAR(256),
    whatsapp_media_type       VARCHAR(256),
    whatsapp_interactive_type VARCHAR(256),
    whatsapp_variable         JSONB,
    media_link                TEXT,
    campaign_message          VARCHAR(256),
    used_message              VARCHAR(256),
    terms_conditions          TEXT,
    bypass_url                TEXT,
    client_url                TEXT,
    redirect_url_type         VARCHAR(2),
    budget_cap                INTEGER,
    scans                     INTEGER DEFAULT 0,
    coupon_reissue_time       VARCHAR(50),
    brand_image_url           TEXT,
    promotional_image_url     TEXT,
    congrats_image_url        TEXT,
    multilink_type            VARCHAR(3),
    multilink_items           JSONB,
    game_config               JSONB,
    shuffle                   TEXT,
    shuffle_gb                TEXT,
    created_at                TIMESTAMPTZ DEFAULT now(),
    updated_at                TIMESTAMPTZ DEFAULT now()
);
CREATE INDEX idx_campaigns_tenant ON campaigns(tenant_id);
```

### `play2win_prizes` (from `Play2WinPrize`)

```sql
CREATE TABLE play2win_prizes (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id   UUID NOT NULL,
    campaign_id UUID NOT NULL REFERENCES campaigns(id),
    name        VARCHAR(128) NOT NULL,
    prize_type  VARCHAR(20) DEFAULT 'none',
    value       NUMERIC(10,2) DEFAULT 0,
    weight      INTEGER DEFAULT 1,
    max_quantity INTEGER,
    slot_color  VARCHAR(7) DEFAULT '#3157EF',
    is_active   BOOLEAN DEFAULT TRUE,
    created_at  TIMESTAMPTZ DEFAULT now()
);
```

### `web_campaigns` (from `webCampaign`)

```sql
CREATE TABLE web_campaigns (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id       UUID NOT NULL,
    name            VARCHAR(256),
    campaign_type   VARCHAR(3),
    campaign_status VARCHAR(1) DEFAULT 'A',
    from_date       DATE,
    to_date         DATE,
    coupon_deliver  VARCHAR(50),
    denominations   TEXT,
    terms_conditions TEXT,
    config          JSONB,
    created_at      TIMESTAMPTZ DEFAULT now(),
    updated_at      TIMESTAMPTZ DEFAULT now()
);
CREATE INDEX idx_web_campaigns_tenant ON web_campaigns(tenant_id);
```

### `tags` (from `Tags`)

```sql
CREATE TABLE tags (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id       UUID NOT NULL,
    segment         VARCHAR(20),
    tag_type        VARCHAR(10),
    tag_source      VARCHAR(256),
    total_lead      INTEGER DEFAULT 0,
    tag_description TEXT,
    created_at      TIMESTAMPTZ DEFAULT now(),
    updated_at      TIMESTAMPTZ DEFAULT now()
);
CREATE INDEX idx_tags_tenant ON tags(tenant_id);
```

### `leads` (from `Lead`)

```sql
CREATE TABLE leads (
    id             UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id      UUID NOT NULL,
    campaign_id    UUID REFERENCES campaigns(id),
    name           VARCHAR(255),
    mobilenumber   VARCHAR(255),
    email          VARCHAR(255),
    address        TEXT,
    location       VARCHAR(255),
    pincode        VARCHAR(30),
    dob            DATE,
    gender         VARCHAR(30),
    occupation     VARCHAR(256),
    gst_number     VARCHAR(256),
    state_name     VARCHAR(30),
    country        VARCHAR(30),
    coupon         VARCHAR(255),
    value          VARCHAR(255),
    used           VARCHAR(255),
    expiry         TIMESTAMPTZ,
    timestamp      TIMESTAMPTZ,
    used_timestamp TIMESTAMPTZ,
    rating         VARCHAR(255),
    comment        VARCHAR(255),
    status         VARCHAR(20),
    redeem_mode    VARCHAR(10) DEFAULT 'none',
    external_lead  BOOLEAN DEFAULT FALSE,
    created_at     TIMESTAMPTZ DEFAULT now(),
    updated_at     TIMESTAMPTZ DEFAULT now()
);
CREATE INDEX idx_leads_tenant ON leads(tenant_id);
CREATE INDEX idx_leads_mobile ON leads(mobilenumber);
```

### `lead_tags` (M2M junction)

```sql
CREATE TABLE lead_tags (
    lead_id UUID REFERENCES leads(id) ON DELETE CASCADE,
    tag_id  UUID REFERENCES tags(id) ON DELETE CASCADE,
    PRIMARY KEY (lead_id, tag_id)
);
```

### `coupons` (from `Coupon`)

```sql
CREATE TABLE coupons (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id           UUID NOT NULL,
    campaign_id         UUID REFERENCES campaigns(id),
    web_campaign_id     UUID REFERENCES web_campaigns(id),
    coupon_code         VARCHAR(255),
    name                VARCHAR(255),
    mobilenumber        VARCHAR(255),
    email               VARCHAR(255),
    state_name          VARCHAR(30),
    dob                 DATE,
    gender              VARCHAR(30),
    occupation          VARCHAR(30),
    units               VARCHAR(255) DEFAULT 'RS',
    value               VARCHAR(255),
    used                VARCHAR(255),
    min_bill_value      VARCHAR(255),
    expiry              TIMESTAMPTZ,
    timestamp           TIMESTAMPTZ,
    used_timestamp      TIMESTAMPTZ,
    location            VARCHAR(255),
    rating              VARCHAR(255),
    product_rating      VARCHAR(255),
    color_rating        VARCHAR(255),
    price_rating        VARCHAR(255),
    comment             VARCHAR(255),
    custom_question     JSONB,
    custom_answer       JSONB,
    acception_id        VARCHAR(256),
    is_unlocked         BOOLEAN DEFAULT FALSE,
    unlock_count        INTEGER DEFAULT 0,
    final_billed_amount FLOAT,
    redeem_mode         VARCHAR(10) DEFAULT 'none',
    created_at          TIMESTAMPTZ DEFAULT now()
);
CREATE INDEX idx_coupons_tenant ON coupons(tenant_id);
CREATE INDEX idx_coupons_mobile ON coupons(mobilenumber);
CREATE INDEX idx_coupons_code ON coupons(coupon_code);
```

### `coupon_unlock_logs` (from `CouponUnlockLog`)

```sql
CREATE TABLE coupon_unlock_logs (
    id             UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id      UUID NOT NULL,
    coupon_id      UUID NOT NULL REFERENCES coupons(id),
    action         VARCHAR(20) NOT NULL,
    notes          TEXT,
    location       VARCHAR(255),
    user_reference VARCHAR(255),
    timestamp      TIMESTAMPTZ DEFAULT now()
);
CREATE INDEX idx_coupon_logs_tenant ON coupon_unlock_logs(tenant_id);
CREATE INDEX idx_coupon_logs_coupon ON coupon_unlock_logs(coupon_id);
```

### `external_coupons` (from `ExternalCoupon`)

```sql
CREATE TABLE external_coupons (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id       UUID NOT NULL,
    web_campaign_id UUID REFERENCES web_campaigns(id),
    coupon_code     VARCHAR(255),
    name            VARCHAR(255),
    mobilenumber    VARCHAR(255),
    email           VARCHAR(255),
    state_name      VARCHAR(30),
    city            VARCHAR(30),
    zipcode         VARCHAR(30),
    ip_address      VARCHAR(255),
    dob             DATE,
    age             VARCHAR(30),
    occupation      VARCHAR(30),
    timestamp       TIMESTAMPTZ,
    created_at      TIMESTAMPTZ DEFAULT now()
);
CREATE INDEX idx_ext_coupons_tenant ON external_coupons(tenant_id);
```

### `coupon_durations` (from `CouponDuration`)

```sql
CREATE TABLE coupon_durations (
    id               UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id        UUID NOT NULL,
    delivery_type    VARCHAR(3) NOT NULL,
    cooling_periods  INTEGER NOT NULL,
    min_order_amount VARCHAR(256) DEFAULT '1500'
);
```

### `shopify_configs` (from `ShopifyCoupon`)

```sql
CREATE TABLE shopify_configs (
    id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id     UUID NOT NULL,
    api_endpoint  TEXT,
    auth_token    VARCHAR(256),
    price_rule_id VARCHAR(256),
    created_at    TIMESTAMPTZ DEFAULT now()
);
```

---

## Service 4: Messaging Service

### `message_templates` (from `Message_template`)

```sql
CREATE TABLE message_templates (
    id                      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id               UUID NOT NULL,
    template_name           VARCHAR(4000) NOT NULL,
    channel                 VARCHAR(10) NOT NULL,
    template_type           VARCHAR(2),
    message                 TEXT,
    template_text           TEXT NOT NULL,
    media_type              VARCHAR(3),
    interactive_type        VARCHAR(3),
    status                  VARCHAR(40) DEFAULT 'Not Approved',
    sender_id               VARCHAR(6),
    cta_button1             VARCHAR(20),
    cta_button2             VARCHAR(20),
    qr_button1              VARCHAR(20),
    qr_button2              VARCHAR(20),
    qr_button3              VARCHAR(20),
    entity_name             VARCHAR(50),
    dlt_principal_entity_id VARCHAR(50),
    dlt_template_id         VARCHAR(50),
    mobtexting_template_id  VARCHAR(120),
    service_type            VARCHAR(1) DEFAULT 'T',
    created_at              TIMESTAMPTZ DEFAULT now()
);
CREATE INDEX idx_msg_templates_tenant ON message_templates(tenant_id);
```

### `bulk_message_jobs` (from `LeadTagMessage`)

```sql
CREATE TABLE bulk_message_jobs (
    id               UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id        UUID NOT NULL,
    user_id          UUID,
    tag_id           UUID REFERENCES tags(id),
    message_type     VARCHAR(20) NOT NULL,
    sender_id        VARCHAR(40),
    template_type    VARCHAR(100),
    media_type       VARCHAR(100),
    interactive_type VARCHAR(100),
    template_name    VARCHAR(100),
    message_template TEXT,
    total_lead       VARCHAR(400),
    media_link       TEXT,
    variable         JSONB,
    coupon_type      VARCHAR(256),
    coupon_value     TEXT,
    start_time       TIME,
    end_time         TIME,
    template_length  VARCHAR(30),
    used_credit      VARCHAR(30),
    status           VARCHAR(50),
    created_at       DATE DEFAULT CURRENT_DATE
);
CREATE INDEX idx_bulk_jobs_tenant ON bulk_message_jobs(tenant_id);
```

### `scheduled_messages` (from `ScheduleMessage`)

```sql
CREATE TABLE scheduled_messages (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id       UUID NOT NULL,
    user_id         UUID,
    tag_id          UUID REFERENCES tags(id),
    message_type    VARCHAR(20) NOT NULL,
    template_name   VARCHAR(100),
    template_text   VARCHAR(400),
    variable        JSONB,
    sender_id       VARCHAR(12),
    media_link      TEXT,
    schedule        TIMESTAMPTZ NOT NULL,
    status          VARCHAR(50) DEFAULT 'Pending',
    created_at      DATE DEFAULT CURRENT_DATE
);
CREATE INDEX idx_scheduled_msgs_tenant ON scheduled_messages(tenant_id);
```

### `sms_reports` (from `SMSReport`)

```sql
CREATE TABLE sms_reports (
    id               UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id        UUID NOT NULL,
    job_id           UUID REFERENCES bulk_message_jobs(id),
    tag              VARCHAR(50),
    msg_id           VARCHAR(150),
    sender_id        VARCHAR(12),
    recipient_number VARCHAR(12),
    units            VARCHAR(50),
    credits          VARCHAR(250),
    location         VARCHAR(250),
    region           VARCHAR(250),
    provider         VARCHAR(50),
    status           VARCHAR(50),
    sent_date        TIMESTAMPTZ,
    deliver_date     TIMESTAMPTZ,
    submit_date      TIMESTAMPTZ,
    created_at       DATE DEFAULT CURRENT_DATE
);
CREATE INDEX idx_sms_reports_tenant ON sms_reports(tenant_id);
```

### `whatsapp_reports` (from `WhatsappReport`)

```sql
CREATE TABLE whatsapp_reports (
    id               UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id        UUID NOT NULL,
    job_id           UUID REFERENCES bulk_message_jobs(id),
    recipient_number VARCHAR(12),
    sender_number    VARCHAR(12),
    operator         VARCHAR(50),
    circle           VARCHAR(50),
    conversation_id  VARCHAR(150),
    template_id      VARCHAR(150),
    conversation_type VARCHAR(250),
    whatsapp_msg_id  VARCHAR(1000),
    guid             VARCHAR(250) UNIQUE,
    tag              VARCHAR(50),
    status           VARCHAR(50),
    reason_code      VARCHAR(50),
    sent_date        TIMESTAMPTZ,
    deliver_date     TIMESTAMPTZ
);
CREATE INDEX idx_wa_reports_tenant ON whatsapp_reports(tenant_id);
```

### `rcs_credentials` (from `RcsCredential`)

```sql
CREATE TABLE rcs_credentials (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id   UUID NOT NULL,
    config      JSONB NOT NULL,
    created_at  TIMESTAMPTZ DEFAULT now()
);
```

### `rcs_templates` (from `RcsTemplate`)

```sql
CREATE TABLE rcs_templates (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id   UUID NOT NULL,
    name        VARCHAR(256),
    content     JSONB,
    status      VARCHAR(40),
    created_at  TIMESTAMPTZ DEFAULT now()
);
CREATE INDEX idx_rcs_templates_tenant ON rcs_templates(tenant_id);
```

### `rcs_reports` (from `RCSReport`)

```sql
CREATE TABLE rcs_reports (
    id               UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id        UUID NOT NULL,
    job_id           UUID REFERENCES bulk_message_jobs(id),
    recipient_number VARCHAR(12),
    guid             VARCHAR(250) UNIQUE,
    status           VARCHAR(50),
    sent_date        TIMESTAMPTZ,
    deliver_date     TIMESTAMPTZ
);
CREATE INDEX idx_rcs_reports_tenant ON rcs_reports(tenant_id);
```

### `message_credits` (from `MessageSummary` + `MsgSummaryUsed`)

```sql
CREATE TABLE message_credits (
    id               UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id        UUID NOT NULL,
    credit_type      VARCHAR(50) NOT NULL,
    add_credit       INTEGER DEFAULT 0,
    reduce_credit    INTEGER DEFAULT 0,
    balance_credit   INTEGER DEFAULT 0,
    payment_inr      VARCHAR(250),
    credit_value     VARCHAR(50),
    payment_detail   VARCHAR(400),
    transaction_date TIMESTAMPTZ DEFAULT now()
);
CREATE INDEX idx_msg_credits_tenant ON message_credits(tenant_id);
```

---

## Service 5: Warranty Service

### `warranty_periods` (from `WarrantyPeriod`)

```sql
CREATE TABLE warranty_periods (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id   UUID NOT NULL,
    months      INTEGER NOT NULL,
    is_active   BOOLEAN DEFAULT TRUE,
    is_default  BOOLEAN DEFAULT FALSE,
    created_at  TIMESTAMPTZ DEFAULT now()
);
```

### `warranties` (from `Warranty`)

```sql
CREATE TABLE warranties (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id           UUID NOT NULL,
    product_item_id     UUID REFERENCES product_items(id),
    serial_number       VARCHAR(120),
    customer_name       VARCHAR(255) NOT NULL,
    mobile              VARCHAR(255) NOT NULL,
    email               VARCHAR(255),
    location            VARCHAR(120),
    ip                  VARCHAR(120),
    purchase_date       DATE,
    warranty_valid_till TIMESTAMPTZ,
    created_at          TIMESTAMPTZ DEFAULT now()
);
CREATE INDEX idx_warranties_tenant ON warranties(tenant_id);
CREATE INDEX idx_warranties_serial ON warranties(serial_number);
```

---

## Service 4: Analytics Service

### `qr_scan_events` (NEW — replaces Metamo)

```sql
CREATE TABLE qr_scan_events (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id       UUID NOT NULL,
    product_item_id UUID REFERENCES product_items(id),
    serial_number   VARCHAR(75),
    campaign_id     UUID,
    scan_timestamp  TIMESTAMPTZ DEFAULT now(),
    device_type     VARCHAR(50),
    os              VARCHAR(50),
    browser         VARCHAR(50),
    ip_address      VARCHAR(45),
    latitude        NUMERIC(9,6),
    longitude       NUMERIC(9,6),
    city            VARCHAR(100),
    state           VARCHAR(100),
    country         VARCHAR(100)
);
CREATE INDEX idx_scan_events_tenant ON qr_scan_events(tenant_id);
CREATE INDEX idx_scan_events_ts ON qr_scan_events(scan_timestamp);
CREATE INDEX idx_scan_events_serial ON qr_scan_events(serial_number);
```

### `meta_campaigns` (from `MetaCampaign`)

```sql
CREATE TABLE meta_campaigns (
    id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id     UUID NOT NULL,
    campaign_id   VARCHAR(256),
    campaign_name VARCHAR(256),
    impressions   INTEGER,
    clicks        INTEGER,
    spend         NUMERIC(10,2),
    reach         INTEGER,
    fetched_at    TIMESTAMPTZ DEFAULT now()
);
CREATE INDEX idx_meta_campaigns_tenant ON meta_campaigns(tenant_id);
```

---

## Migration Mapping Cheat Sheet

| Old Django Model                    | Old App       | New Table                   | New Service       |
| ----------------------------------- | ------------- | --------------------------- | ----------------- |
| `Client`                            | `dashboard`   | `organizations`             | Auth/Tenant       |
| `Brand`                             | `integration` | merged into `organizations` | Auth/Tenant       |
| `User`                              | `users`       | `users`                     | Auth/Tenant       |
| `OTP`                               | `integration` | `otp_verifications`         | Auth/Tenant       |
| `Product`                           | `integration` | `products`                  | Product & QR      |
| `Order`                             | `integration` | `qr_blocks`                 | Product & QR      |
| `ProductItem`                       | `integration` | `product_items`             | Product & QR      |
| `QRActivationParameters`            | `integration` | `qr_activation_parameters`  | Product & QR      |
| `QRActivationTrack`                 | `integration` | `qr_activation_tracks`      | Product & QR      |
| `WarrantyPeriod`                    | `integration` | `warranty_periods`          | Warranty          |
| `Warranty`                          | `integration` | `warranties`                | Warranty          |
| `Campaign`                          | `integration` | `campaigns`                 | Campaign & Coupon |
| `Play2WinPrize`                     | `integration` | `play2win_prizes`           | Campaign & Coupon |
| `webCampaign`                       | `integration` | `web_campaigns`             | Campaign & Coupon |
| `Lead`                              | `integration` | `leads`                     | Campaign & Coupon |
| `Tags`                              | `integration` | `tags`                      | Campaign & Coupon |
| `Coupon`                            | `certgen`     | `coupons`                   | Campaign & Coupon |
| `CouponUnlockLog`                   | `certgen`     | `coupon_unlock_logs`        | Campaign & Coupon |
| `ExternalCoupon`                    | `certgen`     | `external_coupons`          | Campaign & Coupon |
| `CouponDuration`                    | `certgen`     | `coupon_durations`          | Campaign & Coupon |
| `ShopifyCoupon`                     | `certgen`     | `shopify_configs`           | Campaign & Coupon |
| `Message_template`                  | `integration` | `message_templates`         | Messaging         |
| `LeadTagMessage`                    | `integration` | `bulk_message_jobs`         | Messaging         |
| `ScheduleMessage`                   | `integration` | `scheduled_messages`        | Messaging         |
| `SMSReport`                         | `integration` | `sms_reports`               | Messaging         |
| `WhatsappReport`                    | `integration` | `whatsapp_reports`          | Messaging         |
| `RcsTemplate`                       | `integration` | `rcs_templates`             | Messaging         |
| `RcsCredential`                     | `integration` | `rcs_credentials`           | Messaging         |
| `RCSReport`                         | `integration` | `rcs_reports`               | Messaging         |
| `MessageSummary` + `MsgSummaryUsed` | `integration` | `message_credits`           | Messaging         |
| `MetaCampaign`                      | `integration` | `meta_campaigns`            | Analytics         |
| `TenantData`                        | `certgen`     | merged into `organizations` | Auth/Tenant       |

---

## Key Design Decisions

**Brand → Organization merge**
`Brand.public_key`, `Brand.private_key`, and `Brand.short_code` move directly onto
`organizations`. No separate brand table exists in the new system.

**`Order` → `qr_blocks`**
Renamed for domain clarity. The old `firebase_url` becomes `gcs_url`.

**Campaign multi-link columns collapsed**
The 5 separate `multi_link_logo1..5` / `multi_link_name1..5` / `multi_link_url1..5` columns
collapse into a single `multilink_items JSONB` array. Same for `game_field1..6` + `game_value1..6`
→ `game_config JSONB`.

**`Coupon` vs `Lead` separation**
In the old system these were partially duplicated (both stored mobile, name, coupon code).
In the new design `leads` is the customer record and `coupons` is the issued coupon — both
linked via `campaign_id`. Add a `lead_id UUID REFERENCES leads(id)` FK on `coupons` if you
want a hard link between the two.

**DLT compliance on `message_templates`**
`dlt_template_id` and `dlt_principal_entity_id` are kept and remain mandatory when
`channel = 'sms'`. Enforce this at the service layer with a validator.

**`qr_credit_usage` table (new)**
Tracks per-block QR generation against the org's monthly quota. Before generating a block,
check `SUM(quantity) WHERE tenant_id = ? AND used_at >= start_of_month` against
`organizations.qr_credit_limit`.

**`qr_scan_events` table (new)**
Replaces the external Metamo integration. Every QR scan writes a row here with GPS coords
resolved in-house to city/state/country — no Google Maps API dependency.

**Not migrated (excluded from scope)**

- `CertificateTemplate`, `CertificateRecipient`, `CertificateAsyncdownload` — Certificate module
- `Pallet`, `Palletitem`, `PalletDistributor` — Track & Trace module
- `QReport`, `QSection`, `ReportTemplate` — Quality Reports (assess separately)
