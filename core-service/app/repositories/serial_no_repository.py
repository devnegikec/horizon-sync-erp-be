"""Serial number and history repository"""

from uuid import UUID

from sqlalchemy.orm import Session

from app.models.serial_no import SerialNo, SerialNoHistory


class SerialNoRepository:
    def __init__(self, db: Session):
        self.db = db

    def create_serial_no(self, data: dict) -> SerialNo:
        s = SerialNo(**data)
        self.db.add(s)
        self.db.commit()
        self.db.refresh(s)
        return s

    def get_by_id(self, serial_no_id: UUID, organization_id: UUID) -> SerialNo | None:
        return (
            self.db.query(SerialNo)
            .filter(
                SerialNo.id == serial_no_id,
                SerialNo.organization_id == organization_id,
            )
            .first()
        )

    def get_by_serial_and_item(
        self, serial_no: str, item_id: UUID, organization_id: UUID
    ) -> SerialNo | None:
        return (
            self.db.query(SerialNo)
            .filter(
                SerialNo.serial_no == serial_no,
                SerialNo.item_id == item_id,
                SerialNo.organization_id == organization_id,
            )
            .first()
        )

    def update(self, s: SerialNo, data: dict) -> SerialNo:
        for k, v in data.items():
            if hasattr(s, k) and v is not None:
                setattr(s, k, v)
        self.db.commit()
        self.db.refresh(s)
        return s

    def delete(self, s: SerialNo) -> None:
        self.db.delete(s)
        self.db.commit()

    def list_serial_nos(
        self,
        organization_id: UUID,
        item_id: UUID | None = None,
        warehouse_id: UUID | None = None,
        search: str | None = None,
        page: int = 1,
        page_size: int = 20,
        sort_by: str = "created_at",
        sort_order: str = "desc",
    ) -> tuple[list[SerialNo], int]:
        q = self.db.query(SerialNo).filter(SerialNo.organization_id == organization_id)
        if item_id:
            q = q.filter(SerialNo.item_id == item_id)
        if warehouse_id:
            q = q.filter(SerialNo.warehouse_id == warehouse_id)
        if search:
            t = f"%{search}%"
            q = q.filter(SerialNo.serial_no.ilike(t))
        total = q.count()
        col = getattr(SerialNo, sort_by, SerialNo.created_at)
        q = q.order_by(col.desc() if sort_order == "desc" else col.asc())
        items = q.offset((page - 1) * page_size).limit(page_size).all()
        return items, total

    # ----- History -----

    def create_history(self, data: dict) -> SerialNoHistory:
        h = SerialNoHistory(**data)
        self.db.add(h)
        self.db.commit()
        self.db.refresh(h)
        return h

    def list_history(
        self, serial_no_id: UUID, organization_id: UUID, limit: int = 100
    ) -> list[SerialNoHistory]:
        return (
            self.db.query(SerialNoHistory)
            .filter(
                SerialNoHistory.serial_no_id == serial_no_id,
                SerialNoHistory.organization_id == organization_id,
            )
            .order_by(SerialNoHistory.transaction_date.desc())
            .limit(limit)
            .all()
        )
