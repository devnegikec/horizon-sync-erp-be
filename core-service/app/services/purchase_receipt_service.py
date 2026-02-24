"""Purchase receipt service"""

from uuid import UUID

from sqlalchemy.orm import Session

from app.core.exceptions import ResourceNotFoundException
from app.models.base import DocumentStatus
from app.repositories.purchase_receipt_repository import PurchaseReceiptRepository


class PurchaseReceiptService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = PurchaseReceiptRepository(db)

    def create(self, data: dict, organization_id: UUID, user_id: UUID) -> dict:
        payload = {k: v for k, v in data.items() if k != "items"}
        payload["organization_id"] = organization_id
        payload["created_by"] = user_id
        payload["updated_by"] = user_id
        # Auto-generate purchase_receipt_no if not provided
        if not payload.get("purchase_receipt_no"):
            from app.services.document_numbering_service import DocumentNumberingService
            payload["purchase_receipt_no"] = DocumentNumberingService(self.db).get_next_number(
                organization_id, "purchase_receipt"
            )
        if payload.get("status"):
            payload["status"] = DocumentStatus(payload["status"])
        items = data.get("items") or []
        pr = self.repo.create(payload, [dict(it) for it in items])
        return self._to_response(pr)

    def get_by_id(self, purchase_receipt_id: UUID, organization_id: UUID) -> dict:
        pr = self.repo.get_by_id(purchase_receipt_id, organization_id)
        if not pr:
            raise ResourceNotFoundException(
                f"Purchase receipt {purchase_receipt_id} not found"
            )
        return self._to_response(pr)

    def get_list(
        self,
        organization_id: UUID,
        page: int = 1,
        page_size: int = 20,
        supplier_id: UUID | None = None,
        status: str | None = None,
        sort_by: str = "receipt_date",
        sort_order: str = "desc",
    ) -> tuple[list[dict], dict]:
        items, total = self.repo.list_purchase_receipts(
            organization_id=organization_id,
            page=page,
            page_size=page_size,
            supplier_id=supplier_id,
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
        self,
        purchase_receipt_id: UUID,
        data: dict,
        organization_id: UUID,
        user_id: UUID,
    ) -> dict:
        pr = self.repo.get_by_id(purchase_receipt_id, organization_id)
        if not pr:
            raise ResourceNotFoundException(
                f"Purchase receipt {purchase_receipt_id} not found"
            )
        payload = {k: v for k, v in data.items() if v is not None}
        if payload.get("status"):
            payload["status"] = DocumentStatus(payload["status"])
        payload["updated_by"] = user_id
        self.repo.update(pr, payload)
        self.db.refresh(pr)
        return self._to_response(pr)

    def delete(self, purchase_receipt_id: UUID, organization_id: UUID) -> None:
        pr = self.repo.get_by_id(purchase_receipt_id, organization_id)
        if not pr:
            raise ResourceNotFoundException(
                f"Purchase receipt {purchase_receipt_id} not found"
            )
        self.repo.delete(pr)

    @staticmethod
    def _to_response(pr) -> dict:
        return {
            "id": pr.id,
            "organization_id": pr.organization_id,
            "purchase_receipt_no": pr.purchase_receipt_no,
            "supplier_id": pr.supplier_id,
            "receipt_date": pr.receipt_date,
            "status": pr.status.value if pr.status else None,
            "warehouse_id": pr.warehouse_id,
            "reference_type": pr.reference_type,
            "reference_id": pr.reference_id,
            "remarks": pr.remarks,
            "submitted_at": pr.submitted_at,
            "created_by": pr.created_by,
            "updated_by": pr.updated_by,
            "created_at": pr.created_at,
            "updated_at": pr.updated_at,
        }

    @staticmethod
    def _to_list_item(pr) -> dict:
        return {
            "id": pr.id,
            "organization_id": pr.organization_id,
            "purchase_receipt_no": pr.purchase_receipt_no,
            "supplier_id": pr.supplier_id,
            "status": pr.status.value if pr.status else None,
            "receipt_date": pr.receipt_date,
            "created_at": pr.created_at,
        }
