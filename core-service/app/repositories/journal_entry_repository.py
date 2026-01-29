"""Journal entry repository"""

from uuid import UUID

from sqlalchemy.orm import Session

from app.models.journal_entry import JournalEntry, JournalEntryLine


class JournalEntryRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(self, data: dict, lines: list[dict]) -> JournalEntry:
        je = JournalEntry(**data)
        self.db.add(je)
        self.db.flush()
        for ln in lines:
            ln["journal_entry_id"] = je.id
            ln["organization_id"] = je.organization_id
            self.db.add(JournalEntryLine(**ln))
        self.db.commit()
        self.db.refresh(je)
        return je

    def get_by_id(
        self, entry_id: UUID, organization_id: UUID, load_lines: bool = True
    ) -> JournalEntry | None:
        q = self.db.query(JournalEntry).filter(
            JournalEntry.id == entry_id,
            JournalEntry.organization_id == organization_id,
        )
        je = q.first()
        if je and load_lines:
            _ = je.lines
        return je

    def get_by_no(self, entry_no: str, organization_id: UUID) -> JournalEntry | None:
        return (
            self.db.query(JournalEntry)
            .filter(
                JournalEntry.entry_no == entry_no,
                JournalEntry.organization_id == organization_id,
            )
            .first()
        )

    def list_entries(
        self,
        organization_id: UUID,
        page: int = 1,
        page_size: int = 20,
        status: str | None = None,
        sort_by: str = "posting_date",
        sort_order: str = "desc",
    ) -> tuple[list[JournalEntry], int]:
        q = self.db.query(JournalEntry).filter(
            JournalEntry.organization_id == organization_id
        )
        if status is not None:
            q = q.filter(JournalEntry.status == status)
        total = q.count()
        col = getattr(JournalEntry, sort_by, JournalEntry.created_at)
        q = q.order_by(col.desc() if sort_order == "desc" else col.asc())
        items = q.offset((page - 1) * page_size).limit(page_size).all()
        return items, total

    def update(self, je: JournalEntry, data: dict) -> JournalEntry:
        for k, v in data.items():
            if hasattr(je, k):
                setattr(je, k, v)
        self.db.commit()
        self.db.refresh(je)
        return je

    def delete(self, je: JournalEntry) -> None:
        self.db.delete(je)
        self.db.commit()
