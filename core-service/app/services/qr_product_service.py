"""Service layer for QR Products module"""

import logging
import secrets
import string
import uuid
from datetime import UTC, datetime, timedelta
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.config import settings
from app.models.product_item import ProductItem
from app.models.qr_block import QRBlock
from app.models.qr_product import QRProduct
from app.repositories.qr_product_repository import (
    ProductItemRepository,
    QRBlockRepository,
    QRProductRepository,
)
from app.schemas.qr_product import (
    AuthenticateRequest,
    QRActivationParamsCreate,
    QRBlockCreate,
    QRProductCreate,
    QRProductUpdate,
    QRValidateRequest,
)
from app.services.credit_service import CreditService
from app.services.key_service import KeyService
from app.utils.serial_generators import (
    build_qr_url,
    generate_r4dan,
    generate_r6dan,
    sequential_s8dn,
    sequential_s10dn,
    sign_qr_item,
)

logger = logging.getLogger(__name__)


def _build_excel(rows: list[dict], qr_type: str) -> bytes:
    """Build an Excel file from block item rows. Returns raw bytes."""
    from io import BytesIO

    from openpyxl import Workbook
    from openpyxl.styles import Alignment, Font

    wb = Workbook()
    ws = wb.active
    ws.title = "QR Codes"

    qr_type = qr_type.upper()
    if qr_type == "B":
        headers = ["URL (Overt)", "URL (Covert)", "Serial Number"]
    elif qr_type == "SC":
        headers = ["QR URL", "Serial Number", "Secret Code"]
    else:
        headers = ["QR URL", "Serial Number"]

    for col, h in enumerate(headers, 1):
        cell = ws.cell(row=1, column=col, value=h)
        cell.font = Font(bold=True)
        cell.alignment = Alignment(horizontal="center")

    for row_idx, item in enumerate(rows, 2):
        if qr_type == "B":
            ws.cell(row=row_idx, column=1, value=item.get("short_url", ""))
            ws.cell(row=row_idx, column=2, value=item.get("overt_url", ""))
            ws.cell(row=row_idx, column=3, value=item.get("serial", ""))
        elif qr_type == "SC":
            ws.cell(row=row_idx, column=1, value=item.get("short_url", ""))
            ws.cell(row=row_idx, column=2, value=item.get("serial", ""))
            ws.cell(row=row_idx, column=3, value=item.get("secret_code", ""))
        else:
            ws.cell(row=row_idx, column=1, value=item.get("short_url", ""))
            ws.cell(row=row_idx, column=2, value=item.get("serial", ""))

    buf = BytesIO()
    wb.save(buf)
    return buf.getvalue()


