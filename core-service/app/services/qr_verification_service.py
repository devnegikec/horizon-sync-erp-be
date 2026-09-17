"""Public QR verification rules without analytics or scan-event capture."""

import logging
import secrets

from sqlalchemy.orm import Session

from app.config import settings
from app.repositories.qr_verification_repository import QRVerificationRepository
from app.schemas.qr_product import QRType, normalize_qr_type
from app.schemas.qr_verification import (
    PublicQRVerifyRequest,
    QRVerificationChannel,
    QRVerificationStatus,
)
from app.services.key_service import KeyService

logger = logging.getLogger(__name__)


class QRVerificationService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = QRVerificationRepository(db)
        self.key_service = KeyService(settings.brand_key_encryption_secret)

    def verify(self, data: PublicQRVerifyRequest) -> dict:
        identity = self.repo.resolve_active_item_identity(data.serial_number)
        if identity is None:
            return self._invalid_response()

        item_id, organization_id = identity
        item = self.repo.get_tenant_item_for_update(
            item_id,
            data.serial_number,
            organization_id,
        )
        if item is None:
            return self._invalid_response()

        try:
            product = item.product
            brand = product.brand if product else None
            if not self._ownership_is_valid(item, product, brand, organization_id):
                logger.error(
                    "QR ownership validation failed: item_id=%s organization_id=%s",
                    item.id,
                    organization_id,
                )
                self.db.rollback()
                return self._invalid_response()

            if not self._gtin_is_valid(item, product, data.gtin):
                self.db.rollback()
                return self._invalid_response()

            if not self._signature_is_valid(brand, data):
                self.db.rollback()
                return self._invalid_response()

            qr_type = normalize_qr_type(
                getattr(item.block, "qr_type", None) or product.qr_type
            ) or QRType.DYNAMIC

            challenge = self._challenge_response(
                item,
                product,
                brand,
                data,
                qr_type,
            )
            if challenge is not None:
                self.db.rollback()
                return challenge

            is_one_time = qr_type == QRType.ONE_TIME
            if not item.qr_active:
                status = (
                    QRVerificationStatus.ALREADY_USED
                    if is_one_time and bool(item.is_verify)
                    else QRVerificationStatus.NOT_ACTIVATED
                )
                result = self._verified_response(
                    item,
                    product,
                    brand,
                    data.gtin,
                    qr_type,
                    status,
                    authentic=status == QRVerificationStatus.NOT_ACTIVATED,
                    message=(
                        "This One-Time QR code has already been used."
                        if status == QRVerificationStatus.ALREADY_USED
                        else "This genuine QR code has not been activated yet."
                    ),
                    qr_channel=data.qr_channel,
                )
                self.db.rollback()
                return result

            if is_one_time:
                item.qr_active = False
                item.qr_deactive = True
                item.qr_deactive_unit = True
                item.is_auth = True
                item.is_verify = True
                result = self._verified_response(
                    item,
                    product,
                    brand,
                    data.gtin,
                    qr_type,
                    QRVerificationStatus.AUTHENTIC,
                    authentic=True,
                    message="This product is genuine and verified.",
                    qr_channel=data.qr_channel,
                )
                self.db.commit()
            else:
                result = self._verified_response(
                    item,
                    product,
                    brand,
                    data.gtin,
                    qr_type,
                    QRVerificationStatus.AUTHENTIC,
                    authentic=True,
                    message="This product is genuine and verified.",
                    qr_channel=data.qr_channel,
                )
                self.db.rollback()

            logger.info(
                "Public QR verified: item_id=%s organization_id=%s qr_type=%s",
                item.id,
                organization_id,
                qr_type.value,
            )
            return result
        except Exception:
            self.db.rollback()
            raise

    @staticmethod
    def _ownership_is_valid(item, product, brand, organization_id) -> bool:
        if product is None or brand is None:
            return False
        if product.organization_id != organization_id:
            return False
        if brand.organization_id != organization_id or brand.deleted_at is not None:
            return False
        if item.sku and item.sku.organization_id != organization_id:
            return False
        if item.block and item.block.organization_id != organization_id:
            return False
        return product.deleted_at is None and product.is_active

    @staticmethod
    def _gtin_is_valid(item, product, gtin: str) -> bool:
        valid_gtins = {
            value
            for value in (
                getattr(item.sku, "gtin", None),
                getattr(product, "gtin", None),
            )
            if value
        }
        return gtin in valid_gtins

    def _signature_is_valid(self, brand, data: PublicQRVerifyRequest) -> bool:
        if not brand.public_key:
            return False
        message = f"{data.serial_number}~{data.timestamp}"
        return self.key_service.verify_signature(
            brand.public_key,
            message,
            data.signature,
        )

    def _challenge_response(
        self,
        item,
        product,
        brand,
        data: PublicQRVerifyRequest,
        qr_type: QRType,
    ) -> dict | None:
        if qr_type == QRType.DUAL and data.qr_channel == QRVerificationChannel.OVERT:
            return self._verified_response(
                item,
                product,
                brand,
                data.gtin,
                qr_type,
                QRVerificationStatus.VERIFICATION_REQUIRED,
                authentic=False,
                message="Scan the protected QR code to complete product verification.",
                requires_action=True,
                challenge_type="scan_covert",
                qr_channel=data.qr_channel,
            )

        if qr_type != QRType.SECURE_CODE:
            return None
        if not data.secure_code:
            return self._verified_response(
                item,
                product,
                brand,
                data.gtin,
                qr_type,
                QRVerificationStatus.VERIFICATION_REQUIRED,
                authentic=False,
                message="Enter the protected code to verify this product.",
                requires_action=True,
                challenge_type="secure_code",
            )

        expected_code = (item.secrete_code or "").strip().upper()
        submitted_code = data.secure_code.strip().upper()
        if expected_code and secrets.compare_digest(expected_code, submitted_code):
            return None
        return self._verified_response(
            item,
            product,
            brand,
            data.gtin,
            qr_type,
            QRVerificationStatus.INVALID,
            authentic=False,
            message="The protected code is invalid. Check the code and try again.",
            requires_action=True,
            challenge_type="secure_code",
        )

    @staticmethod
    def _invalid_response(message: str = "QR verification failed.") -> dict:
        return {
            "verification_status": QRVerificationStatus.INVALID,
            "authentic": False,
            "message": message,
        }

    @staticmethod
    def _verified_response(
        item,
        product,
        brand,
        gtin: str,
        qr_type: QRType,
        verification_status: QRVerificationStatus,
        *,
        authentic: bool,
        message: str,
        requires_action: bool = False,
        challenge_type: str | None = None,
        qr_channel: QRVerificationChannel | None = None,
    ) -> dict:
        sku = item.sku
        variant_attributes = sku.attribute_display if sku else {}
        return {
            "verification_status": verification_status,
            "authentic": authentic,
            "message": message,
            "requires_action": requires_action,
            "challenge_type": challenge_type,
            "product_name": product.name,
            "generic_name": getattr(product, "generic_name", None),
            "brand_name": brand.name,
            "sku_name": getattr(sku, "name", None),
            "sku_code": getattr(sku, "sku_code", None),
            "variant_attributes": variant_attributes,
            "gtin": gtin,
            "serial_number": item.serial_number,
            "qr_type": qr_type.value,
            "qr_channel": qr_channel,
            "activation_method": product.activation_method,
            "industry": getattr(product, "industry", None),
            "warranty_period_months": (
                getattr(sku, "warranty_period_months", None)
                or getattr(product, "warranty_period_months", None)
            ),
            "logo_url": product.image_url,
            "product_image_url": getattr(sku, "image_url", None)
            or product.image_url,
            "banner_image_url": product.banner_image_url,
            "contact_email": getattr(product, "email", None),
            "contact_phone": getattr(product, "phone_number", None),
            "website_url": getattr(product, "landing_page", None),
        }
