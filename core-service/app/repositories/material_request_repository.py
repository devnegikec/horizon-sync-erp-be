"""Material Request repository"""

from uuid import UUID

from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload

from app.models.material_request import MaterialRequest, MaterialRequestLine


class MaterialRequestRepository:
    """Repository for Material Request operations"""

    def __init__(self, db: Session):
        self.db = db

    def create(self, data: dict) -> MaterialRequest:
        """Create a new Material Request"""
        material_request = MaterialRequest(**data)
        self.db.add(material_request)
        self.db.commit()
        self.db.refresh(material_request)
        return material_request

    def get_by_id(
        self, material_request_id: UUID, organization_id: UUID
    ) -> MaterialRequest | None:
        """Get Material Request by ID"""
        return (
            self.db.query(MaterialRequest)
            .options(joinedload(MaterialRequest.line_items))
            .filter(
                MaterialRequest.id == material_request_id,
                MaterialRequest.organization_id == organization_id,
                MaterialRequest.deleted_at.is_(None),
            )
            .first()
        )

    def list_material_requests(
        self,
        organization_id: UUID,
        page: int = 1,
        page_size: int = 20,
        status: str | None = None,
        sort_by: str = "created_at",
        sort_order: str = "desc",
        search: str | None = None,
    ) -> tuple[list[MaterialRequest], int]:
        """List Material Requests with pagination"""
        q = self.db.query(MaterialRequest).filter(
            MaterialRequest.organization_id == organization_id,
            MaterialRequest.deleted_at.is_(None),
        )

        if status is not None:
            q = q.filter(MaterialRequest.status == status)

        if search is not None:
            search_pattern = f"%{search}%"
            q = q.filter(MaterialRequest.notes.ilike(search_pattern))

        total = q.count()

        col = getattr(MaterialRequest, sort_by, MaterialRequest.created_at)
        q = q.order_by(col.desc() if sort_order == "desc" else col.asc())

        items = q.offset((page - 1) * page_size).limit(page_size).all()
        return items, total

    def update(self, material_request: MaterialRequest, data: dict) -> MaterialRequest:
        """Update Material Request"""
        for k, v in data.items():
            if hasattr(material_request, k):
                setattr(material_request, k, v)
        self.db.commit()
        self.db.refresh(material_request)
        return material_request

    def delete(self, material_request: MaterialRequest) -> None:
        """Delete Material Request"""
        self.db.delete(material_request)
        self.db.commit()

    def create_line_item(self, data: dict) -> MaterialRequestLine:
        """Create a Material Request line item"""
        line_item = MaterialRequestLine(**data)
        self.db.add(line_item)
        self.db.commit()
        self.db.refresh(line_item)
        return line_item

    def delete_line_items(self, material_request_id: UUID) -> None:
        """Delete all line items for a Material Request"""
        self.db.query(MaterialRequestLine).filter(
            MaterialRequestLine.material_request_id == material_request_id
        ).delete()
        self.db.commit()

    def get_line_items_count(self, material_request_id: UUID) -> int:
        """Get count of line items for a Material Request"""
        return (
            self.db.query(func.count(MaterialRequestLine.id))
            .filter(MaterialRequestLine.material_request_id == material_request_id)
            .scalar()
        )
