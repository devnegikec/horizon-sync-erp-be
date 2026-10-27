#!/usr/bin/env python3
"""
Phase 2 — Migrate the `elemaze` client's QSeal data
        from the old Django/AWS Postgres tenant schema (`elemage`)
        into the new ERP core-service database (Railway dev).

Phase 1 (`phase1_*.sql`) migrated organizations/users into identity_db.
This script migrates the QSeal *domain* data into core_db.

What it migrates
----------------
  old (schema `elemage`)                     ->  new (core_db)
  ------------------------------------------    -----------------------------
  integration_brand                          ->  brands
  integration_product                        ->  products + qr_products
  integration_serialnumformat                ->  qr_product_settings (serial_prefix)
  integration_channel                        ->  qr_product_settings (channel)
  integration_destinationmarket              ->  destination_markets
                                                 + qr_product_settings (destination)
  integration_warrantyperiod                 ->  warranty_periods
                                                 + qr_product_settings (shelf_life)
  (derived, one per product)                 ->  product_skus
  integration_order                          ->  qr_blocks
  integration_productitem                    ->  product_items
  integration_qractivationparameters         ->  qr_activation_parameters
                                                 (+ qseal_parameters with --mirror-qseal)
  integration_productcertificate             ->  qr_scan_events
  integration_lead                           ->  campaign_leads
  integration_warranty                       ->  warranties  (empty in elemage)

Not migrated (no target equivalent / out of QSeal scope)
---------------------------------------------------------
  integration_store, integration_storeposbill, integration_storepospayment,
  integration_storepospurchaseitem, integration_pallet, integration_palletitem,
  integration_skuqr, integration_qr, integration_analyticsevent,
  integration_messagesummary / _smsreport / _whatsappreport (messaging),
  integration_nft, integration_campaign, integration_leadaction,
  integration_otp, auth_* (users moved in Phase 1).
  See the report printed at the end.

Design notes
------------
* IDs are deterministic (uuid5) so the script is safely re-runnable — every
  insert is `ON CONFLICT (id) DO UPDATE`.
* Source extraction runs `psql --csv` INSIDE the prod container over SSH, so no
  AWS credentials leave the server and no port has to be opened.
* Nothing is committed unless every step succeeds (`--dry-run` rolls back).
* `product_items.serial_number` has a *global* unique index in the new schema,
  so rows whose serial already exists under a different id are skipped and
  reported instead of aborting the whole migration.

Usage
-----
  export TARGET_DATABASE_URL='postgresql://postgres:PASS@xxx.proxy.rlwy.net:PORT/railway'
  export IDENTITY_DATABASE_URL='postgresql://postgres:PASS@yyy.proxy.rlwy.net:PORT/railway'

  # preview, no writes
  python scripts/migration/phase2_migrate_elemage_qseal.py --dry-run

  # real run
  python scripts/migration/phase2_migrate_elemage_qseal.py \
      --org-slug elemage --mirror-qseal

  # if you already have a tunnel/open DB instead of SSH
  python ... --source-mode direct --source-url "$AWS_PROD_URL"

Dependencies: psycopg2-binary (already in core-service requirements),
cryptography (only needed to re-key the brand).
"""

from __future__ import annotations

import argparse
import csv
import io
import json
import os
import shlex
import shutil
import subprocess
import sys
import uuid
from collections import Counter
from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation
from typing import Any, Iterable

try:
    import psycopg2
    import psycopg2.extras
    from psycopg2.extras import Json, execute_values
except ImportError:  # pragma: no cover
    sys.exit("psycopg2 is required: pip install psycopg2-binary")

# --------------------------------------------------------------------------- #
# Deterministic IDs
# --------------------------------------------------------------------------- #
NS = uuid.UUID("6f9619ff-8b86-d011-b42d-00c04fc964ff")  # stable, project-local


def did(kind: str, src_id: Any) -> str:
    """Deterministic UUID for a legacy row: same input -> same UUID forever."""
    return str(uuid.uuid5(NS, f"elemage:{kind}:{src_id}"))


# --------------------------------------------------------------------------- #
# CSV / value coercion helpers (psql --csv emits '' for NULL and 't'/'f' bools)
# --------------------------------------------------------------------------- #
def s(v: Any) -> str | None:
    """Empty string -> None, otherwise stripped string."""
    if v is None:
        return None
    v = str(v).strip()
    return v or None


def i(v: Any) -> int | None:
    v = s(v)
    if v is None:
        return None
    try:
        return int(float(v))
    except ValueError:
        return None


def d(v: Any) -> Decimal | None:
    v = s(v)
    if v is None:
        return None
    try:
        return Decimal(v)
    except InvalidOperation:
        return None


def b(v: Any) -> bool:
    v = s(v)
    if v is None:
        return False
    return v.lower() in ("t", "true", "1", "yes", "y")


def ts(v: Any) -> str | None:
    """Timestamps/dates are handed to Postgres verbatim; just normalise blanks."""
    return s(v)


def js(obj: Any) -> Json:
    return Json(obj, dumps=lambda o: json.dumps(o, default=str))


# --------------------------------------------------------------------------- #
# Source access: SSH -> docker exec -> psql --csv
# --------------------------------------------------------------------------- #
class SSHSource:
    def __init__(
        self,
        host: str,
        user: str,
        key: str,
        container: str,
        pg_user: str,
        pg_db: str,
        schema: str,
    ):
        self.host, self.user, self.key = host, user, key
        self.container, self.pg_user, self.pg_db, self.schema = (
            container,
            pg_user,
            pg_db,
            schema,
        )
        if not os.path.exists(os.path.expanduser(self.key)):
            sys.exit(f"SSH key not found: {self.key}")
        if not shutil.which("ssh"):
            sys.exit("ssh client not found on PATH")

    def q(self, sql: str) -> list[dict[str, str]]:
        remote = (
            f"docker exec -i {shlex.quote(self.container)} "
            f"psql -U {shlex.quote(self.pg_user)} -d {shlex.quote(self.pg_db)} "
            f"--csv -q -f -"
        )
        cmd = [
            "ssh",
            "-i",
            os.path.expanduser(self.key),
            "-o",
            "BatchMode=yes",
            "-o",
            "StrictHostKeyChecking=accept-new",
            "-o",
            "ConnectTimeout=15",
            f"{self.user}@{self.host}",
            remote,
        ]
        proc = subprocess.run(
            cmd, input=sql.encode("utf-8"), capture_output=True, timeout=1800
        )
        if proc.returncode != 0:
            raise RuntimeError(
                f"Source query failed (rc={proc.returncode}):\n"
                f"{proc.stderr.decode('utf-8', 'replace')[:2000]}"
            )
        return _csv_rows(proc.stdout.decode("utf-8", "replace"))


