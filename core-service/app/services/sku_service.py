"""Service layer for ProductSKU, VariantAttribute, VariantAttributeValue"""

from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.repositories.sku_repository import (
    ProductSKURepository,
    VariantAttributeRepository,
    VariantAttributeValueRepository,
)
from app.schemas.sku import (
    ProductSKUCreateRequest,
    ProductSKUUpdateRequest,
    SKUAttributeValueResponse,
    VariantAttributeCreateRequest,
    VariantAttributeUpdateRequest,
    VariantAttributeValueCreateRequest,
    VariantAttributeValueUpdateRequest,
)


class SKUService:
    def __init__(self, db: Session):
        self.db = db
        self.attr_repo = VariantAttributeRepository(db)
        self.value_repo = VariantAttributeValueRepository(db)
        self.sku_repo = ProductSKURepository(db)

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _build_pagination(self, total: int, page: int, page_size: int) -> dict:
        total_pages = max(1, (total + page_size - 1) // page_size)
        return {
            "page": page,
            "page_size": page_size,
            "total_items": total,
            "total_pages": total_pages,
            "has_next": page < total_pages,
            "has_prev": page > 1,
        }

    def _build_sku_attr_value_response(self, sku) -> list[SKUAttributeValueResponse]:
        """Build the nested attribute value list for a SKU response."""
        result = []
        for link in sku.sku_attribute_values:
            av = link.attribute_value
            result.append(
                SKUAttributeValueResponse(
                    id=link.id,
                    attribute_value_id=av.id,
                    attribute_name=av.attribute.name if av.attribute else "",
                    value=av.value,
                    display_value=av.display_value or av.value,
                )
            )
        return result

    # ── Variant Attribute ─────────────────────────────────────────────────────

    def create_attribute(
        self,
        data: VariantAttributeCreateRequest,
        organization_id: UUID,
        user_id: UUID,
    ):
        # Prevent duplicate name within org
        existing = self.attr_repo.get_by_name(data.name, organization_id)
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Attribute '{data.name}' already exists for this organisation.",
            )

        return self.attr_repo.create(
            {
                "organization_id": organization_id,
                "name": data.name,
                "unit": data.unit,
                "created_by": user_id,
                "updated_by": user_id,
            }
        )

    def list_attributes(
        self,
        organization_id: UUID,
        page: int = 1,
        page_size: int = 20,
        search: str | None = None,
    ):
        items, total = self.attr_repo.list_all(organization_id, page, page_size, search)
        return items, self._build_pagination(total, page, page_size)

    def get_attribute(self, attribute_id: UUID, organization_id: UUID):
        attr = self.attr_repo.get_by_id(attribute_id, organization_id)
        if not attr:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Variant attribute not found.",
            )
        return attr

    def update_attribute(
        self,
        attribute_id: UUID,
        data: VariantAttributeUpdateRequest,
        organization_id: UUID,
        user_id: UUID,
    ):
        attr = self.get_attribute(attribute_id, organization_id)

        update_data = data.model_dump(exclude_none=True)

        # If name is changing, check for duplicates
        if "name" in update_data and update_data["name"] != attr.name:
            conflict = self.attr_repo.get_by_name(update_data["name"], organization_id)
            if conflict:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Attribute '{update_data['name']}' already exists.",
                )

        update_data["updated_by"] = user_id
        return self.attr_repo.update(attr, update_data)

    def delete_attribute(self, attribute_id: UUID, organization_id: UUID) -> None:
        attr = self.get_attribute(attribute_id, organization_id)
        # Guard: don't delete if values exist (would cascade and break SKUs)
        if attr.values:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot delete attribute '{attr.name}' — it has {len(attr.values)} value(s). "
                       "Delete all values first or remove them from SKUs.",
            )
        self.attr_repo.delete(attr)

    # ── Variant Attribute Value ───────────────────────────────────────────────

    def create_attribute_value(
        self,
        attribute_id: UUID,
        data: VariantAttributeValueCreateRequest,
        organization_id: UUID,
        user_id: UUID,
    ):
        # Verify the attribute belongs to this org
        self.get_attribute(attribute_id, organization_id)

        # Prevent duplicate value under same attribute
        existing = self.value_repo.get_by_value(data.value, attribute_id)
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Value '{data.value}' already exists under this attribute.",
            )

        return self.value_repo.create(
            {
                "attribute_id": attribute_id,
                "value": data.value,
                "display_value": data.display_value,
                "sort_order": data.sort_order,
                "created_by": user_id,
            }
        )

    def list_attribute_values(self, attribute_id: UUID, organization_id: UUID):
        # Verify attribute belongs to org first
        self.get_attribute(attribute_id, organization_id)
        return self.value_repo.list_by_attribute(attribute_id, organization_id)

    def get_attribute_value(
        self, value_id: UUID, attribute_id: UUID, organization_id: UUID
    ):
        value = self.value_repo.get_by_id(value_id, attribute_id, organization_id)
        if not value:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Attribute value not found.",
            )
        return value

    def update_attribute_value(
        self,
        value_id: UUID,
        attribute_id: UUID,
        data: VariantAttributeValueUpdateRequest,
        organization_id: UUID,
    ):
        value = self.get_attribute_value(value_id, attribute_id, organization_id)
        update_data = data.model_dump(exclude_none=True)

        if "value" in update_data and update_data["value"] != value.value:
            conflict = self.value_repo.get_by_value(update_data["value"], attribute_id)
            if conflict:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Value '{update_data['value']}' already exists under this attribute.",
                )

        return self.value_repo.update(value, update_data)

    def delete_attribute_value(
        self, value_id: UUID, attribute_id: UUID, organization_id: UUID
    ) -> None:
        value = self.get_attribute_value(value_id, attribute_id, organization_id)
        self.value_repo.delete(value)

    # ── ProductSKU ────────────────────────────────────────────────────────────

    def create_sku(
        self,
        data: ProductSKUCreateRequest,
        organization_id: UUID,
        user_id: UUID,
    ):
        # Check SKU code uniqueness
        if self.sku_repo.get_by_code(data.sku_code, organization_id):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"SKU code '{data.sku_code}' already exists.",
            )

        av_ids = [av.attribute_value_id for av in data.attribute_values]

        # Validate all attribute value IDs exist and belong to this org
        if av_ids:
            values = self.value_repo.get_by_ids(av_ids)
            found_ids = {v.id for v in values}
            missing = [str(i) for i in av_ids if i not in found_ids]
            if missing:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Attribute value ID(s) not found: {', '.join(missing)}",
                )

            # Check for duplicate attribute combo under same product
            if self.sku_repo.check_duplicate_attribute_combo(data.product_id, av_ids):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="A SKU with this exact combination of attribute values already exists "
                           "under this product.",
                )

        sku_data = {
            "organization_id": organization_id,
            "product_id": data.product_id,
            "sku_code": data.sku_code,
            "name": data.name,
            "gtin": data.gtin,
            "mrp": data.mrp,
            "sr_number_type": data.sr_number_type,
            "image_url": data.image_url,
            "warranty_period_months": data.warranty_period_months,
            "is_active": True,
            "created_by": user_id,
            "updated_by": user_id,
        }

        return self.sku_repo.create(sku_data, av_ids)

    def list_skus(
        self,
        organization_id: UUID,
        page: int = 1,
        page_size: int = 20,
        search: str | None = None,
        product_id: UUID | None = None,
        is_active: bool | None = None,
    ):
        items, total = self.sku_repo.list_all(
            organization_id, page, page_size, search, product_id, is_active
        )
        return items, self._build_pagination(total, page, page_size)

    def list_skus_by_product(
        self,
        product_id: UUID,
        organization_id: UUID,
        page: int = 1,
        page_size: int = 20,
        is_active: bool | None = None,
    ):
        items, total = self.sku_repo.list_by_product(
            product_id, organization_id, page, page_size, is_active
        )
        return items, self._build_pagination(total, page, page_size)

    def get_sku(self, sku_id: UUID, organization_id: UUID):
        sku = self.sku_repo.get_by_id(sku_id, organization_id)
        if not sku:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="SKU not found.",
            )
        return sku

    def update_sku(
        self,
        sku_id: UUID,
        data: ProductSKUUpdateRequest,
        organization_id: UUID,
        user_id: UUID,
    ):
        sku = self.get_sku(sku_id, organization_id)
        update_data = data.model_dump(exclude={"attribute_values"}, exclude_none=True)

        # Check code uniqueness if changing
        if "sku_code" in update_data and update_data["sku_code"] != sku.sku_code:
            if self.sku_repo.get_by_code(update_data["sku_code"], organization_id):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"SKU code '{update_data['sku_code']}' already exists.",
                )

        av_ids = None
        if data.attribute_values is not None:
            av_ids = [av.attribute_value_id for av in data.attribute_values]
            if av_ids:
                values = self.value_repo.get_by_ids(av_ids)
                found_ids = {v.id for v in values}
                missing = [str(i) for i in av_ids if i not in found_ids]
                if missing:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Attribute value ID(s) not found: {', '.join(missing)}",
                    )
                if self.sku_repo.check_duplicate_attribute_combo(
                    sku.product_id, av_ids, exclude_sku_id=sku_id
                ):
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Another SKU with this attribute combination already exists.",
                    )

        update_data["updated_by"] = user_id
        return self.sku_repo.update(sku, update_data, av_ids)

    def delete_sku(self, sku_id: UUID, organization_id: UUID) -> None:
        sku = self.get_sku(sku_id, organization_id)
        self.sku_repo.soft_delete(sku)