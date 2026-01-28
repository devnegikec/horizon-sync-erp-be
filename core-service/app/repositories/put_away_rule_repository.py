"""Put away rule repository"""

from uuid import UUID

from sqlalchemy.orm import Session

from app.models.put_away_rule import PutAwayRule


class PutAwayRuleRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(self, data: dict) -> PutAwayRule:
        r = PutAwayRule(**data)
        self.db.add(r)
        self.db.commit()
        self.db.refresh(r)
        return r

    def get_by_id(self, rule_id: UUID, organization_id: UUID) -> PutAwayRule | None:
        return (
            self.db.query(PutAwayRule)
            .filter(
                PutAwayRule.id == rule_id,
                PutAwayRule.organization_id == organization_id,
            )
            .first()
        )

    def update(self, r: PutAwayRule, data: dict) -> PutAwayRule:
        for k, v in data.items():
            if hasattr(r, k) and v is not None:
                setattr(r, k, v)
        self.db.commit()
        self.db.refresh(r)
        return r

    def delete(self, r: PutAwayRule) -> None:
        self.db.delete(r)
        self.db.commit()

    def list_rules(
        self,
        organization_id: UUID,
        warehouse_id: UUID | None = None,
        item_id: UUID | None = None,
        item_group_id: UUID | None = None,
        is_active: bool | None = None,
        search: str | None = None,
        page: int = 1,
        page_size: int = 20,
        sort_by: str = "priority",
        sort_order: str = "asc",
    ) -> tuple[list[PutAwayRule], int]:
        q = self.db.query(PutAwayRule).filter(
            PutAwayRule.organization_id == organization_id
        )
        if warehouse_id:
            q = q.filter(PutAwayRule.warehouse_id == warehouse_id)
        if item_id:
            q = q.filter(PutAwayRule.item_id == item_id)
        if item_group_id:
            q = q.filter(PutAwayRule.item_group_id == item_group_id)
        if is_active is not None:
            q = q.filter(PutAwayRule.is_active == is_active)
        if search:
            t = f"%{search}%"
            q = q.filter(PutAwayRule.name.ilike(t))
        total = q.count()
        col = getattr(PutAwayRule, sort_by, PutAwayRule.priority)
        q = q.order_by(col.asc() if sort_order == "asc" else col.desc())
        items = q.offset((page - 1) * page_size).limit(page_size).all()
        return items, total
