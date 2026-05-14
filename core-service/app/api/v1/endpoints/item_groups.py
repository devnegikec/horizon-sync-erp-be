"""Item Group management API endpoints"""

import csv
import io
import logging
from uuid import UUID

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import CurrentUser, get_current_active_user
from app.models.item_group import ItemGroup
from app.schemas.common import PaginationMeta
from app.schemas.item_group import (
    ItemGroupCreate,
    ItemGroupListItem,
    ItemGroupListResponse,
    ItemGroupResponse,
    ItemGroupTreeNode,
    ItemGroupUpdate,
    TaxInfo,
    TaxRuleBreakup,
)
from app.services.item_group_service import ItemGroupService

logger = logging.getLogger(__name__)

router = APIRouter()


class ItemGroupImportResponse(BaseModel):
    total_rows: int
    created: int
    updated: int
    failed: int
    errors: list[dict]


def _build_tax_info(tax_template) -> TaxInfo | None:
    """Build TaxInfo schema from a TaxTemplate ORM object."""
    if tax_template is None:
        return None
    has_compound = any(r.is_compound for r in tax_template.tax_rules)
    return TaxInfo(
        id=tax_template.id,
        template_name=tax_template.template_name,
        template_code=tax_template.template_code,
        is_compound=has_compound,
        breakup=[
            TaxRuleBreakup(
                rule_name=r.rule_name,
                tax_type=r.tax_type,
                rate=float(r.tax_rate),
                is_compound=r.is_compound,
            )
            for r in tax_template.tax_rules
        ],
    )


