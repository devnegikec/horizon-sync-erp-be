"""JSON Layout Designer API endpoints.

Exposes:
- GET  /layout-design/rules               — diagnostic rule registry
- GET  /layout-design/examples            — import templates
- GET  /layout-design/examples/{name}     — one import template
- POST /layout-design/validate            — compile only, no writes
- POST /layout-design/preview             — compile + geometry, no writes
- POST /layout-design/apply               — compile + persist locations + floor plan
- GET  /layout-design/{plan_id}/document  — the stored document, for round-tripping

A document is validated *before* anything is written, and an apply that fails
never touches the warehouse: the endpoint returns 400 with the blocking rule code
in the envelope, so the UI can explain exactly which rule stopped it.

Design ref: docs/LAYOUT_JSON_DESIGNER_PLAN.md section 6
"""

from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.authorization import WAREHOUSE_MANAGE, WAREHOUSE_READ
from app.database import get_db
from app.dependencies import CurrentUser, require_permission
from app.schemas.layout_design import (
    LayoutApplyRequest,
    LayoutApplyResponse,
    LayoutExampleOut,
    LayoutPreviewRequest,
    LayoutPreviewResponse,
    LayoutRuleOut,
    LayoutValidateRequest,
    LayoutValidateResponse,
)
from app.services.layout_design_service import LayoutDesignService

router = APIRouter()


@router.get(
    "/rules", response_model=list[LayoutRuleOut], summary="List diagnostic rules"
)
async def list_layout_rules(
    current_user: CurrentUser = Depends(require_permission(WAREHOUSE_READ)),
    db: Session = Depends(get_db),
):
    """Return every rule the compiler can report, with its severity.

    The designer uses this to explain a code it received, so the rule catalogue
    lives on the server rather than being duplicated in the UI.
    """
    return LayoutDesignService(db).list_rules()


@router.get(
    "/examples", response_model=list[LayoutExampleOut], summary="List import templates"
)
async def list_layout_examples(
    current_user: CurrentUser = Depends(require_permission(WAREHOUSE_READ)),
    db: Session = Depends(get_db),
):
    """List the reference documents the designer offers as import templates."""
    examples = LayoutDesignService(db).list_examples()
    return [
        LayoutExampleOut(name=name, document=document)
        for name, document in examples.items()
    ]


@router.get(
    "/examples/{name}",
    response_model=LayoutExampleOut,
    summary="Get an import template",
)
async def get_layout_example(
    name: str,
    current_user: CurrentUser = Depends(require_permission(WAREHOUSE_READ)),
    db: Session = Depends(get_db),
):
    """Return one reference document by name (404 when unknown)."""
    examples = LayoutDesignService(db).list_examples()
    document = examples.get(name)
    if document is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "message": f"Unknown layout example '{name}'",
                "status_code": 404,
                "code": "LAYOUT_EXAMPLE_NOT_FOUND",
                "available": sorted(examples),
            },
        )
    return LayoutExampleOut(name=name, document=document)


@router.post(
    "/validate",
    response_model=LayoutValidateResponse,
    summary="Validate a layout document",
)
async def validate_layout_document(
    body: LayoutValidateRequest,
    current_user: CurrentUser = Depends(require_permission(WAREHOUSE_READ)),
    db: Session = Depends(get_db),
):
    """Compile a document and return its diagnostics and summary.

    Nothing is written, so this is safe to call on every edit or on paste.
    """
    return LayoutDesignService(db).validate(body.document)


@router.post(
    "/preview",
    response_model=LayoutPreviewResponse,
    summary="Preview a layout document",
)
async def preview_layout_document(
    body: LayoutPreviewRequest,
    current_user: CurrentUser = Depends(require_permission(WAREHOUSE_READ)),
    db: Session = Depends(get_db),
):
    """Compile a document and return the derived bins, zones and plan geometry.

    Nothing is written. ``limit`` caps how many bins come back, so a 100k-bin
    document cannot flood the response.
    """
    return LayoutDesignService(db).preview(body.document, limit=body.limit)


@router.post(
    "/apply",
    response_model=LayoutApplyResponse,
    summary="Apply a layout document",
)
async def apply_layout_document(
    body: LayoutApplyRequest,
    current_user: CurrentUser = Depends(require_permission(WAREHOUSE_MANAGE)),
    db: Session = Depends(get_db),
):
    """Compile a document and persist it as the warehouse's location hierarchy.

    Locations are upserted by ``full_path``: an existing bin keeps its id, so
    placements and stock keep pointing at it. Set ``replace_existing=true`` to
    soft-deactivate locations the new document no longer contains (historical
    stock rows are preserved either way).

    ``diagnostics`` in the response carries non-blocking warnings — notably
    ``BIN_OVER_CAPACITY_AFTER_APPLY`` when the applied limits leave an
    already-stocked bin below its contents (its available capacity will go
    negative until stock is removed).
    """
    result = LayoutDesignService(db).apply(
        warehouse_id=body.warehouse_id,
        organization_id=current_user.organization_id,
        document=body.document,
        name=body.name,
        description=body.description,
        replace_existing=body.replace_existing,
    )

    if not result.applyable or result.response is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "message": "The layout document has blocking errors and was not applied",
                "status_code": 400,
                "code": result.blocking_code or "LAYOUT_DOC_NOT_APPLYABLE",
                "diagnostics": [item.model_dump() for item in result.diagnostics],
            },
        )

    return result.response


@router.get(
    "/{floor_plan_id}/document",
    response_model=dict[str, Any],
    summary="Get the stored layout document",
)
async def get_layout_document(
    floor_plan_id: UUID,
    current_user: CurrentUser = Depends(require_permission(WAREHOUSE_READ)),
    db: Session = Depends(get_db),
):
    """Return the document stored on a floor plan, so it can be edited and re-imported."""
    document = LayoutDesignService(db).get_stored_document(
        floor_plan_id, current_user.organization_id
    )
    if document is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "message": "No layout document is stored on that floor plan",
                "status_code": 404,
                "code": "LAYOUT_DOC_NOT_STORED",
            },
        )
    return document
