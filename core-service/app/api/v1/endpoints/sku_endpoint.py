"""API endpoints for ProductSKU, VariantAttribute, VariantAttributeValue"""

from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import CurrentUser, require_permission
from app.schemas.sku import (
    ProductSKUCreateRequest,
    ProductSKUListResponse,
    ProductSKUResponse,
    ProductSKUUpdateRequest,
    VariantAttributeCreateRequest,
    VariantAttributeListResponse,
    VariantAttributeResponse,
    VariantAttributeUpdateRequest,
    VariantAttributeValueCreateRequest,
    VariantAttributeValueResponse,
    VariantAttributeValueUpdateRequest,
    VariantAttributeWithValuesResponse,
)
from app.services.sku_service import SKUService

router = APIRouter()


# ─────────────────────────────────────────────────────────────────────────────
# VARIANT ATTRIBUTES
# ─────────────────────────────────────────────────────────────────────────────

@router.post(
    "/attributes",
    response_model=VariantAttributeResponse,
    status_code=201,
    summary="Create a variant attribute",
    description=(
        "Creates a new axis of variation, e.g. Capacity (Litre), Size, Color. "
        "Attributes are reusable across all products in the organisation."
    ),
)
async def create_attribute(
    req: VariantAttributeCreateRequest,
    current_user: CurrentUser = Depends(require_permission("sku.create")),
    db: Session = Depends(get_db),
):
    svc = SKUService(db)
    return svc.create_attribute(req, current_user.organization_id, current_user.id)


@router.get(
    "/attributes",
    response_model=VariantAttributeListResponse,
    summary="List variant attributes",
)
async def list_attributes(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    search: str | None = Query(None),
    current_user: CurrentUser = Depends(require_permission("sku.read")),
    db: Session = Depends(get_db),
):
    svc = SKUService(db)
    items, pagination = svc.list_attributes(
        current_user.organization_id, page, page_size, search
    )
    return VariantAttributeListResponse(
        attributes=[VariantAttributeResponse.model_validate(a) for a in items],
        pagination=pagination,
    )


@router.get(
    "/attributes/{attribute_id}",
    response_model=VariantAttributeWithValuesResponse,
    summary="Get a variant attribute with its values",
)
async def get_attribute(
    attribute_id: UUID,
    current_user: CurrentUser = Depends(require_permission("sku.read")),
    db: Session = Depends(get_db),
):
    svc = SKUService(db)
    attr = svc.get_attribute(attribute_id, current_user.organization_id)
    return VariantAttributeWithValuesResponse.model_validate(attr)


@router.patch(
    "/attributes/{attribute_id}",
    response_model=VariantAttributeResponse,
    summary="Update a variant attribute",
)
async def update_attribute(
    attribute_id: UUID,
    req: VariantAttributeUpdateRequest,
    current_user: CurrentUser = Depends(require_permission("sku.update")),
    db: Session = Depends(get_db),
):
    svc = SKUService(db)
    return svc.update_attribute(
        attribute_id, req, current_user.organization_id, current_user.id
    )


@router.delete(
    "/attributes/{attribute_id}",
    status_code=204,
    summary="Delete a variant attribute",
    description="Only allowed if the attribute has no values. Delete all values first.",
)
async def delete_attribute(
    attribute_id: UUID,
    current_user: CurrentUser = Depends(require_permission("sku.delete")),
    db: Session = Depends(get_db),
):
    svc = SKUService(db)
    svc.delete_attribute(attribute_id, current_user.organization_id)


# ─────────────────────────────────────────────────────────────────────────────
# VARIANT ATTRIBUTE VALUES
# ─────────────────────────────────────────────────────────────────────────────

@router.post(
    "/attributes/{attribute_id}/values",
    response_model=VariantAttributeValueResponse,
    status_code=201,
    summary="Add a value to a variant attribute",
    description=(
        "e.g. Add '1L' / '1 Litre' to the 'Capacity' attribute. "
        "The value field is used in logic; display_value is shown in the UI."
    ),
)
async def create_attribute_value(
    attribute_id: UUID,
    req: VariantAttributeValueCreateRequest,
    current_user: CurrentUser = Depends(require_permission("sku.create")),
    db: Session = Depends(get_db),
):
    svc = SKUService(db)
    return svc.create_attribute_value(
        attribute_id, req, current_user.organization_id, current_user.id
    )


@router.get(
    "/attributes/{attribute_id}/values",
    response_model=list[VariantAttributeValueResponse],
    summary="List values for a variant attribute",
)
async def list_attribute_values(
    attribute_id: UUID,
    current_user: CurrentUser = Depends(require_permission("sku.read")),
    db: Session = Depends(get_db),
):
    svc = SKUService(db)
    values = svc.list_attribute_values(attribute_id, current_user.organization_id)
    return [VariantAttributeValueResponse.model_validate(v) for v in values]


@router.get(
    "/attributes/{attribute_id}/values/{value_id}",
    response_model=VariantAttributeValueResponse,
    summary="Get a single attribute value",
)
async def get_attribute_value(
    attribute_id: UUID,
    value_id: UUID,
    current_user: CurrentUser = Depends(require_permission("sku.read")),
    db: Session = Depends(get_db),
):
    svc = SKUService(db)
    return VariantAttributeValueResponse.model_validate(
        svc.get_attribute_value(value_id, attribute_id, current_user.organization_id)
    )


