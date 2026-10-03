"""Bulk import / export for QR products (CSV + XLSX).

Design notes
------------
* **SKU is the upsert key.** A row whose (case/whitespace-insensitive) SKU
  matches an active product updates that product; otherwise a new one is
  created through :class:`QRProductService`, so the linked inventory Item is
  auto-created exactly like the single-product flow.
* Rows are applied **one transaction at a time**: a bad row is reported and
  skipped without aborting the rest of the file.
* Settings (shelf life / serial prefix) may be supplied either as an id or as
  the setting's human ``value`` — both are exported for round-tripping.
"""

from __future__ import annotations

import csv
import io
import logging
from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import func, or_
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session, joinedload

from app.models.qr_product import QRProduct
from app.models.qr_product_setting import QRProductSetting
from app.schemas.qr_product import (
    QRProductCreate,
    QRProductPackagingDetails,
    QRProductUpdate,
)
from app.services.qr_product_service import (
    QRProductService,
    find_active_product_by_sku,
    normalize_sku,
)

logger = logging.getLogger(__name__)

#: Columns a file may carry. Order defines the template/export layout.
PRODUCT_COLUMNS: list[str] = [
    "name",
    "sku",
    "generic_name",
    "gtin",
    "industry",
    "email",
    "phone_number",
    "activation_method",
    "sr_number_type",
    "qr_type",
    "warranty_period_months",
    "redirect_to_client",
    "is_active",
    "brand_id",
    "shelf_life_setting_id",
    "shelf_life_setting_value",
    "serial_prefix_setting_id",
    "serial_prefix_setting_value",
    "unit_name",
    "conversion_factor",
    "items_per_master_pack",
    "length_mm",
    "width_mm",
    "height_mm",
    "weight_grams",
]

#: Extra, read-only columns included in exports only.
EXPORT_ONLY_COLUMNS: list[str] = [
    "id",
    "linked_item_id",
    "linked_item_code",
    "serial_prefix",
    "created_at",
    "updated_at",
]

_PACKAGING_COLUMNS = (
    "unit_name",
    "conversion_factor",
    "items_per_master_pack",
    "length_mm",
    "width_mm",
    "height_mm",
    "weight_grams",
)

_BOOL_TRUE = {"1", "true", "yes", "y", "t"}

CSV_MEDIA_TYPE = "text/csv"
XLSX_MEDIA_TYPE = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"

MAX_IMPORT_ROWS = 5000


# ── primitive coercion ────────────────────────────────────────────────────────


def _as_text(value) -> str | None:
    if value is None:
        return None
    if isinstance(value, str):
        cleaned = value.strip()
        return cleaned or None
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, float) and value.is_integer():
        value = int(value)
    cleaned = str(value).strip()
    return cleaned or None


def _to_bool(value, *, field: str, default: bool = False) -> bool:
    text = _as_text(value)
    if text is None:
        return default
    lowered = text.lower()
    if lowered in _BOOL_TRUE:
        return True
    if lowered in {"0", "false", "no", "n", "f"}:
        return False
    raise ValueError(f"{field} must be a boolean (true/false)")


def _to_int(value, *, field: str) -> int | None:
    text = _as_text(value)
    if text is None:
        return None
    try:
        number = Decimal(text)
    except InvalidOperation as exc:
        raise ValueError(f"{field} must be a whole number") from exc
    # ``int(Decimal("1.9"))`` silently truncates to 1 — reject fractions
    # instead of accepting a value the error message says must be whole.
    if number != number.to_integral_value():
        raise ValueError(f"{field} must be a whole number")
    return int(number)


def _to_decimal(value, *, field: str) -> Decimal | None:
    text = _as_text(value)
    if text is None:
        return None
    try:
        return Decimal(text)
    except InvalidOperation as exc:
        raise ValueError(f"{field} must be a number") from exc


def _maybe_uuid(value) -> UUID | None:
    text = _as_text(value)
    if text is None:
        return None
    try:
        return UUID(text)
    except (ValueError, AttributeError):
        return None


