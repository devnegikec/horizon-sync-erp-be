"""ASN ingestion API endpoints for ai-service.

Upload → Parse → Extract → Validate → Draft ASN
"""

import logging
import os
import shutil
import uuid
from datetime import datetime, timezone
from pathlib import Path
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Body, Depends, File, Form, HTTPException, UploadFile, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.clients.core_service import core_client
from app.config import settings
from app.database import SessionLocal, get_db
from app.models.ingestion_job import AsnSourceType, IngestionJob, IngestionStatus
from app.services.doc_parser import get_parser
from app.services.extractor import get_extractor
from app.services.ingestion_validator import get_validator

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/asn", tags=["asn-ingestion"])

# Ensure upload directory exists
UPLOAD_DIR = Path(os.environ.get("UPLOAD_DIR", "/tmp/ai-uploads"))
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


# ── Schemas ──────────────────────────────────────────────────────────────
class IngestResponse(BaseModel):
    job_id: UUID
    status: str
    message: str


class JobStatusResponse(BaseModel):
    job_id: UUID
    status: str
    status_message: str | None = None
    original_filename: str
    source_type: str | None = None
    document_type: str | None = None
    rejection_reason: str | None = None
    confidence_score: float | None = None
    low_confidence_fields: list[str] = Field(default_factory=list)
    validation_errors: list[str] = Field(default_factory=list)
    draft_asn_order_id: UUID | None = None
    draft_asn_order_number: str | None = None
    extracted_json: dict | None = None
    created_at: datetime
    updated_at: datetime
    completed_at: datetime | None = None


class AsnLineItem(BaseModel):
    sku: str
    item_name: str
    quantity: int = Field(..., gt=0)
    uom: str = "pieces"
    batch_no: str | None = None
    serial_nos: list[str] = Field(default_factory=list)
    unit_cost: float | None = None


class CreateAsnRequest(BaseModel):
    """Structured ASN data for manual entry (no document upload)."""

    supplier_name: str
    supplier_id: UUID | None = None
    expected_delivery_date: str | None = None  # YYYY-MM-DD
    warehouse_id: UUID
    line_items: list[AsnLineItem] = Field(..., min_length=1)
    po_reference: str | None = None
    vehicle_number: str | None = None
    driver_name: str | None = None
    organization_id: UUID | None = None
    created_by_user_id: UUID | None = None
    notes: str | None = None


class ReviewAction(BaseModel):
    action: str  # confirm | reject
    review_notes: str | None = None
    corrected_json: dict | None = None


# ── Endpoints ──────────────────────────────────────────────────────────────
@router.post(
    "/ingest",
    response_model=IngestResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Upload an ASN document for ingestion",
)
async def ingest_asn_document(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(..., description="PDF, Excel, or image containing ASN data"),
    organization_id: str | None = Form(None, description="Organization UUID"),
    warehouse_id: str | None = Form(None, description="Destination warehouse UUID"),
    db: Session = Depends(get_db),
):
    """Upload an ASN document and kick off the ingestion pipeline.

    Returns a job_id immediately. Poll GET /ai/asn/ingest/{job_id} for status.
    """
    # Validate file size (max 20 MB)
    max_size = 20 * 1024 * 1024
    file_bytes = await file.read()
    if len(file_bytes) > max_size:
        raise HTTPException(status_code=413, detail="File exceeds 20 MB limit")

    # Store raw file
    ext = Path(file.filename or "unknown").suffix
    stored_name = f"{uuid.uuid4().hex}{ext}"
    stored_path = UPLOAD_DIR / stored_name
    with open(stored_path, "wb") as f:
        f.write(file_bytes)

    # Create job record
    job = IngestionJob(
        original_filename=file.filename or "unknown",
        stored_path=str(stored_path),
        file_type=file.content_type,
        status=IngestionStatus.PENDING,
        source_type=AsnSourceType.DOCUMENT_UPLOAD,
        organization_id=UUID(organization_id) if organization_id else None,
        warehouse_id=UUID(warehouse_id) if warehouse_id else None,
    )
    db.add(job)
    db.commit()
    db.refresh(job)

    logger.info("Ingestion job %s created for %s", job.id, job.original_filename)

    # Kick off pipeline in background so we can return 202 immediately
    background_tasks.add_task(_run_pipeline_sync, job.id)

    return IngestResponse(
        job_id=job.id,
        status=job.status.value,
        message="Ingestion job accepted. Poll /ai/asn/ingest/{job_id} for status.",
    )


