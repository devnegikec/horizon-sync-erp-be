"""Stock movement repository"""

from uuid import UUID

from sqlalchemy.orm import Session, joinedload

from app.models.base import MovementType
from app.models.stock_movement import StockMovement


class StockMovementRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(self, data: dict) -> StockMovement:
        m = StockMovement(**data)
        self.db.add(m)
        self.db.commit()
        self.db.refresh(m)
        # Eagerly load relationships
        self.db.refresh(m, ["product", "warehouse"])
        return m

    def get_by_id(
        self, movement_id: UUID, organization_id: UUID
    ) -> StockMovement | None:
        return (
            self.db.query(StockMovement)
            .options(
                joinedload(StockMovement.product), joinedload(StockMovement.warehouse)
            )
            .filter(
                StockMovement.id == movement_id,
                StockMovement.organization_id == organization_id,
            )
            .first()
        )

    def list_movements(
        self,
        organization_id: UUID,
        product_id: UUID | None = None,
        warehouse_id: UUID | None = None,
        movement_type: MovementType | None = None,
        reference_type: str | None = None,
        reference_id: UUID | None = None,
        page: int = 1,
        page_size: int = 20,
        sort_by: str = "performed_at",
        sort_order: str = "desc",
    ) -> tuple[list[StockMovement], int]:
        q = (
            self.db.query(StockMovement)
            .options(
                joinedload(StockMovement.product), joinedload(StockMovement.warehouse)
            )
            .filter(StockMovement.organization_id == organization_id)
        )
        if product_id:
            q = q.filter(StockMovement.product_id == product_id)
        if warehouse_id:
            q = q.filter(StockMovement.warehouse_id == warehouse_id)
        if movement_type is not None:
            q = q.filter(StockMovement.movement_type == movement_type)
        if reference_type:
            q = q.filter(StockMovement.reference_type == reference_type)
        if reference_id:
            q = q.filter(StockMovement.reference_id == reference_id)
        total = q.count()
        col = getattr(StockMovement, sort_by, StockMovement.performed_at)
        q = q.order_by(col.desc() if sort_order == "desc" else col.asc())
        items = q.offset((page - 1) * page_size).limit(page_size).all()
        return items, total
