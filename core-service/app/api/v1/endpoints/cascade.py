"""Cascade module API endpoints"""

from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import CurrentUser, require_permission
from app.models.qr_activation import QRTypeEnum
from app.schemas.cascade import (
    ChildQRRequest,
    ChildQRResponse,
    MappingChildRequest,
    MappingChildResponse,
    ParentQRCreate,
    ParentQRListResponse,
    ParentQRResponse,
    QRLabelDownloadRequest,
    QRScanCascadeRequest,
    QRScanCascadeResponse,
    QRTrackListResponse,
    QRTrackResponse,
    QRTrackUpdate,
)
from app.services.cascade_service import CascadeService

router = APIRouter()





@router.post("/parents", response_model=ParentQRResponse, status_code=status.HTTP_201_CREATED, summary="Create a parent QR node (e.g. shipper, pallet, container)",)
async def create_parent_track(
    data: ParentQRCreate,
    current_user: CurrentUser = Depends(require_permission("cascade.create")),
    db: Session = Depends(get_db),
):
    svc = CascadeService(db)
    track = svc.create_parent(data, current_user.organization_id, current_user.id)
    return ParentQRResponse.model_validate(track)



# ── QR Scan Cascade ───────────────────────────────────────────────────────────

@router.post(
    "/scan",
    response_model=QRScanCascadeResponse,
    summary="Scan QR and validate it can be cascaded",
)
async def scan_cascade(
    req: QRScanCascadeRequest,
   # request: Request,
    current_user: CurrentUser = Depends(require_permission("cascade.read")),
    db: Session = Depends(get_db),
):
    svc = CascadeService(db)
    sr_number =  await svc.scan_cascade(req, current_user.organization_id)
    return QRScanCascadeResponse(serial_number=sr_number)


# ── Child QR ──────────────────────────────────────────────────────────────────

@router.post(
    "/children",
    response_model=ChildQRResponse,
    summary="Get children for a parent QR",
)
async def get_children(
    req: ChildQRRequest,
    current_user: CurrentUser = Depends(require_permission("cascade.read")),
    db: Session = Depends(get_db),
):
    svc = CascadeService(db)
    result = await svc.get_children(req, current_user.organization_id)
    return ChildQRResponse(**result)


# ── Mapping ───────────────────────────────────────────────────────────────────

@router.post(
    "/map",
    response_model=MappingChildResponse,
    summary="Map children QR codes to a parent",
)
async def map_children(
    req: MappingChildRequest,
    current_user: CurrentUser = Depends(require_permission("cascade.create")),
    db: Session = Depends(get_db),
):
    svc = CascadeService(db)
    serial_list = [s.strip() for s in req.srnumber.split(",") if s.strip()]
    svc.map_children(req.parent_srnumber, serial_list, current_user.organization_id)
    return MappingChildResponse(message="Cascade completed successfully.")


# ── Label Download ────────────────────────────────────────────────────────────




@router.post("/label-download")
async def get_label_download(
    req: QRLabelDownloadRequest,
    current_user: CurrentUser = Depends(require_permission("cascade.read")),
    db: Session = Depends(get_db),
):
    svc = CascadeService(db)

    content, filename = svc.get_label_stream(
            req.parent_srnumber,
            current_user.organization_id,
        )

    return StreamingResponse(
            iter([content]),
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={
                "Content-Disposition": f"attachment; filename={filename}"
            },
        )

    # return StreamingResponse(
    #     iter([content]),
    #     media_type="image/png",
    #     headers={
    #         "Content-Disposition": f"attachment; filename={filename}"
    #     },
    # )

    # try:
    #     # ✅ Try signed URL first
    #     url, expires_at = svc.get_label_download_url(
    #         req.parent_srnumber,
    #         current_user.organization_id,
    #     )

    #     return {
    #         "download_url": url,
    #         "expires_at": expires_at,
    #     }

    # except HTTPException:
    #     # 🔁 Fallback → generate file
    #     content, filename = svc.get_label_stream(
    #         req.parent_srnumber,
    #         current_user.organization_id,
    #     )

    #     return StreamingResponse(
    #         iter([content]),
    #         media_type="image/png",
    #         headers={
    #             "Content-Disposition": f"attachment; filename={filename}"
    #         },
    #     )




@router.get(
    "/parents",
    response_model=ParentQRListResponse,
    summary="List parent QR nodes",
)
def list_parent(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    qr_type: QRTypeEnum | None = None,
   # qr_type: QRTypeEnum | None = Query(None,description="Filter by QR type",example="pallet"),
    current_user: CurrentUser = Depends(require_permission("cascade.read")),
    db: Session = Depends(get_db),
):
    svc = CascadeService(db)
    qr_type_value = qr_type.value if qr_type else None
    return svc.list_parents(current_user.organization_id, page, page_size, qr_type_value)






@router.get(
    "/tracks/history",
    response_model=QRTrackListResponse,
    summary="List history QR tracks ",
)
async def list_history_tracks(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    qr_type: QRTypeEnum | None = Query(None,description="Filter by QR type",example="pallet"),
    current_user: CurrentUser = Depends(require_permission("cascade.read")),
    db: Session = Depends(get_db),
):
    svc = CascadeService(db)
    return svc.list_history(current_user.organization_id, page, page_size, qr_type.value)

@router.patch(
    "/tracks/{track_id}",
    response_model=QRTrackResponse,
    summary="Update QR activation track",
)
async def update_track(
    track_id: UUID,
    data: QRTrackUpdate,
    current_user: CurrentUser = Depends(require_permission("cascade.update")),
    db: Session = Depends(get_db),
):
    svc = CascadeService(db)
    track = svc.update_track(track_id, data, current_user.organization_id)
    return QRTrackResponse.model_validate(track)


# @router.get(
#     "/tracks",
#     response_model=QRTrackListResponse,
#     summary="List parent QR tracks ",
# )
# async def list_parent_tracks(
#     page: int = Query(1, ge=1),
#     page_size: int = Query(20, ge=1, le=100),
#     qr: str | None = Query(None),
#     current_user: CurrentUser = Depends(require_permission("cascade.read")),
#     db: Session = Depends(get_db),
# ):
#     svc = CascadeService(db)
#     items, pagination = svc.list_parents(
#         current_user.organization_id, page, page_size, search
#     )
#     return QRTrackListResponse(
#         items=[QRTrackResponse.model_validate(i) for i in items],
#         pagination=pagination,
#     )
