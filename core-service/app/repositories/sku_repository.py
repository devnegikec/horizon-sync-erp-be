"""Repository for ProductSKU, VariantAttribute, VariantAttributeValue"""

from uuid import UUID

from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload

from app.models.product_sku import ProductSKU
from app.models.sku_variant_attribute import (
    ProductSKUAttributeValue,
    VariantAttribute,
    VariantAttributeValue,
)


# ── Variant Attribute Repository ──────────────────────────────────────────────

class VariantAttributeRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(self, data: dict) -> VariantAttribute:
        instance = VariantAttribute(**data)
        self.db.add(instance)
        self.db.commit()
        self.db.refresh(instance)
        return instance

    def get_by_id(self, attribute_id: UUID, organization_id: UUID) -> VariantAttribute | None:
        return (
            self.db.query(VariantAttribute)
            .filter(
                VariantAttribute.id == attribute_id,
                VariantAttribute.organization_id == organization_id,
            )
            .first()
        )

    def get_by_name(self, name: str, organization_id: UUID) -> VariantAttribute | None:
        return (
            self.db.query(VariantAttribute)
            .filter(
                VariantAttribute.name == name,
                VariantAttribute.organization_id == organization_id,
            )
            .first()
        )

    def list_all(
        self,
        organization_id: UUID,
        page: int = 1,
        page_size: int = 20,
        search: str | None = None,
    ) -> tuple[list[VariantAttribute], int]:
        query = (
            self.db.query(VariantAttribute)
            .options(joinedload(VariantAttribute.values))
            .filter(VariantAttribute.organization_id == organization_id)
        )
        if search:
            query = query.filter(VariantAttribute.name.ilike(f"%{search}%"))

        total = query.count()
        items = query.offset((page - 1) * page_size).limit(page_size).all()
        return items, total

    def update(self, attribute: VariantAttribute, data: dict) -> VariantAttribute:
        for key, value in data.items():
            setattr(attribute, key, value)
        self.db.commit()
        self.db.refresh(attribute)
        return attribute

    def delete(self, attribute: VariantAttribute) -> None:
        self.db.delete(attribute)
        self.db.commit()


# ── Variant Attribute Value Repository ───────────────────────────────────────

class VariantAttributeValueRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(self, data: dict) -> VariantAttributeValue:
        instance = VariantAttributeValue(**data)
        self.db.add(instance)
        self.db.commit()
        self.db.refresh(instance)
        return instance

    def get_by_id(
        self,
        value_id: UUID,
        attribute_id: UUID,
        organization_id: UUID,
    ) -> VariantAttributeValue | None:
        return (
            self.db.query(VariantAttributeValue)
            .join(VariantAttribute, VariantAttributeValue.attribute_id == VariantAttribute.id)
            .filter(
                VariantAttributeValue.id == value_id,
                VariantAttributeValue.attribute_id == attribute_id,
                VariantAttribute.organization_id == organization_id,
            )
            .first()
        )

    def get_by_value(
        self, value: str, attribute_id: UUID
    ) -> VariantAttributeValue | None:
        return (
            self.db.query(VariantAttributeValue)
            .filter(
                VariantAttributeValue.value == value,
                VariantAttributeValue.attribute_id == attribute_id,
            )
            .first()
        )

    def list_by_attribute(
        self, attribute_id: UUID, organization_id: UUID
    ) -> list[VariantAttributeValue]:
        return (
            self.db.query(VariantAttributeValue)
            .join(VariantAttribute, VariantAttributeValue.attribute_id == VariantAttribute.id)
            .filter(
                VariantAttributeValue.attribute_id == attribute_id,
                VariantAttribute.organization_id == organization_id,
            )
            .order_by(VariantAttributeValue.sort_order)
            .all()
        )

    def get_by_ids(self, value_ids: list[UUID]) -> list[VariantAttributeValue]:
        """Bulk fetch by list of IDs — used during SKU creation."""
        return (
            self.db.query(VariantAttributeValue)
            .options(joinedload(VariantAttributeValue.attribute))
            .filter(VariantAttributeValue.id.in_(value_ids))
            .all()
        )

    def update(
        self, value: VariantAttributeValue, data: dict
    ) -> VariantAttributeValue:
        for key, val in data.items():
            setattr(value, key, val)
        self.db.commit()
        self.db.refresh(value)
        return value

    def delete(self, value: VariantAttributeValue) -> None:
        self.db.delete(value)
        self.db.commit()


# ── ProductSKU Repository ─────────────────────────────────────────────────────

