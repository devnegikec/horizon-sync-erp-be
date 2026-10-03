"""Product (shared catalog core) service."""

import logging
from datetime import UTC, datetime
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.models.products import Product
from app.schemas.product import ProductCreate, ProductUpdate

logger = logging.getLogger(__name__)


class ProductService:
    """Service for catalog-core Product operations."""

    def __init__(self, db: Session):
        self.db = db

    def list_products(
        self,
        organization_id: UUID,
        page: int = 1,
        page_size: int = 20,
        search: str | None = None,
        is_active: bool | None = None,
        product_type: str | None = None,
    ) -> tuple[list[Product], dict]:
        q = self.db.query(Product).filter(
            Product.organization_id == organization_id,
            Product.deleted_at.is_(None),
        )
        if search:
            like = f"%{search}%"
            q = q.filter(
                or_(
                    Product.name.ilike(like),
                    Product.sku.ilike(like),
                    Product.gtin.ilike(like),
                )
            )
        if is_active is not None:
            q = q.filter(Product.is_active == is_active)
        if product_type:
            q = q.filter(Product.product_type == product_type)

        total = q.count()
        products = (
            q.order_by(Product.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
            .all()
        )
        total_pages = (total + page_size - 1) // page_size if page_size else 0
        pagination = {
            "page": page,
            "page_size": page_size,
            "total": total,
            "total_pages": total_pages,
            "has_next": page < total_pages,
            "has_prev": page > 1,
        }
        return products, pagination

    def get_product(self, product_id: UUID, organization_id: UUID) -> Product:
        product = (
            self.db.query(Product)
            .filter(
                Product.id == product_id,
                Product.organization_id == organization_id,
                Product.deleted_at.is_(None),
            )
            .first()
        )
        if not product:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Product not found"
            )
        return product

    def create_product(
        self, data: ProductCreate, organization_id: UUID, user_id: UUID
    ) -> Product:
        payload = data.model_dump()
        payload["organization_id"] = organization_id
        payload["created_by"] = user_id
        payload["updated_by"] = user_id
        product = Product(**payload)
        self.db.add(product)
        self.db.commit()
        self.db.refresh(product)
        return product

    def update_product(
        self,
        product_id: UUID,
        data: ProductUpdate,
        organization_id: UUID,
        user_id: UUID,
    ) -> Product:
        product = self.get_product(product_id, organization_id)
        for key, value in data.model_dump(exclude_unset=True).items():
            setattr(product, key, value)
        product.updated_by = user_id
        self.db.commit()
        self.db.refresh(product)
        return product

    def delete_product(self, product_id: UUID, organization_id: UUID) -> None:
        product = self.get_product(product_id, organization_id)
        product.deleted_at = datetime.now(UTC)
        self.db.commit()
