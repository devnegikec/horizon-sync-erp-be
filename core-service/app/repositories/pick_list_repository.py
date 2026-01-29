"""Pick list repository"""

from uuid import UUID

from sqlalchemy.orm import Session

from app.models.pick_list import PickList, PickListItem


class PickListRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(self, data: dict, items: list[dict]) -> PickList:
        pl = PickList(**data)
        self.db.add(pl)
        self.db.flush()
        for it in items:
            it["pick_list_id"] = pl.id
            it["organization_id"] = pl.organization_id
            self.db.add(PickListItem(**it))
        self.db.commit()
        self.db.refresh(pl)
        return pl

    def get_by_id(
        self, pick_list_id: UUID, organization_id: UUID, load_items: bool = True
    ) -> PickList | None:
        q = self.db.query(PickList).filter(
            PickList.id == pick_list_id,
            PickList.organization_id == organization_id,
        )
        pl = q.first()
        if pl and load_items:
            _ = pl.items
        return pl

    def get_by_no(self, pick_list_no: str, organization_id: UUID) -> PickList | None:
        return (
            self.db.query(PickList)
            .filter(
                PickList.pick_list_no == pick_list_no,
                PickList.organization_id == organization_id,
            )
            .first()
        )

    def list_pick_lists(
        self,
        organization_id: UUID,
        page: int = 1,
        page_size: int = 20,
        warehouse_id: UUID | None = None,
        status: str | None = None,
        sort_by: str = "created_at",
        sort_order: str = "desc",
    ) -> tuple[list[PickList], int]:
        q = self.db.query(PickList).filter(PickList.organization_id == organization_id)
        if warehouse_id is not None:
            q = q.filter(PickList.warehouse_id == warehouse_id)
        if status is not None:
            q = q.filter(PickList.status == status)
        total = q.count()
        col = getattr(PickList, sort_by, PickList.created_at)
        q = q.order_by(col.desc() if sort_order == "desc" else col.asc())
        items = q.offset((page - 1) * page_size).limit(page_size).all()
        return items, total

    def update(self, pl: PickList, data: dict) -> PickList:
        for k, v in data.items():
            if hasattr(pl, k):
                setattr(pl, k, v)
        self.db.commit()
        self.db.refresh(pl)
        return pl

    def delete(self, pl: PickList) -> None:
        self.db.delete(pl)
        self.db.commit()