class ProductSKURepository:
    def __init__(self, db: Session):
        self.db = db

    def _base_query(self, organization_id: UUID):
        """Base query with attribute values eagerly loaded."""
        return (
            self.db.query(ProductSKU)
            .options(
                joinedload(ProductSKU.sku_attribute_values).joinedload(
                    ProductSKUAttributeValue.attribute_value
                ).joinedload(VariantAttributeValue.attribute)
            )
            .filter(ProductSKU.organization_id == organization_id)
        )

    def create(self, data: dict, attribute_value_ids: list[UUID]) -> ProductSKU:
        """Create a SKU and link its attribute values in one transaction."""
        sku = ProductSKU(**data)
        self.db.add(sku)
        self.db.flush()  # get the sku.id without committing

        for av_id in attribute_value_ids:
            link = ProductSKUAttributeValue(
                sku_id=sku.id,
                attribute_value_id=av_id,
                created_by=data.get("created_by"),
            )
            self.db.add(link)

        self.db.commit()
        self.db.refresh(sku)
        return sku

    def get_by_id(self, sku_id: UUID, organization_id: UUID) -> ProductSKU | None:
        return (
            self._base_query(organization_id)
            .filter(ProductSKU.id == sku_id, ProductSKU.deleted_at.is_(None))
            .first()
        )

    def get_by_code(self, sku_code: str, organization_id: UUID) -> ProductSKU | None:
        return (
            self.db.query(ProductSKU)
            .filter(
                ProductSKU.sku_code == sku_code,
                ProductSKU.organization_id == organization_id,
                ProductSKU.deleted_at.is_(None),
            )
            .first()
        )

    def list_by_product(
        self,
        product_id: UUID,
        organization_id: UUID,
        page: int = 1,
        page_size: int = 20,
        is_active: bool | None = None,
    ) -> tuple[list[ProductSKU], int]:
        query = (
            self._base_query(organization_id)
            .filter(
                ProductSKU.product_id == product_id,
                ProductSKU.deleted_at.is_(None),
            )
        )
        if is_active is not None:
            query = query.filter(ProductSKU.is_active == is_active)

        total = self.db.query(func.count(ProductSKU.id)).filter(
            ProductSKU.product_id == product_id,
            ProductSKU.organization_id == organization_id,
            ProductSKU.deleted_at.is_(None),
        ).scalar() or 0

        items = query.offset((page - 1) * page_size).limit(page_size).all()
        return items, total

    def list_all(
        self,
        organization_id: UUID,
        page: int = 1,
        page_size: int = 20,
        search: str | None = None,
        product_id: UUID | None = None,
        is_active: bool | None = None,
    ) -> tuple[list[ProductSKU], int]:
        query = self._base_query(organization_id).filter(
            ProductSKU.deleted_at.is_(None)
        )

        if search:
            query = query.filter(
                ProductSKU.sku_code.ilike(f"%{search}%")
                | ProductSKU.name.ilike(f"%{search}%")
            )
        if product_id:
            query = query.filter(ProductSKU.product_id == product_id)
        if is_active is not None:
            query = query.filter(ProductSKU.is_active == is_active)

        count_query = self.db.query(func.count(ProductSKU.id)).filter(
            ProductSKU.organization_id == organization_id,
            ProductSKU.deleted_at.is_(None),
        )
        if product_id:
            count_query = count_query.filter(ProductSKU.product_id == product_id)
        total = count_query.scalar() or 0

        items = query.offset((page - 1) * page_size).limit(page_size).all()
        return items, total

    def update(
        self,
        sku: ProductSKU,
        data: dict,
        attribute_value_ids: list[UUID] | None = None,
    ) -> ProductSKU:
        for key, value in data.items():
            setattr(sku, key, value)

        # Replace attribute value links if provided
        if attribute_value_ids is not None:
            self.db.query(ProductSKUAttributeValue).filter(
                ProductSKUAttributeValue.sku_id == sku.id
            ).delete()
            for av_id in attribute_value_ids:
                link = ProductSKUAttributeValue(
                    sku_id=sku.id,
                    attribute_value_id=av_id,
                    created_by=data.get("updated_by"),
                )
                self.db.add(link)

        self.db.commit()
        self.db.refresh(sku)
        return sku

    def soft_delete(self, sku: ProductSKU) -> None:
        from datetime import UTC, datetime
        sku.deleted_at = datetime.now(UTC)
        sku.is_active = False
        self.db.commit()

    def check_duplicate_attribute_combo(
        self,
        product_id: UUID,
        attribute_value_ids: list[UUID],
        exclude_sku_id: UUID | None = None,
    ) -> bool:
        """
        Returns True if another SKU under the same product already has
        the exact same set of attribute values — prevents duplicates like
        two "Red Large" pants SKUs under the same product.
        """
        av_count = len(attribute_value_ids)
        if av_count == 0:
            return False

        # Find SKUs under this product that share any of the attribute values
        candidate_ids = (
            self.db.query(ProductSKUAttributeValue.sku_id)
            .join(ProductSKU, ProductSKUAttributeValue.sku_id == ProductSKU.id)
            .filter(
                ProductSKU.product_id == product_id,
                ProductSKU.deleted_at.is_(None),
                ProductSKUAttributeValue.attribute_value_id.in_(attribute_value_ids),
            )
        )
        if exclude_sku_id:
            candidate_ids = candidate_ids.filter(
                ProductSKUAttributeValue.sku_id != exclude_sku_id
            )

        # A duplicate exists if any candidate has exactly the same count of matching values
        for sku_id_row in candidate_ids.distinct().all():
            match_count = (
                self.db.query(func.count(ProductSKUAttributeValue.id))
                .filter(
                    ProductSKUAttributeValue.sku_id == sku_id_row.sku_id,
                    ProductSKUAttributeValue.attribute_value_id.in_(attribute_value_ids),
                )
                .scalar() or 0
            )
            if match_count == av_count:
                return True
        return False