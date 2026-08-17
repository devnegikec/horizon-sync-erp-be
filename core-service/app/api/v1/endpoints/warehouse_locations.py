"""Warehouse location layout and capacity API endpoints"""

from decimal import Decimal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.core.authorization import WAREHOUSE_CREATE, WAREHOUSE_READ, WAREHOUSE_UPDATE
from app.database import get_db
from app.dependencies import CurrentUser, require_permission
from app.models.warehouse import Warehouse
from app.schemas.common import PaginationMeta
from app.schemas.warehouse_location import (
    CreateLocationRequest,
    LocationResponse,
    LocationSummary,
    LocationTree,
    PaginatedLocations,
    UpdateLocationRequest,
)
from app.services.bin_capacity_service import BinCapacityService
from app.services.layout_service import LayoutService

router = APIRouter()


@router.post(
    "",
    response_model=LocationResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create warehouse location",
    description="Create a new location node in the warehouse hierarchy",
)
async def create_location(
    data: CreateLocationRequest,
    current_user: CurrentUser = Depends(require_permission(WAREHOUSE_CREATE)),
    db: Session = Depends(get_db),
):
    """
    Create a new warehouse location (zone, aisle, bay, level, or bin).

    Validates the parent-child hierarchy and generates the full_path code.

    **Request Body:**
    - **warehouse_id**: The warehouse this location belongs to
    - **parent_location_id**: Parent location UUID (None for zones)
    - **location_type**: One of zone, aisle, bay, level, bin
    - **code**: Short code for this location (e.g., Z01, A03)
    - **name**: Optional human-readable name
    - **capacity**: Storage capacity (default: 0)
    - **capacity_uom**: Unit of measure for capacity
    - **position_x**: X coordinate for routing
    - **position_y**: Y coordinate for routing

    **Returns:** Created location details
    """
    layout_service = LayoutService(db)
    location = layout_service.create_location(
        warehouse_id=data.warehouse_id,
        organization_id=current_user.organization_id,
        location_type=data.location_type,
        code=data.code,
        name=data.name,
        parent_location_id=data.parent_location_id,
        capacity=data.capacity,
        capacity_uom=data.capacity_uom,
        position_x=data.position_x,
        position_y=data.position_y,
    )
    return LocationResponse.model_validate(location)


@router.get(
    "/tree/{warehouse_id}",
    response_model=list[LocationTree],
    summary="Get location hierarchy tree",
    description="Get the full location hierarchy for a warehouse as a nested tree",
)
async def get_location_tree(
    warehouse_id: UUID,
    current_user: CurrentUser = Depends(require_permission(WAREHOUSE_READ)),
    db: Session = Depends(get_db),
):
    """
    Get the full location hierarchy for a warehouse as a nested tree.

    When volume-based capacity is enabled for the warehouse, capacity is
    calculated with the same engine as /capacity/warehouses/{id}/tree and the
    response carries m³ values instead of unit counts.

    **Path Parameters:**
    - **warehouse_id**: Warehouse UUID

    **Returns:** List of root-level locations with nested children
    """
    layout_service = LayoutService(db)
    tree = layout_service.get_tree(
        warehouse_id=warehouse_id,
        organization_id=current_user.organization_id,
    )

    warehouse = db.get(Warehouse, warehouse_id)
    if warehouse is not None and BinCapacityService._use_volume(warehouse):
        capacity_tree = BinCapacityService(db).get_capacity_tree(
            warehouse_id=warehouse_id,
            org_id=current_user.organization_id,
        )
        _merge_volume_capacity(tree, capacity_tree)

    return tree


def _merge_volume_capacity(locations: list[dict], capacity_tree: dict) -> None:
    """Overlay volume-based capacity values onto the location tree nodes."""
    cap_by_id: dict[str, dict] = {}

    def _index(node: dict) -> None:
        cap_by_id[node.get("node")] = node
        for child in node.get("children") or []:
            _index(child)

    _index(capacity_tree)

    def _merge(nodes: list[dict]) -> None:
        for node in nodes:
            cap = cap_by_id.get(str(node.get("id")))
            if cap:
                volume = cap.get("volume") or {}
                weight = cap.get("weight") or {}
                occupied_m3 = volume.get("occupied_m3") or Decimal("0")
                capacity_m3 = volume.get("capacity_m3")

                node["volume"] = volume
                node["weight"] = weight
                node["binding_pct"] = cap.get("binding_pct")
                node["bin_state"] = cap.get("bin_state")
                node["is_available"] = cap.get("is_available")

                node["capacity"] = (
                    capacity_m3 if capacity_m3 is not None else Decimal("0")
                )
                node["total_capacity"] = (
                    capacity_m3 if capacity_m3 is not None else Decimal("0")
                )
                node["available_capacity"] = (
                    capacity_m3 - occupied_m3
                    if capacity_m3 is not None
                    else Decimal("0")
                )
                node["capacity_uom"] = "m3"

            _merge(node.get("children") or [])

    _merge(locations)


