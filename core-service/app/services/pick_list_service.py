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
        # Auto-generate pick_list_no if not provided
        if not payload.get("pick_list_no"):
            from app.services.document_numbering_service import DocumentNumberingService
            payload["pick_list_no"] = DocumentNumberingService(self.db).get_next_number(
                organization_id, "pick_list"
            )
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
        return self._to_response_enriched(pl)

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

    def _to_response_enriched(self, pl) -> dict:
        """Enhanced response with item, warehouse, and reference details"""
        from app.models.item import Item
        from app.models.warehouse import Warehouse
        from app.models.sales_order import SalesOrder
        
        # Get warehouse details for the pick list
        warehouse = None
        if pl.warehouse_id:
            warehouse = self.db.query(Warehouse).filter(
                Warehouse.id == pl.warehouse_id
            ).first()
        
        # Get reference details (sales order)
        reference = None
        if pl.reference_type == "sales_order" and pl.reference_id:
            so = self.db.query(SalesOrder).filter(
                SalesOrder.id == pl.reference_id
            ).first()
            if so:
                reference = {
                    "id": str(so.id),
                    "reference_type": "sales_order",
                    "name": so.sales_order_no,
                    "code": so.sales_order_no,
                }
        
        # Build enriched items with item and warehouse details
        enriched_items = []
        for item in pl.items:
            # Get item details
            item_obj = self.db.query(Item).filter(Item.id == item.item_id).first()
            
            # Get warehouse details for this item
            item_warehouse = self.db.query(Warehouse).filter(
                Warehouse.id == item.warehouse_id
            ).first()
            
            enriched_item = {
                "id": item.id,
                "organization_id": item.organization_id,
                "item": {
                    "id": str(item_obj.id),
                    "name": item_obj.item_name,
                    "code": item_obj.item_code,
                } if item_obj else None,
                "warehouse": {
                    "id": str(item_warehouse.id),
                    "name": item_warehouse.name,
                    "code": item_warehouse.code,
                } if item_warehouse else None,
                "qty": item.qty,
                "picked_qty": item.picked_qty,
                "uom": item.uom,
                "batch_no": item.batch_no,
                "sort_order": item.sort_order,
                "created_at": item.created_at,
            }
            enriched_items.append(enriched_item)
        
        return {
            "id": pl.id,
            "organization_id": pl.organization_id,
            "pick_list_no": pl.pick_list_no,
            "warehouse_id": pl.warehouse_id,
            "warehouse": {
                "id": str(warehouse.id),
                "name": warehouse.name,
                "code": warehouse.code,
            } if warehouse else None,
            "status": pl.status.value if pl.status else None,
            "pick_date": pl.pick_date,
            "reference_type": pl.reference_type,
            "reference_id": pl.reference_id,
            "reference": reference,
            "remarks": pl.remarks,
            "completed_at": pl.completed_at,
            "created_by": pl.created_by,
            "updated_by": pl.updated_by,
            "created_at": pl.created_at,
            "updated_at": pl.updated_at,
            "items": enriched_items,
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
