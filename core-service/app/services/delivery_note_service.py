"""Delivery note service"""

from uuid import UUID

from sqlalchemy.orm import Session

from app.core.exceptions import ResourceNotFoundException
from app.models.base import DocumentStatus
from app.repositories.delivery_note_repository import DeliveryNoteRepository


class DeliveryNoteService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = DeliveryNoteRepository(db)

    def create(self, data: dict, organization_id: UUID, user_id: UUID) -> dict:
        payload = {k: v for k, v in data.items() if k != "items"}
        payload["organization_id"] = organization_id
        payload["created_by"] = user_id
        payload["updated_by"] = user_id
        if payload.get("status"):
            payload["status"] = DocumentStatus(payload["status"])
        items = data.get("items") or []
        dn = self.repo.create(payload, [dict(it) for it in items])
        return self._to_response(dn)

    def get_by_id(self, delivery_note_id: UUID, organization_id: UUID) -> dict:
        dn = self.repo.get_by_id(delivery_note_id, organization_id)
        if not dn:
            raise ResourceNotFoundException(
                f"Delivery note {delivery_note_id} not found"
            )
        return self._to_response(dn)

    def get_list(
        self,
        organization_id: UUID,
        page: int = 1,
        page_size: int = 20,
        customer_id: UUID | None = None,
        status: str | None = None,
        sort_by: str = "delivery_date",
        sort_order: str = "desc",
    ) -> tuple[list[dict], dict]:
        items, total = self.repo.list_delivery_notes(
            organization_id=organization_id,
            page=page,
            page_size=page_size,
            customer_id=customer_id,
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
        self, delivery_note_id: UUID, data: dict, organization_id: UUID, user_id: UUID
    ) -> dict:
        dn = self.repo.get_by_id(delivery_note_id, organization_id)
        if not dn:
            raise ResourceNotFoundException(
                f"Delivery note {delivery_note_id} not found"
            )
        payload = {k: v for k, v in data.items() if v is not None}
        if payload.get("status"):
            payload["status"] = DocumentStatus(payload["status"])
        payload["updated_by"] = user_id
        self.repo.update(dn, payload)
        self.db.refresh(dn)
        return self._to_response(dn)

    def delete(self, delivery_note_id: UUID, organization_id: UUID) -> None:
        dn = self.repo.get_by_id(delivery_note_id, organization_id)
        if not dn:
            raise ResourceNotFoundException(
                f"Delivery note {delivery_note_id} not found"
            )
        self.repo.delete(dn)

    @staticmethod
    def _to_response(dn) -> dict:
        # Get customer data
        customer_data = None
        if dn.customer:
            customer_data = {
                "customer_name": dn.customer.customer_name,
                "customer_code": dn.customer.customer_code,
                "phone": dn.customer.phone,
                "email": dn.customer.email,
            }

        # Get warehouse data
        warehouse_data = None
        if dn.warehouse:
            warehouse_data = {
                "warehouse_name": dn.warehouse.name,
                "warehouse_code": dn.warehouse.code,
            }

        # Get items data
        items_data = []
        if hasattr(dn, "items") and dn.items:
            for item in dn.items:
                items_data.append(
                    {
                        "id": item.id,
                        "item_id": item.item_id,
                        "qty": item.qty,
                        "uom": item.uom,
                        "rate": item.rate,
                        "amount": item.amount,
                        "warehouse_id": item.warehouse_id,
                        "batch_no": item.batch_no,
                        "serial_nos": item.serial_nos,
                        "sort_order": item.sort_order,
                        "extra_data": item.extra_data,
                    }
                )

        return {
            "id": dn.id,
            "organization_id": dn.organization_id,
            "delivery_note_no": dn.delivery_note_no,
            "customer_id": dn.customer_id,
            "customer": customer_data,
            "delivery_date": dn.delivery_date,
            "status": dn.status.value if dn.status else None,
            "warehouse_id": dn.warehouse_id,
            "warehouse": warehouse_data,
            "pick_list_id": dn.pick_list_id,
            "reference_type": dn.reference_type,
            "reference_id": dn.reference_id,
            "remarks": dn.remarks,
            "extra_data": dn.extra_data,
            "items": items_data,
            "submitted_at": dn.submitted_at,
            "created_by": dn.created_by,
            "updated_by": dn.updated_by,
            "created_at": dn.created_at,
            "updated_at": dn.updated_at,
        }

    @staticmethod
    def _to_list_item(dn) -> dict:
        # Get customer data
        customer_data = None
        if dn.customer:
            customer_data = {
                "customer_name": dn.customer.customer_name,
                "customer_code": dn.customer.customer_code,
                "phone": dn.customer.phone,
                "email": dn.customer.email,
            }

        # Get warehouse data
        warehouse_data = None
        if dn.warehouse:
            warehouse_data = {
                "warehouse_name": dn.warehouse.name,
                "warehouse_code": dn.warehouse.code,
            }

        return {
            "id": dn.id,
            "organization_id": dn.organization_id,
            "delivery_note_no": dn.delivery_note_no,
            "customer_id": dn.customer_id,
            "customer": customer_data,
            "status": dn.status.value if dn.status else None,
            "delivery_date": dn.delivery_date,
            "warehouse_id": dn.warehouse_id,
            "warehouse": warehouse_data,
            "remarks": dn.remarks,
            "created_at": dn.created_at,
        }