@router.get(
    "/search",
    response_model=list[LocationResponse],
    summary="Search locations",
    description="Search locations by code or name (case-insensitive partial match)",
)
async def search_locations(
    warehouse_id: UUID = Query(..., description="Warehouse UUID to search within"),
    q: str = Query(..., min_length=1, description="Search query string"),
    limit: int = Query(20, ge=1, le=100, description="Maximum results to return"),
    current_user: CurrentUser = Depends(require_permission(WAREHOUSE_READ)),
    db: Session = Depends(get_db),
):
    """
    Search locations by code, full_path, or name.

    **Query Parameters:**
    - **warehouse_id**: Warehouse to search within
    - **q**: Search string (matches code, full_path, or name)
    - **limit**: Maximum results (default: 20, max: 100)

    **Returns:** List of matching locations
    """
    layout_service = LayoutService(db)
    locations = layout_service.search_locations(
        warehouse_id=warehouse_id,
        organization_id=current_user.organization_id,
        query=q,
        limit=limit,
    )
    return [LocationResponse.model_validate(loc) for loc in locations]


@router.get(
    "",
    response_model=PaginatedLocations,
    summary="List warehouse locations",
    description="Get paginated list of warehouse locations with optional filters",
)
async def list_locations(
    warehouse_id: UUID = Query(..., description="Warehouse UUID"),
    location_type: str | None = Query(
        None, description="Filter by type (zone, aisle, bay, level, bin)"
    ),
    parent_location_id: UUID | None = Query(
        None, description="Filter by parent location ID"
    ),
    is_active: bool | None = Query(None, description="Filter by active status"),
    has_stock: bool | None = Query(
        None, description="Filter to locations with stock > 0"
    ),
    page: int = Query(1, ge=1, description="Page number (1-indexed)"),
    page_size: int = Query(50, ge=1, le=100, description="Items per page (max 100)"),
    current_user: CurrentUser = Depends(require_permission(WAREHOUSE_READ)),
    db: Session = Depends(get_db),
):
    """
    List warehouse locations with optional filters and pagination.

    **Query Parameters:**
    - **warehouse_id**: Warehouse UUID (required)
    - **location_type**: Filter by type
    - **parent_location_id**: Filter by parent
    - **is_active**: Filter by active status
    - **has_stock**: Filter to locations with stock
    - **page**: Page number (default: 1)
    - **page_size**: Items per page (default: 50, max: 100)

    **Returns:** Paginated list of locations
    """
    layout_service = LayoutService(db)
    result = layout_service.list_locations(
        warehouse_id=warehouse_id,
        organization_id=current_user.organization_id,
        location_type=location_type,
        parent_location_id=parent_location_id,
        is_active=is_active,
        has_stock=has_stock,
        page=page,
        page_size=page_size,
    )

    locations = [LocationResponse.model_validate(loc) for loc in result["locations"]]

    return PaginatedLocations(
        locations=locations,
        pagination=PaginationMeta(**result["pagination"]),
    )


@router.get(
    "/{location_id}",
    response_model=LocationResponse,
    summary="Get warehouse location",
    description="Get a single warehouse location by ID",
)
async def get_location(
    location_id: UUID,
    current_user: CurrentUser = Depends(require_permission(WAREHOUSE_READ)),
    db: Session = Depends(get_db),
):
    """
    Get a single warehouse location by ID.

    **Path Parameters:**
    - **location_id**: Location UUID

    **Returns:** Location details
    """
    layout_service = LayoutService(db)
    location = layout_service._get_location(
        location_id=location_id,
        organization_id=current_user.organization_id,
    )
    return LocationResponse.model_validate(location)