class DirectSource:
    def __init__(self, url: str):
        self.url = url

    def q(self, sql: str) -> list[dict[str, str]]:
        with psycopg2.connect(self.url, connect_timeout=30) as conn:
            with conn.cursor() as cur:
                cur.execute(sql)
                cols = [c[0] for c in cur.description]
                out = []
                for row in cur.fetchall():
                    out.append({c: _direct_str(v) for c, v in zip(cols, row)})
                return out


def _direct_str(v: Any) -> str:
    if v is None:
        return ""
    if isinstance(v, bool):
        return "t" if v else "f"
    return str(v)


def _csv_rows(text: str) -> list[dict[str, str]]:
    reader = csv.DictReader(io.StringIO(text))
    return [dict(r) for r in reader]


# --------------------------------------------------------------------------- #
# Target helpers
# --------------------------------------------------------------------------- #
def upsert_many(
    cur,
    table: str,
    cols: list[str],
    rows: list[tuple],
    conflict: str = "(id)",
    page_size: int = 500,
    update: bool = True,
) -> int:
    if not rows:
        return 0
    updatable = [c for c in cols if c not in ("id", "created_at")]
    if update and updatable:
        set_clause = ", ".join(f"{c} = EXCLUDED.{c}" for c in updatable)
        action = f"DO UPDATE SET {set_clause}"
    else:
        action = "DO NOTHING"
    sql = (
        f"INSERT INTO {table} ({', '.join(cols)}) VALUES %s "
        f"ON CONFLICT {conflict} {action}"
    )
    execute_values(cur, sql, rows, page_size=page_size)
    return len(rows)


def table_exists(cur, table: str) -> bool:
    cur.execute("SELECT to_regclass(%s) IS NOT NULL", (f"public.{table}",))
    return bool(cur.fetchone()[0])


# --------------------------------------------------------------------------- #
# Brand key re-generation (old = RSA/unknown, new = ECDSA P-256 + Fernet)
# --------------------------------------------------------------------------- #
def new_brand_keypair(
    fk_secret: str | None, seed: str
) -> tuple[str | None, str | None]:
    """Build a Fernet-encrypted ECDSA P-256 pair.

    The scalar is derived deterministically from (secret, seed) so re-running
    the migration does not silently rotate the brand's signing key.
    """
    if not fk_secret:
        return None, None
    try:
        from cryptography.fernet import Fernet
        from cryptography.hazmat.primitives import serialization
        from cryptography.hazmat.primitives.asymmetric import ec
    except ImportError:
        return None, None

    import hashlib

    order = 0xFFFFFFFF00000000FFFFFFFFFFFFFFFFBCE6FAADA7179E84F3B9CAC2FC632551
    digest = hashlib.sha256(f"{fk_secret}|{seed}".encode()).digest()
    scalar = (int.from_bytes(digest, "big") % (order - 1)) + 1
    key = ec.derive_private_key(scalar, ec.SECP256R1())
    priv_hex = format(scalar, "064x")
    enc = Fernet(fk_secret.encode()).encrypt(priv_hex.encode()).decode()
    pub = (
        key.public_key()
        .public_bytes(
            serialization.Encoding.X962, serialization.PublicFormat.UncompressedPoint
        )
        .hex()
    )
    return enc, pub


# --------------------------------------------------------------------------- #
# Migration
# --------------------------------------------------------------------------- #
CERT_TYPE_TO_QR_TYPE = {
    "B": "dual",
    "C": "dynamic",
    "D": "secure_code",
    "O": "one_time",
    "S": "static",
    "W": "post_activation",
}


