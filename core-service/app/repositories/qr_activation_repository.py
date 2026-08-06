"""Repository for Landing / Public API module"""

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.product_item import ProductItem
from app.models.qr_activation import QRActivationParameters
from app.models.qr_product import QRProduct
from app.models.destination_market import DestinationMarket


class DestinationMarketRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_active_by_name(self, name: str, organization_id):
        from app.models.destination_market import DestinationMarket

        return (
            self.db.query(DestinationMarket)
            .filter(
                DestinationMarket.name == name,
                DestinationMarket.organization_id == organization_id,
                DestinationMarket.is_active.is_(True),
            )
            .first()
        )

    def list_all(self,organization_id,
        page: int = 1,
        page_size: int = 20,
        search: str | None = None,):

        query = self.db.query(DestinationMarket).filter(
            DestinationMarket.organization_id == organization_id
        )

        if search:
            query = query.filter(DestinationMarket.name.ilike(f"%{search}%"))

        total = query.count()

        items = (
            query
            .offset((page - 1) * page_size)
            .limit(page_size)
            .all()
        )

        return items, total




class QRActivationRepository:
    def __init__(self, db: Session):
        self.db = db


   

    def get_active_settings(self, product_id: UUID,organization_id: UUID) -> QRActivationParameters | None:
        """Get latest active (non-history) QR settings for a product"""
        return (
            self.db.query(QRActivationParameters)
            .filter(
                QRActivationParameters.product_id == product_id,
                QRActivationParameters.qr_settings.is_(True),
                QRActivationParameters.organization_id == organization_id,
              #  QRActivationParameters.history.is_(False),
            )
            .order_by(QRActivationParameters.created_at.desc())
            .first()
        )
    
    def get_active_settings_by_products(self, product_ids: list[UUID], organization_id: UUID):
        return (
            self.db.query(QRActivationParameters)
            .filter(
                QRActivationParameters.product_id.in_(product_ids),
                QRActivationParameters.organization_id == organization_id,
                QRActivationParameters.qr_settings.is_(True),
            )
            .all()
        )

    def get_settings_by_batch(
        self, batch: str, product_id: UUID,organization_id: UUID
    ) -> QRActivationParameters | None:
        return (
            self.db.query(QRActivationParameters)
            .filter(
                QRActivationParameters.dispatch_batch == batch,
                QRActivationParameters.product_id == product_id,
                QRActivationParameters.qr_settings.is_(True),
                QRActivationParameters.organization_id == organization_id,
               # QRActivationParameters.history.is_(False),
            )
            .first()
        )

    def get_activated_serials_in_batch(
        self, batch: str, created_after: datetime, organization_id: UUID, limit: int = 100
    ) -> list[str]:
        """Get serial numbers activated after batch was created (with limit for safety)"""
        rows = (
            self.db.query(QRActivationParameters.serial_number)
            .filter(
                QRActivationParameters.qr_settings.is_(False),
                QRActivationParameters.dispatch_batch == batch,
                QRActivationParameters.organization_id == organization_id,
                QRActivationParameters.created_at >= created_after,
            )
            .limit(limit)
            .all()
        )
        return [r.serial_number for r in rows]

    def count_activated_serials_in_batch(
        self, batch: str, created_after: datetime, organization_id: UUID
    ) -> int:
        """Count serial numbers activated after batch was created (memory efficient)"""
        return (
            self.db.query(func.count(QRActivationParameters.serial_number))
            .filter(
                QRActivationParameters.qr_settings.is_(False),
                QRActivationParameters.dispatch_batch == batch,
                QRActivationParameters.organization_id == organization_id,
                QRActivationParameters.created_at >= created_after,
            )
            .scalar() or 0
        )

    # def get_by_serial(self, serial_number: str,organization_id: UUID) -> QRActivationParameters | None:
    #     return (
    #         self.db.query(QRActivationParameters)
    #         .filter(QRActivationParameters.serial_number == serial_number
    #         , QRActivationParameters.organization_id == organization_id)
    #         .with_for_update()
    #         .first()
    #     )

    def get_by_serials(self, serials: list[str], organization_id: UUID):
        return (
            self.db.query(QRActivationParameters)
            .filter(
                QRActivationParameters.serial_number.in_(serials),
                QRActivationParameters.organization_id == organization_id,
            )
            .all()
        )

    
    
    def create_settings(self, data: dict) -> QRActivationParameters:
        instance = QRActivationParameters(**data)
        self.db.add(instance)
        self.db.commit()
        self.db.refresh(instance)
        
        return instance

    def archive_and_create(
        self, existing: QRActivationParameters, new_data: dict
    ) -> QRActivationParameters:
        """Archive old settings and create new ones"""
        existing.history = True
        self.db.flush()

        new_instance = QRActivationParameters(**new_data)
        self.db.add(new_instance)
        self.db.commit()
        self.db.refresh(new_instance)
        return new_instance


class ProductItemRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_serial(self, serial_number: str,organization_id: UUID) -> ProductItem | None:
        return (
            self.db.query(ProductItem)
            .filter(
                ProductItem.serial_number == serial_number,
                ProductItem.organization_id == organization_id,
                ProductItem.deleted_at.is_(None),
            )
            .first()
        )
    
    def get_by_serials(self, serials: list[str], organization_id: UUID):
        return (
            self.db.query(ProductItem)
            .filter(
                ProductItem.serial_number.in_(serials),
                ProductItem.organization_id == organization_id,
                ProductItem.deleted_at.is_(None),
            )
            .all()
        )

    def count_inactive_by_product(self, product_id: UUID,organization_id: UUID) -> int:
        """Count items that are not yet activated (qr_deactive or qr_deactive_unit)"""
        from sqlalchemy import or_
        return (
            self.db.query(func.count(ProductItem.id))
            .filter(
                ProductItem.product_id == product_id,
                ProductItem.organization_id == organization_id,
                ProductItem.deleted_at.is_(None),
                or_(
                    ProductItem.qr_deactive_unit.is_(True),
                    ProductItem.qr_deactive.is_(True),
                ),
            )
            .scalar() or 0
        )

    def update_qr_status(self, item: ProductItem) -> None:
        """Mark item as activated"""
        item.qr_deactive = False
        item.qr_deactive_unit = False
        item.qr_active = True
        self.db.flush()
