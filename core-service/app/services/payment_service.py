"""Payment service"""

from uuid import UUID

from sqlalchemy.orm import Session

from app.core.exceptions import ResourceNotFoundException
from app.models.base import PaymentMethod, PaymentStatus, PaymentType
from app.repositories.payment_repository import PaymentRepository


class PaymentService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = PaymentRepository(db)

    def create(self, data: dict, organization_id: UUID, user_id: UUID) -> dict:
        payload = dict(data)
        payload["organization_id"] = organization_id
        payload["created_by"] = user_id
        payload["updated_by"] = user_id
        if payload.get("payment_type"):
            payload["payment_type"] = PaymentType(payload["payment_type"])
        if payload.get("status"):
            payload["status"] = PaymentStatus(payload["status"])
        if payload.get("payment_method"):
            payload["payment_method"] = PaymentMethod(payload["payment_method"])
        p = self.repo.create(payload)
        return self._to_response(p)

    def get_by_id(self, payment_id: UUID, organization_id: UUID) -> dict:
        p = self.repo.get_by_id(payment_id, organization_id)
        if not p:
            raise ResourceNotFoundException(f"Payment {payment_id} not found")
        return self._to_response(p)

    def get_list(
        self,
        organization_id: UUID,
        page: int = 1,
        page_size: int = 20,
        party_id: UUID | None = None,
        status: str | None = None,
        payment_type: str | None = None,
        sort_by: str = "posting_date",
        sort_order: str = "desc",
    ) -> tuple[list[dict], dict]:
        items, total = self.repo.list_payments(
            organization_id=organization_id,
            page=page,
            page_size=page_size,
            party_id=party_id,
            status=status,
            payment_type=payment_type,
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
        self, payment_id: UUID, data: dict, organization_id: UUID, user_id: UUID
    ) -> dict:
        p = self.repo.get_by_id(payment_id, organization_id)
        if not p:
            raise ResourceNotFoundException(f"Payment {payment_id} not found")
        payload = {k: v for k, v in data.items() if v is not None}
        if payload.get("status"):
            payload["status"] = PaymentStatus(payload["status"])
        payload["updated_by"] = user_id
        self.repo.update(p, payload)
        self.db.refresh(p)
        return self._to_response(p)

    def delete(self, payment_id: UUID, organization_id: UUID) -> None:
        p = self.repo.get_by_id(payment_id, organization_id)
        if not p:
            raise ResourceNotFoundException(f"Payment {payment_id} not found")
        self.repo.delete(p)

    @staticmethod
    def _to_response(p) -> dict:
        return {
            "id": p.id,
            "organization_id": p.organization_id,
            "payment_no": p.payment_no,
            "payment_type": p.payment_type.value if p.payment_type else None,
            "party_id": p.party_id,
            "party_type": p.party_type,
            "posting_date": p.posting_date,
            "amount": p.amount,
            "status": p.status.value if p.status else None,
            "payment_method": p.payment_method.value if p.payment_method else None,
            "reference_no": p.reference_no,
            "remarks": p.remarks,
            "created_by": p.created_by,
            "updated_by": p.updated_by,
            "created_at": p.created_at,
            "updated_at": p.updated_at,
        }

    @staticmethod
    def _to_list_item(p) -> dict:
        return {
            "id": p.id,
            "organization_id": p.organization_id,
            "payment_no": p.payment_no,
            "payment_type": p.payment_type.value if p.payment_type else None,
            "party_id": p.party_id,
            "status": p.status.value if p.status else None,
            "amount": p.amount,
            "posting_date": p.posting_date,
            "created_at": p.created_at,
        }