class Migrator:
    def __init__(self, args, org_id: uuid.UUID):
        self.a = args
        self.org = str(org_id)
        self.src: SSHSource | DirectSource = self._make_source()
        self.schema = args.schema
        self.stats: dict[str, int] = {}
        self.warnings: list[str] = []
        self.skipped_serial: list[str] = []
        # id maps
        self.m_brand: dict[str, str] = {}
        self.m_product: dict[str, str] = {}
        self.m_shared_product: dict[str, str] = {}
        self.m_sku: dict[str, str] = {}
        self.m_block: dict[str, str] = {}
        self.m_item: dict[str, str] = {}
        self.m_setting: dict[str, str] = {}  # (type, src_id) -> uuid
        self.m_destmarket: dict[str, str] = {}

    # -- infra ------------------------------------------------------------- #
    def _make_source(self):
        if self.a.source_mode == "direct":
            url = self.a.source_url or os.getenv("SOURCE_DATABASE_URL")
            if not url:
                sys.exit(
                    "--source-mode direct requires --source-url / SOURCE_DATABASE_URL"
                )
            return DirectSource(url)
        return SSHSource(
            self.a.ssh_host,
            self.a.ssh_user,
            self.a.ssh_key,
            self.a.container,
            self.a.pg_user,
            self.a.pg_db,
            self.a.schema,
        )

    def t(self, name: str) -> str:
        """Fully-qualified source table name."""
        return f"{self.schema}.{name}"

    def warn(self, msg: str) -> None:
        self.warnings.append(msg)
        print(f"   ! {msg}")

    # -- steps ------------------------------------------------------------- #
    def migrate(self, cur) -> None:
        self.step_brand(cur)
        self.step_settings(cur)
        self.step_products(cur)
        self.step_skus(cur)
        self.step_blocks(cur)
        self.step_items(cur)
        self.step_activation(cur)
        self.step_scan_events(cur)
        self.step_leads(cur)
        self.step_warranties(cur)

    # 1. brands ------------------------------------------------------------- #
    def step_brand(self, cur) -> None:
        rows = self.src.q(
            f"SELECT id, name, short_code, public_key, private_key "
            f"FROM {self.t('integration_brand')} ORDER BY id"
        )
        out = []
        for r in rows:
            buid = did("brand", r["id"])
            self.m_brand[r["id"]] = buid
            enc, pub = new_brand_keypair(
                self.a.brand_key_secret, f"elemage:brand:{r['id']}"
            )
            legacy_pub = s(r.get("public_key"))
            if not pub and legacy_pub:
                self.warn(
                    "brand public key copied from old DB but it is the legacy "
                    "key format (new ERP uses ECDSA P-256). Provide "
                    "--brand-key-secret to generate a compatible pair."
                )
            out.append(
                (
                    buid,
                    self.org,
                    s(r.get("name")),
                    s(r.get("short_code")),
                    pub or legacy_pub,
                    enc,  # old private key is NOT reusable (Fernet/ECDSA)
                    ts(self.a.now),
                    ts(self.a.now),
                )
            )
        n = upsert_many(
            cur,
            "brands",
            [
                "id",
                "organization_id",
                "name",
                "short_code",
                "public_key",
                "private_key_encrypted",
                "created_at",
                "updated_at",
            ],
            out,
        )
        self.stats["brands"] = n
        print(f"✓ brands                     {n}")

    # 2. lookup settings ---------------------------------------------------- #
    def step_settings(self, cur) -> None:
        # ---- serial prefixes
        rows = self.src.q(
            f"SELECT id, serial_prefix, is_active, is_default, create_time "
            f"FROM {self.t('integration_serialnumformat')} ORDER BY id"
        )
        out = []
        for r in rows:
            suid = did("setting:serial_prefix", r["id"])
            self.m_setting[f"serial_prefix:{r['id']}"] = suid
            out.append(
                (
                    suid,
                    self.org,
                    "serial_prefix",
                    s(r["serial_prefix"]) or "",
                    s(r["serial_prefix"]) or "",
                    "Serial prefix migrated from elemaze",
                    0,
                    b(r.get("is_active")),
                    js({"old_id": r["id"], "is_default": b(r.get("is_default"))}),
                    ts(r.get("create_time")),
                    ts(r.get("create_time")),
                )
            )
        n1 = upsert_many(
            cur,
            "qr_product_settings",
            [
                "id",
                "organization_id",
                "setting_type",
                "value",
                "label",
                "description",
                "sort_order",
                "is_active",
                "extra_data",
                "created_at",
                "updated_at",
            ],
            out,
        )

        # ---- channels
        rows = self.src.q(
            f"SELECT id, name, description, is_active, is_default, email, "
            f"distributor_id, created_at FROM {self.t('integration_channel')} ORDER BY id"
        )
        out = []
        for r in rows:
            suid = did("setting:channel", r["id"])
            self.m_setting[f"channel:{r['id']}"] = suid
            out.append(
                (
                    suid,
                    self.org,
                    "channel",
                    s(r["name"]) or "",
                    s(r["name"]) or "",
                    s(r.get("description")),
                    0,
                    b(r.get("is_active")),
                    js(
                        {
                            "old_id": r["id"],
                            "is_default": b(r.get("is_default")),
                            "email": s(r.get("email")),
                            "distributor_id": s(r.get("distributor_id")),
                        }
                    ),
                    ts(r.get("created_at")),
                    ts(r.get("created_at")),
                )
            )
        n2 = upsert_many(
            cur,
            "qr_product_settings",
            [
                "id",
                "organization_id",
                "setting_type",
                "value",
                "label",
                "description",
                "sort_order",
                "is_active",
                "extra_data",
                "created_at",
                "updated_at",
            ],
            out,
        )

        # ---- destination markets (both tables)
        rows = self.src.q(
            f"SELECT id, name, currency, is_active, create_time "
            f"FROM {self.t('integration_destinationmarket')} ORDER BY id"
        )
        dm_out, ps_out = [], []
        for r in rows:
            duid = did("destination_market", r["id"])
            self.m_destmarket[r["id"]] = duid
            suid = did("setting:destination", r["id"])
            self.m_setting[f"destination:{r['id']}"] = suid
            name = s(r["name"]) or ""
            dm_out.append(
                (
                    duid,
                    self.org,
                    name,
                    (name[:20] if name else "NA"),
                    name,
                    None,
                    s(r.get("currency")),
                    None,
                    None,
                    b(r.get("is_active")),
                    None,
                    js({"old_id": r["id"]}),
                    ts(r.get("create_time")),
                    ts(r.get("create_time")),
                )
            )
            ps_out.append(
                (
                    suid,
                    self.org,
                    "destination",
                    s(r.get("currency")) or name,
                    name,
                    None,
                    0,
                    b(r.get("is_active")),
                    js({"old_id": r["id"], "currency": s(r.get("currency"))}),
                    ts(r.get("create_time")),
                    ts(r.get("create_time")),
                )
            )
        n3 = upsert_many(
            cur,
            "destination_markets",
            [
                "id",
                "organization_id",
                "name",
                "code",
                "country",
                "region",
                "currency_code",
                "language",
                "tax_rate",
                "is_active",
                "notes",
                "extra_data",
                "created_at",
                "updated_at",
            ],
            dm_out,
        )
        n4 = upsert_many(
            cur,
            "qr_product_settings",
            [
                "id",
                "organization_id",
                "setting_type",
                "value",
                "label",
                "description",
                "sort_order",
                "is_active",
                "extra_data",
                "created_at",
                "updated_at",
            ],
            ps_out,
        )

        # ---- warranty periods (shelf life)
        rows = self.src.q(
            f"SELECT id, number_of_years, is_active, is_default, created_at "
            f"FROM {self.t('integration_warrantyperiod')} ORDER BY id"
        )
        wp_out, ps_out = [], []
        for r in rows:
            wuid = did("warranty_period", r["id"])
            suid = did("setting:shelf_life", r["id"])
            self.m_setting[f"shelf_life:{r['id']}"] = suid
            months = i(r.get("number_of_years"))
            wp_out.append(
                (
                    wuid,
                    self.org,
                    months,
                    b(r.get("is_active")),
                    b(r.get("is_default")),
                    ts(r.get("created_at")),
                )
            )
            ps_out.append(
                (
                    suid,
                    self.org,
                    "shelf_life",
                    str(months),
                    f"{months} Months",
                    "Migrated from old warranty period",
                    0,
                    b(r.get("is_active")),
                    js({"old_id": r["id"], "is_default": b(r.get("is_default"))}),
                    ts(r.get("created_at")),
                    ts(r.get("created_at")),
                )
            )
        n5 = upsert_many(
            cur,
            "warranty_periods",
            [
                "id",
                "organization_id",
                "months",
                "is_active",
                "is_default",
                "created_at",
            ],
            wp_out,
        )
        n6 = upsert_many(
            cur,
            "qr_product_settings",
            [
                "id",
                "organization_id",
                "setting_type",
                "value",
                "label",
                "description",
                "sort_order",
                "is_active",
                "extra_data",
                "created_at",
                "updated_at",
            ],
            ps_out,
        )
        self.stats["qr_product_settings"] = n1 + n2 + n4 + n6
        self.stats["destination_markets"] = n3
        self.stats["warranty_periods"] = n5
        print(
            f"✓ lookup settings            serial={n1} channel={n2} "
            f"destination={n4} shelf_life={n6}"
        )
        print(f"✓ destination_markets        {n3}")
        print(f"✓ warranty_periods           {n5}")

    # 3. products (shared catalog + qr_products) ---------------------------- #
    def step_products(self, cur) -> None:
        rows = self.src.q(
            f"""SELECT p.id, p.name, p."GTIN" AS gtin, p.landing_page, p.image,
                       p.banner_image, p.email, p.phone_number,
                       p.client_product_auth_url, p.activation_method,
                       p.num_activated_qr, p.sr_number_type,
                       p.redirect_to_client, p.created_at, p.generic_name,
                       p.brand_id, p.warrantyperiod_id, p.serialnumformat_id,
                       p.industry_id, p.show_consumer_risk_warning,
                       ind.name AS industry_name,
                       wp.number_of_years AS warranty_months
                  FROM {self.t("integration_product")} p
                  LEFT JOIN {self.t("integration_industry")} ind
                         ON ind.id = p.industry_id
                  LEFT JOIN {self.t("integration_warrantyperiod")} wp
                         ON wp.id = p.warrantyperiod_id
                 ORDER BY p.id"""
        )
        shared, qrp = [], []
        for r in rows:
            pid = r["id"]
            qid = did("qr_product", pid)
            sid = did("product", pid)
            self.m_product[pid] = qid
            self.m_shared_product[pid] = sid
            brand = self.m_brand.get(r.get("brand_id") or "")
            shelf = self.m_setting.get(f"shelf_life:{r.get('warrantyperiod_id') or ''}")
            prefix = self.m_setting.get(
                f"serial_prefix:{r.get('serialnumformat_id') or ''}"
            )
            name = s(r["name"]) or f"Product {pid}"

            shared.append(
                (
                    sid,
                    self.org,
                    name,
                    None,
                    s(r.get("gtin")),
                    s(r.get("generic_name")),
                    brand,
                    None,
                    "qseal",
                    js(
                        {
                            k: v
                            for k, v in {
                                "image": s(r.get("image")),
                                "banner": s(r.get("banner_image")),
                            }.items()
                            if v
                        }
                    ),
                    None,
                    True,
                    ts(r.get("created_at")),
                    ts(r.get("created_at")),
                )
            )
            qrp.append(
                (
                    qid,
                    self.org,
                    brand,
                    sid,
                    shelf,
                    prefix,
                    name,
                    None,
                    s(r.get("generic_name")),
                    s(r.get("gtin")),
                    s(r.get("industry_name")),
                    s(r.get("landing_page")),
                    s(r.get("image")),
                    s(r.get("banner_image")),
                    s(r.get("email")),
                    s(r.get("phone_number")),
                    s(r.get("client_product_auth_url")),
                    s(r.get("activation_method")) or "pre",
                    i(r.get("num_activated_qr")) or 0,
                    s(r.get("sr_number_type")),
                    b(r.get("redirect_to_client")),
                    i(r.get("warranty_months")),
                    None,
                    True,
                    None,
                    s(r.get("generic_name")),
                    None,
                    None,
                    None,
                    None,
                    None,
                    s(r.get("gtin")),
                    None,
                    None,
                    True,
                    js(
                        {
                            "old_id": pid,
                            "serialnumformat_id": r.get("serialnumformat_id"),
                            "show_consumer_risk_warning": b(
                                r.get("show_consumer_risk_warning")
                            ),
                        }
                    ),
                    ts(r.get("created_at")),
                    ts(r.get("created_at")),
                )
            )

        n_shared = upsert_many(
            cur,
            "products",
            [
                "id",
                "organization_id",
                "name",
                "sku",
                "gtin",
                "description",
                "brand_id",
                "category_id",
                "product_type",
                "images",
                "tags",
                "is_active",
                "created_at",
                "updated_at",
            ],
            shared,
        )
        n_qrp = upsert_many(
            cur,
            "qr_products",
            [
                "id",
                "organization_id",
                "brand_id",
                "product_id",
                "shelf_life_setting_id",
                "serial_prefix_setting_id",
                "name",
                "sku",
                "generic_name",
                "gtin",
                "industry",
                "landing_page",
                "image_url",
                "banner_image_url",
                "email",
                "phone_number",
                "client_product_auth_url",
                "activation_method",
                "num_activated_qr",
                "sr_number_type",
                "redirect_to_client",
                "warranty_period_months",
                "qr_type",
                "is_active",
                "item_code",
                "description",
                "uom",
                "standard_rate",
                "valuation_rate",
                "weight_per_unit",
                "weight_uom",
                "barcode",
                "maintain_stock",
                "has_batch_no",
                "has_serial_no",
                "extra_data",
                "created_at",
                "updated_at",
            ],
            qrp,
        )
        self.stats["products"] = n_shared
        self.stats["qr_products"] = n_qrp
        print(f"✓ products (catalog)         {n_shared}")
        print(f"✓ qr_products                {n_qrp}")

    # 4. one default SKU per product ---------------------------------------- #
    def step_skus(self, cur) -> None:
        rows = self.src.q(
            f"""SELECT id, name, "GTIN" AS gtin, sr_number_type, created_at
                  FROM {self.t("integration_product")} ORDER BY id"""
        )
        out = []
        for r in rows:
            pid = r["id"]
            suid = did("product_sku", pid)
            self.m_sku[pid] = suid
            out.append(
                (
                    suid,
                    self.org,
                    self.m_product[pid],
                    f"ELEMAGE-{pid}",
                    s(r.get("name")),
                    s(r.get("gtin")),
                    None,
                    s(r.get("sr_number_type")),
                    None,
                    None,
                    True,
                    js(
                        {
                            "old_id": pid,
                            "note": "auto-created: legacy products had no SKU variants",
                        }
                    ),
                    ts(r.get("created_at")),
                    ts(r.get("created_at")),
                )
            )
        n = upsert_many(
            cur,
            "product_skus",
            [
                "id",
                "organization_id",
                "product_id",
                "sku_code",
                "name",
                "gtin",
                "mrp",
                "sr_number_type",
                "image_url",
                "warranty_period_months",
                "is_active",
                "extra_data",
                "created_at",
                "updated_at",
            ],
            out,
        )
        self.stats["product_skus"] = n
        print(f"✓ product_skus               {n}")

    # 5. blocks (old Order) -------------------------------------------------- #
    def step_blocks(self, cur) -> None:
        rows = self.src.q(
            f"""SELECT id, product_id, batch, serialnumformat, sr_number,
                       sr_number_type, quantity, cert_type, size, colour_desc,
                       price, style, task_status, qr_image, manufacture_date,
                       expiry_date, firebase_url, created_at, updated_at
                  FROM {self.t("integration_order")} ORDER BY id"""
        )
        # actual number of generated units per order
        cnt_rows = self.src.q(
            f"""SELECT order_id, count(*) AS n
                  FROM {self.t("integration_productitem")}
                 WHERE order_id IS NOT NULL
                 GROUP BY order_id"""
        )
        item_counts = {r["order_id"]: i(r["n"]) or 0 for r in cnt_rows}
        out = []
        for r in rows:
            oid = r["id"]
            pid = r.get("product_id")
            product_uuid = self.m_product.get(pid or "")
            if not product_uuid:
                self.warn(f"order/block {oid} skipped: product {pid} not mapped")
                continue
            buid = did("qr_block", oid)
            self.m_block[oid] = buid
            cert = (s(r.get("cert_type")) or "C").upper()[:1]
            qr_type = CERT_TYPE_TO_QR_TYPE.get(cert, "dynamic")
            qty = i(r.get("quantity")) or 0
            generated = item_counts.get(oid, 0)
            done = (s(r.get("task_status")) or "").lower() in ("completed", "done")
            out.append(
                (
                    buid,
                    self.org,
                    self.m_sku.get(pid or ""),
                    product_uuid,
                    None,
                    None,
                    s(r.get("batch")) or f"batch-{oid}",
                    qr_type,
                    s(r.get("serialnumformat")),
                    s(r.get("sr_number")),
                    s(r.get("sr_number")),
                    s(r.get("sr_number_type")),
                    qty,
                    cert,
                    s(r.get("size")),
                    s(r.get("colour_desc")),
                    i(r.get("price")) if s(r.get("price")) else None,
                    s(r.get("style")),
                    s(r.get("task_status")),
                    "completed" if done else (s(r.get("task_status")) or "pending"),
                    None,
                    b(r.get("qr_image")),
                    generated,
                    100 if (done or generated) else 0,
                    None,
                    ts(r.get("manufacture_date")),
                    ts(r.get("expiry_date")),
                    False,
                    None,
                    None,
                    s(r.get("firebase_url")),
                    ts(r.get("created_at")),
                    ts(r.get("updated_at")),
                )
            )
        n = upsert_many(
            cur,
            "qr_blocks",
            [
                "id",
                "organization_id",
                "sku_id",
                "product_id",
                "channel_setting_id",
                "destination_setting_id",
                "batch",
                "qr_type",
                "serial_prefix",
                "starting_serial",
                "sr_number",
                "sr_number_type",
                "quantity",
                "cert_type",
                "size",
                "colour_desc",
                "price",
                "style",
                "task_status",
                "status",
                "task_id",
                "qr_image",
                "generated_count",
                "progress",
                "error_code",
                "manufacture_date",
                "expiry_date",
                "master_pack_enabled",
                "master_pack_size",
                "gcs_url",
                "download_url",
                "created_at",
                "updated_at",
            ],
            out,
            conflict="(id)",
        )
        self.stats["qr_blocks"] = n
        print(f"✓ qr_blocks (old orders)     {n}")

    # 6. product items ------------------------------------------------------- #
    def step_items(self, cur) -> None:
        rows = self.src.q(
            f"""SELECT id, product_id, order_id, channel_id, country_id,
                       serial_number, secrete_code, token_id, is_unit,
                       is_suspicious, is_verify, is_auth, qr_deactive,
                       qr_deactive_unit, scan_date, scans, scratch_scan_count,
                       created_at, updated_at
                  FROM {self.t("integration_productitem")} ORDER BY id"""
        )
        # scan aggregates from certificates
        scan_rows = self.src.q(
            f"""SELECT product_item_id, count(*) AS n,
                       min(created_at) AS first_scan,
                       max(created_at) AS last_scan
                  FROM {self.t("integration_productcertificate")}
                 GROUP BY product_item_id"""
        )
        scans = {r["product_item_id"]: r for r in scan_rows}

        # existing serials in target (global unique index) -> skip conflicts
        cur.execute(
            "SELECT serial_number, id::text FROM product_items WHERE organization_id = %s",
            (self.org,),
        )
        existing = {sn: pid for sn, pid in cur.fetchall()}

        out, skipped = [], []
        for r in rows:
            iid = r["id"]
            iuid = did("product_item", iid)
            self.m_item[iid] = iuid
            serial = s(r.get("serial_number"))
            pid = r.get("product_id")
            order_id = r.get("order_id")
            if serial and serial in existing and existing[serial] != iuid:
                # Point any child rows at the row that already owns this serial
                self.m_item[iid] = existing[serial]
                skipped.append(serial)
                continue
            if not self.m_product.get(pid or ""):
                self.warn(f"product_item {iid} skipped: product {pid} not mapped")
                continue
            agg = scans.get(iid)
            n_scans = i(agg["n"]) if agg else (i(r.get("scans")) or 0)
            out.append(
                (
                    iuid,
                    self.org,
                    self.m_product.get(pid or ""),
                    self.m_block.get(order_id or ""),
                    self.m_sku.get(pid or ""),
                    serial,
                    s(r.get("secrete_code")),
                    s(r.get("token_id")),
                    b(r.get("is_unit")),
                    b(r.get("is_suspicious")),
                    b(r.get("is_verify")),
                    b(r.get("is_auth")),
                    b(r.get("qr_deactive")),
                    b(r.get("qr_deactive_unit")),
                    not b(r.get("qr_deactive")),
                    ts(r.get("scan_date")) or (ts(agg["first_scan"]) if agg else None),
                    n_scans,
                    n_scans,
                    ts(agg["last_scan"]) if agg else ts(r.get("scan_date")),
                    None,
                    js(
                        {
                            "old_id": iid,
                            "old_order_id": order_id,
                            "channel_id": r.get("channel_id"),
                            "country_id": r.get("country_id"),
                            "scratch_scan_count": i(r.get("scratch_scan_count")),
                        }
                    ),
                    ts(r.get("created_at")),
                    ts(r.get("updated_at")),
                )
            )

        n = upsert_many(
            cur,
            "product_items",
            [
                "id",
                "organization_id",
                "product_id",
                "block_id",
                "sku_id",
                "serial_number",
                "secrete_code",
                "token_id",
                "is_unit",
                "is_suspicious",
                "is_verify",
                "is_auth",
                "qr_deactive",
                "qr_deactive_unit",
                "qr_active",
                "scan_date",
                "scans",
                "scan_count",
                "last_scanned_at",
                "destination_market",
                "extra_data",
                "created_at",
                "updated_at",
            ],
            out,
        )
        self.stats["product_items"] = n
        self.stats["product_items_skipped"] = len(skipped)
        self.skipped_serial = skipped[:20]
        print(f"✓ product_items              {n}")
        if skipped:
            self.warn(
                f"{len(skipped)} product_items skipped: serial already exists in "
                f"target with a different id (global unique index). e.g. {skipped[:5]}"
            )

    # 7. activation parameters ---------------------------------------------- #
    def step_activation(self, cur) -> None:
        rows = self.src.q(
            f"""SELECT id, product_id, order_id, serial_number,
                       manufacturing_date, expiry_date, manufacturing_unit,
                       dispatch_batch, destination_market, mrp, currency,
                       batch_size, qr_settings, history, qr_cascade,
                       parent_id, parent_app_id, created_on
                  FROM {self.t("integration_qractivationparameters")}
                 ORDER BY id"""
        )
        qrap, qseal = [], []
        for r in rows:
            aid = r["id"]
            auid = did("qr_activation_parameter", aid)
            pid = r.get("product_id")
            common = (
                auid,
                self.org,
                self.m_product.get(pid or ""),
                self.m_block.get(r.get("order_id") or ""),
                s(r.get("serial_number")),
                ts(r.get("manufacturing_date")),
                ts(r.get("expiry_date")),
                s(r.get("manufacturing_unit")) or "Unknown",
                s(r.get("dispatch_batch")),
                s(r.get("destination_market")),
                d(r.get("mrp")),
                s(r.get("currency")),
                i(r.get("batch_size")),
            )
            extra = js(
                {
                    "old_id": aid,
                    "old_order_id": r.get("order_id"),
                    "old_parent_id": r.get("parent_id"),
                    "old_parent_app_id": r.get("parent_app_id"),
                }
            )
            # parent_id / parent_app_id pointed at integration_qractivationtrack,
            # which is EMPTY in this tenant -> always NULL here.
            qrap.append(
                common
                + (
                    b(r.get("qr_settings")),
                    b(r.get("history")),
                    b(r.get("qr_cascade")),
                    extra,
                    None,
                    None,
                    ts(r.get("created_on")),
                    ts(r.get("created_on")),
                )
            )
            qseal.append(
                common
                + (
                    b(r.get("qr_settings")),
                    b(r.get("qr_cascade")),
                    None,
                    None,
                    extra,
                    ts(r.get("created_on")),
                )
            )

        n = upsert_many(
            cur,
            "qr_activation_parameters",
            [
                "id",
                "organization_id",
                "product_id",
                "block_id",
                "serial_number",
                "manufacturing_date",
                "expiry_date",
                "manufacturing_unit",
                "dispatch_batch",
                "destination_market",
                "mrp",
                "currency",
                "batch_size",
                "qr_settings",
                "history",
                "qr_cascade",
                "extra_data",
                "parent_id",
                "parent_app_id",
                "created_at",
                "updated_at",
            ],
            qrap,
        )
        self.stats["qr_activation_parameters"] = n
        print(f"✓ qr_activation_parameters   {n}")

        if self.a.mirror_qseal and table_exists(cur, "qseal_parameters"):
            n2 = upsert_many(
                cur,
                "qseal_parameters",
                [
                    "id",
                    "organization_id",
                    "product_id",
                    "block_id",
                    "serial_number",
                    "manufacturing_date",
                    "expiry_date",
                    "manufacturing_unit",
                    "dispatch_batch",
                    "destination_market",
                    "mrp",
                    "currency",
                    "batch_size",
                    "qseal_settings",
                    "qseal_cascade",
                    "parent_id",
                    "parent_app_id",
                    "extra_data",
                    "created_at",
                ],
                qseal,
            )
            self.stats["qseal_parameters"] = n2
            print(f"✓ qseal_parameters (mirror)  {n2}")
        elif self.a.mirror_qseal:
            self.warn("qseal_parameters table not found in target — mirror skipped")

    # 8. scan events (old ProductCertificate) -------------------------------- #
    def step_scan_events(self, cur) -> None:
        rows = self.src.q(
            f"""SELECT c.id, c.product_item_id, c.product_id, c.name,
                       c.mobile_number, c.email, c.coupon, c.scan_location,
                       c.ip, c.latitude, c.longitude, c.is_auth,
                       c.is_suspicious, c.created_at,
                       i.serial_number, i.order_id
                  FROM {self.t("integration_productcertificate")} c
                  LEFT JOIN {self.t("integration_productitem")} i
                         ON i.id = c.product_item_id
                 ORDER BY c.id"""
        )
        out = []
        for r in rows:
            cid = r["id"]
            euid = did("qr_scan_event", cid)
            item_id = r.get("product_item_id")
            order_id = r.get("order_id")
            pid = r.get("product_id")
            out.append(
                (
                    euid,
                    self.org,
                    self.m_item.get(item_id or ""),
                    self.m_product.get(pid or ""),
                    self.m_block.get(order_id or ""),
                    s(r.get("serial_number")),
                    ts(r.get("created_at")),
                    s(r.get("ip")),
                    d(r.get("latitude")),
                    d(r.get("longitude")),
                    s(r.get("scan_location")),
                    js(
                        {
                            "old_id": cid,
                            "old_product_item_id": item_id,
                            "name": s(r.get("name")),
                            "mobile": s(r.get("mobile_number")),
                            "email": s(r.get("email")),
                            "coupon": s(r.get("coupon")),
                            "source": "integration_productcertificate",
                        }
                    ),
                    euid,
                    "suspicious" if b(r.get("is_suspicious")) else "valid",
                    b(r.get("is_auth")),
                    False,  # is_bot
                    b(r.get("is_suspicious")),
                    100 if b(r.get("is_suspicious")) else 0,  # risk_score
                    js([]),  # suspicious_reasons
                    "not_flagged",
                )
            )
        n = upsert_many(
            cur,
            "qr_scan_events",
            [
                "id",
                "organization_id",
                "product_item_id",
                "product_id",
                "block_id",
                "serial_number",
                "scan_timestamp",
                "ip_address",
                "latitude",
                "longitude",
                "city",
                "extra_data",
                "event_id",
                "verification_status",
                "authentic",
                "is_bot",
                "is_suspicious",
                "risk_score",
                "suspicious_reasons",
                "review_status",
            ],
            out,
        )
        self.stats["qr_scan_events"] = n
        print(f"✓ qr_scan_events             {n}")

    # 9. leads --------------------------------------------------------------- #
    def step_leads(self, cur) -> None:
        rows = self.src.q(
            f"""SELECT id, coupon, name, mobilenumber, email, value, used,
                       expiry, timestamp, used_timestamp, location, enjoy, easy,
                       rating, comment, status, campaign_id, lead_owner_id,
                       external_lead, state_name, dob, gender, tag_external_id,
                       address, country, gstnumber, material_status, occuption,
                       pincode, redeem_mode
                  FROM {self.t("integration_lead")} ORDER BY id"""
        )
        out = []
        for r in rows:
            lid = r["id"]
            out.append(
                (
                    did("campaign_lead", lid),
                    self.org,
                    None,  # campaign_id: integration_campaign is empty in elemage
                    s(r.get("name")),
                    s(r.get("mobilenumber")),
                    s(r.get("email")),
                    s(r.get("address")),
                    s(r.get("location")),
                    s(r.get("pincode")),
                    ts(r.get("dob")),
                    s(r.get("gender")),
                    s(r.get("occuption")),
                    s(r.get("gstnumber")),
                    s(r.get("state_name")),
                    s(r.get("country")),
                    s(r.get("coupon")),
                    s(r.get("value")),
                    s(r.get("used")),
                    ts(r.get("expiry")),
                    ts(r.get("timestamp")),
                    ts(r.get("used_timestamp")),
                    s(r.get("rating")),
                    s(r.get("comment")),
                    s(r.get("status")),
                    s(r.get("redeem_mode")) or "none",
                    b(r.get("external_lead")),
                    js(
                        {
                            "old_id": lid,
                            "enjoy": s(r.get("enjoy")),
                            "easy": s(r.get("easy")),
                            "material_status": s(r.get("material_status")),
                            "lead_owner_id": r.get("lead_owner_id"),
                            "tag_external_id": r.get("tag_external_id"),
                            "old_campaign_id": r.get("campaign_id"),
                        }
                    ),
                    ts(r.get("timestamp")),
                    ts(r.get("timestamp")),
                )
            )
        n = upsert_many(
            cur,
            "campaign_leads",
            [
                "id",
                "organization_id",
                "campaign_id",
                "name",
                "mobilenumber",
                "email",
                "address",
                "location",
                "pincode",
                "dob",
                "gender",
                "occupation",
                "gst_number",
                "state_name",
                "country",
                "coupon",
                "value",
                "used",
                "expiry",
                "timestamp",
                "used_timestamp",
                "rating",
                "comment",
                "status",
                "redeem_mode",
                "external_lead",
                "extra_data",
                "created_at",
                "updated_at",
            ],
            out,
        )
        self.stats["campaign_leads"] = n
        print(f"✓ campaign_leads             {n}")
        if rows:
            self.warn(
                "campaign_leads inserted with campaign_id = NULL because "
                "integration_campaign is empty in elemage."
            )

    # 10. warranties (empty in elemage, kept for completeness) --------------- #
    def step_warranties(self, cur) -> None:
        rows = self.src.q(
            f"""SELECT id, name, mobilenumber, email, serial_number, location,
                       ip, created_on, warranty_valid_till
                  FROM {self.t("integration_warranty")} ORDER BY id"""
        )
        if not rows:
            self.stats["warranties"] = 0
            print("✓ warranties                 0 (none in source)")
            return
        out = []
        for r in rows:
            out.append(
                (
                    did("warranty", r["id"]),
                    self.org,
                    None,
                    s(r.get("serial_number")),
                    s(r.get("name")) or "Unknown",
                    s(r.get("mobilenumber")) or "",
                    s(r.get("email")),
                    s(r.get("location")),
                    s(r.get("ip")),
                    None,
                    ts(r.get("warranty_valid_till")),
                    js({"old_id": r["id"]}),
                    ts(r.get("created_on")),
                )
            )
        n = upsert_many(
            cur,
            "warranties",
            [
                "id",
                "organization_id",
                "product_item_id",
                "serial_number",
                "customer_name",
                "mobile",
                "email",
                "location",
                "ip",
                "purchase_date",
                "warranty_valid_till",
                "extra_data",
                "created_at",
            ],
            out,
        )
        self.stats["warranties"] = n
        print(f"✓ warranties                 {n}")


