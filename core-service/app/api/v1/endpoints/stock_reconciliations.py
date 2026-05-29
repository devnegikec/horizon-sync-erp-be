"""Stock reconciliations and items API endpoints"""

import logging
from uuid import UUID

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    Query,
    UploadFile,
    status,
)
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import CurrentUser, get_current_active_user
from app.schemas.common import PaginationMeta
from app.schemas.stock_reconciliation import (
    ReconciliationUploadPreview,
    StockReconciliationCreate,
    StockReconciliationItemCreate,
    StockReconciliationItemResponse,
    StockReconciliationItemUpdate,
    StockReconciliationListItem,
    StockReconciliationListResponse,
    StockReconciliationResponse,
    StockReconciliationUpdate,
)
from app.services.stock_reconciliation_service import StockReconciliationService
from app.services.stock_reconciliation_wizard_service import (
    StockReconciliationWizardService,
)

logger = logging.getLogger(__name__)

router = APIRouter()


# =====================================================================
# Wizard endpoints (must be before /{rec_id} to avoid path conflicts)
# =====================================================================


@router.get(
    "/template",
    summary="Download CSV template for stock reconciliation",
    response_class=Response,
    responses={200: {"content": {"text/csv": {}}, "description": "CSV template file"}},
)
async def download_reconciliation_template(
    warehouse_id: UUID = Query(..., description="Warehouse to generate template for"),
    current_user: CurrentUser = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Download a CSV template pre-populated with current stock for the selected warehouse."""
    svc = StockReconciliationWizardService(db)
    try:
        content = svc.generate_template_csv(warehouse_id, current_user.organization_id)
    except Exception as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    return Response(
        content=content,
        media_type="text/csv",
        headers={
            "Content-Disposition": 'attachment; filename="stock_reconciliation_template.csv"'
        },
    )


@router.post(
    "/upload",
    response_model=ReconciliationUploadPreview,
    status_code=status.HTTP_200_OK,
    summary="Upload CSV and preview discrepancies",
)
async def upload_reconciliation(
    warehouse_id: str = Form(..., description="Warehouse UUID"),
    file: UploadFile = File(..., description="CSV file with actual_qty filled in"),
    current_user: CurrentUser = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    Upload a filled-in CSV template. The backend compares actual_qty vs system_qty
    and returns a preview of discrepancies. No stock is adjusted yet.
    """
    if not file.filename or not file.filename.lower().endswith(".csv"):
        raise HTTPException(status_code=400, detail="Only CSV files are supported.")

    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")
    if len(content) > 10 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="File exceeds the 10 MB limit.")

    try:
        wh_id = UUID(warehouse_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid warehouse_id format.")

    svc = StockReconciliationWizardService(db)
    try:
        result = svc.upload_and_preview(
            wh_id, content, current_user.organization_id, current_user.id
        )
    except Exception as exc:
        logger.exception("Reconciliation upload failed")
        status_code = getattr(exc, "status_code", 422)
        detail = str(exc)
        # Include per-row validation errors if available
        if hasattr(exc, "details") and exc.details:
            detail = {"message": str(exc), "errors": exc.details}
        raise HTTPException(status_code=status_code, detail=detail)
    return result


@router.post(
    "/{reconciliation_id}/confirm",
    response_model=StockReconciliationResponse,
    summary="Confirm and commit reconciliation adjustments",
)
async def confirm_reconciliation(
    reconciliation_id: UUID,
    current_user: CurrentUser = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    After reviewing discrepancies, confirm to commit stock adjustments.
    Updates quantity_on_hand in stock_levels and creates stock_movement audit records.
    """
    svc = StockReconciliationWizardService(db)
    try:
        rec = svc.confirm(
            reconciliation_id, current_user.organization_id, current_user.id
        )
    except Exception as exc:
        logger.exception("Reconciliation confirm failed")
        status_code = getattr(exc, "status_code", 422)
        if "not found" in str(exc).lower():
            status_code = 404
        raise HTTPException(status_code=status_code, detail=str(exc))
    return StockReconciliationResponse.model_validate(rec)


# =====================================================================
# Standard CRUD endpoints
# =====================================================================


@router.post(
    "", response_model=StockReconciliationResponse, status_code=status.HTTP_201_CREATED
)
async def create_stock_reconciliation(
    data: StockReconciliationCreate,
    current_user: CurrentUser = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Create a stock reconciliation with optional line items."""
    svc = StockReconciliationService(db)
    r = svc.create(data, current_user.organization_id, current_user.id)
    return StockReconciliationResponse.model_validate(r)


@router.get("", response_model=StockReconciliationListResponse)
async def list_stock_reconciliations(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: str | None = Query(None),
    warehouse_id: UUID | None = Query(None, description="Filter by warehouse"),
    search: str | None = None,
    sort_by: str = Query("posting_date"),
    sort_order: str = Query("desc", pattern="^(asc|desc)$"),
    current_user: CurrentUser = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """List stock reconciliations with filters."""
    svc = StockReconciliationService(db)
    items, pagination = svc.get_list(
        organization_id=current_user.organization_id,
        status=status,
        warehouse_id=warehouse_id,
        search=search,
        page=page,
        page_size=page_size,
        sort_by=sort_by,
        sort_order=sort_order,
    )
    return StockReconciliationListResponse(
        stock_reconciliations=[
            StockReconciliationListItem.model_validate(r) for r in items
        ],
        pagination=PaginationMeta(**pagination),
    )


@router.get("/{rec_id}", response_model=StockReconciliationResponse)
async def get_stock_reconciliation(
    rec_id: UUID,
    current_user: CurrentUser = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Get stock reconciliation by ID including line items."""
    svc = StockReconciliationService(db)
    r = svc.get_by_id(rec_id, current_user.organization_id)
    return StockReconciliationResponse.model_validate(r)


@router.put("/{rec_id}", response_model=StockReconciliationResponse)
async def update_stock_reconciliation(
    rec_id: UUID,
    data: StockReconciliationUpdate,
    current_user: CurrentUser = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Update stock reconciliation header (draft only)."""
    svc = StockReconciliationService(db)
    svc.update(rec_id, data, current_user.organization_id, current_user.id)
    return StockReconciliationResponse.model_validate(
        svc.get_by_id(rec_id, current_user.organization_id)
    )


@router.delete("/{rec_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_stock_reconciliation(
    rec_id: UUID,
    current_user: CurrentUser = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Delete a draft stock reconciliation."""
    StockReconciliationService(db).delete(rec_id, current_user.organization_id)
    return None


# ----- Items (sub-resource) -----


@router.post(
    "/{rec_id}/items",
    response_model=StockReconciliationItemResponse,
    status_code=status.HTTP_201_CREATED,
)
async def add_stock_reconciliation_item(
    rec_id: UUID,
    data: StockReconciliationItemCreate,
    current_user: CurrentUser = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Add a line item to a draft stock reconciliation."""
    svc = StockReconciliationService(db)
    it = svc.add_item(rec_id, data, current_user.organization_id)
    return StockReconciliationItemResponse.model_validate(it)


@router.put("/{rec_id}/items/{item_id}", response_model=StockReconciliationItemResponse)
async def update_stock_reconciliation_item(
    rec_id: UUID,
    item_id: UUID,
    data: StockReconciliationItemUpdate,
    current_user: CurrentUser = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Update a line item in a draft stock reconciliation."""
    svc = StockReconciliationService(db)
    it = svc.update_item(rec_id, item_id, data, current_user.organization_id)
    return StockReconciliationItemResponse.model_validate(it)


@router.delete("/{rec_id}/items/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_stock_reconciliation_item(
    rec_id: UUID,
    item_id: UUID,
    current_user: CurrentUser = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Remove a line item from a draft stock reconciliation."""
    StockReconciliationService(db).delete_item(
        rec_id, item_id, current_user.organization_id
    )
    return None
