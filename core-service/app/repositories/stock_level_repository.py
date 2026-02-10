"""Stock level repository"""

from uuid import UUID

from sqlalchemy.orm import Session, joinedload

from app.models.stock_level import StockLevel


class StockLevelRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, level_id: UUID, organization_id: UUID) -> StockLevel | None:
        return (
            self.db.query(StockLevel)
            .options(
                joinedload(StockLevel.product),
                joinedload(StockLevel.warehouse),
            )
            .filter(
                StockLevel.id == level_id,
                StockLevel.organization_id == organization_id,
            )
            .first()
        )

    def get_by_product_warehouse(
        self, product_id: UUID, warehouse_id: UUID, organization_id: UUID
    ) -> StockLevel | None:
        return (
            self.db.query(StockLevel)
            .options(
                joinedload(StockLevel.product),
                joinedload(StockLevel.warehouse),
            )
            .filter(
                StockLevel.product_id == product_id,
                StockLevel.warehouse_id == warehouse_id,
                StockLevel.organization_id == organization_id,
            )
            .first()
        )

    def create(self, data: dict) -> StockLevel:
        s = StockLevel(**data)
        self.db.add(s)
        self.db.commit()
        self.db.refresh(s)
        return self.get_by_id(s.id, s.organization_id)

    def update(self, s: StockLevel, data: dict) -> StockLevel:
        for k, v in data.items():
            if hasattr(s, k) and v is not None:
                setattr(s, k, v)
        self.db.commit()
        self.db.refresh(s)
        return self.get_by_id(s.id, s.organization_id)

    def list_levels(
        self,
        organization_id: UUID,
        product_id: UUID | None = None,
        warehouse_id: UUID | None = None,
        page: int = 1,
        page_size: int = 20,
        sort_by: str = "updated_at",
        sort_order: str = "desc",
    ) -> tuple[list[StockLevel], int]:
        q = (
            self.db.query(StockLevel)
            .options(
                joinedload(StockLevel.product),
                joinedload(StockLevel.warehouse),
            )
            .filter(StockLevel.organization_id == organization_id)
        )
        if product_id:
            q = q.filter(StockLevel.product_id == product_id)
        if warehouse_id:
            q = q.filter(StockLevel.warehouse_id == warehouse_id)
        total = q.count()
        col = getattr(StockLevel, sort_by, StockLevel.updated_at)
        q = q.order_by(col.desc() if sort_order == "desc" else col.asc())
        items = q.offset((page - 1) * page_size).limit(page_size).all()
        return items, total
