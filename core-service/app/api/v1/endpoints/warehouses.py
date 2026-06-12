"""Warehouse management API endpoints"""

import csv
import io
import logging
from uuid import UUID

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.authorization import (
    WAREHOUSE_CREATE,
    WAREHOUSE_DELETE,
    WAREHOUSE_READ,
    WAREHOUSE_UPDATE,
)
from app.database import get_db
from app.dependencies import CurrentUser, require_permission
from app.models.base import WarehouseType, WarehouseUserRole
from app.models.warehouse import Warehouse
from app.schemas.common import PaginationMeta
from app.schemas.warehouse import (
    WarehouseCreate,
    WarehouseListItem,
    WarehouseListResponse,
    WarehouseResponse,
    WarehouseStatusCounts,
    WarehouseTreeNode,
    WarehouseTypeCounts,
    WarehouseUpdate,
)
from app.services.warehouse_service import WarehouseService
from app.services.warehouse_user_service import WarehouseUserService

logger = logging.getLogger(__name__)

router = APIRouter()


class WarehouseImportResponse(BaseModel):
    total_rows: int
    created: int
    updated: int
    failed: int
    errors: list[dict]


@router.post(
    "",
    response_model=WarehouseResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create warehouse",
    description="Create a new warehouse",
)
async def create_warehouse(
    warehouse_data: WarehouseCreate,
    current_user: CurrentUser = Depends(require_permission(WAREHOUSE_CREATE)),
    db: Session = Depends(get_db),
):
    """
    Create a new warehouse.

    Requires authentication.

    **Request Body:**
    - **name**: Warehouse name (required)
    - **code**: Unique warehouse code (required)
    - **description**: Warehouse description
    - **warehouse_type**: Type (warehouse, store, virtual, transit)
    - **parent_warehouse_id**: Parent warehouse for hierarchy
    - **address_line1, city, state, etc.**: Address information
    - **contact_name, contact_phone, contact_email**: Contact information
    - **total_capacity, capacity_uom**: Capacity information
    - **is_active**: Active status (default: true)
    - **is_default**: Default warehouse flag

    **Returns:** Created warehouse details
    """
    warehouse_service = WarehouseService(db)
    warehouse = warehouse_service.create_warehouse(
        warehouse_data=warehouse_data,
        organization_id=current_user.organization_id,
        user_id=current_user.id,
    )

    # Auto-assign creator so the warehouse appears in /my-warehouses
    wh_user_svc = WarehouseUserService(db)
    wh_user_svc.create(
        data={
            "user_id": current_user.id,
            "warehouse_id": warehouse.id,
            "role": WarehouseUserRole.MANAGER,
            "is_primary": False,
            "is_active": True,
        },
        organization_id=current_user.organization_id,
        created_by=current_user.id,
    )
    db.commit()

    return WarehouseResponse.model_validate(warehouse)


