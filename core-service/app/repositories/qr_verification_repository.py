"""Database operations for public QR verification."""

from uuid import UUID

from sqlalchemy.orm import Session

from app.models.product_item import ProductItem


class QRVerificationRepository:
    def __init__(self, db: Session):
        self.db = db

    def resolve_active_item_identity(
        self,
        serial_number: str,
    ) -> tuple[UUID, UUID] | None:
        """Resolve the public global serial into only item and organization IDs."""
        rows = (
            self.db.query(ProductItem.id, ProductItem.organization_id)
            .filter(
                ProductItem.serial_number == serial_number,
                ProductItem.deleted_at.is_(None),
            )
            .limit(2)
            .all()
        )
        if len(rows) != 1:
            return None
        return rows[0][0], rows[0][1]

    def get_tenant_item_for_update(
        self,
        item_id: UUID,
        serial_number: str,
        organization_id: UUID,
    ) -> ProductItem | None:
        """Lock one resolved item while enforcing its organization boundary."""
        return (
            self.db.query(ProductItem)
            .filter(
                ProductItem.id == item_id,
                ProductItem.serial_number == serial_number,
                ProductItem.organization_id == organization_id,
                ProductItem.deleted_at.is_(None),
            )
            .with_for_update()
            .first()
        )
