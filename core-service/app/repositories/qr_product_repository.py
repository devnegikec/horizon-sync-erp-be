"""Repository for QR Products module"""

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import func, or_
from sqlalchemy.orm import Session, joinedload

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
            .options(joinedload(QRProduct.brand))
            .options(joinedload(QRProduct.serial_prefix_setting))
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
        q = self.db.query(QRProduct).options(joinedload(QRProduct.brand)).options(joinedload(QRProduct.serial_prefix_setting))
        .filter(
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

    def create(self, data: dict, *, commit: bool = True) -> QRBlock:
        block = QRBlock(**data)
        self.db.add(block)
        if commit:
            self.db.commit()
            self.db.refresh(block)
        else:
            self.db.flush()
        return block

    def get_by_id_for_update(
        self,
        block_id: UUID,
        organization_id: UUID,
    ) -> QRBlock | None:
        return (
            self.db.query(QRBlock)
            .filter(
                QRBlock.id == block_id,
                QRBlock.organization_id == organization_id,
                QRBlock.deleted_at.is_(None),
            )
            .with_for_update()
            .first()
        )

    def get_by_id(self, block_id: UUID, organization_id: UUID) -> QRBlock | None:
        return (
            self.db.query(QRBlock)
            .options(
                joinedload(QRBlock.channel_setting),
                joinedload(QRBlock.destination_setting),
            )
            .filter(
                QRBlock.id == block_id,
                QRBlock.organization_id == organization_id,
                QRBlock.deleted_at.is_(None),
            )
            .first()
        )

    def batch_exists(self, batch: str, organization_id: UUID) -> bool:
        return (
            self.db.query(QRBlock.id)
            .filter(
                func.lower(QRBlock.batch) == batch.lower(),
                QRBlock.organization_id == organization_id,
                QRBlock.deleted_at.is_(None),
            )
            .first()
            is not None
        )

    def list_by_product(
        self,
        product_id: UUID,
        organization_id: UUID,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[QRBlock], int]:
        q = self.db.query(QRBlock).options(
            joinedload(QRBlock.channel_setting),
            joinedload(QRBlock.destination_setting),
        ).filter(
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
        search: str | None = None,
        qr_type: str | None = None,
        created_from: datetime | None = None,
        created_to: datetime | None = None,
    ) -> tuple[list[tuple[QRBlock, str | None]], int]:
        q = (
            self.db.query(QRBlock, QRProduct.name)
            .options(
                joinedload(QRBlock.channel_setting),
                joinedload(QRBlock.destination_setting),
            )
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
        if search:
            pattern = f"%{search.strip()}%"
            q = q.filter(
                or_(
                    QRBlock.batch.ilike(pattern),
                    QRProduct.name.ilike(pattern),
                )
            )
        if qr_type is not None:
            q = q.filter(QRBlock.qr_type == qr_type)
        if created_from is not None:
            q = q.filter(QRBlock.created_at >= created_from)
        if created_to is not None:
            q = q.filter(QRBlock.created_at < created_to)
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

    def get_by_serial_global(self, serial_number: str) -> ProductItem | None:
        """Look up a ProductItem by serial number without an org filter.

        Used by the public /authenticate endpoint where the caller (a consumer
        scanning a QR code) does not know the organization_id.
        Serial numbers are unique across the entire system.
        """
        return (
            self.db.query(ProductItem)
            .filter(
                ProductItem.serial_number == serial_number,
                ProductItem.deleted_at.is_(None),
            )
            .first()
        )

    def get_existing_serials(
        self, serial_numbers: list[str], organization_id: UUID
    ) -> set[str]:
        if not serial_numbers:
            return set()
        rows = (
            self.db.query(ProductItem.serial_number)
            .filter(
                ProductItem.serial_number.in_(serial_numbers),
                ProductItem.organization_id == organization_id,
                ProductItem.deleted_at.is_(None),
            )
            .all()
        )
        return {row[0] for row in rows}

    def get_existing_serials_global(
        self,
        serial_numbers: list[str],
    ) -> set[str]:
        """Return active collisions for the globally unique public serial key."""
        if not serial_numbers:
            return set()
        rows = (
            self.db.query(ProductItem.serial_number)
            .filter(
                ProductItem.serial_number.in_(serial_numbers),
                ProductItem.deleted_at.is_(None),
            )
            .all()
        )
        return {row[0] for row in rows}

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

    def list_by_product(
        self,
        product_id: UUID,
        organization_id: UUID,
        page: int = 1,
        page_size: int = 50,
    ) -> tuple[list[ProductItem], int]:
        """List all serial numbers across every block for a given QR product."""
        q = self.db.query(ProductItem).filter(
            ProductItem.product_id == product_id,
            ProductItem.organization_id == organization_id,
            ProductItem.deleted_at.is_(None),
        )
        total = q.count()
        items = (
            q.order_by(ProductItem.created_at.asc())
            .offset((page - 1) * page_size)
            .limit(page_size)
            .all()
        )
        return items, total

    def get_activation_summary(
        self, block_id: UUID, organization_id: UUID
    ) -> tuple[int, int]:
        """Count all and active items in one tenant-scoped Block query."""
        total, active = (
            self.db.query(
                func.count(ProductItem.id),
                func.count(ProductItem.id).filter(
                    ProductItem.qr_active.is_(True)
                ),
            )
            .filter(
                ProductItem.block_id == block_id,
                ProductItem.organization_id == organization_id,
                ProductItem.deleted_at.is_(None),
            )
            .one()
        )
        return int(total or 0), int(active or 0)

    def soft_delete_by_block(
        self, block_id: UUID, organization_id: UUID
    ) -> int:
        """Deactivate generated items when their Block generation fails."""
        return (
            self.db.query(ProductItem)
            .filter(
                ProductItem.block_id == block_id,
                ProductItem.organization_id == organization_id,
                ProductItem.deleted_at.is_(None),
            )
            .update(
                {ProductItem.deleted_at: datetime.now(UTC)},
                synchronize_session=False,
            )
        )

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