def parse_row(raw: dict, row_number: int) -> dict:
    """Normalise one raw file row into a validated payload.

    Returns only the columns that were actually provided (plus the always-
    required ``name``) so an upsert never blanks out untouched fields.
    Raises ``ValueError`` with a human message for an invalid row.
    """
    payload: dict = {"row": row_number}

    name = _as_text(raw.get("name"))
    if not name:
        raise ValueError("name is required")
    payload["name"] = name

    sku = normalize_sku(_as_text(raw.get("sku")))
    if sku is not None:
        payload["sku"] = sku

    _parse_text_fields(raw, payload)
    _parse_activation(raw, payload)
    _parse_warranty(raw, payload)
    _parse_bools(raw, payload)
    _parse_brand(raw, payload)
    _parse_settings(raw, payload)

    packaging = _parse_packaging(raw)
    if packaging:
        payload["packaging"] = packaging

    return payload


_TEXT_FIELDS = ("generic_name", "gtin", "industry", "email", "phone_number")


def _parse_text_fields(raw: dict, payload: dict) -> None:
    for field in _TEXT_FIELDS:
        text = _as_text(raw.get(field))
        if text is not None:
            payload[field] = text


def _parse_activation(raw: dict, payload: dict) -> None:
    activation = _as_text(raw.get("activation_method"))
    if activation is not None:
        activation = activation.lower()
        if activation not in {"pre", "post"}:
            raise ValueError("activation_method must be 'pre' or 'post'")
        payload["activation_method"] = activation

    for field in ("sr_number_type", "qr_type"):
        text = _as_text(raw.get(field))
        if text is not None:
            payload[field] = text


def _parse_warranty(raw: dict, payload: dict) -> None:
    warranty = _to_int(
        raw.get("warranty_period_months"), field="warranty_period_months"
    )
    if warranty is not None:
        if warranty < 0:
            raise ValueError("warranty_period_months cannot be negative")
        payload["warranty_period_months"] = warranty


def _parse_bools(raw: dict, payload: dict) -> None:
    for field in ("redirect_to_client", "is_active"):
        if _as_text(raw.get(field)) is not None:
            payload[field] = _to_bool(raw.get(field), field=field)


def _parse_brand(raw: dict, payload: dict) -> None:
    if _as_text(raw.get("brand_id")) is None:
        return
    brand_id = _maybe_uuid(raw.get("brand_id"))
    if brand_id is None:
        raise ValueError("brand_id must be a valid UUID")
    payload["brand_id"] = brand_id


def _parse_settings(raw: dict, payload: dict) -> None:
    """Accept each setting as an id or as its human ``value``."""
    for prefix in ("shelf_life_setting", "serial_prefix_setting"):
        setting_id = _maybe_uuid(raw.get(f"{prefix}_id"))
        setting_value = _as_text(raw.get(f"{prefix}_value"))
        raw_id_text = _as_text(raw.get(f"{prefix}_id"))
        if setting_id is None and setting_value is None and raw_id_text:
            # A code was placed in the *_id column — treat it as a value.
            setting_value = raw_id_text
        if setting_id is not None:
            payload[f"{prefix}_id"] = setting_id
        if setting_value is not None:
            payload[f"{prefix}_value"] = setting_value


def _parse_packaging(raw: dict) -> dict:
    packaging: dict = {}

    unit_name = _as_text(raw.get("unit_name"))
    if unit_name is not None:
        packaging["unit_name"] = unit_name

    conversion = _to_decimal(raw.get("conversion_factor"), field="conversion_factor")
    if conversion is not None:
        if conversion <= 0:
            raise ValueError("conversion_factor must be greater than 0")
        packaging["conversion_factor"] = conversion

    per_master = _to_int(
        raw.get("items_per_master_pack"), field="items_per_master_pack"
    )
    if per_master is not None:
        if per_master <= 0:
            raise ValueError("items_per_master_pack must be greater than 0")
        packaging["items_per_master_pack"] = per_master

    for field in ("length_mm", "width_mm", "height_mm", "weight_grams"):
        dim = _to_decimal(raw.get(field), field=field)
        if dim is not None:
            if dim < 0:
                raise ValueError(f"{field} cannot be negative")
            packaging[field] = dim

    if not any(key in packaging for key in _PACKAGING_COLUMNS):
        return {}
    packaging.setdefault("unit_name", "Each")
    packaging.setdefault("conversion_factor", Decimal("1"))
    return packaging


