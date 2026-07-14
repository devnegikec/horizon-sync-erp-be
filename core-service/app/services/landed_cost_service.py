"""Landed cost voucher service"""

from uuid import UUID

from sqlalchemy.orm import Session

from app.core.exceptions import ResourceNotFoundException
from app.models.base import DocumentStatus
from app.repositories.landed_cost_repository import LandedCostRepository


class LandedCostService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = LandedCostRepository(db)

    def create(self, data: dict, organization_id: UUID, user_id: UUID) -> dict:
        payload = dict(data)
        payload["organization_id"] = organization_id
        payload["created_by"] = user_id
        payload["updated_by"] = user_id
        if payload.get("status"):
            payload["status"] = DocumentStatus(payload["status"])
        lc = self.repo.create(payload)
        return self._to_response(lc)

    def get_by_id(self, voucher_id: UUID, organization_id: UUID) -> dict:
        lc = self.repo.get_by_id(voucher_id, organization_id)
        if not lc:
            raise ResourceNotFoundException(
                f"Landed cost voucher {voucher_id} not found"
            )
        return self._to_response(lc)

    def get_list(
        self,
        organization_id: UUID,
        page: int = 1,
        page_size: int = 20,
        status: str | None = None,
        sort_by: str = "posting_date",
        sort_order: str = "desc",
    ) -> tuple[list[dict], dict]:
        items, total = self.repo.list_vouchers(
            organization_id=organization_id,
            page=page,
            page_size=page_size,
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
        self, voucher_id: UUID, data: dict, organization_id: UUID, user_id: UUID
    ) -> dict:
        lc = self.repo.get_by_id(voucher_id, organization_id)
        if not lc:
            raise ResourceNotFoundException(
                f"Landed cost voucher {voucher_id} not found"
            )
        payload = {k: v for k, v in data.items() if v is not None}
        if payload.get("status"):
            payload["status"] = DocumentStatus(payload["status"])
        payload["updated_by"] = user_id
        self.repo.update(lc, payload)
        self.db.refresh(lc)
        return self._to_response(lc)

    def delete(self, voucher_id: UUID, organization_id: UUID) -> None:
        lc = self.repo.get_by_id(voucher_id, organization_id)
        if not lc:
            raise ResourceNotFoundException(
                f"Landed cost voucher {voucher_id} not found"
            )
        self.repo.delete(lc)

    @staticmethod
    def _to_response(lc) -> dict:
        return {
            "id": lc.id,
            "organization_id": lc.organization_id,
            "voucher_no": lc.voucher_no,
            "posting_date": lc.posting_date,
            "status": lc.status.value if lc.status else None,
            "remarks": lc.remarks,
            "submitted_at": lc.submitted_at,
            "created_by": lc.created_by,
            "updated_by": lc.updated_by,
            "created_at": lc.created_at,
            "updated_at": lc.updated_at,
        }

    @staticmethod
    def _to_list_item(lc) -> dict:
        return {
            "id": lc.id,
            "organization_id": lc.organization_id,
            "voucher_no": lc.voucher_no,
            "status": lc.status.value if lc.status else None,
            "posting_date": lc.posting_date,
            "created_at": lc.created_at,
        }