# --------------------------------------------------------------------------- #
# CLI / main
# --------------------------------------------------------------------------- #
def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Phase 2: migrate elemage (elemaze) QSeal data -> new ERP core_db",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    p.add_argument(
        "--target-url",
        default=os.getenv("TARGET_DATABASE_URL"),
        help="core-service Postgres URL (Railway dev). Env: TARGET_DATABASE_URL",
    )
    p.add_argument(
        "--identity-url",
        default=os.getenv("IDENTITY_DATABASE_URL"),
        help="identity_db URL, used to resolve --org-slug. Env: IDENTITY_DATABASE_URL",
    )
    p.add_argument("--org-id", help="Target organization UUID (skips slug lookup)")
    p.add_argument("--org-slug", default="elemage", help="Target organization slug")

    # source
    p.add_argument("--source-mode", choices=("ssh", "direct"), default="ssh")
    p.add_argument(
        "--source-url", help="Direct source DB URL (with --source-mode direct)"
    )
    p.add_argument("--ssh-host", default="3.6.154.21")
    p.add_argument("--ssh-user", default="ec2-user")
    p.add_argument("--ssh-key", default="~/adminportal-prod-key.pem")
    p.add_argument("--container", default="postgres_db")
    p.add_argument("--pg-user", default="adminportal_user")
    p.add_argument("--pg-db", default="adminportal")
    p.add_argument("--schema", default="elemage")

    # behaviour
    p.add_argument(
        "--brand-key-secret",
        default=os.getenv("BRAND_KEY_ENCRYPTION_SECRET"),
        help="Fernet key to generate an ECDSA pair for the brand",
    )
    p.add_argument(
        "--mirror-qseal",
        action="store_true",
        help="Also write the same rows into qseal_parameters",
    )
    p.add_argument("--dry-run", action="store_true", help="Roll back everything")
    p.add_argument(
        "--purge-org",
        action="store_true",
        help="Delete this org's QSeal rows before migrating (dangerous)",
    )
    return p.parse_args()


