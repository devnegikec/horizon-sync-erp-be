"""Invoice service"""

from uuid import UUID

from sqlalchemy.orm import Session

from app.core.exceptions import ResourceNotFoundException
from app.models.base import InvoiceStatus, InvoiceType
from app.repositories.invoice_repository import InvoiceRepository


class InvoiceService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = InvoiceRepository(db)

    def create(self, data: dict, organization_id: UUID, user_id: UUID) -> dict:
        payload = dict(data)
        payload["organization_id"] = organization_id
        payload["created_by"] = user_id
        payload["updated_by"] = user_id
        if payload.get("invoice_type"):
            payload["invoice_type"] = InvoiceType(payload["invoice_type"])
        if payload.get("status"):
            payload["status"] = InvoiceStatus(payload["status"])
        inv = self.repo.create(payload)
        return self._to_response(inv)

    def get_by_id(self, invoice_id: UUID, organization_id: UUID) -> dict:
        inv = self.repo.get_by_id(invoice_id, organization_id)
        if not inv:
            raise ResourceNotFoundException(f"Invoice {invoice_id} not found")
        return self._to_response(inv)

    def get_list(
        self,
        organization_id: UUID,
        page: int = 1,
        page_size: int = 20,
        party_id: UUID | None = None,
        status: str | None = None,
        invoice_type: str | None = None,
        sort_by: str = "posting_date",
        sort_order: str = "desc",
    ) -> tuple[list[dict], dict]:
        items, total = self.repo.list_invoices(
            organization_id=organization_id,
            page=page,
            page_size=page_size,
            party_id=party_id,
            status=status,
            invoice_type=invoice_type,
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
        self, invoice_id: UUID, data: dict, organization_id: UUID, user_id: UUID
    ) -> dict:
        inv = self.repo.get_by_id(invoice_id, organization_id)
        if not inv:
            raise ResourceNotFoundException(f"Invoice {invoice_id} not found")
        payload = {k: v for k, v in data.items() if v is not None}
        if payload.get("status"):
            payload["status"] = InvoiceStatus(payload["status"])
        payload["updated_by"] = user_id
        self.repo.update(inv, payload)
        self.db.refresh(inv)
        return self._to_response(inv)

    def delete(self, invoice_id: UUID, organization_id: UUID) -> None:
        inv = self.repo.get_by_id(invoice_id, organization_id)
        if not inv:
            raise ResourceNotFoundException(f"Invoice {invoice_id} not found")
        self.repo.delete(inv)

    @staticmethod
    def _to_response(inv) -> dict:
        return {
            "id": inv.id,
            "organization_id": inv.organization_id,
            "invoice_no": inv.invoice_no,
            "invoice_type": inv.invoice_type.value if inv.invoice_type else None,
            "party_id": inv.party_id,
            "party_type": inv.party_type,
            "posting_date": inv.posting_date,
            "due_date": inv.due_date,
            "status": inv.status.value if inv.status else None,
            "grand_total": inv.grand_total,
            "outstanding_amount": inv.outstanding_amount,
            "currency": inv.currency,
            "reference_type": inv.reference_type,
            "reference_id": inv.reference_id,
            "remarks": inv.remarks,
            "submitted_at": inv.submitted_at,
            "created_by": inv.created_by,
            "updated_by": inv.updated_by,
            "created_at": inv.created_at,
            "updated_at": inv.updated_at,
        }

    @staticmethod
    def _to_list_item(inv) -> dict:
        return {
            "id": inv.id,
            "organization_id": inv.organization_id,
            "invoice_no": inv.invoice_no,
            "invoice_type": inv.invoice_type.value if inv.invoice_type else None,
            "party_id": inv.party_id,
            "status": inv.status.value if inv.status else None,
            "posting_date": inv.posting_date,
            "grand_total": inv.grand_total,
            "created_at": inv.created_at,
        }
