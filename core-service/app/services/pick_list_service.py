"""Pick list service"""

from uuid import UUID

from sqlalchemy.orm import Session

from app.core.exceptions import ResourceNotFoundException
from app.models.base import PickListStatus
from app.repositories.pick_list_repository import PickListRepository


class PickListService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = PickListRepository(db)

    def create(self, data: dict, organization_id: UUID, user_id: UUID) -> dict:
        payload = {k: v for k, v in data.items() if k != "items"}
        payload["organization_id"] = organization_id
        payload["created_by"] = user_id
        payload["updated_by"] = user_id
        if payload.get("status"):
            payload["status"] = PickListStatus(payload["status"])
        items = data.get("items") or []
        item_list = [dict(it) for it in items]
        pl = self.repo.create(payload, item_list)
        return self._to_response(pl)

    def get_by_id(self, pick_list_id: UUID, organization_id: UUID) -> dict:
        pl = self.repo.get_by_id(pick_list_id, organization_id)
        if not pl:
            raise ResourceNotFoundException(f"Pick list {pick_list_id} not found")
        return self._to_response(pl)

    def get_list(
        self,
        organization_id: UUID,
        page: int = 1,
        page_size: int = 20,
        warehouse_id: UUID | None = None,
        status: str | None = None,
        sort_by: str = "created_at",
        sort_order: str = "desc",
    ) -> tuple[list[dict], dict]:
        items, total = self.repo.list_pick_lists(
            organization_id=organization_id,
            page=page,
            page_size=page_size,
            warehouse_id=warehouse_id,
            status=status,
            sort_by=sort_by,
            sort_order=sort_order,
        )
        total_pages = (total + page_size - 1) // page_size if page_size else 0
        pagination = {
            "page": page,
            "page_size": page_size,
            "total_items": total,
            "total_pages": total_pages,
            "has_next": page < total_pages,
            "has_prev": page > 1,
        }
        return [self._to_list_item(x) for x in items], pagination

    def update(
        self, pick_list_id: UUID, data: dict, organization_id: UUID, user_id: UUID
    ) -> dict:
        pl = self.repo.get_by_id(pick_list_id, organization_id)
        if not pl:
            raise ResourceNotFoundException(f"Pick list {pick_list_id} not found")
        payload = {k: v for k, v in data.items() if v is not None}
        if payload.get("status"):
            payload["status"] = PickListStatus(payload["status"])
        payload["updated_by"] = user_id
        self.repo.update(pl, payload)
        self.db.refresh(pl)
        return self._to_response(pl)

    def delete(self, pick_list_id: UUID, organization_id: UUID) -> None:
        pl = self.repo.get_by_id(pick_list_id, organization_id)
        if not pl:
            raise ResourceNotFoundException(f"Pick list {pick_list_id} not found")
        self.repo.delete(pl)

    @staticmethod
    def _to_response(pl) -> dict:
        return {
            "id": pl.id,
            "organization_id": pl.organization_id,
            "pick_list_no": pl.pick_list_no,
            "warehouse_id": pl.warehouse_id,
            "status": pl.status.value if pl.status else None,
            "pick_date": pl.pick_date,
            "reference_type": pl.reference_type,
            "reference_id": pl.reference_id,
            "remarks": pl.remarks,
            "completed_at": pl.completed_at,
            "created_by": pl.created_by,
            "updated_by": pl.updated_by,
            "created_at": pl.created_at,
            "updated_at": pl.updated_at,
            "items": [
                {
                    "id": item.id,
                    "organization_id": item.organization_id,
                    "pick_list_id": item.pick_list_id,
                    "item_id": item.item_id,
                    "warehouse_id": item.warehouse_id,
                    "qty": item.qty,
                    "picked_qty": item.picked_qty,
                    "uom": item.uom,
                    "batch_no": item.batch_no,
                    "sort_order": item.sort_order,
                    "created_at": item.created_at,
                }
                for item in pl.items
            ],
        }

    @staticmethod
    def _to_list_item(pl) -> dict:
        return {
            "id": pl.id,
            "organization_id": pl.organization_id,
            "pick_list_no": pl.pick_list_no,
            "warehouse_id": pl.warehouse_id,
            "status": pl.status.value if pl.status else None,
            "pick_date": pl.pick_date,
            "created_at": pl.created_at,
        }
