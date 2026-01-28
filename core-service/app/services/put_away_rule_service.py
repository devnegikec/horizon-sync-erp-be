"""Put away rule service"""

from uuid import UUID

from sqlalchemy.orm import Session

from app.core.exceptions import PutAwayRuleNotFoundException
from app.models.put_away_rule import PutAwayRule
from app.repositories.put_away_rule_repository import PutAwayRuleRepository
from app.schemas.put_away_rule import PutAwayRuleCreate, PutAwayRuleUpdate


class PutAwayRuleService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = PutAwayRuleRepository(db)

    def create(
        self, data: PutAwayRuleCreate, organization_id: UUID, user_id: UUID
    ) -> PutAwayRule:
        d = data.model_dump()
        d["organization_id"] = organization_id
        d["created_by"] = user_id
        d["updated_by"] = user_id
        return self.repo.create(d)

    def get_by_id(self, rule_id: UUID, organization_id: UUID) -> PutAwayRule:
        r = self.repo.get_by_id(rule_id, organization_id)
        if not r:
            raise PutAwayRuleNotFoundException(
                f"Put away rule with ID {rule_id} not found"
            )
        return r

    def update(
        self,
        rule_id: UUID,
        data: PutAwayRuleUpdate,
        organization_id: UUID,
        user_id: UUID,
    ) -> PutAwayRule:
        r = self.get_by_id(rule_id, organization_id)
        d = data.model_dump(exclude_unset=True)
        d["updated_by"] = user_id
        return self.repo.update(r, d)

    def delete(self, rule_id: UUID, organization_id: UUID) -> None:
        r = self.get_by_id(rule_id, organization_id)
        self.repo.delete(r)

    def get_list(
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
    ) -> tuple[list[PutAwayRule], dict]:
        page_size = min(page_size, 100)
        items, total = self.repo.list_rules(
            organization_id=organization_id,
            warehouse_id=warehouse_id,
            item_id=item_id,
            item_group_id=item_group_id,
            is_active=is_active,
            search=search,
            page=page,
            page_size=page_size,
            sort_by=sort_by,
            sort_order=sort_order,
        )
        tp = (total + page_size - 1) // page_size
        return items, {
            "page": page,
            "page_size": page_size,
            "total_items": total,
            "total_pages": tp,
            "has_next": page < tp,
            "has_prev": page > 1,
        }