@router.patch(
    "/{location_id}",
    response_model=LocationResponse,
    summary="Update warehouse location",
    description="Update a location's mutable fields (name, capacity, position)",
)
async def update_location(
    location_id: UUID,
    data: UpdateLocationRequest,
    current_user: CurrentUser = Depends(require_permission(WAREHOUSE_UPDATE)),
    db: Session = Depends(get_db),
):
    """
    Update a warehouse location's mutable fields.

    Does NOT allow changing location_type, parent, or code after creation.

    **Path Parameters:**
    - **location_id**: Location UUID

    **Request Body:** Fields to update (all optional)
    - **name**: New name
    - **capacity**: New capacity
    - **capacity_uom**: New capacity UOM
    - **position_x**: New X position
    - **position_y**: New Y position

    **Returns:** Updated location details
    """
    layout_service = LayoutService(db)
    location = layout_service.update_location(
        location_id=location_id,
        organization_id=current_user.organization_id,
        name=data.name,
        capacity=data.capacity,
        capacity_uom=data.capacity_uom,
        position_x=data.position_x,
        position_y=data.position_y,
    )
    return LocationResponse.model_validate(location)


@router.post(
    "/{location_id}/deactivate",
    response_model=LocationResponse,
    summary="Deactivate warehouse location",
    description="Deactivate a location and all its descendants",
)
async def deactivate_location(
    location_id: UUID,
    current_user: CurrentUser = Depends(require_permission(WAREHOUSE_UPDATE)),
    db: Session = Depends(get_db),
):
    """
    Deactivate a location and cascade to all descendants.

    Deactivated locations cannot receive new stock.

    **Path Parameters:**
    - **location_id**: Location UUID

    **Returns:** The deactivated location
    """
    layout_service = LayoutService(db)
    location = layout_service.deactivate_location(
        location_id=location_id,
        organization_id=current_user.organization_id,
    )
    return LocationResponse.model_validate(location)


@router.get(
    "/{location_id}/summary",
    response_model=LocationSummary,
    summary="Get location subtree summary",
    description="Get summary statistics for a location's subtree",
)
async def get_location_summary(
    location_id: UUID,
    current_user: CurrentUser = Depends(require_permission(WAREHOUSE_READ)),
    db: Session = Depends(get_db),
):
    """
    Get summary statistics for a location's subtree.

    Returns total bins, occupied bins, total/used/available capacity,
    and distinct item count within the subtree.

    **Path Parameters:**
    - **location_id**: Location UUID

    **Returns:** Summary statistics
    """
    layout_service = LayoutService(db)
    summary = layout_service.get_location_summary(
        location_id=location_id,
        organization_id=current_user.organization_id,
    )
    return LocationSummary(
        total_bins=summary["total_bins"],
        occupied_bins=summary["occupied_bins"],
        total_capacity=summary["total_capacity"],
        used_capacity=summary["used_capacity"],
        available_capacity=summary["available_capacity"],
        item_count=summary.get("distinct_items", 0),
    )


@router.get(
    "/{location_id}/qr-image",
    responses={
        404: {"description": "Location not found"},
    },
    summary="Generate QR code image for a bin location",
    description="Generate a printable QR code PNG for a bin. The QR encodes org, warehouse, and bin full path as JSON.",
)
async def get_location_qr_image(
    location_id: UUID,
    current_user: CurrentUser = Depends(require_permission(WAREHOUSE_READ)),
    db: Session = Depends(get_db),
):
    """Generate a printable QR code for a bin location.

    The QR encodes org, warehouse, and full bin path as JSON.
    Mobile app scans this to identify the exact bin during inbound/outbound.
    """
    import io

    import qrcode

    layout_service = LayoutService(db)
    payload = layout_service.get_location_qr_payload(
        location_id=location_id,
        organization_id=current_user.organization_id,
    )

    qr = qrcode.QRCode(
        version=None,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=10,
        border=2,
    )
    qr.add_data(payload.model_dump_json())
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")

    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)

    return StreamingResponse(
        buf,
        media_type="image/png",
        headers={
            "Content-Disposition": f"inline; filename=bin-qr-{payload.full_path}.png"
        },
    )


@router.get(
    "/by-qr/{qr_code}",
    response_model=LocationResponse,
    summary="Lookup bin by QR code",
    description="Find a bin location using its 5-character QR code",
)
async def lookup_by_qr_code(
    qr_code: str,
    current_user: CurrentUser = Depends(require_permission(WAREHOUSE_READ)),
    db: Session = Depends(get_db),
):
    """
    Lookup a bin location by its unique 5-character QR code.

    Returns the full location details including location_id (UUID)
    needed for put-away API calls.
    """
    from app.models.warehouse_location import WarehouseLocation

    loc = (
        db.query(WarehouseLocation)
        .filter(
            WarehouseLocation.qr_code == qr_code.upper(),
            WarehouseLocation.organization_id == current_user.organization_id,
        )
        .first()
    )
    if not loc:
        raise HTTPException(
            status_code=404, detail=f"Bin with QR code '{qr_code}' not found"
        )

    return LocationResponse.model_validate(loc)
