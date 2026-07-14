"""Communication repository"""

from uuid import UUID

from sqlalchemy.orm import Session

from app.models.communication import CommunicationLog


class CommunicationRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(self, data: dict) -> CommunicationLog:
        comm = CommunicationLog(**data)
        self.db.add(comm)
        self.db.commit()
        self.db.refresh(comm)
        return comm

    def get_by_id(
        self, communication_id: UUID, organization_id: UUID
    ) -> CommunicationLog | None:
        return (
            self.db.query(CommunicationLog)
            .filter(
                CommunicationLog.id == communication_id,
                CommunicationLog.organization_id == organization_id,
            )
            .first()
        )

    def list_communications(
        self,
        organization_id: UUID,
        page: int = 1,
        page_size: int = 20,
        doc_type: str | None = None,
        doc_id: UUID | None = None,
        channel: str | None = None,
        status: str | None = None,
        recipient_type: str | None = None,
        sort_by: str = "created_at",
        sort_order: str = "desc",
    ) -> tuple[list[CommunicationLog], int]:
        q = self.db.query(CommunicationLog).filter(
            CommunicationLog.organization_id == organization_id
        )

        if doc_type is not None:
            q = q.filter(CommunicationLog.doc_type == doc_type)
        if doc_id is not None:
            q = q.filter(CommunicationLog.doc_id == doc_id)
        if channel is not None:
            q = q.filter(CommunicationLog.channel == channel)
        if status is not None:
            q = q.filter(CommunicationLog.status == status)
        if recipient_type is not None:
            q = q.filter(CommunicationLog.recipient_type == recipient_type)

        total = q.count()

        col = getattr(CommunicationLog, sort_by, CommunicationLog.created_at)
        q = q.order_by(col.desc() if sort_order == "desc" else col.asc())

        items = q.offset((page - 1) * page_size).limit(page_size).all()
        return items, total

    def update(self, comm: CommunicationLog, data: dict) -> CommunicationLog:
        for k, v in data.items():
            if hasattr(comm, k):
                setattr(comm, k, v)
        self.db.commit()
        self.db.refresh(comm)
        return comm

    def delete(self, comm: CommunicationLog) -> None:
        self.db.delete(comm)
        self.db.commit()