class QRProductBulkService:
    """Import/export QR products as CSV or XLSX."""

    def __init__(self, db: Session):
        self.db = db
        self.product_service = QRProductService(db)

    # ── Export ────────────────────────────────────────────────────────────

    def export_products(
        self,
        organization_id: UUID,
        *,
        file_format: str = "csv",
        is_active: bool | None = None,
        search: str | None = None,
    ) -> tuple[bytes, str]:
        """Return ``(bytes, filename)`` for every matching product."""
        query = (
            self.db.query(QRProduct)
            .options(
                joinedload(QRProduct.shelf_life_setting),
                joinedload(QRProduct.serial_prefix_setting),
                joinedload(QRProduct.items),
            )
            .filter(
                QRProduct.organization_id == organization_id,
                QRProduct.deleted_at.is_(None),
            )
        )
        if is_active is not None:
            query = query.filter(QRProduct.is_active == is_active)
        if search:
            term = f"%{search.strip()}%"
            query = query.filter(
                or_(QRProduct.name.ilike(term), QRProduct.sku.ilike(term))
            )
        products = query.order_by(QRProduct.created_at.asc()).all()

        rows = [self._export_row(product) for product in products]
        columns = PRODUCT_COLUMNS + EXPORT_ONLY_COLUMNS
        return self._render(rows, columns, file_format, "qr_products_export")

    def template(self, file_format: str = "csv") -> tuple[bytes, str]:
        """Return ``(bytes, filename)`` for an import template (headers only)."""
        columns = PRODUCT_COLUMNS
        return self._render([], columns, file_format, "qr_products_import_template")

    @staticmethod
    def _export_row(product: QRProduct) -> dict:
        item = product.items[0] if product.items else None
        packaging = product.extra_data or {}
        packaging = packaging.get("packaging_details") or {}
        return {
            "id": str(product.id),
            "name": product.name,
            "sku": product.sku,
            "generic_name": product.generic_name,
            "gtin": product.gtin,
            "industry": product.industry,
            "email": product.email,
            "phone_number": product.phone_number,
            "activation_method": product.activation_method,
            "sr_number_type": product.sr_number_type,
            "qr_type": product.qr_type,
            "warranty_period_months": product.warranty_period_months,
            "redirect_to_client": product.redirect_to_client,
            "is_active": product.is_active,
            "brand_id": str(product.brand_id) if product.brand_id else None,
            "shelf_life_setting_id": str(product.shelf_life_setting_id)
            if product.shelf_life_setting_id
            else None,
            "shelf_life_setting_value": (
                product.shelf_life_setting.value if product.shelf_life_setting else None
            ),
            "serial_prefix_setting_id": str(product.serial_prefix_setting_id)
            if product.serial_prefix_setting_id
            else None,
            "serial_prefix_setting_value": (
                product.serial_prefix_setting.value
                if product.serial_prefix_setting
                else None
            ),
            "unit_name": packaging.get("unit_name"),
            "conversion_factor": packaging.get("conversion_factor"),
            "items_per_master_pack": packaging.get("items_per_master_pack"),
            "length_mm": packaging.get("length_mm"),
            "width_mm": packaging.get("width_mm"),
            "height_mm": packaging.get("height_mm"),
            "weight_grams": packaging.get("weight_grams"),
            "linked_item_id": str(item.id) if item else None,
            "linked_item_code": item.item_code if item else None,
            "serial_prefix": product.serial_prefix,
            "created_at": product.created_at.isoformat()
            if product.created_at
            else None,
            "updated_at": product.updated_at.isoformat()
            if product.updated_at
            else None,
        }

    @staticmethod
    def _render(
        rows: list[dict], columns: list[str], file_format: str, stem: str
    ) -> tuple[bytes, str]:
        file_format = (file_format or "csv").lower()
        stamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
        if file_format in {"xlsx", "xlsm"}:
            from openpyxl import Workbook

            wb = Workbook()
            ws = wb.active
            ws.title = "QR Products"
            ws.append(columns)
            for row in rows:
                ws.append([_cell(row.get(col)) for col in columns])
            buffer = io.BytesIO()
            wb.save(buffer)
            return buffer.getvalue(), f"{stem}_{stamp}.xlsx"

        buffer = io.StringIO()
        writer = csv.DictWriter(buffer, fieldnames=columns, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow({col: _cell(row.get(col)) for col in columns})
        return buffer.getvalue().encode("utf-8-sig"), f"{stem}_{stamp}.csv"

    # ── Import ────────────────────────────────────────────────────────────

    def import_products(
        self,
        organization_id: UUID,
        user_id: UUID,
        file_bytes: bytes,
        filename: str | None,
    ) -> dict:
        """Upsert products from a CSV/XLSX file and return a per-row summary."""
        rows = self._read_rows(file_bytes, filename)
        if len(rows) > MAX_IMPORT_ROWS:
            raise ValueError(
                f"File has {len(rows)} rows; the maximum is {MAX_IMPORT_ROWS}"
            )

        created = updated = 0
        errors: list[dict] = []
        for index, raw in enumerate(rows, start=2):  # row 1 is the header
            try:
                payload = parse_row(raw, index)
                was_created = self._upsert_row(organization_id, user_id, payload)
            except (HTTPException, ValueError, IntegrityError) as exc:
                # Expected, row-scoped failures: record and keep going.
                self.db.rollback()
                message = getattr(exc, "detail", None) or str(exc)
                errors.append(
                    {
                        "row": index,
                        "sku": _as_text(raw.get("sku")),
                        "message": str(message),
                    }
                )
                continue
            except SQLAlchemyError:
                # A database outage / programming error is not a row problem —
                # surface it instead of reporting a misleading partial success.
                self.db.rollback()
                raise
            created += was_created
            updated += not was_created

        return {
            "total_rows": len(rows),
            "created": created,
            "updated": updated,
            "failed": len(errors),
            "errors": errors,
        }

    def _upsert_row(self, organization_id: UUID, user_id: UUID, payload: dict) -> bool:
        """Create or update one product. Returns True when a row was created."""
        packaging = payload.get("packaging")
        if payload.get("brand_id") is not None:
            self._assert_brand(organization_id, payload["brand_id"])

        existing = find_active_product_by_sku(
            self.db, organization_id, payload.get("sku")
        )
        packaging_details = (
            QRProductPackagingDetails(**packaging) if packaging else None
        )

        # Settings are only resolved when the row supplies them, so a partial
        # update (e.g. name + sku) preserves the existing shelf-life /
        # serial-prefix instead of failing on a missing setting.
        if existing is not None:
            update = QRProductUpdate(
                **self._update_kwargs(payload),
                **self._resolved_settings(organization_id, payload, required=False),
                packaging_details=packaging_details,
            )
            self.product_service.update_product(
                existing.id, update, organization_id, user_id
            )
            return False

        create = QRProductCreate(
            **self._create_kwargs(payload),
            **self._resolved_settings(organization_id, payload, required=True),
            packaging_details=packaging_details,
        )
        self.product_service.create_product(create, organization_id, user_id)
        return True

    def _resolved_settings(
        self, organization_id: UUID, payload: dict, *, required: bool
    ) -> dict:
        """Resolve whichever settings the row provided (by id or by value)."""
        settings: dict = {}
        for prefix, setting_type in (
            ("shelf_life_setting", "shelf_life"),
            ("serial_prefix_setting", "serial_prefix"),
        ):
            provided = f"{prefix}_id" in payload or f"{prefix}_value" in payload
            if not provided:
                if required:
                    raise ValueError(f"{prefix}_id or {prefix}_value is required")
                continue
            settings[f"{prefix}_id"] = self._resolve_setting(
                organization_id, payload, prefix, setting_type
            )
        return settings

    @staticmethod
    def _create_kwargs(payload: dict) -> dict:
        allowed = (
            "name",
            "sku",
            "generic_name",
            "gtin",
            "brand_id",
            "industry",
            "email",
            "phone_number",
            "activation_method",
            "sr_number_type",
            "qr_type",
            "warranty_period_months",
            "redirect_to_client",
        )
        return {key: payload[key] for key in allowed if key in payload}

    @staticmethod
    def _update_kwargs(payload: dict) -> dict:
        # ``sku`` is the upsert key and ``brand_id`` is immutable after create.
        allowed = (
            "name",
            "generic_name",
            "gtin",
            "industry",
            "email",
            "phone_number",
            "activation_method",
            "sr_number_type",
            "qr_type",
            "warranty_period_months",
            "redirect_to_client",
            "is_active",
        )
        return {key: payload[key] for key in allowed if key in payload}

    def _resolve_setting(
        self,
        organization_id: UUID,
        payload: dict,
        prefix: str,
        setting_type: str,
    ) -> UUID:
        """Resolve a setting to its id from either the id or the human value."""
        setting_id = payload.get(f"{prefix}_id")
        setting_value = payload.get(f"{prefix}_value")
        if setting_id is None and setting_value is None:
            raise ValueError(f"{prefix}_id or {prefix}_value is required")

        setting = None
        if setting_id is not None:
            setting = (
                self.db.query(QRProductSetting)
                .filter(
                    QRProductSetting.id == setting_id,
                    QRProductSetting.organization_id == organization_id,
                    QRProductSetting.deleted_at.is_(None),
                )
                .first()
            )
        elif setting_value is not None:
            setting = (
                self.db.query(QRProductSetting)
                .filter(
                    QRProductSetting.organization_id == organization_id,
                    QRProductSetting.setting_type == setting_type,
                    func.lower(QRProductSetting.value) == setting_value.lower(),
                    QRProductSetting.deleted_at.is_(None),
                )
                .first()
            )

        if setting is None:
            label = setting_value or setting_id
            raise ValueError(f"{setting_type} setting '{label}' was not found")
        if setting.setting_type != setting_type:
            raise ValueError(f"Setting '{label}' is not a {setting_type} setting")
        if not setting.is_active:
            raise ValueError(f"{setting_type} setting '{label}' is inactive")
        return setting.id

    def _assert_brand(self, organization_id: UUID, brand_id: UUID) -> None:
        from app.repositories.brand_repository import BrandRepository

        if BrandRepository(self.db).get_by_id(brand_id, organization_id) is None:
            raise ValueError(f"Brand '{brand_id}' was not found")

    # ── File parsing ──────────────────────────────────────────────────────

    def _read_rows(self, file_bytes: bytes, filename: str | None) -> list[dict]:
        if not file_bytes:
            raise ValueError("Uploaded file is empty")
        ext = (
            filename.rsplit(".", 1)[-1].lower()
            if filename and "." in filename
            else "csv"
        )
        if ext in {"xlsx", "xlsm", "xltx"}:
            rows = self._read_xlsx(file_bytes)
        elif ext in {"csv", "txt"}:
            rows = self._read_csv(file_bytes)
        else:
            raise ValueError(f"Unsupported file type '.{ext}'. Supported: csv, xlsx")
        return [row for row in rows if self._has_values(row)]

    @staticmethod
    def _has_values(row: dict) -> bool:
        return any(_as_text(value) is not None for value in row.values())

    @staticmethod
    def _read_csv(file_bytes: bytes) -> list[dict]:
        text = file_bytes.decode("utf-8-sig", errors="replace")
        reader = csv.DictReader(io.StringIO(text))
        rows = []
        for raw in reader:
            rows.append(
                {
                    (key.strip() if isinstance(key, str) else key): value
                    for key, value in raw.items()
                    if key is not None
                }
            )
        return rows

    @staticmethod
    def _read_xlsx(file_bytes: bytes) -> list[dict]:
        from openpyxl import load_workbook

        workbook = load_workbook(io.BytesIO(file_bytes), read_only=True, data_only=True)
        sheet = workbook.active
        iterator = sheet.iter_rows(values_only=True)
        header = next(iterator, None)
        if not header:
            return []
        columns = [(_as_text(cell) or "") for cell in header]
        rows = []
        for values in iterator:
            row = {
                columns[idx]: values[idx] for idx in range(len(columns)) if columns[idx]
            }
            rows.append(row)
        return rows


#: Leading characters spreadsheet software may interpret as a formula.
_FORMULA_TRIGGERS = ("=", "+", "-", "@", "\t", "\r")


def _cell(value):
    """Render a value for CSV/XLSX output, neutralising formula injection.

    A user-controlled string such as ``=HYPERLINK(...)`` or ``+cmd|...`` would
    be executed as a formula when the file is opened in Excel/Sheets; prefixing
    it with an apostrophe keeps it inert text.
    """
    if value is None:
        return ""
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, str) and value[:1] in _FORMULA_TRIGGERS:
        return "'" + value
    return value