class QRProductService:
    def __init__(self, db: Session):
        self.db = db
        self.product_repo = QRProductRepository(db)
        self.block_repo = QRBlockRepository(db)
        self.item_repo = ProductItemRepository(db)
        self.credit_service = CreditService(db)
        self.key_service = (
            KeyService(settings.brand_key_encryption_secret)
            if settings.brand_key_encryption_secret
            else None
        )

    # ── Products ──────────────────────────────────────────────────────────────

    def create_product(
        self, data: QRProductCreate, organization_id: UUID, user_id: UUID
    ) -> QRProduct:
        product_dict = data.model_dump()
        product_dict["organization_id"] = organization_id
        product_dict["created_by"] = user_id
        product_dict["updated_by"] = user_id

        # Validate brand_id belongs to the organization when provided
        if product_dict.get("brand_id"):
            from app.repositories.brand_repository import BrandRepository

            brand_repo = BrandRepository(self.db)
            brand = brand_repo.get_by_id(product_dict["brand_id"], organization_id)
            if not brand:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Brand not found",
                )

        qr_product = self.product_repo.create(product_dict)

        # Auto-create a corresponding inventory Item linked to this QR product.
        # This ensures every QR product has a trackable item in the ERP without
        # requiring a separate frontend call.
        self._create_linked_item(qr_product, organization_id, user_id)

        return qr_product

    def _create_linked_item(
        self, qr_product: QRProduct, organization_id: UUID, user_id: UUID
    ) -> None:
        """Create an inventory Item that references this QR product.

        Uses the QR product's name as the item name. The item_code is
        auto-generated via DocumentNumberingService. Errors are logged but
        never bubble up — a failed item creation must not roll back the
        QR product itself.
        """
        try:
            from app.models.base import ItemStatus, ItemType, ValuationMethod
            from app.models.item import Item
            from app.repositories.item_repository import ItemRepository
            from app.services.document_numbering_service import DocumentNumberingService

            item_code = DocumentNumberingService(self.db).get_next_number(
                organization_id, "item"
            )

            item_repo = ItemRepository(self.db)
            item = Item(
                organization_id=organization_id,
                item_code=item_code,
                item_name=qr_product.name,
                description=qr_product.generic_name,
                item_type=ItemType.STOCK,
                uom="Nos",
                maintain_stock=True,
                status=ItemStatus.ACTIVE,
                qr_product_id=qr_product.id,
                image_url=qr_product.image_url,
                created_by=user_id,
                updated_by=user_id,
            )
            self.db.add(item)
            self.db.commit()
            self.db.refresh(item)
            logger.info(
                "Auto-created item '%s' (id=%s) linked to QR product '%s' (id=%s)",
                item.item_code,
                item.id,
                qr_product.name,
                qr_product.id,
            )
        except Exception as exc:
            # Roll back only the item insert, keep the QR product committed
            self.db.rollback()
            logger.error(
                "Failed to auto-create item for QR product '%s' (id=%s): %s",
                qr_product.name,
                qr_product.id,
                exc,
            )

    def get_product(self, product_id: UUID, organization_id: UUID) -> QRProduct:
        product = self.product_repo.get_by_id(product_id, organization_id)
        if not product:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="QR product not found"
            )
        return product

    def list_products(
        self,
        organization_id: UUID,
        page: int = 1,
        page_size: int = 20,
        search: str | None = None,
        is_active: bool | None = None,
    ) -> tuple[list[QRProduct], dict]:
        items, total = self.product_repo.list(
            organization_id, page, page_size, search, is_active
        )
        total_pages = max(1, (total + page_size - 1) // page_size)
        pagination = {
            "page": page,
            "page_size": page_size,
            "total_items": total,
            "total_pages": total_pages,
            "has_next": page < total_pages,
            "has_prev": page > 1,
        }
        return items, pagination

    def update_product(
        self,
        product_id: UUID,
        data: QRProductUpdate,
        organization_id: UUID,
        user_id: UUID,
    ) -> QRProduct:
        product = self.get_product(product_id, organization_id)
        update_dict = data.model_dump(exclude_unset=True)

        # brand_id is immutable after creation
        if "brand_id" in update_dict:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="brand_id cannot be modified after creation",
            )

        update_dict["updated_by"] = user_id
        return self.product_repo.update(product, update_dict)

    def delete_product(
        self, product_id: UUID, organization_id: UUID, user_id: UUID
    ) -> None:
        product = self.get_product(product_id, organization_id)
        self.product_repo.soft_delete(product, user_id)

    # ── QR Blocks ─────────────────────────────────────────────────────────────

    def generate_block(
        self,
        product_id: UUID,
        data: QRBlockCreate,
        organization_id: UUID,
        user_id: UUID,
        org_credit_limit: int = 0,
    ) -> QRBlock:
        """Generate a QR block for a product.

        Enhanced flow:
        1. Validate product exists
        2. Check credits via CreditService.check_balance()
        3. Create block with status="pending"
        4. Set status="in_progress", generate items
        5. On success: status="completed", deduct credits
        6. On failure: status="failed", no credit deduction

        Requirements: 5.1-5.7, 6.3, 6.4, 7.1-7.9, 8.1-8.5
        """
        # 1. Validate product exists
        product = self.get_product(product_id, organization_id)

        # 2. Credit check via CreditService
        self.credit_service.check_balance(organization_id, data.quantity)

        # 3. Create block with status="pending"
        # qr_type lives on QRProduct, not QRBlock — strip it before DB insert
        block_dict = {k: v for k, v in data.model_dump().items() if k != "qr_type"}
        block_dict["product_id"] = product_id
        block_dict["organization_id"] = organization_id
        block_dict["created_by"] = user_id
        block_dict["updated_by"] = user_id
        block_dict["status"] = "pending"
        block_dict["task_status"] = "pending"

        block = self.block_repo.create(block_dict)

        # 4. Set status="in_progress" and generate items
        block.status = "in_progress"
        block.task_status = "in_progress"
        self.db.commit()

        try:
            self._generate_product_items(block, product, organization_id, user_id)

            # 5. Success: mark completed, deduct credits
            block.status = "completed"
            block.task_status = "completed"
            block.completed_at = datetime.now(UTC)
            self.db.commit()

            self.credit_service.deduct_credits(organization_id, block.id, data.quantity)

        except Exception:
            # 6. Failure: mark failed, no credit deduction
            block.status = "failed"
            block.task_status = "failed"
            self.db.commit()
            logger.exception(
                "Block generation failed: block_id=%s product_id=%s org=%s",
                block.id,
                product_id,
                organization_id,
            )
            raise

        logger.info(
            "QR block generated: block_id=%s product_id=%s qty=%d org=%s",
            block.id,
            product_id,
            data.quantity,
            organization_id,
        )
        return block

    # ── Serial number helpers ─────────────────────────────────────────────────

    def _get_serial_generator(self, sr_number_type: str | None):
        """Return a callable that produces serial numbers for the given type."""
        sr_type = (sr_number_type or "R6DAN").upper()
        if sr_type == "R4DAN":
            return generate_r4dan
        if sr_type == "S8DN":
            gen = sequential_s8dn()
            return lambda: next(gen)
        if sr_type == "S10DN":
            gen = sequential_s10dn()
            return lambda: next(gen)
        # Default: R6DAN
        return generate_r6dan

    @staticmethod
    def _generate_secret_code() -> str:
        """Generate a 12-character alphanumeric secret code for SecureCode QR."""
        return "".join(
            secrets.choice(string.ascii_uppercase + string.digits) for _ in range(12)
        )

    # ── Item generation ───────────────────────────────────────────────────────

    def _generate_product_items(
        self,
        block: QRBlock,
        product: QRProduct,
        organization_id: UUID,
        user_id: UUID,
    ) -> None:
        """Generate ProductItem rows for the block.

        Handles brand-based signing and QR type-specific behaviour:
        - S (Static): same serial for all items
        - SC (SecureCode): 12-char secret per item
        - O (OneTime): qr_active based on activation_method
        - B (Dual): two URLs per item (covert + overt)
        - D (Dynamic) / default: unique URL per item
        """
        now = datetime.now(UTC)
        qr_type = (product.qr_type or "D").upper()
        sr_number_type = block.sr_number_type or product.sr_number_type
        prefix = block.serial_prefix or ""

        # Determine if we need signing (product linked to a brand)
        brand = None
        private_key = None
        org_short_code = ""
        gtin = product.gtin or ""

        if product.brand_id and self.key_service:
            from app.repositories.brand_repository import BrandRepository

            brand_repo = BrandRepository(self.db)
            brand = brand_repo.get_by_id(product.brand_id, organization_id)
            if brand and brand.private_key_encrypted:
                private_key = self.key_service.decrypt_private_key(
                    brand.private_key_encrypted
                )
                org_short_code = brand.short_code or ""

        serial_gen = self._get_serial_generator(sr_number_type)

        # For Static QR: generate one serial used for all items
        static_serial = None
        if qr_type == "S":
            static_serial = f"{prefix}{serial_gen()}"

        items: list[dict] = []

        for _ in range(block.quantity):
            serial = static_serial if static_serial else f"{prefix}{serial_gen()}"

            item_dict: dict = {
                "id": uuid.uuid4(),
                "organization_id": organization_id,
                "product_id": block.product_id,
                "block_id": block.id,
                "serial_number": serial,
                "created_by": user_id,
                "updated_by": user_id,
                "created_at": now,
                "updated_at": now,
            }

            # SecureCode: generate 12-char secret
            if qr_type == "SC":
                item_dict["secrete_code"] = self._generate_secret_code()

            # OneTime: set qr_active based on activation_method
            if qr_type == "O":
                item_dict["qr_active"] = product.activation_method == "pre"

            # Sign if brand is linked
            if private_key is not None:
                sig, ts = sign_qr_item(self.key_service, private_key, serial)
                url = build_qr_url(
                    org_short_code, settings.qr_domain, gtin, serial, ts, sig
                )
                item_dict["token_id"] = url

                # Dual QR: generate a second (covert) URL
                if qr_type == "B":
                    sig2, ts2 = sign_qr_item(self.key_service, private_key, serial)
                    covert_url = build_qr_url(
                        org_short_code, settings.qr_domain, gtin, serial, ts2, sig2
                    )
                    item_dict.setdefault("extra_data", {})
                    item_dict["extra_data"]["covert_url"] = covert_url

            items.append(item_dict)

        self.item_repo.bulk_create(items)

    def get_block(self, block_id: UUID, organization_id: UUID) -> QRBlock:
        block = self.block_repo.get_by_id(block_id, organization_id)
        if not block:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="QR block not found"
            )
        return block

    def get_block_download_url(
        self, block_id: UUID, organization_id: UUID
    ) -> tuple[str, datetime]:
        """Return a signed download URL for a completed block's Excel file."""
        from app.services import storage_service

        block = self.get_block(block_id, organization_id)

        if block.status != "completed":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Block is not ready (status: {block.status})",
            )

        expiry_minutes = 60
        expires_at = datetime.now(UTC) + timedelta(minutes=expiry_minutes)

        # If a GCS URL is stored, return it (signed or direct)
        if block.download_url:
            if storage_service.is_full_url(block.download_url):
                return block.download_url, expires_at
            signed_url = storage_service.get_signed_url(block.download_url, expiry_minutes)
            return signed_url, expires_at

        # No stored URL — raise so the endpoint falls back to streaming
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Download file not available",
        )

    def get_block_excel_stream(
        self, block_id: UUID, organization_id: UUID
    ) -> tuple[bytes, str]:
        """
        Generate the Excel file on-demand from the block's ProductItems.
        Used when download_url is not set (GCS not configured).
        Returns (excel_bytes, filename).
        """
        from app.models.product_item import ProductItem as PIModel

        block = self.get_block(block_id, organization_id)

        if block.status != "completed":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Block is not ready (status: {block.status})",
            )

        product = self.product_repo.get_by_id(block.product_id, organization_id)
        qr_type = (product.qr_type if product else None) or "D"

        items = (
            self.db.query(PIModel)
            .filter(
                PIModel.block_id == block_id,
                PIModel.organization_id == organization_id,
                PIModel.deleted_at.is_(None),
            )
            .order_by(PIModel.created_at.asc())
            .all()
        )

        rows = [
            {
                "serial": item.serial_number,
                "short_url": item.token_id or "",
                "secret_code": item.secrete_code or "",
                "overt_url": (item.extra_data or {}).get("covert_url", ""),
            }
            for item in items
        ]

        excel_bytes = _build_excel(rows, qr_type)
        filename = f"qr_block_{block.batch}_{block_id}.xlsx"
        return excel_bytes, filename

    def list_blocks(
        self,
        product_id: UUID,
        organization_id: UUID,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[QRBlock], dict]:
        # Validate product
        self.get_product(product_id, organization_id)
        items, total = self.block_repo.list_by_product(
            product_id, organization_id, page, page_size
        )
        total_pages = max(1, (total + page_size - 1) // page_size)
        pagination = {
            "page": page,
            "page_size": page_size,
            "total_items": total,
            "total_pages": total_pages,
            "has_next": page < total_pages,
            "has_prev": page > 1,
        }
        return items, pagination

    def list_blocks_by_org(
        self,
        organization_id: UUID,
        page: int = 1,
        page_size: int = 20,
        status: str | None = None,
        product_id: UUID | None = None,
    ) -> tuple[list[dict], dict]:
        rows, total = self.block_repo.list_by_org(
            organization_id, page, page_size, status, product_id
        )
        total_pages = max(1, (total + page_size - 1) // page_size)
        pagination = {
            "page": page,
            "page_size": page_size,
            "total_items": total,
            "total_pages": total_pages,
            "has_next": page < total_pages,
            "has_prev": page > 1,
        }
        enriched = []
        for block, product_name in rows:
            block_dict = {
                k: v
                for k, v in block.__dict__.items()
                if k != "_sa_instance_state"
            }
            block_dict["product_name"] = product_name
            enriched.append(block_dict)
        return enriched, pagination

    # ── Product Items ─────────────────────────────────────────────────────────

    def list_items(
        self,
        block_id: UUID,
        organization_id: UUID,
        page: int = 1,
        page_size: int = 50,
    ) -> tuple[list[ProductItem], dict]:
        block = self.block_repo.get_by_id(block_id, organization_id)
        if not block:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="QR block not found"
            )
        items, total = self.item_repo.list_by_block(
            block_id, organization_id, page, page_size
        )
        total_pages = max(1, (total + page_size - 1) // page_size)
        pagination = {
            "page": page,
            "page_size": page_size,
            "total_items": total,
            "total_pages": total_pages,
            "has_next": page < total_pages,
            "has_prev": page > 1,
        }
        return items, pagination

    # ── QR Validate (public) ──────────────────────────────────────────────────

    def validate_qr(self, req: QRValidateRequest) -> dict:
        """
        Authenticate a QR scan. Records the scan event and returns authenticity.
        This endpoint is typically called from the consumer-facing landing page.
        organization_id is resolved from the serial number — callers don't need to supply it.
        """
        item = self.item_repo.get_by_serial_global(req.serial_number)
        if not item:
            return {
                "is_authentic": False,
                "is_suspicious": False,
                "scans": 0,
                "product_name": None,
                "message": "QR code not found. This product may be counterfeit.",
            }

        # Flag as suspicious if scanned more than once (configurable threshold)
        if item.scans >= 1 and not item.is_suspicious:
            item.is_suspicious = True
            self.db.flush()

        # Record scan event
        scan_data = {
            k: v
            for k, v in req.model_dump().items()
            if k != "serial_number" and v is not None
        }
        self.item_repo.record_scan(item, scan_data)

        product_name = item.product.name if item.product else None
        is_first_scan = item.scans == 1

        logger.info(
            "QR scan: serial=%s org=%s scans=%d suspicious=%s",
            req.serial_number,
            item.organization_id,
            item.scans,
            item.is_suspicious,
        )

        return {
            "is_authentic": True,
            "is_suspicious": item.is_suspicious,
            "scans": item.scans,
            "product_name": product_name,
            "message": (
                "Authentic product."
                if is_first_scan
                else f"Warning: This QR has been scanned {item.scans} times."
            ),
        }

    # ── QR Authenticate (public, ECDSA) ─────────────────────────────────────

    def authenticate(self, data: AuthenticateRequest) -> dict:
        """
        Verify a QR scan using ECDSA signature verification.

        organization_id is NOT required — serial numbers are globally unique,
        so we look up the item across all orgs. This allows the public
        /authenticate endpoint to work without the caller knowing the org.

        Requirements: 9.1-9.9, 8.4
        """
        # 1. Look up item by serial_number globally (no org filter)
        item = self.item_repo.get_by_serial_global(data.serial_number)
        if not item:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Serial number not found",
            )

        # 2. Load product and brand via relationships
        product = item.product
        brand = product.brand if product else None

        # 3. Check post-activation: qr_active must be True
        if product and product.activation_method == "post" and not item.qr_active:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Product has not been activated",
            )

        # 4. Brand must exist for ECDSA verification
        if not brand:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No brand linked to product",
            )

        # 5. Reconstruct message and verify signature
        message = f"{data.serial_number}~{data.nonce}"
        is_valid = self.key_service.verify_signature(
            brand.public_key, message, data.cipher
        )

        if not is_valid:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "message": "Authentication Failed",
                    "authentic": False,
                },
            )

        # 6. Valid signature — update scan tracking
        item.scan_count = (item.scan_count or 0) + 1
        item.last_scanned_at = datetime.now(UTC)

        # 7. OneTime QR: deactivate after first successful verification
        if product.qr_type == "O":
            item.qr_active = False

        self.db.commit()

        logger.info(
            "QR authenticate: serial=%s org=%s authentic=True scan_count=%d",
            data.serial_number,
            item.organization_id,
            item.scan_count,
        )

        return {
            "message": "Authentic Product",
            "authentic": True,
            "product_name": product.name,
            "brand_name": brand.name,
            "gtin": product.gtin,
            "serial_number": data.serial_number,
        }

    # ── Scan Analytics ────────────────────────────────────────────────────────

    def get_scan_analytics(self, product_id: UUID, organization_id: UUID) -> dict:
        self.get_product(product_id, organization_id)
        return self.item_repo.get_scan_analytics(product_id, organization_id)

    # ── Activation Parameters ─────────────────────────────────────────────────

    def set_activation_params(
        self,
        data: QRActivationParamsCreate,
        organization_id: UUID,
        user_id: UUID,
    ):
        from app.models.qr_activation import QRActivationParameters

        params_dict = data.model_dump()
        params_dict["organization_id"] = organization_id
        params_dict["created_by"] = user_id
        params = QRActivationParameters(**params_dict)
        self.db.add(params)
        self.db.commit()
        self.db.refresh(params)
        return params