def resolve_org(args) -> uuid.UUID:
    if args.org_id:
        return uuid.UUID(args.org_id)
    if not args.identity_url:
        sys.exit(
            "Provide --org-id, or --identity-url/IDENTITY_DATABASE_URL so the "
            "script can resolve --org-slug"
        )
    with psycopg2.connect(args.identity_url, connect_timeout=30) as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id FROM organizations WHERE slug = %s AND deleted_at IS NULL",
                (args.org_slug,),
            )
            row = cur.fetchone()
            if not row:
                cur.execute("SELECT id, slug, name FROM organizations ORDER BY slug")
                print("Available organizations:")
                for r in cur.fetchall():
                    print(f"  - {r[1]}  ({r[2]})  {r[0]}")
                sys.exit(f"Organization slug '{args.org_slug}' not found")
            return row[0]


def purge(cur, org: str) -> None:
    order = [
        "qr_scan_events",
        "qr_activation_parameters",
        "qseal_parameters",
        "product_items",
        "qr_blocks",
        "product_skus",
        "qr_products",
        "products",
        "qr_product_settings",
        "destination_markets",
        "warranty_periods",
        "campaign_leads",
        "brands",
    ]
    for t in order:
        if table_exists(cur, t):
            cur.execute(f"DELETE FROM {t} WHERE organization_id = %s", (org,))
            print(f"  - purged {t}: {cur.rowcount}")