@router.patch(
    "/attributes/{attribute_id}/values/{value_id}",
    response_model=VariantAttributeValueResponse,
    summary="Update an attribute value",
)
async def update_attribute_value(
    attribute_id: UUID,
    value_id: UUID,
    req: VariantAttributeValueUpdateRequest,
    current_user: CurrentUser = Depends(require_permission("sku.update")),
    db: Session = Depends(get_db),
):
    svc = SKUService(db)
    return VariantAttributeValueResponse.model_validate(
        svc.update_attribute_value(
            value_id, attribute_id, req, current_user.organization_id
        )
    )


@router.delete(
    "/attributes/{attribute_id}/values/{value_id}",
    status_code=204,
    summary="Delete an attribute value",
)
async def delete_attribute_value(
    attribute_id: UUID,
    value_id: UUID,
    current_user: CurrentUser = Depends(require_permission("sku.delete")),
    db: Session = Depends(get_db),
):
    svc = SKUService(db)
    svc.delete_attribute_value(value_id, attribute_id, current_user.organization_id)


# ─────────────────────────────────────────────────────────────────────────────
# PRODUCT SKUs
# ─────────────────────────────────────────────────────────────────────────────

@router.post(
    "/skus",
    response_model=ProductSKUResponse,
    status_code=201,
    summary="Create a SKU",
    description=(
        "Creates a specific sellable variant under a product. "
        "Pass attribute_values as a list of attribute_value_id UUIDs. "
        "A pressure cooker 1L SKU would pass the UUID of the '1L' Capacity value. "
        "A fan SKU with Sweep:1200mm + Color:White would pass two UUIDs."
    ),
)
async def create_sku(
    req: ProductSKUCreateRequest,
    current_user: CurrentUser = Depends(require_permission("sku.create")),
    db: Session = Depends(get_db),
):
    svc = SKUService(db)
    sku = svc.create_sku(req, current_user.organization_id, current_user.id)
    response = ProductSKUResponse.model_validate(sku)
    response.attribute_values = svc._build_sku_attr_value_response(sku)
    return response


@router.get(
    "/skus",
    response_model=ProductSKUListResponse,
    summary="List all SKUs",
    description="Filter by product_id to get SKUs for a specific product.",
)
async def list_skus(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    search: str | None = Query(None, description="Search by SKU code or name"),
    product_id: UUID | None = Query(None),
    is_active: bool | None = Query(None),
    current_user: CurrentUser = Depends(require_permission("sku.read")),
    db: Session = Depends(get_db),
):
    svc = SKUService(db)
    items, pagination = svc.list_skus(
        current_user.organization_id, page, page_size, search, product_id, is_active
    )
    skus = []
    for sku in items:
        r = ProductSKUResponse.model_validate(sku)
        r.attribute_values = svc._build_sku_attr_value_response(sku)
        skus.append(r)
    return ProductSKUListResponse(skus=skus, pagination=pagination)


@router.get(
    "/products/{product_id}/skus",
    response_model=ProductSKUListResponse,
    summary="List SKUs for a product",
)
async def list_skus_by_product(
    product_id: UUID,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    is_active: bool | None = Query(None),
    current_user: CurrentUser = Depends(require_permission("sku.read")),
    db: Session = Depends(get_db),
):
    svc = SKUService(db)
    items, pagination = svc.list_skus_by_product(
        product_id, current_user.organization_id, page, page_size, is_active
    )
    skus = []
    for sku in items:
        r = ProductSKUResponse.model_validate(sku)
        r.attribute_values = svc._build_sku_attr_value_response(sku)
        skus.append(r)
    return ProductSKUListResponse(skus=skus, pagination=pagination)


@router.get(
    "/skus/{sku_id}",
    response_model=ProductSKUResponse,
    summary="Get a SKU",
)
async def get_sku(
    sku_id: UUID,
    current_user: CurrentUser = Depends(require_permission("sku.read")),
    db: Session = Depends(get_db),
):
    svc = SKUService(db)
    sku = svc.get_sku(sku_id, current_user.organization_id)
    response = ProductSKUResponse.model_validate(sku)
    response.attribute_values = svc._build_sku_attr_value_response(sku)
    return response


@router.patch(
    "/skus/{sku_id}",
    response_model=ProductSKUResponse,
    summary="Update a SKU",
    description=(
        "Pass attribute_values to replace all linked attribute values for this SKU. "
        "Omit attribute_values entirely to leave them unchanged."
    ),
)
async def update_sku(
    sku_id: UUID,
    req: ProductSKUUpdateRequest,
    current_user: CurrentUser = Depends(require_permission("sku.update")),
    db: Session = Depends(get_db),
):
    svc = SKUService(db)
    sku = svc.update_sku(sku_id, req, current_user.organization_id, current_user.id)
    response = ProductSKUResponse.model_validate(sku)
    response.attribute_values = svc._build_sku_attr_value_response(sku)
    return response


@router.delete(
    "/skus/{sku_id}",
    status_code=204,
    summary="Soft-delete a SKU",
    description="Marks the SKU as inactive and sets deleted_at. Does not remove QR blocks or items.",
)
async def delete_sku(
    sku_id: UUID,
    current_user: CurrentUser = Depends(require_permission("sku.delete")),
    db: Session = Depends(get_db),
):
    svc = SKUService(db)
    svc.delete_sku(sku_id, current_user.organization_id)
