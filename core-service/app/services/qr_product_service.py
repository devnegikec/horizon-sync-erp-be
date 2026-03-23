"""Service layer for QR Products module"""

import logging
import uuid
from datetime import UTC, datetime
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.product_item import ProductItem
from app.models.qr_block import QRBlock
from app.models.qr_product import QRProduct
from app.repositories.qr_product_repository import (
    ProductItemRepository,
    QRBlockRepository,
    QRProductRepository,
)
from app.schemas.qr_product import (
    QRActivationParamsCreate,
    QRBlockCreate,
    QRProductCreate,
    QRProductUpdate,
    QRValidateRequest,
)

logger = logging.getLogger(__name__)


class QRProductService:
    def __init__(self, db: Session):
        self.db = db
        self.product_repo = QRProductRepository(db)
        self.block_repo = QRBlockRepository(db)
        self.item_repo = ProductItemRepository(db)

    # ── Products ──────────────────────────────────────────────────────────────

    def create_product(
        self, data: QRProductCreate, organization_id: UUID, user_id: UUID
    ) -> QRProduct:
        product_dict = data.model_dump()
        product_dict["organization_id"] = organization_id
        product_dict["created_by"] = user_id
        product_dict["updated_by"] = user_id
        return self.product_repo.create(product_dict)

    def get_product(self, product_id: UUID, organization_id: UUID) -> QRProduct:
        product = self.product_repo.get_by_id(product_id, organization_id)
        if not product:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                                detail="QR product not found")
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
        self, product_id: UUID, data: QRProductUpdate,
        organization_id: UUID, user_id: UUID
    ) -> QRProduct:
        product = self.get_product(product_id, organization_id)
        update_dict = data.model_dump(exclude_unset=True)
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
        """
        Generate a QR block for a product.
        Checks monthly credit quota before creating.
        """
        # Validate product exists
        self.get_product(product_id, organization_id)

        # Credit check (0 = unlimited)
        if org_credit_limit > 0:
            used = self.block_repo.get_monthly_credit_used(organization_id)
            if used + data.quantity > org_credit_limit:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail=(
                        f"QR credit limit exceeded. "
                        f"Monthly limit: {org_credit_limit}, "
                        f"Used: {used}, Requested: {data.quantity}"
                    ),
                )

        block_dict = data.model_dump()
        block_dict["product_id"] = product_id
        block_dict["organization_id"] = organization_id
        block_dict["created_by"] = user_id
        block_dict["updated_by"] = user_id
        block_dict["task_status"] = "pending"

        block = self.block_repo.create(block_dict)

        # Record credit usage
        self.block_repo.record_credit_usage(organization_id, block.id, data.quantity)

        # Generate individual product items (serial numbers)
        self._generate_product_items(block, organization_id, user_id)

        logger.info(
            "QR block generated: block_id=%s product_id=%s qty=%d org=%s",
            block.id, product_id, data.quantity, organization_id,
        )
        return block

    def _generate_product_items(
        self, block: QRBlock, organization_id: UUID, user_id: UUID
    ) -> None:
        """Bulk-insert ProductItem rows for each serial in the block"""
        prefix = block.serial_prefix or ""
        now = datetime.now(UTC)
        items = []
        for i in range(block.quantity):
            serial = f"{prefix}{str(uuid.uuid4()).replace('-', '')[:12].upper()}"
            items.append({
                "id": uuid.uuid4(),
                "organization_id": organization_id,
                "product_id": block.product_id,
                "block_id": block.id,
                "serial_number": serial,
                "created_by": user_id,
                "updated_by": user_id,
                "created_at": now,
                "updated_at": now,
            })
        self.item_repo.bulk_create(items)

        # Mark block as completed
        block.task_status = "completed"
        self.db.commit()

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
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                                detail="QR block not found")
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

    def validate_qr(
        self, organization_id: UUID, req: QRValidateRequest
    ) -> dict:
        """
        Authenticate a QR scan. Records the scan event and returns authenticity.
        This endpoint is typically called from the consumer-facing landing page.
        """
        item = self.item_repo.get_by_serial(req.serial_number, organization_id)
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
            k: v for k, v in req.model_dump().items()
            if k != "serial_number" and v is not None
        }
        self.item_repo.record_scan(item, scan_data)

        product_name = item.product.name if item.product else None
        is_first_scan = item.scans == 1

        logger.info(
            "QR scan: serial=%s org=%s scans=%d suspicious=%s",
            req.serial_number, organization_id, item.scans, item.is_suspicious,
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