def verify(cur, org: str) -> None:
    print("\nVerification (target row counts for this organization):")
    checks = [
        ("brands", "brands"),
        ("products", "products"),
        ("qr_products", "qr_products"),
        ("product_skus", "product_skus"),
        ("qr_blocks", "qr_blocks"),
        ("product_items", "product_items"),
        ("qr_activation_parameters", "qr_activation_parameters"),
        ("qseal_parameters", "qseal_parameters"),
        ("qr_scan_events", "qr_scan_events"),
        ("campaign_leads", "campaign_leads"),
        ("warranty_periods", "warranty_periods"),
        ("destination_markets", "destination_markets"),
        ("qr_product_settings", "qr_product_settings"),
    ]
    for table, label in checks:
        if not table_exists(cur, table):
            print(f"  {label:28} -- table missing!")
            continue
        cur.execute(f"SELECT count(*) FROM {table} WHERE organization_id = %s", (org,))
        print(f"  {label:28} {cur.fetchone()[0]}")


def main() -> None:
    args = parse_args()
    if not args.target_url:
        sys.exit("Provide --target-url or set TARGET_DATABASE_URL")

    print("=" * 72)
    print("Phase 2 — elemage (elemaze) QSeal  ->  new ERP core_db")
    print("=" * 72)

    org = resolve_org(args)
    print(f"Target organization: {org}  (slug={args.org_slug})")
    print(f"Source: {args.source_mode}  schema={args.schema}")
    args.now = datetime.now(UTC).isoformat()

    mig = Migrator(args, org)

    # connectivity + schema sanity
    with psycopg2.connect(args.target_url, connect_timeout=30) as tconn:
        tconn.autocommit = False
        with tconn.cursor() as cur:
            for t in (
                "brands",
                "products",
                "qr_product_settings",
                "qr_products",
                "product_skus",
                "qr_blocks",
                "product_items",
                "qr_activation_parameters",
                "qr_scan_events",
                "campaign_leads",
            ):
                if not table_exists(cur, t):
                    sys.exit(
                        f"Target table '{t}' not found. Run the core-service "
                        f"alembic migrations on the Railway dev DB first."
                    )
            if args.purge_org:
                print("\n--purge-org: deleting existing QSeal rows for this org")
                purge(cur, str(org))

            mig.migrate(cur)

            if args.dry_run:
                tconn.rollback()
                print("\nDRY RUN — all changes rolled back.")
            else:
                tconn.commit()
                print("\nCommitted.")
            verify(cur, str(org))

    # ---- report -----------------------------------------------------------
    print("\n" + "=" * 72)
    print("SUMMARY")
    print("=" * 72)
    for k, v in mig.stats.items():
        print(f"  {k:32} {v}")

    print("\nNot migrated (no target equivalent / outside QSeal scope):")
    for t in (
        "integration_store (28), integration_storeposbill (108), "
        "integration_storepospayment (122), integration_storepospurchaseitem (362)",
        "integration_pallet / palletitem / palletdistributor",
        "integration_skuqr (7), integration_qr (3)",
        "integration_analyticsevent, integration_messagesummary / smsreport / whatsappreport",
        "integration_nft, integration_campaign (0), integration_leadaction (0)",
        "integration_otp (4), auth_* / django_* (Phase 1 handled users)",
    ):
        print(f"  - {t}")

    if mig.warnings:
        print("\nWARNINGS")
        for w in mig.warnings:
            print(f"  ! {w}")

    print("\nDone.")


if __name__ == "__main__":
    main()
