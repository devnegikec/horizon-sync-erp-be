"""Repository for QR Products module"""

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.product_item import ProductItem
from app.models.qr_block import QRBlock
from app.models.qr_credit import QRCreditUsage
from app.models.qr_product import QRProduct
from app.models.qr_scan_event import QRScanEvent


class QRProductRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(self, data: dict) -> QRProduct:
        product = QRProduct(**data)
        self.db.add(product)
        self.db.commit()
        self.db.refresh(product)
        return product

    def get_by_id(self, product_id: UUID, organization_id: UUID) -> QRProduct | None:
        return (
            self.db.query(QRProduct)
            .filter(
                QRProduct.id == product_id,
                QRProduct.organization_id == organization_id,
                QRProduct.deleted_at.is_(None),
            )
            .first()
        )

    def list(
        self,
        organization_id: UUID,
        page: int = 1,
        page_size: int = 20,
        search: str | None = None,
        is_active: bool | None = None,
    ) -> tuple[list[QRProduct], int]:
        q = self.db.query(QRProduct).filter(
            QRProduct.organization_id == organization_id,
            QRProduct.deleted_at.is_(None),
        )
        if search:
            q = q.filter(QRProduct.name.ilike(f"%{search}%"))
        if is_active is not None:
            q = q.filter(QRProduct.is_active == is_active)
        total = q.count()
        items = q.order_by(QRProduct.created_at.desc()) \
                 .offset((page - 1) * page_size).limit(page_size).all()
        return items, total

    def update(self, product: QRProduct, data: dict) -> QRProduct:
        for k, v in data.items():
            setattr(product, k, v)
        self.db.commit()
        self.db.refresh(product)
        return product

    def soft_delete(self, product: QRProduct, user_id: UUID) -> QRProduct:
        product.deleted_at = datetime.now(UTC)
        product.updated_by = user_id
        self.db.commit()
        return product


class QRBlockRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(self, data: dict) -> QRBlock:
        block = QRBlock(**data)
        self.db.add(block)
        self.db.commit()
        self.db.refresh(block)
        return block

    def get_by_id(self, block_id: UUID, organization_id: UUID) -> QRBlock | None:
        return (
            self.db.query(QRBlock)
            .filter(
                QRBlock.id == block_id,
                QRBlock.organization_id == organization_id,
                QRBlock.deleted_at.is_(None),
            )
            .first()
        )

    def list_by_product(
        self,
        product_id: UUID,
        organization_id: UUID,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[QRBlock], int]:
        q = self.db.query(QRBlock).filter(
            QRBlock.product_id == product_id,
            QRBlock.organization_id == organization_id,
            QRBlock.deleted_at.is_(None),
        )
        total = q.count()
        items = q.order_by(QRBlock.created_at.desc()) \
                 .offset((page - 1) * page_size).limit(page_size).all()
        return items, total

    def list_by_org(
        self,
        organization_id: UUID,
        page: int = 1,
        page_size: int = 20,
        status: str | None = None,
        product_id: UUID | None = None,
    ) -> tuple[list[tuple[QRBlock, str | None]], int]:
        q = (
            self.db.query(QRBlock, QRProduct.name)
            .outerjoin(QRProduct, QRBlock.product_id == QRProduct.id)
            .filter(
                QRBlock.organization_id == organization_id,
                QRBlock.deleted_at.is_(None),
            )
        )
        if status is not None:
            q = q.filter(QRBlock.status == status)
        if product_id is not None:
            q = q.filter(QRBlock.product_id == product_id)
        total = q.count()
        rows = (
            q.order_by(QRBlock.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
            .all()
        )
        return rows, total

    def get_monthly_credit_used(self, organization_id: UUID) -> int:
        """Sum QR credits used in the current calendar month"""
        now = datetime.now(UTC)
        month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        result = (
            self.db.query(func.coalesce(func.sum(QRCreditUsage.quantity), 0))
            .filter(
                QRCreditUsage.organization_id == organization_id,
                QRCreditUsage.used_at >= month_start,
            )
            .scalar()
        )
        return int(result)

    def record_credit_usage(self, organization_id: UUID, block_id: UUID,
                            quantity: int) -> QRCreditUsage:
        usage = QRCreditUsage(
            organization_id=organization_id,
            block_id=block_id,
            quantity=quantity,
        )
        self.db.add(usage)
        self.db.commit()
        return usage


class ProductItemRepository:
    def __init__(self, db: Session):
        self.db = db

    def bulk_create(self, items: list[dict]) -> int:
        self.db.bulk_insert_mappings(ProductItem, items)
        self.db.commit()
        return len(items)

    def get_by_serial(self, serial_number: str,
                      organization_id: UUID) -> ProductItem | None:
        return (
            self.db.query(ProductItem)
            .filter(
                ProductItem.serial_number == serial_number,
                ProductItem.organization_id == organization_id,
                ProductItem.deleted_at.is_(None),
            )
            .first()
        )

    def list_by_block(
        self,
        block_id: UUID,
        organization_id: UUID,
        page: int = 1,
        page_size: int = 50,
    ) -> tuple[list[ProductItem], int]:
        q = self.db.query(ProductItem).filter(
            ProductItem.block_id == block_id,
            ProductItem.organization_id == organization_id,
            ProductItem.deleted_at.is_(None),
        )
        total = q.count()
        items = q.order_by(ProductItem.created_at.asc()) \
                 .offset((page - 1) * page_size).limit(page_size).all()
        return items, total

    def update(self, item: ProductItem, data: dict) -> ProductItem:
        for k, v in data.items():
            setattr(item, k, v)
        self.db.commit()
        self.db.refresh(item)
        return item

    def record_scan(self, item: ProductItem, scan_data: dict) -> QRScanEvent:
        """Increment scan counter and record scan event"""
        item.scans = (item.scans or 0) + 1
        item.scan_date = datetime.now(UTC)
        self.db.flush()

        event = QRScanEvent(
            organization_id=item.organization_id,
            product_item_id=item.id,
            serial_number=item.serial_number,
            **scan_data,
        )
        self.db.add(event)
        self.db.commit()
        self.db.refresh(event)
        return event

    def get_scan_analytics(self, product_id: UUID,
                           organization_id: UUID) -> dict:
        """Aggregate scan stats for a product"""
        base = (
            self.db.query(QRScanEvent)
            .join(ProductItem, QRScanEvent.product_item_id == ProductItem.id)
            .filter(
                ProductItem.product_id == product_id,
                ProductItem.organization_id == organization_id,
            )
        )
        total_scans = base.count()
        unique_serials = (
            base.with_entities(func.count(func.distinct(QRScanEvent.serial_number)))
            .scalar() or 0
        )
        suspicious = (
            self.db.query(func.count(ProductItem.id))
            .filter(
                ProductItem.product_id == product_id,
                ProductItem.organization_id == organization_id,
                ProductItem.is_suspicious.is_(True),
            )
            .scalar() or 0
        )
        by_country = (
            base.with_entities(
                QRScanEvent.country,
                func.count(QRScanEvent.id).label("count"),
            )
            .group_by(QRScanEvent.country)
            .order_by(func.count(QRScanEvent.id).desc())
            .limit(10)
            .all()
        )
        by_day = (
            base.with_entities(
                func.date_trunc("day", QRScanEvent.scan_timestamp).label("day"),
                func.count(QRScanEvent.id).label("count"),
            )
            .group_by("day")
            .order_by("day")
            .limit(30)
            .all()
        )
        return {
            "total_scans": total_scans,
            "unique_serials": unique_serials,
            "suspicious_count": suspicious,
            "scans_by_country": [
                {"country": r.country or "Unknown", "count": r.count}
                for r in by_country
            ],
            "scans_by_day": [
                {"day": str(r.day)[:10], "count": r.count}
                for r in by_day
            ],
        }