@router.post(
    "",
    response_model=ItemGroupResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create item group",
    description="Create a new item group",
)
async def create_item_group(
    item_group_data: ItemGroupCreate,
    current_user: CurrentUser = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    Create a new item group.

    Requires authentication.

    **Request Body:**
    - **name**: Item group name (required)
    - **code**: Unique item group code (required)
    - **description**: Item group description
    - **parent_id**: Parent item group for hierarchy
    - **default_valuation_method**: Default valuation (fifo, lifo, moving_average, standard)
    - **default_uom**: Default unit of measure
    - **is_active**: Active status (default: true)

    **Returns:** Created item group details
    """
    item_group_service = ItemGroupService(db)
    item_group = item_group_service.create_item_group(
        item_group_data=item_group_data,
        organization_id=current_user.organization_id,
        user_id=current_user.id,
    )
    return ItemGroupResponse.model_validate(item_group)


@router.get(
    "",
    response_model=ItemGroupListResponse,
    summary="List item groups",
    description="Get paginated list of item groups with optional filters",
)
async def list_item_groups(
    page: int = Query(1, ge=1, description="Page number (1-indexed)"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page (max 100)"),
    is_active: bool | None = Query(None, description="Filter by active status"),
    parent_id: UUID | None = Query(None, description="Filter by parent item group ID"),
    search: str | None = Query(None, description="Search in name, code"),
    sort_by: str = Query("created_at", description="Field to sort by"),
    sort_order: str = Query("desc", pattern="^(asc|desc)$", description="Sort order"),
    current_user: CurrentUser = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    List item groups with pagination and filters.

    Requires authentication.

    **Query Parameters:**
    - **page**: Page number (default: 1)
    - **page_size**: Items per page (default: 20, max: 100)
    - **is_active**: Filter by active status
    - **parent_id**: Filter by parent item group
    - **search**: Search term for name, code
    - **sort_by**: Field to sort by (default: created_at)
    - **sort_order**: Sort order - asc or desc (default: desc)

    **Returns:** Paginated list of item groups
    """
    item_group_service = ItemGroupService(db)

    item_groups, pagination = item_group_service.get_item_groups(
        organization_id=current_user.organization_id,
        page=page,
        page_size=page_size,
        is_active=is_active,
        parent_id=parent_id,
        search=search,
        sort_by=sort_by,
        sort_order=sort_order,
    )

    # Convert to response schema with tax info
    item_group_items = []
    for ig in item_groups:
        item = ItemGroupListItem.model_validate(ig)
        item.sales_tax_info = _build_tax_info(ig.sales_tax_template)
        item.purchase_tax_info = _build_tax_info(ig.purchase_tax_template)
        item_group_items.append(item)

    return ItemGroupListResponse(
        item_groups=item_group_items, pagination=PaginationMeta(**pagination)
    )


@router.get(
    "/tree",
    response_model=list[ItemGroupTreeNode],
    summary="Get item group tree",
    description="Get item groups as a hierarchical tree structure",
)
async def get_item_group_tree(
    current_user: CurrentUser = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    Get item groups as a tree structure.

    Requires authentication.

    **Returns:** List of root-level item groups with nested children
    """
    item_group_service = ItemGroupService(db)
    return item_group_service.get_item_group_tree(current_user.organization_id)


@router.get(
    "/active",
    response_model=list[ItemGroupListItem],
    summary="Get active item groups",
    description="Get all active item groups in the organization as a flat list",
)
async def get_active_item_groups(
    current_user: CurrentUser = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    Get all active item groups.

    Requires authentication.

    **Returns:** List of active item groups
    """
    item_group_service = ItemGroupService(db)
    item_groups = item_group_service.get_active_item_groups(
        current_user.organization_id
    )
    return [ItemGroupListItem.model_validate(ig) for ig in item_groups]


@router.get(
    "/{item_group_id}",
    response_model=ItemGroupResponse,
    summary="Get item group",
    description="Get item group details by ID",
)
async def get_item_group(
    item_group_id: UUID,
    current_user: CurrentUser = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    Get item group details by ID.

    Requires authentication.

    **Path Parameters:**
    - **item_group_id**: Item Group UUID

    **Returns:** Item group details including parent info
    """
    item_group_service = ItemGroupService(db)
    item_group = item_group_service.get_item_group_by_id(
        item_group_id=item_group_id,
        organization_id=current_user.organization_id,
        include_parent=True,
    )
    return ItemGroupResponse.model_validate(item_group)


@router.put(
    "/{item_group_id}",
    response_model=ItemGroupResponse,
    summary="Update item group",
    description="Update an existing item group",
)
async def update_item_group(
    item_group_id: UUID,
    item_group_data: ItemGroupUpdate,
    current_user: CurrentUser = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    Update an existing item group.

    Requires authentication.

    **Path Parameters:**
    - **item_group_id**: Item Group UUID

    **Request Body:** Fields to update (all optional)

    **Returns:** Updated item group details
    """
    item_group_service = ItemGroupService(db)
    item_group = item_group_service.update_item_group(
        item_group_id=item_group_id,
        item_group_data=item_group_data,
        organization_id=current_user.organization_id,
        user_id=current_user.id,
    )
    return ItemGroupResponse.model_validate(item_group)


@router.delete(
    "/{item_group_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete item group",
    description="Soft delete an item group",
)
async def delete_item_group(
    item_group_id: UUID,
    force: bool = Query(
        False, description="Force delete even if has children or items"
    ),
    current_user: CurrentUser = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    Soft delete an item group.

    Requires authentication.

    **Path Parameters:**
    - **item_group_id**: Item Group UUID

    **Query Parameters:**
    - **force**: Force delete even if has children or items (default: false)

    **Returns:** 204 No Content on success
    """
    item_group_service = ItemGroupService(db)
    item_group_service.delete_item_group(
        item_group_id=item_group_id,
        organization_id=current_user.organization_id,
        user_id=current_user.id,
        force=force,
    )
    return None


@router.post(
    "/import",
    response_model=ItemGroupImportResponse,
    status_code=status.HTTP_200_OK,
    summary="Import item groups from CSV",
    description="Upload a CSV file to bulk import/update item groups",
)
async def import_item_groups(
    file: UploadFile = File(..., description="CSV file with item group data"),
    current_user: CurrentUser = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> ItemGroupImportResponse:
    """
    Import item groups from a CSV file.

    - Upserts by `name`: if an item group with the same name exists, it is updated; otherwise a new one is created.
    - Auto-generates code if not provided.

    Supported columns: name, code, description, default_valuation_method, default_uom, is_active
    """
    if not file.filename:
        raise HTTPException(status_code=400, detail="File name is required.")

    ext = file.filename.rsplit(".", 1)[-1].lower() if "." in file.filename else ""
    if ext not in ("csv",):
        raise HTTPException(status_code=400, detail="Only CSV files are supported.")

    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")

    if len(content) > 5 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="File exceeds 5 MB limit.")

    try:
        text = content.decode("utf-8-sig")
    except UnicodeDecodeError:
        text = content.decode("latin-1")

    reader = csv.DictReader(io.StringIO(text))
    rows = list(reader)

    if not rows:
        raise HTTPException(status_code=400, detail="No data rows found in file.")

    if len(rows) > 500:
        raise HTTPException(status_code=400, detail="Maximum 500 rows allowed per import.")

    created = 0
    updated = 0
    failed = 0
    errors: list[dict] = []

    VALID_VALUATION_METHODS = {"fifo", "lifo", "moving_average", "standard"}

    for row_num, row in enumerate(rows, start=1):
        # Normalize keys
        row = {k.strip().lower(): (v.strip() if v else "") for k, v in row.items()}

        name = row.get("name", "")
        if not name:
            failed += 1
            errors.append({"row": row_num, "field": "name", "message": "Name is required"})
            continue

        code = row.get("code", "")
        if not code:
            code = name.upper().replace(" ", "_")[:50]

        try:
            # Check if item group with same name exists (upsert by name)
            existing = db.query(ItemGroup).filter(
                ItemGroup.organization_id == current_user.organization_id,
                ItemGroup.name == name,
                ItemGroup.deleted_at.is_(None),
            ).first()

            data: dict = {"name": name}

            # description
            if row.get("description"):
                data["description"] = row["description"]

            # default_valuation_method
            val_method = row.get("default_valuation_method", "").lower()
            if val_method and val_method in VALID_VALUATION_METHODS:
                data["default_valuation_method"] = val_method

            # default_uom
            if row.get("default_uom"):
                data["default_uom"] = row["default_uom"]

            # is_active
            is_active_str = row.get("is_active", "").lower()
            if is_active_str in ("true", "1", "yes", "t"):
                data["is_active"] = True
            elif is_active_str in ("false", "0", "no", "f"):
                data["is_active"] = False

            if existing:
                # Update existing item group
                data["updated_by"] = current_user.id
                for key, value in data.items():
                    setattr(existing, key, value)
                # Update code if provided
                if row.get("code"):
                    existing.code = code
                db.commit()
                updated += 1
            else:
                # Create new item group
                new_group = ItemGroup(
                    organization_id=current_user.organization_id,
                    code=code,
                    is_active=data.get("is_active", True),
                    created_by=current_user.id,
                    updated_by=current_user.id,
                    **{k: v for k, v in data.items() if k != "is_active"},
                )
                db.add(new_group)
                db.commit()
                created += 1

        except Exception as e:
            db.rollback()
            failed += 1
            errors.append({"row": row_num, "field": "general", "message": str(e)})
            logger.error(f"Item group import row {row_num} failed: {e}")

    return ItemGroupImportResponse(
        total_rows=len(rows),
        created=created,
        updated=updated,
        failed=failed,
        errors=errors,
    )
