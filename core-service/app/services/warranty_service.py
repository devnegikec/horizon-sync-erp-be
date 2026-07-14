"""Service layer for Warranty module"""

import logging
from datetime import UTC, datetime, timedelta
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.warranty import Warranty, WarrantyPeriod
from app.repositories.warranty_repository import WarrantyPeriodRepository, WarrantyRepository
from app.schemas.warranty import WarrantyPeriodCreate, WarrantyRegisterRequest

logger = logging.getLogger(__name__)


class WarrantyService:
    def __init__(self, db: Session):
        self.db = db
        self.period_repo = WarrantyPeriodRepository(db)
        self.warranty_repo = WarrantyRepository(db)

    # ── Warranty Periods ──────────────────────────────────────────────────────

    def create_period(
        self, data: WarrantyPeriodCreate, organization_id: UUID
    ) -> WarrantyPeriod:
        period_dict = data.model_dump()
        period_dict["organization_id"] = organization_id
        return self.period_repo.create(period_dict)

    def list_periods(self, organization_id: UUID) -> list[WarrantyPeriod]:
        return self.period_repo.list(organization_id)

    # ── Warranty Registration ─────────────────────────────────────────────────

    def register(
        self,
        organization_id: UUID,
        req: WarrantyRegisterRequest,
    ) -> Warranty:
        """
        Register a warranty for a product serial number.
        Looks up the product item to get warranty_period_months from the product.
        Falls back to the org's default warranty period.
        """
        # Check for duplicate registration
        existing = self.warranty_repo.get_by_serial(req.serial_number, organization_id)
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Warranty already registered for serial number '{req.serial_number}'",
            )

        # Resolve warranty duration
        warranty_months = self._resolve_warranty_months(
            req.serial_number, organization_id
        )

        # Calculate valid_till
        base_date = req.purchase_date or datetime.now(UTC).date()
        valid_till = datetime(
            base_date.year, base_date.month, base_date.day, tzinfo=UTC
        ) + timedelta(days=warranty_months * 30)

        # Resolve product_item_id if serial exists
        product_item_id = self._get_product_item_id(req.serial_number, organization_id)

        warranty_dict = req.model_dump()
        warranty_dict["organization_id"] = organization_id
        warranty_dict["warranty_valid_till"] = valid_till
        warranty_dict["product_item_id"] = product_item_id

        warranty = self.warranty_repo.create(warranty_dict)
        logger.info(
            "Warranty registered: serial=%s org=%s valid_till=%s",
            req.serial_number, organization_id, valid_till.date(),
        )
        return warranty

    def _resolve_warranty_months(self, serial_number: str,
                                  organization_id: UUID) -> int:
        """Get warranty months from product → fallback to org default → fallback to 12"""
        from app.models.product_item import ProductItem

        item = (
            self.db.query(ProductItem)
            .filter(
                ProductItem.serial_number == serial_number,
                ProductItem.organization_id == organization_id,
                ProductItem.deleted_at.is_(None),
            )
            .first()
        )
        if item and item.product and item.product.warranty_period_months:
            return item.product.warranty_period_months

        default_period = self.period_repo.get_default(organization_id)
        if default_period:
            return default_period.months

        return 12  # global fallback

    def _get_product_item_id(self, serial_number: str,
                              organization_id: UUID) -> UUID | None:
        from app.models.product_item import ProductItem

        item = (
            self.db.query(ProductItem)
            .filter(
                ProductItem.serial_number == serial_number,
                ProductItem.organization_id == organization_id,
                ProductItem.deleted_at.is_(None),
            )
            .first()
        )
        return item.id if item else None

    # ── Warranty Check ────────────────────────────────────────────────────────

    def check_by_serial(self, serial_number: str, organization_id: UUID) -> dict:
        warranty = self.warranty_repo.get_by_serial(serial_number, organization_id)
        if not warranty:
            return {
                "found": False, "is_valid": False, "warranty_id": None,
                "serial_number": serial_number, "customer_name": None,
                "purchase_date": None, "warranty_valid_till": None,
                "days_remaining": None,
                "message": "No warranty found for this serial number",
            }
        return self._build_check_response(warranty)

    def search_by_mobile(self, mobile: str,
                         organization_id: UUID) -> list[dict]:
        warranties = self.warranty_repo.get_by_mobile(mobile, organization_id)
        return [self._build_check_response(w) for w in warranties]

    def _build_check_response(self, warranty: Warranty) -> dict:
        now = datetime.now(UTC)
        is_valid = bool(
            warranty.warranty_valid_till and warranty.warranty_valid_till > now
        )
        days_remaining = None
        if warranty.warranty_valid_till:
            delta = warranty.warranty_valid_till - now
            days_remaining = max(0, delta.days)

        return {
            "found": True,
            "is_valid": is_valid,
            "warranty_id": warranty.id,
            "serial_number": warranty.serial_number,
            "customer_name": warranty.customer_name,
            "purchase_date": warranty.purchase_date,
            "warranty_valid_till": warranty.warranty_valid_till,
            "days_remaining": days_remaining,
            "message": "Warranty is active" if is_valid else "Warranty has expired",
        }

    # ── Warranty List ─────────────────────────────────────────────────────────

    def list_warranties(
        self,
        organization_id: UUID,
        page: int = 1,
        page_size: int = 20,
        search: str | None = None,
    ) -> tuple[list[Warranty], dict]:
        items, total = self.warranty_repo.list(
            organization_id, page, page_size, search
        )
        total_pages = max(1, (total + page_size - 1) // page_size)
        return items, {
            "page": page, "page_size": page_size, "total_items": total,
            "total_pages": total_pages,
            "has_next": page < total_pages, "has_prev": page > 1,
        }
