"""Serial number and history service"""

from uuid import UUID

from sqlalchemy.orm import Session

from app.core.exceptions import DuplicateSerialNoException, SerialNoNotFoundException
from app.models.serial_no import SerialNo, SerialNoHistory
from app.repositories.serial_no_repository import SerialNoRepository
from app.schemas.serial_no import SerialNoCreate, SerialNoHistoryCreate, SerialNoUpdate


class SerialNoService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = SerialNoRepository(db)

    def create(self, data: SerialNoCreate, organization_id: UUID) -> SerialNo:
        if self.repo.get_by_serial_and_item(
            data.serial_no, data.item_id, organization_id
        ):
            raise DuplicateSerialNoException(
                f"Serial number '{data.serial_no}' already exists for this item"
            )
        d = data.model_dump()
        d["organization_id"] = organization_id
        return self.repo.create_serial_no(d)

    def get_by_id(self, serial_no_id: UUID, organization_id: UUID) -> SerialNo:
        s = self.repo.get_by_id(serial_no_id, organization_id)
        if not s:
            raise SerialNoNotFoundException(
                f"Serial number with ID {serial_no_id} not found"
            )
        return s

    def update(
        self, serial_no_id: UUID, data: SerialNoUpdate, organization_id: UUID
    ) -> SerialNo:
        s = self.get_by_id(serial_no_id, organization_id)
        return self.repo.update(s, data.model_dump(exclude_unset=True))

    def delete(self, serial_no_id: UUID, organization_id: UUID) -> None:
        s = self.get_by_id(serial_no_id, organization_id)
        self.repo.delete(s)

    def get_list(
        self,
        organization_id: UUID,
        item_id: UUID | None = None,
        warehouse_id: UUID | None = None,
        search: str | None = None,
        page: int = 1,
        page_size: int = 20,
        sort_by: str = "created_at",
        sort_order: str = "desc",
    ) -> tuple[list[SerialNo], dict]:
        page_size = min(page_size, 100)
        items, total = self.repo.list_serial_nos(
            organization_id=organization_id,
            item_id=item_id,
            warehouse_id=warehouse_id,
            search=search,
            page=page,
            page_size=page_size,
            sort_by=sort_by,
            sort_order=sort_order,
        )
        tp = (total + page_size - 1) // page_size
        pagination = {
            "page": page,
            "page_size": page_size,
            "total_items": total,
            "total_pages": tp,
            "has_next": page < tp,
            "has_prev": page > 1,
        }
        return items, pagination

    def list_history(
        self, serial_no_id: UUID, organization_id: UUID, limit: int = 100
    ) -> list[SerialNoHistory]:
        self.get_by_id(serial_no_id, organization_id)
        return self.repo.list_history(serial_no_id, organization_id, limit=limit)

    def add_history(
        self,
        serial_no_id: UUID,
        data: SerialNoHistoryCreate,
        organization_id: UUID,
    ) -> SerialNoHistory:
        from datetime import UTC, datetime

        self.get_by_id(serial_no_id, organization_id)
        d = data.model_dump()
        d["serial_no_id"] = serial_no_id
        d["organization_id"] = organization_id
        if d.get("transaction_date") is None:
            d["transaction_date"] = datetime.now(UTC)
        return self.repo.create_history(d)