def _run_pipeline_sync(job_id: UUID) -> None:
    """Synchronous wrapper for the async pipeline (for BackgroundTasks)."""
    import asyncio
    db = SessionLocal()
    try:
        asyncio.run(run_ingestion_pipeline(job_id, db))
    finally:
        db.close()


@router.get("/ingest/{job_id}", response_model=JobStatusResponse)
async def get_ingestion_status(
    job_id: UUID,
    db: Session = Depends(get_db),
):
    """Get the status and results of an ingestion job."""
    job = db.query(IngestionJob).filter(IngestionJob.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Ingestion job not found")

    return JobStatusResponse(
        job_id=job.id,
        status=job.status.value,
        status_message=job.status_message,
        original_filename=job.original_filename,
        source_type=job.source_type.value if job.source_type else None,
        document_type=job.document_type,
        rejection_reason=job.rejection_reason,
        confidence_score=job.confidence_score,
        low_confidence_fields=job.low_confidence_fields or [],
        validation_errors=job.validation_errors or [],
        draft_asn_order_id=job.draft_asn_order_id,
        draft_asn_order_number=job.draft_asn_order_number,
        extracted_json=job.extracted_json,
        created_at=job.created_at,
        updated_at=job.updated_at,
        completed_at=job.completed_at,
    )


# ── Manual ASN creation endpoint (no document upload) ────────────────────
@router.post(
    "/create",
    response_model=IngestResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Create an ASN directly from structured data",
)
async def create_asn_directly(
    background_tasks: BackgroundTasks,
    request: CreateAsnRequest = Body(...),
    db: Session = Depends(get_db),
):
    """Create an ASN directly from structured data without uploading a document.

    Skips parse/classify/extract. Goes straight to validation → draft creation.
    Used by warehouse operators, inter-warehouse transfers, and supplier APIs.

    Returns a job_id immediately. Poll GET /ai/asn/ingest/{job_id} for status.
    """
    # Build extracted JSON from request
    extracted = {
        "supplier_name": request.supplier_name,
        "supplier_id": str(request.supplier_id) if request.supplier_id else None,
        "expected_delivery_date": request.expected_delivery_date,
        "vehicle_number": request.vehicle_number,
        "driver_name": request.driver_name,
        "po_reference": request.po_reference,
        "line_items": [
            {
                "sku": item.sku,
                "item_name": item.item_name,
                "quantity": item.quantity,
                "uom": item.uom,
                "batch_no": item.batch_no,
                "serial_nos": item.serial_nos,
                "unit_cost": item.unit_cost,
            }
            for item in request.line_items
        ],
        "confidence_score": 1.0,
        "low_confidence_fields": [],
    }

    job = IngestionJob(
        original_filename="manual_entry",
        stored_path=None,
        file_type=None,
        status=IngestionStatus.VALIDATING,
        source_type=AsnSourceType.MANUAL_ENTRY,
        extracted_json=extracted,
        confidence_score=1.0,
        organization_id=request.organization_id,
        warehouse_id=request.warehouse_id,
        created_by_user_id=request.created_by_user_id,
    )
    db.add(job)
    db.commit()
    db.refresh(job)

    logger.info("Manual ASN job %s created by user %s", job.id, request.created_by_user_id)

    background_tasks.add_task(_run_manual_pipeline_sync, job.id, extracted)

    return IngestResponse(
        job_id=job.id,
        status=job.status.value,
        message="Manual ASN accepted. Validating and creating draft. Poll /ai/asn/ingest/{job_id} for status.",
    )


def _run_manual_pipeline_sync(job_id: UUID, extracted: dict) -> None:
    """Synchronous wrapper for manual pipeline (for BackgroundTasks)."""
    import asyncio

    db = SessionLocal()
    try:
        asyncio.run(run_manual_pipeline(job_id, extracted, db))
    finally:
        db.close()


@router.post("/ingest/{job_id}/review", response_model=JobStatusResponse)
async def review_ingestion_job(
    job_id: UUID,
    action: ReviewAction = Body(...),
    db: Session = Depends(get_db),
):
    """Confirm or reject a draft ASN after human review."""
    job = db.query(IngestionJob).filter(IngestionJob.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Ingestion job not found")

    if job.status not in (IngestionStatus.DRAFT_CREATED, IngestionStatus.MANUAL_REVIEW):
        raise HTTPException(
            status_code=400,
            detail=f"Job is in '{job.status.value}' state and cannot be reviewed",
        )

    if action.action == "confirm":
        job.status = IngestionStatus.CONFIRMED
        job.status_message = "Confirmed by human reviewer"
        job.review_notes = action.review_notes
        if action.corrected_json:
            job.extracted_json = action.corrected_json
            job.status_message = "Confirmed with corrections"
    elif action.action == "reject":
        job.status = IngestionStatus.REJECTED
        job.status_message = action.review_notes or "Rejected by human reviewer"
        job.review_notes = action.review_notes
    else:
        raise HTTPException(status_code=400, detail="action must be 'confirm' or 'reject'")

    job.completed_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(job)

    return JobStatusResponse(
        job_id=job.id,
        status=job.status.value,
        status_message=job.status_message,
        original_filename=job.original_filename,
        source_type=job.source_type.value if job.source_type else None,
        document_type=job.document_type,
        rejection_reason=job.rejection_reason,
        confidence_score=job.confidence_score,
        low_confidence_fields=job.low_confidence_fields or [],
        validation_errors=job.validation_errors or [],
        draft_asn_order_id=job.draft_asn_order_id,
        draft_asn_order_number=job.draft_asn_order_number,
        extracted_json=job.extracted_json,
        created_at=job.created_at,
        updated_at=job.updated_at,
        completed_at=job.completed_at,
    )


# ── Background pipeline runner (called from lifespan or polling trigger) ──
async def run_ingestion_pipeline(job_id: UUID, db: Session) -> None:
    """Run the full ingestion pipeline for a job.

    Stages: PENDING → PARSING → EXTRACTING → VALIDATING → DRAFT_CREATED / MANUAL_REVIEW / FAILED
    """
    job = db.query(IngestionJob).filter(IngestionJob.id == job_id).first()
    if not job:
        logger.error("Pipeline called for non-existent job %s", job_id)
        return

    async def _set_status(status: IngestionStatus, message: str | None = None):
        job.status = status
        if message:
            job.status_message = message
        job.updated_at = datetime.now(timezone.utc)
        db.commit()

    try:
        await _set_status(IngestionStatus.PARSING, "Extracting text from document")

        # Stage 1: Parse
        parser = get_parser()
        with open(job.stored_path, "rb") as f:
            file_bytes = f.read()
        raw_text = parser.parse(file_bytes, job.original_filename, job.file_type)
        job.raw_text = raw_text

        # Stage 1b: Classify document type (gate before extraction)
        extractor = get_extractor()
        doc_type = await extractor.classify(raw_text)
        job.document_type = doc_type
        logger.info("Document %s classified as: %s", job_id, doc_type)

        if doc_type != "asn":
            reason = f"Document classified as '{doc_type}', not an ASN. Ingestion aborted."
            logger.warning("Job %s rejected: %s", job_id, reason)
            job.status = IngestionStatus.REJECTED
            job.rejection_reason = reason
            job.status_message = reason
            job.completed_at = datetime.now(timezone.utc)
            db.commit()
            return

        await _set_status(IngestionStatus.EXTRACTING, "Running LLM extraction")

        # Stage 2: Extract
        extracted = await extractor.extract(raw_text)
        job.extracted_json = extracted
        job.confidence_score = extracted.get("confidence_score")
        job.low_confidence_fields = extracted.get("low_confidence_fields", [])
        await _set_status(IngestionStatus.VALIDATING, "Validating against master data")

        # Stage 3: Validate
        validator = get_validator()
        validation = await validator.validate(
            extracted,
            organization_id=job.organization_id,
            warehouse_id=job.warehouse_id,
        )
        job.validation_errors = validation["errors"] + validation["warnings"]

        if not validation["is_valid"]:
            await _set_status(
                IngestionStatus.FAILED,
                f"Validation failed: {'; '.join(validation['errors'])}",
            )
            return

        # Stage 4: Create draft or request manual review
        if validation["auto_create"]:
            await _set_status(IngestionStatus.DRAFT_CREATED, "Creating draft ASN in core-service")

            # Build core-service payload from extracted data
            payload = _build_asn_payload(extracted, validation, job)
            try:
                draft = await core_client.create_asn_draft(payload)
                job.draft_asn_order_id = draft.get("id")
                job.draft_asn_order_number = draft.get("order_number")
                job.matched_supplier_id = validation["matched_supplier_id"]
                await _set_status(IngestionStatus.DRAFT_CREATED, "Draft ASN created successfully")
                job.completed_at = datetime.now(timezone.utc)
            except Exception as e:
                logger.exception("Failed to create draft ASN in core-service")
                await _set_status(IngestionStatus.FAILED, f"core-service error: {e}")
        else:
            job.matched_supplier_id = validation["matched_supplier_id"]
            await _set_status(
                IngestionStatus.MANUAL_REVIEW,
                f"Needs review: {'; '.join(validation['warnings'])}",
            )

    except Exception as e:
        logger.exception("Ingestion pipeline failed for job %s", job_id)
        await _set_status(IngestionStatus.FAILED, str(e))


# ── Manual pipeline runner (skips parse/classify/extract) ────────────────
async def run_manual_pipeline(job_id: UUID, extracted: dict, db: Session) -> None:
    """Run validation + draft creation for manually-entered ASN data.

    Skips: PARSING, EXTRACTING, CLASSIFYING
    Runs: VALIDATING → DRAFT_CREATED / MANUAL_REVIEW / FAILED
    """
    job = db.query(IngestionJob).filter(IngestionJob.id == job_id).first()
    if not job:
        logger.error("Manual pipeline called for non-existent job %s", job_id)
        return

    async def _set_status(status: IngestionStatus, message: str | None = None):
        job.status = status
        if message:
            job.status_message = message
        job.updated_at = datetime.now(timezone.utc)
        db.commit()

    try:
        await _set_status(IngestionStatus.VALIDATING, "Validating structured ASN data")

        # Validate
        validator = get_validator()
        validation = await validator.validate(
            extracted,
            organization_id=job.organization_id,
            warehouse_id=job.warehouse_id,
        )
        job.validation_errors = validation["errors"] + validation["warnings"]

        if not validation["is_valid"]:
            await _set_status(
                IngestionStatus.FAILED,
                f"Validation failed: {'; '.join(validation['errors'])}",
            )
            return

        # Create draft or request manual review
        if validation["auto_create"]:
            await _set_status(IngestionStatus.DRAFT_CREATED, "Creating draft ASN in core-service")

            payload = _build_asn_payload(extracted, validation, job)
            try:
                draft = await core_client.create_asn_draft(payload)
                job.draft_asn_order_id = draft.get("id")
                job.draft_asn_order_number = draft.get("order_number")
                job.matched_supplier_id = validation["matched_supplier_id"]
                await _set_status(IngestionStatus.DRAFT_CREATED, "Draft ASN created successfully")
                job.completed_at = datetime.now(timezone.utc)
            except Exception as e:
                logger.exception("Failed to create draft ASN in core-service")
                await _set_status(IngestionStatus.FAILED, f"core-service error: {e}")
        else:
            job.matched_supplier_id = validation["matched_supplier_id"]
            await _set_status(
                IngestionStatus.MANUAL_REVIEW,
                f"Needs review: {'; '.join(validation['warnings'])}",
            )

    except Exception as e:
        logger.exception("Manual pipeline failed for job %s", job_id)
        await _set_status(IngestionStatus.FAILED, str(e))


def _build_asn_payload(
    extracted: dict, validation: dict, job: IngestionJob
) -> dict:
    """Transform extracted JSON into core-service ASN create payload."""
    payload: dict = {
        "warehouse_id_to": str(job.warehouse_id) if job.warehouse_id else None,
        "status": "draft",
        "source": "ai_ingestion",
        "ingestion_job_id": str(job.id),
    }

    if validation.get("matched_supplier_id"):
        payload["supplier_id"] = str(validation["matched_supplier_id"])

    if extracted.get("expected_delivery_date"):
        payload["expected_delivery_date"] = extracted["expected_delivery_date"]

    if extracted.get("vehicle_number"):
        payload["vehicle_number"] = extracted["vehicle_number"]

    if extracted.get("driver_name"):
        payload["driver_name"] = extracted["driver_name"]

    # Line items
    items = extracted.get("line_items", [])
    payload["items"] = []
    line_results = validation.get("line_item_results", [])
    for idx, item in enumerate(items):
        mapped = {
            "sku": item.get("sku", ""),
            "item_name": item.get("item_name", ""),
            "quantity": item.get("quantity", 0),
            "uom": item.get("uom", "pieces"),
        }
        if idx < len(line_results) and line_results[idx].get("matched_item_id"):
            mapped["item_id"] = str(line_results[idx]["matched_item_id"])
        if item.get("batch_no"):
            mapped["batch_no"] = item["batch_no"]
        if item.get("serial_nos"):
            mapped["serial_nos"] = item["serial_nos"]
        if item.get("unit_cost") is not None:
            mapped["unit_cost"] = item["unit_cost"]
        payload["items"].append(mapped)

    return payload