@router.get(
    "",
    response_model=WarehouseListResponse,
    summary="List warehouses",
    description="Get paginated list of warehouses with optional filters",
)
async def list_warehouses(
    page: int = Query(1, ge=1, description="Page number (1-indexed)"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page (max 100)"),
    is_active: bool | None = Query(None, description="Filter by active status"),
    warehouse_type: str | None = Query(
        None, description="Filter by type (warehouse, store, virtual, transit)"
    ),
    parent_warehouse_id: UUID | None = Query(
        None, description="Filter by parent warehouse ID"
    ),
    search: str | None = Query(None, description="Search in name, code, city"),
    sort_by: str = Query("created_at", description="Field to sort by"),
    sort_order: str = Query("desc", pattern="^(asc|desc)$", description="Sort order"),
    scope: str = Query(
        "assigned",
        pattern="^(assigned|all)$",
        description="Scope: 'assigned' (default) = only user's assigned warehouses; 'all' = all organization warehouses",
    ),
    current_user: CurrentUser = Depends(require_permission(WAREHOUSE_READ)),
    db: Session = Depends(get_db),
):
    """
    List warehouses with pagination and filters.

    Requires authentication.

    **Query Parameters:**
    - **page**: Page number (default: 1)
    - **page_size**: Items per page (default: 20, max: 100)
    - **is_active**: Filter by active status
    - **warehouse_type**: Filter by warehouse type
    - **parent_warehouse_id**: Filter by parent warehouse
    - **search**: Search term for name, code, city
    - **sort_by**: Field to sort by (default: created_at)
    - **sort_order**: Sort order - asc or desc (default: desc)
    - **scope**: 'assigned' (default) for user-scoped view, 'all' for organization-wide view (e.g. ASN destination selection)

    **Returns:** Paginated list of warehouses with status and type counts
    """
    # Determine scoped warehouse IDs for this user
    allowed_warehouse_ids = None
    if current_user.user_type != "system_admin" and scope != "all":
        wh_user_svc = WarehouseUserService(db)
        scoped_warehouses = wh_user_svc.get_user_warehouses(
            user_id=current_user.id,
            organization_id=current_user.organization_id,
            user_type=current_user.user_type,
            user_email=current_user.email,
        )
        allowed_warehouse_ids = [w["id"] for w in scoped_warehouses]

    warehouse_service = WarehouseService(db)

    (
        warehouses,
        pagination,
        status_counts,
        type_counts,
    ) = warehouse_service.get_warehouses(
        organization_id=current_user.organization_id,
        page=page,
        page_size=page_size,
        is_active=is_active,
        warehouse_type=warehouse_type,
        parent_warehouse_id=parent_warehouse_id,
        search=search,
        sort_by=sort_by,
        sort_order=sort_order,
        warehouse_ids=allowed_warehouse_ids,
    )

    # Convert to response schema
    warehouse_items = [WarehouseListItem.model_validate(w) for w in warehouses]

    return WarehouseListResponse(
        warehouses=warehouse_items,
        pagination=PaginationMeta(**pagination),
        status_counts=WarehouseStatusCounts(**status_counts),
        type_counts=WarehouseTypeCounts(**type_counts),
    )


@router.get(
    "/tree",
    response_model=list[WarehouseTreeNode],
    summary="Get warehouse tree",
    description="Get warehouses as a hierarchical tree structure",
)
async def get_warehouse_tree(
    current_user: CurrentUser = Depends(require_permission(WAREHOUSE_READ)),
    db: Session = Depends(get_db),
):
    """
    Get warehouses as a tree structure.

    Requires authentication.

    **Returns:** List of root-level warehouses with nested children
    """
    warehouse_service = WarehouseService(db)
    return warehouse_service.get_warehouse_tree(current_user.organization_id)


@router.get(
    "/{warehouse_id}",
    response_model=WarehouseResponse,
    summary="Get warehouse",
    description="Get warehouse details by ID",
)
async def get_warehouse(
    warehouse_id: UUID,
    current_user: CurrentUser = Depends(require_permission(WAREHOUSE_READ)),
    db: Session = Depends(get_db),
):
    """
    Get warehouse details by ID.

    Requires authentication.

    **Path Parameters:**
    - **warehouse_id**: Warehouse UUID

    **Returns:** Warehouse details including parent info
    """
    warehouse_service = WarehouseService(db)
    warehouse = warehouse_service.get_warehouse_by_id(
        warehouse_id=warehouse_id,
        organization_id=current_user.organization_id,
        include_parent=True,
    )
    return WarehouseResponse.model_validate(warehouse)


@router.put(
    "/{warehouse_id}",
    response_model=WarehouseResponse,
    summary="Update warehouse",
    description="Update an existing warehouse",
)
async def update_warehouse(
    warehouse_id: UUID,
    warehouse_data: WarehouseUpdate,
    current_user: CurrentUser = Depends(require_permission(WAREHOUSE_UPDATE)),
    db: Session = Depends(get_db),
):
    """
    Update an existing warehouse.

    Requires authentication.

    **Path Parameters:**
    - **warehouse_id**: Warehouse UUID

    **Request Body:** Fields to update (all optional)

    **Returns:** Updated warehouse details
    """
    warehouse_service = WarehouseService(db)
    warehouse = warehouse_service.update_warehouse(
        warehouse_id=warehouse_id,
        warehouse_data=warehouse_data,
        organization_id=current_user.organization_id,
        user_id=current_user.id,
    )
    return WarehouseResponse.model_validate(warehouse)


@router.delete(
    "/{warehouse_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete warehouse",
    description="Soft delete a warehouse",
)
async def delete_warehouse(
    warehouse_id: UUID,
    current_user: CurrentUser = Depends(require_permission(WAREHOUSE_DELETE)),
    db: Session = Depends(get_db),
):
    """
    Soft delete a warehouse.

    Requires authentication.

    **Path Parameters:**
    - **warehouse_id**: Warehouse UUID

    **Returns:** 204 No Content on success
    """
    warehouse_service = WarehouseService(db)
    warehouse_service.delete_warehouse(
        warehouse_id=warehouse_id,
        organization_id=current_user.organization_id,
        user_id=current_user.id,
    )
    return None


@router.post(
    "/import",
    response_model=WarehouseImportResponse,
    status_code=status.HTTP_200_OK,
    summary="Import warehouses from CSV",
    description="Upload a CSV file to bulk import/update warehouses",
)
async def import_warehouses(
    file: UploadFile = File(..., description="CSV file with warehouse data"),
    current_user: CurrentUser = Depends(require_permission(WAREHOUSE_CREATE)),
    db: Session = Depends(get_db),
) -> WarehouseImportResponse:
    """
    Import warehouses from a CSV file.

    - Upserts by `code`: if a warehouse with the same code exists, it is updated; otherwise a new one is created.
    - Auto-generates code if not provided (WH-XXXX format).

    Supported columns: name, code, description, warehouse_type, is_active,
    address_line1, address_line2, city, state, country, postal_code,
    contact_name, contact_phone, contact_email, total_capacity, capacity_uom
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

    # Auto-generate code counter
    code_counter = db.query(Warehouse).filter(
        Warehouse.organization_id == current_user.organization_id
    ).count()

    VALID_TYPES = {"warehouse", "store", "transit", "virtual"}
    STRING_FIELDS = [
        "name", "description", "address_line1", "address_line2",
        "city", "state", "country", "postal_code",
        "contact_name", "contact_phone", "contact_email", "capacity_uom",
    ]

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
            code_counter += 1
            code = f"WH-{code_counter:04d}"

        try:
            # Check if warehouse with same code exists (upsert)
            existing = db.query(Warehouse).filter(
                Warehouse.organization_id == current_user.organization_id,
                Warehouse.code == code,
                Warehouse.deleted_at.is_(None),
            ).first()

            # Build data dict
            data: dict = {"name": name}
            for field in STRING_FIELDS:
                if field in row and row[field]:
                    data[field] = row[field]

            # warehouse_type
            wh_type_str = row.get("warehouse_type", "").lower()
            if wh_type_str and wh_type_str in VALID_TYPES:
                data["warehouse_type"] = WarehouseType(wh_type_str)

            # is_active
            is_active_str = row.get("is_active", "").lower()
            if is_active_str in ("true", "1", "yes", "t"):
                data["is_active"] = True
            elif is_active_str in ("false", "0", "no", "f"):
                data["is_active"] = False

            # total_capacity
            capacity_str = row.get("total_capacity", "")
            if capacity_str:
                try:
                    data["total_capacity"] = int(float(capacity_str))
                except (ValueError, TypeError):
                    pass

            if existing:
                # Update existing warehouse
                data["updated_by"] = current_user.id
                for key, value in data.items():
                    setattr(existing, key, value)
                db.commit()
                updated += 1
            else:
                # Create new warehouse
                new_warehouse = Warehouse(
                    organization_id=current_user.organization_id,
                    code=code,
                    created_by=current_user.id,
                    updated_by=current_user.id,
                    **data,
                )
                db.add(new_warehouse)
                db.commit()
                db.refresh(new_warehouse)
                created += 1

                # Auto-assign importer to the new warehouse so it appears in /my-warehouses
                wh_user_svc = WarehouseUserService(db)
                wh_user_svc.create(
                    data={
                        "user_id": current_user.id,
                        "warehouse_id": new_warehouse.id,
                        "role": WarehouseUserRole.MANAGER,
                        "is_primary": False,
                        "is_active": True,
                    },
                    organization_id=current_user.organization_id,
                    created_by=current_user.id,
                )
                db.commit()

        except Exception as e:
            db.rollback()
            failed += 1
            errors.append({"row": row_num, "field": "general", "message": str(e)})
            logger.error(f"Warehouse import row {row_num} failed: {e}")

    return WarehouseImportResponse(
        total_rows=len(rows),
        created=created,
        updated=updated,
        failed=failed,
        errors=errors,
    )
