"""Material Request repository"""

from uuid import UUID

from sqlalchemy import func, inspect
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

        allowed_sort_fields = {"id", "created_at", "updated_at", "status"}
        requested_sort_field = sort_by if sort_by in allowed_sort_fields else "created_at"

        existing_columns: set[str] = set()
        try:
            table_columns = inspect(self.db.get_bind()).get_columns("material_requests")
            existing_columns = {column["name"] for column in table_columns}
        except Exception:
            existing_columns = set()

        if existing_columns:
            if requested_sort_field not in existing_columns:
                requested_sort_field = "created_at" if "created_at" in existing_columns else "id"

        col = getattr(MaterialRequest, requested_sort_field, MaterialRequest.id)
        normalized_order = "desc" if str(sort_order).lower() == "desc" else "asc"
        q = q.order_by(col.desc() if normalized_order == "desc" else col.asc())

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

    def count_by_year(self, organization_id: UUID, year: int) -> int:
        """Count Material Requests created in a specific year for an organization"""
        from datetime import datetime
        start_date = datetime(year, 1, 1)
        end_date = datetime(year, 12, 31, 23, 59, 59)
        
        return (
            self.db.query(func.count(MaterialRequest.id))
            .filter(
                MaterialRequest.organization_id == organization_id,
                MaterialRequest.created_at >= start_date,
                MaterialRequest.created_at <= end_date,
                MaterialRequest.deleted_at.is_(None),
            )
            .scalar()
        )
