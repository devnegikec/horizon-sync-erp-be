"""QSeal activation service.

All writes live here so the React administration UI and mobile client share
the same validation, tenant isolation, and transaction semantics.
"""

import hashlib
import json
from datetime import UTC, date, datetime
from decimal import Decimal
from urllib.parse import urlparse
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import func, or_, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.config import settings
from app.models.audit_log import AuditLog
from app.models.destination_market import DestinationMarket
from app.models.product_item import ProductItem
from app.models.qr_activation import QRActivationParameters
from app.models.qr_product import QRProduct
from app.models.qr_product_setting import QRProductSetting
from app.models.qseal_activation_request import QSealActivationRequest
from app.schemas.qseal_activation import ActivationSettingsInput
from app.services.activation_expiry import (
    calculate_shelf_life_expiry,
    resolve_shelf_life_months,
)


def activation_error(http_status: int, code: str, message: str, **extra):
    raise HTTPException(http_status, detail={"code": code, "message": message, **extra})


class QSealActivationService:
    def __init__(self, db: Session):
        self.db = db

    def product(self, product_id: UUID, org_id: UUID, *, lock=False):
        query = self.db.query(QRProduct).filter(
            QRProduct.id == product_id,
            QRProduct.organization_id == org_id,
            QRProduct.deleted_at.is_(None),
        )
        if lock:
            query = query.with_for_update()
        product = query.first()
        if not product:
            activation_error(404, "PRODUCT_NOT_FOUND", "Product was not found.")
        return product

    def current_settings(self, product_id: UUID, org_id: UUID, *, lock=False):
        query = self.db.query(QRActivationParameters).filter(
            QRActivationParameters.product_id == product_id,
            QRActivationParameters.organization_id == org_id,
            QRActivationParameters.qr_settings.is_(True),
            QRActivationParameters.history.is_(False),
            QRActivationParameters.deleted_at.is_(None),
        ).order_by(QRActivationParameters.created_at.desc(), QRActivationParameters.id.desc())
        if lock:
            query = query.with_for_update()
        return query.first()

    def summary(self, product_id: UUID, org_id: UUID):
        product = self.product(product_id, org_id)
        total = self.db.query(func.count(ProductItem.id)).filter(
            ProductItem.product_id == product_id,
            ProductItem.organization_id == org_id,
            ProductItem.deleted_at.is_(None),
        ).scalar() or 0
        available = self.db.query(func.count(ProductItem.id)).filter(
            ProductItem.product_id == product_id,
            ProductItem.organization_id == org_id,
            ProductItem.deleted_at.is_(None),
            or_(ProductItem.qr_deactive.is_(True), ProductItem.qr_deactive_unit.is_(True)),
        ).scalar() or 0
        activated = total - available
        return {
            "product_id": product_id,
            "activation_method": product.activation_method,
            "total_blocks": total,
            "activated_blocks": activated,
            "available_blocks": available,
            "activation_percentage": round((activated / total) * 100, 2) if total else 0.0,
            "current_settings": self.current_settings(product_id, org_id),
        }

    def destination_currency(self, name: str, org_id: UUID) -> str | None:
        """Resolve currency from the tenant's active destination configuration."""
        market = self.db.query(DestinationMarket).filter(
            DestinationMarket.organization_id == org_id,
            DestinationMarket.name == name,
            DestinationMarket.is_active.is_(True),
            DestinationMarket.deleted_at.is_(None),
        ).first()
        if market:
            return market.currency_code

        setting = self.db.query(QRProductSetting).filter(
            QRProductSetting.organization_id == org_id,
            QRProductSetting.setting_type == "destination",
            QRProductSetting.is_active.is_(True),
            QRProductSetting.deleted_at.is_(None),
            or_(QRProductSetting.value == name, QRProductSetting.label.ilike(name)),
        ).first()
        if setting:
            return (
                (setting.extra_data or {}).get("currency_code")
                or (setting.extra_data or {}).get("currency")
            )
        activation_error(400, "DESTINATION_MARKET_INACTIVE", "Destination market does not exist or is inactive.")

    def calculate_expiry(self, product_id: UUID, manufacturing_date: date, org_id: UUID) -> date:
        product = self.product(product_id, org_id)
        shelf_life_months = resolve_shelf_life_months(
            self.db, product.shelf_life_setting_id, org_id
        )
        if shelf_life_months is None:
            activation_error(
                400,
                "SHELF_LIFE_NOT_CONFIGURED",
                "Shelf life is not configured or is invalid for this product.",
            )
        return calculate_shelf_life_expiry(manufacturing_date, shelf_life_months)

    def mobile_scan(self, url: str, serial_numbers: str | None, org_id: UUID):
        """Implement the Django mobile scan response using QSeal data."""
        serial = self.resolve_serial(url, org_id)
        item = self.db.query(ProductItem).filter(
            ProductItem.serial_number == serial,
            ProductItem.organization_id == org_id,
            ProductItem.deleted_at.is_(None),
        ).first()
        if not item:
            activation_error(400, "SERIAL_NOT_FOUND", "Serial number was not found.")

        config = self.current_settings(item.product_id, org_id)
        if not config:
            activation_error(
                400,
                "QR_SETTINGS_NOT_CONFIGURED",
                "Product activation settings are not configured.",
            )
        if not item.qr_deactive and not item.qr_deactive_unit:
            return {
                "message": "Activated",
                "sr_number": item.serial_number,
                "product_id": item.product_id,
            }

        submitted = {
            value.strip()
            for value in (serial_numbers or "").split(",")
            if value.strip()
        }
        activated_count = self.db.query(func.count(QRActivationParameters.id)).filter(
            QRActivationParameters.product_id == item.product_id,
            QRActivationParameters.organization_id == org_id,
            QRActivationParameters.dispatch_batch == config.dispatch_batch,
            QRActivationParameters.qr_settings.is_(False),
            QRActivationParameters.deleted_at.is_(None),
            QRActivationParameters.created_at >= config.created_at,
        ).scalar() or 0
        if activated_count + len(submitted) + 1 > (config.batch_size or 0):
            activation_error(
                400,
                "BATCH_CAPACITY_EXCEEDED",
                "D-Batch limit exceeded. Increase its size or create a new D-batch.",
            )
        return {
            "message": "Not Activate",
            "sr_number": item.serial_number,
            "product_id": item.product_id,
        }

    def save_settings(self, product_id: UUID, data: ActivationSettingsInput, org_id: UUID, user_id: UUID | None):
        product = self.product(product_id, org_id, lock=True)
        currency = self.destination_currency(data.destination_market, org_id)
        available = self.db.query(func.count(ProductItem.id)).filter(
            ProductItem.product_id == product_id,
            ProductItem.organization_id == org_id,
            ProductItem.deleted_at.is_(None),
            or_(ProductItem.qr_deactive.is_(True), ProductItem.qr_deactive_unit.is_(True)),
        ).scalar() or 0
        existing = self.db.query(QRActivationParameters).filter(
            QRActivationParameters.product_id == product_id,
            QRActivationParameters.organization_id == org_id,
            QRActivationParameters.dispatch_batch == data.dispatch_batch,
            QRActivationParameters.qr_settings.is_(True),
            QRActivationParameters.history.is_(False),
            QRActivationParameters.deleted_at.is_(None),
        ).with_for_update().first()
        if existing and not data.append_to_existing:
            activation_error(409, "BATCH_EXISTS", "This dispatch batch already has active settings. Confirm to update.", requires_confirmation=True)
        if data.batch_size > available and not existing:
            activation_error(400, "INVALID_BATCH_SIZE", "Batch size cannot exceed available QR blocks.", available_blocks=available)
        shelf_life_months = resolve_shelf_life_months(
            self.db, product.shelf_life_setting_id, org_id
        )
        if shelf_life_months is None:
            activation_error(
                400,
                "SHELF_LIFE_NOT_CONFIGURED",
                "Shelf life is not configured or is invalid for this product.",
            )
        expiry = calculate_shelf_life_expiry(data.manufacturing_date, shelf_life_months)
        now = datetime.now(UTC)
        if existing:
            existing.history = True
            self.db.flush()
        row = QRActivationParameters(
            product_id=product_id, organization_id=org_id, dispatch_batch=data.dispatch_batch,
            batch_size=data.batch_size, manufacturing_date=data.manufacturing_date,
            manufacturing_unit=data.manufacturing_unit.strip(), expiry_date=expiry,
            destination_market=data.destination_market, currency=currency,
            mrp=data.mrp, qr_settings=True, history=False, created_by=user_id, created_at=now,
        )
        self.db.add(row)
        try:
            self.db.flush()
            self.db.add(AuditLog(
                user_id=user_id,
                organization_id=org_id,
                action="CREATE",
                table_name="qr_activation_parameters",
                record_id=row.id,
                new_values={
                    "product_id": str(product_id),
                    "dispatch_batch": row.dispatch_batch,
                    "batch_size": row.batch_size,
                    "manufacturing_date": row.manufacturing_date.isoformat(),
                    "expiry_date": row.expiry_date.isoformat(),
                    "destination_market": row.destination_market,
                    "currency": row.currency,
                },
                changed_fields=["activation_settings"],
            ))
            self.db.commit()
            self.db.refresh(row)
        except Exception:
            self.db.rollback()
            raise
        return row

    def history(self, product_id: UUID, org_id: UUID, page: int, page_size: int):
        self.product(product_id, org_id)
        query = self.db.query(QRActivationParameters).filter(
            QRActivationParameters.product_id == product_id,
            QRActivationParameters.organization_id == org_id,
            QRActivationParameters.qr_settings.is_(True),
            QRActivationParameters.deleted_at.is_(None),
        ).order_by(QRActivationParameters.created_at.desc(), QRActivationParameters.id.desc())
        total = query.count()
        return query.offset((page - 1) * page_size).limit(page_size).all(), total

    def resolve_serial(self, value: str, org_id: UUID | None = None):
        parsed = urlparse(value)
        if parsed.scheme and parsed.netloc:
            trusted_hosts = {
                host.lower()
                for host in (settings.qr_domain, settings.qr_shortener_cdn_prefix)
                if host
            }
            if parsed.hostname and parsed.hostname.lower() not in trusted_hosts:
                activation_error(400, "INVALID_REQUEST", "QR URL domain is not trusted.")

            # QR generation stores the exact short URL on ProductItem. Resolve
            # it locally first so scanning never waits on an external redirect.
            if org_id is not None:
                candidates = {value, value.rstrip("/")}
                item = self.db.query(ProductItem).filter(
                    ProductItem.organization_id == org_id,
                    ProductItem.token_id.in_(candidates),
                    ProductItem.deleted_at.is_(None),
                ).first()
                if item:
                    return item.serial_number

            parts = [p for p in parsed.path.split("/") if p]
            if not parts:
                activation_error(400, "INVALID_REQUEST", "QR URL does not contain a serial number.")
            if len(parts) == 1:
                activation_error(
                    400,
                    "INVALID_REQUEST",
                    "Short QR URL could not be resolved locally; send the serial number.",
                )
            return parts[-1]
        serial = value.strip()
        if not serial:
            activation_error(400, "INVALID_REQUEST", "Serial number cannot be blank.")
        return serial

    def validate_scan(self, serial_or_url: str, product_id: UUID | None, org_id: UUID):
        serial = self.resolve_serial(serial_or_url, org_id)
        item = self.db.query(ProductItem).filter(
            ProductItem.serial_number == serial,
            ProductItem.organization_id == org_id,
            ProductItem.deleted_at.is_(None),
        ).first()
        if not item or (product_id and item.product_id != product_id):
            activation_error(404, "SERIAL_NOT_FOUND", "Serial number was not found.")
        return {"valid": True, "serial_number": serial, "product_id": item.product_id,
                "status": "ACTIVATED" if not item.qr_deactive and not item.qr_deactive_unit else "NOT_ACTIVATED",
                "message": "QR code is already activated" if not item.qr_deactive and not item.qr_deactive_unit else "QR code is ready for activation"}

    @staticmethod
    def _activation_request_hash(
        product_id: UUID, serials: list[str], settings_id: UUID | None
    ) -> str:
        """Create a stable fingerprint for an idempotent activation request."""
        payload = {
            "product_id": str(product_id),
            "serial_numbers": sorted(serials),
            "settings_id": str(settings_id) if settings_id else None,
        }
        encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
        return hashlib.sha256(encoded).hexdigest()

    @staticmethod
    def _restore_activation_response(payload: dict) -> dict:
        """Convert the JSON response back to the service's normal return shape."""
        response = dict(payload)
        if isinstance(response.get("product_id"), str):
            response["product_id"] = UUID(response["product_id"])
        return response

    def _existing_idempotent_response(
        self, request: QSealActivationRequest, request_hash: str
    ) -> dict | None:
        if request.request_hash != request_hash:
            activation_error(
                409,
                "IDEMPOTENCY_KEY_REUSED",
                "The idempotency key was already used with a different activation request.",
            )
        if request.status == "completed" and request.response_payload:
            return self._restore_activation_response(request.response_payload)
        activation_error(
            409,
            "IDEMPOTENCY_IN_PROGRESS",
            "An activation request with this idempotency key is already in progress.",
        )

    def _claim_idempotency_key(
        self,
        product_id: UUID,
        serials: list[str],
        settings_id: UUID | None,
        org_id: UUID,
        idempotency_key: str | None,
    ) -> tuple[QSealActivationRequest | None, dict | None]:
        """Claim a key, safely handling two workers receiving the same retry."""
        if not idempotency_key:
            return None, None

        request_hash = self._activation_request_hash(product_id, serials, settings_id)
        query = self.db.query(QSealActivationRequest).filter(
            QSealActivationRequest.organization_id == org_id,
            QSealActivationRequest.idempotency_key == idempotency_key,
        )
        existing = query.with_for_update().first()
        if existing:
            return existing, self._existing_idempotent_response(existing, request_hash)

        request = QSealActivationRequest(
            organization_id=org_id,
            product_id=product_id,
            idempotency_key=idempotency_key,
            request_hash=request_hash,
            status="processing",
        )
        try:
            # A savepoint prevents a unique-key race from poisoning the outer
            # activation transaction, allowing us to read the winning record.
            with self.db.begin_nested():
                self.db.add(request)
                self.db.flush()
        except IntegrityError:
            existing = query.with_for_update().first()
            if not existing:
                raise
            return existing, self._existing_idempotent_response(existing, request_hash)
        return request, None

    def activate(
        self,
        product_id: UUID,
        serials: list[str],
        settings_id: UUID | None,
        org_id: UUID,
        user_id: UUID | None = None,
        idempotency_key: str | None = None,
    ):
        serials = [s.strip() for s in serials]
        idempotency_key = idempotency_key.strip() if idempotency_key else None
        if any(not serial for serial in serials):
            activation_error(400, "INVALID_REQUEST", "Serial numbers cannot be blank.")
        if len(set(serials)) != len(serials):
            activation_error(400, "INVALID_REQUEST", "Serial numbers must be unique.")
        product = self.product(product_id, org_id, lock=True)
        config = self.current_settings(product_id, org_id, lock=True)
        if not config:
            activation_error(404, "QR_SETTINGS_NOT_CONFIGURED", "Product activation settings are not configured.")
        if settings_id and config.id != settings_id:
            activation_error(409, "INVALID_REQUEST", "The supplied settings are not current.")
        idempotency_request = None
        if idempotency_key:
            request_hash = self._activation_request_hash(product_id, serials, settings_id)
            existing_request = self.db.query(QSealActivationRequest).filter(
                QSealActivationRequest.organization_id == org_id,
                QSealActivationRequest.idempotency_key == idempotency_key,
            ).with_for_update().first()
            if existing_request:
                replay = self._existing_idempotent_response(existing_request, request_hash)
                if replay is not None:
                    return replay
        items = self.db.query(ProductItem).filter(
            ProductItem.product_id == product_id, ProductItem.organization_id == org_id,
            ProductItem.serial_number.in_(serials), ProductItem.deleted_at.is_(None),
        ).with_for_update().all()
        found = {i.serial_number: i for i in items}
        errors = [{"serial_number": s, "code": "SERIAL_NOT_FOUND", "message": "Serial number was not found."} for s in serials if s not in found]
        if errors:
            activation_error(400, "ACTIVATION_VALIDATION_FAILED", "Activation failed; no records were changed.", errors=errors)
        existing = {r.serial_number: r for r in self.db.query(QRActivationParameters).filter(
            QRActivationParameters.product_id == product_id, QRActivationParameters.organization_id == org_id,
            QRActivationParameters.serial_number.in_(serials), QRActivationParameters.qr_settings.is_(False),
            QRActivationParameters.deleted_at.is_(None),
        ).with_for_update().all()}
        used_in_batch = self.db.query(func.count(QRActivationParameters.id)).filter(
            QRActivationParameters.product_id == product_id,
            QRActivationParameters.organization_id == org_id,
            QRActivationParameters.dispatch_batch == config.dispatch_batch,
            QRActivationParameters.qr_settings.is_(False),
            QRActivationParameters.deleted_at.is_(None),
        ).scalar() or 0
        # Existing rows in a retried request are not counted twice.
        new_batch_rows = sum(1 for serial in serials if serial not in existing)
        if used_in_batch + new_batch_rows > (config.batch_size or 0):
            activation_error(
                409, "BATCH_CAPACITY_EXCEEDED",
                "Activation exceeds the configured dispatch-batch capacity.",
                batch_size=config.batch_size, used_blocks=used_in_batch,
            )
        idempotency_request, replay = self._claim_idempotency_key(
            product_id, serials, settings_id, org_id, idempotency_key
        )
        if replay is not None:
            return replay
        newly = 0
        for serial in serials:
            item = found[serial]
            if item.qr_deactive or item.qr_deactive_unit:
                newly += 1
                item.qr_deactive = False; item.qr_deactive_unit = False; item.qr_active = True
            if serial not in existing:
                self.db.add(QRActivationParameters(
                    product_id=product_id, organization_id=org_id, serial_number=serial,
                    manufacturing_date=config.manufacturing_date, expiry_date=config.expiry_date,
                    manufacturing_unit=config.manufacturing_unit, dispatch_batch=config.dispatch_batch,
                    destination_market=config.destination_market, currency=config.currency,
                    mrp=config.mrp, qr_settings=False, history=False, created_by=user_id,
                    extra_data=(
                        {"activation_idempotency_key": idempotency_key}
                        if idempotency_key else None
                    ),
                ))
        if newly:
            product.num_activated_qr = (product.num_activated_qr or 0) + newly
        response = {
            "message": "QR codes activated successfully", "product_id": product_id,
            "activated_count": newly, "already_activated_count": len(serials) - newly,
            "product_activated_total": product.num_activated_qr or 0, "serial_numbers": serials,
        }
        try:
            self.db.flush()
            if idempotency_request:
                idempotency_request.status = "completed"
                idempotency_request.response_payload = {
                    **response,
                    "product_id": str(product_id),
                }
                self.db.flush()
            self.db.add(AuditLog(
                user_id=user_id,
                organization_id=org_id,
                action="UPDATE",
                table_name="qr_products",
                record_id=product_id,
                new_values={
                    "dispatch_batch": config.dispatch_batch,
                    "activated_count": newly,
                    "already_activated_count": len(serials) - newly,
                    "serial_numbers": serials,
                    "idempotency_key": idempotency_key,
                },
                changed_fields=["activation_status", "num_activated_qr"],
            ))
            self.db.commit()
        except Exception:
            self.db.rollback()
            raise
        return response
