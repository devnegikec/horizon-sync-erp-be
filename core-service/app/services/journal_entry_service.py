"""Journal entry service"""

from uuid import UUID

from sqlalchemy.orm import Session

from app.core.exceptions import ResourceNotFoundException
from app.models.base import JournalStatus
from app.repositories.journal_entry_repository import JournalEntryRepository


class JournalEntryService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = JournalEntryRepository(db)

    def create(self, data: dict, organization_id: UUID, user_id: UUID) -> dict:
        payload = {k: v for k, v in data.items() if k != "lines"}
        payload["organization_id"] = organization_id
        payload["created_by"] = user_id
        payload["updated_by"] = user_id
        if payload.get("status"):
            payload["status"] = JournalStatus(payload["status"])

        # Generate entry_no if not provided
        if not payload.get("entry_no"):
            from app.services.document_numbering_service import DocumentNumberingService

            doc_num_svc = DocumentNumberingService(self.db)
            payload["entry_no"] = doc_num_svc.get_next_number(
                organization_id,
                "journal_entry",
                reference_date=payload.get("posting_date"),
            )

        lines = data.get("lines") or []
        line_list = [dict(ln) for ln in lines]
        je = self.repo.create(payload, line_list)
        return self._to_response(je)

    def get_by_id(self, entry_id: UUID, organization_id: UUID) -> dict:
        je = self.repo.get_by_id(entry_id, organization_id)
        if not je:
            raise ResourceNotFoundException(f"Journal entry {entry_id} not found")
        return self._to_response(je)

    def get_list(
        self,
        organization_id: UUID,
        page: int = 1,
        page_size: int = 20,
        status: str | None = None,
        sort_by: str = "posting_date",
        sort_order: str = "desc",
    ) -> tuple[list[dict], dict]:
        items, total = self.repo.list_entries(
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
        self, entry_id: UUID, data: dict, organization_id: UUID, user_id: UUID
    ) -> dict:
        je = self.repo.get_by_id(entry_id, organization_id)
        if not je:
            raise ResourceNotFoundException(f"Journal entry {entry_id} not found")
        payload = {k: v for k, v in data.items() if v is not None}
        if payload.get("status"):
            payload["status"] = JournalStatus(payload["status"])
        payload["updated_by"] = user_id
        self.repo.update(je, payload)
        self.db.refresh(je)
        return self._to_response(je)

    def get_by_reference(
        self, reference_type: str, reference_id: UUID, organization_id: UUID
    ) -> dict | None:
        """Get journal entry by reference type and ID"""
        je = self.repo.get_by_reference(reference_type, reference_id, organization_id)
        if not je:
            return None
        return self._to_response(je)

    def delete(self, entry_id: UUID, organization_id: UUID) -> None:
        je = self.repo.get_by_id(entry_id, organization_id)
        if not je:
            raise ResourceNotFoundException(f"Journal entry {entry_id} not found")
        self.repo.delete(je)

    @staticmethod
    def _to_response(je) -> dict:
        return {
            "id": je.id,
            "organization_id": je.organization_id,
            "entry_no": je.entry_no,
            "posting_date": je.posting_date,
            "status": je.status.value if je.status else None,
            "voucher_type": je.voucher_type,
            "reference_type": je.reference_type,
            "reference_id": je.reference_id,
            "total_debit": je.total_debit,
            "total_credit": je.total_credit,
            "remarks": je.remarks,
            "posted_at": je.posted_at,
            "created_by": je.created_by,
            "updated_by": je.updated_by,
            "created_at": je.created_at,
            "updated_at": je.updated_at,
        }

    @staticmethod
    def _to_list_item(je) -> dict:
        lines = []
        if hasattr(je, "lines") and je.lines:
            for line in je.lines:
                line_dict = {
                    "id": line.id,
                    "account_id": line.account_id,
                    "debit": line.debit,
                    "credit": line.credit,
                    "remarks": line.remarks,
                }
                # Add account information if available
                if hasattr(line, "account") and line.account:
                    line_dict["account_code"] = line.account.account_code
                    line_dict["account_name"] = line.account.account_name
                lines.append(line_dict)

        return {
            "id": je.id,
            "organization_id": je.organization_id,
            "entry_no": je.entry_no,
            "status": je.status.value if je.status else None,
            "posting_date": je.posting_date,
            "voucher_type": je.voucher_type,
            "total_debit": je.total_debit,
            "total_credit": je.total_credit,
            "remarks": je.remarks,
            "lines": lines,
            "created_at": je.created_at,
        }
