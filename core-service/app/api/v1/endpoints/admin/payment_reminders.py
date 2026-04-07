"""Payment Reminders Admin endpoints for managing reminder configurations and logs"""

import logging
from typing import Any, Dict, List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import CurrentUser, require_permission
from app.models.reminder_config import ReminderConfig, ReminderLog, ReminderStage, ReminderStatus, ReminderType
from app.services.payment_reminder_service import PaymentReminderService
from app.services.admin_organization_service import AdminOrganizationService

logger = logging.getLogger(__name__)

router = APIRouter()
security = HTTPBearer()


# ── Pydantic Models ──────────────────────────────────────────────────

class ReminderConfigResponse(BaseModel):
    """Response model for reminder configuration"""
    id: UUID
    organization_id: UUID
    organization_name: Optional[str] = None  # Fetched from identity service
    reminder_type: ReminderType
    grace_period_days: int
    first_reminder_days: int
    second_reminder_days: int
    final_notice_days: int
    auto_deactivate_days: Optional[int]
    reminder_frequency_days: int
    max_reminders_per_stage: int
    escalation_sequence: List[str]
    is_enabled: bool
    first_reminder_template: str
    second_reminder_template: str
    final_notice_template: str
    deactivation_notice_template: str
    created_at: str
    updated_at: str

    class Config:
        from_attributes = True


class ReminderConfigCreate(BaseModel):
    """Request model for creating reminder configuration"""
    organization_id: UUID
    reminder_type: ReminderType = ReminderType.AUTO
    grace_period_days: int = Field(default=30, ge=0, le=365)
    first_reminder_days: int = Field(default=30, ge=1, le=365)
    second_reminder_days: int = Field(default=60, ge=1, le=365)
    final_notice_days: int = Field(default=90, ge=1, le=365)
    auto_deactivate_days: Optional[int] = Field(default=120, ge=1, le=500)
    reminder_frequency_days: int = Field(default=7, ge=1, le=30)
    max_reminders_per_stage: int = Field(default=3, ge=1, le=10)
    is_enabled: bool = True
    first_reminder_template: str = "payment_reminder_first"
    second_reminder_template: str = "payment_reminder_second"
    final_notice_template: str = "payment_reminder_final"
    deactivation_notice_template: str = "payment_reminder_deactivation"


class ReminderConfigUpdate(BaseModel):
    """Request model for updating reminder configuration"""
    reminder_type: Optional[ReminderType] = None
    grace_period_days: Optional[int] = Field(default=None, ge=0, le=365)
    first_reminder_days: Optional[int] = Field(default=None, ge=1, le=365)
    second_reminder_days: Optional[int] = Field(default=None, ge=1, le=365)
    final_notice_days: Optional[int] = Field(default=None, ge=1, le=365)
    auto_deactivate_days: Optional[int] = Field(default=None, ge=1, le=500)
    reminder_frequency_days: Optional[int] = Field(default=None, ge=1, le=30)
    max_reminders_per_stage: Optional[int] = Field(default=None, ge=1, le=10)
    is_enabled: Optional[bool] = None
    first_reminder_template: Optional[str] = None
    second_reminder_template: Optional[str] = None
    final_notice_template: Optional[str] = None
    deactivation_notice_template: Optional[str] = None


class ReminderLogResponse(BaseModel):
    """Response model for reminder log"""
    id: UUID
    reminder_config_id: UUID
    invoice_id: UUID
    reminder_stage: ReminderStage
    reminder_type: ReminderType
    status: ReminderStatus
    sent_at: Optional[str]
    recipient_email: str
    subject: str
    content: Optional[str]
    error_message: Optional[str]
    created_at: str

    class Config:
        from_attributes = True


class PaginatedResponse(BaseModel):
    """Generic paginated response model"""
    data: List[Any]
    total: int
    page: int
    page_size: int
    total_pages: int


# ── Endpoints ─────────────────────────────────────────────────────────

@router.get("/configs", response_model=PaginatedResponse)
async def list_reminder_configs(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Page size"),
    organization_id: Optional[UUID] = Query(None, description="Filter by organization ID"),
    enabled: Optional[bool] = Query(None, description="Filter by enabled status"),
    current_user: CurrentUser = Depends(require_permission("system_admin.billing")),
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
):
    """
    List payment reminder configurations with pagination
    
    **Required Permission:** system_admin.billing
    """
    try:
        # Build query
        query = db.query(ReminderConfig)
        
        if organization_id:
            query = query.filter(ReminderConfig.organization_id == organization_id)
        
        if enabled is not None:
            query = query.filter(ReminderConfig.is_enabled == enabled)
        
        # Get total count
        total = query.count()
        
        # Apply pagination
        offset = (page - 1) * page_size
        configs = query.offset(offset).limit(page_size).all()
        
        # Fetch organization names for configs
        org_service = AdminOrganizationService(db, token=credentials.credentials)
        
        # Convert to response models
        config_responses = []
        for config in configs:
            config_dict = config.__dict__.copy()
            config_dict.pop('_sa_instance_state', None)
            config_dict['created_at'] = config.created_at.isoformat()
            config_dict['updated_at'] = config.updated_at.isoformat()
            
            # Fetch organization name individually for more reliable results
            org_name = 'Default'
            try:
                org_detail = await org_service.get_organization(config.organization_id)
                org_name = org_detail.name or org_detail.display_name or f"Organization {str(config.organization_id)[:8]}"
                logger.debug(f"Successfully fetched organization name: {org_name} for ID: {config.organization_id}")
            except Exception as e:
                logger.warning(f"Failed to fetch organization name for {config.organization_id}: {e}")
                # Try to use any existing name or create a meaningful fallback
                if hasattr(config, 'organization_name') and config.organization_name:
                    org_name = config.organization_name
                else:
                    org_name = f"Organization {str(config.organization_id)[:8]}"
            
            config_dict['organization_name'] = org_name
            config_responses.append(config_dict)
        
        return PaginatedResponse(
            data=config_responses,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=(total + page_size - 1) // page_size
        )
        
    except Exception as e:
        logger.error(f"Error listing reminder configs: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list reminder configurations: {str(e)}"
        )


@router.get("/configs/{config_id}", response_model=ReminderConfigResponse)
async def get_reminder_config(
    config_id: UUID,
    current_user: CurrentUser = Depends(require_permission("system_admin.billing")),
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
):
    """
    Get specific payment reminder configuration
    
    **Required Permission:** system_admin.billing
    """
    try:
        config = db.query(ReminderConfig).filter(ReminderConfig.id == config_id).first()
        
        if not config:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Reminder configuration {config_id} not found"
            )
        
        # Fetch organization name
        org_service = AdminOrganizationService(db, token=credentials.credentials)
        org_name = 'Unknown Organization'
        
        try:
            org_detail = await org_service.get_organization(config.organization_id)
            org_name = org_detail.name
        except Exception as e:
            logger.warning(f"Failed to fetch organization name for {config.organization_id}: {e}")
        
        config_dict = config.__dict__.copy()
        config_dict.pop('_sa_instance_state', None)
        config_dict['created_at'] = config.created_at.isoformat()
        config_dict['updated_at'] = config.updated_at.isoformat()
        config_dict['organization_name'] = org_name
        
        return ReminderConfigResponse(**config_dict)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting reminder config {config_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get reminder configuration: {str(e)}"
        )


@router.post("/configs", response_model=ReminderConfigResponse, status_code=status.HTTP_201_CREATED)
async def create_reminder_config(
    config_data: ReminderConfigCreate,
    current_user: CurrentUser = Depends(require_permission("system_admin.billing")),
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
):
    """
    Create a new payment reminder configuration
    
    **Required Permission:** system_admin.billing
    """
    try:
        # Check if config already exists for organization
        existing_config = db.query(ReminderConfig).filter(
            ReminderConfig.organization_id == config_data.organization_id
        ).first()
        
        if existing_config:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Reminder configuration already exists for organization {config_data.organization_id}"
            )
        
        # Create new configuration directly without using the service method
        # to avoid the race condition in create_default_reminder_config
        config = ReminderConfig(
            organization_id=config_data.organization_id,
            reminder_type=config_data.reminder_type,
            grace_period_days=config_data.grace_period_days,
            first_reminder_days=config_data.first_reminder_days,
            second_reminder_days=config_data.second_reminder_days,
            final_notice_days=config_data.final_notice_days,
            auto_deactivate_days=config_data.auto_deactivate_days,
            reminder_frequency_days=config_data.reminder_frequency_days,
            max_reminders_per_stage=config_data.max_reminders_per_stage,
            is_enabled=config_data.is_enabled,
            first_reminder_template=config_data.first_reminder_template,
            second_reminder_template=config_data.second_reminder_template,
            final_notice_template=config_data.final_notice_template,
            deactivation_notice_template=config_data.deactivation_notice_template,
        )
        
        # Build escalation sequence based on stages
        escalation_sequence = []
        if config_data.first_reminder_days and config_data.first_reminder_days > 0:
            escalation_sequence.append(ReminderStage.FIRST_REMINDER.value)
        if config_data.second_reminder_days and config_data.second_reminder_days > 0:
            escalation_sequence.append(ReminderStage.SECOND_REMINDER.value)
        if config_data.final_notice_days and config_data.final_notice_days > 0:
            escalation_sequence.append(ReminderStage.FINAL_NOTICE.value)
        if config_data.auto_deactivate_days and config_data.auto_deactivate_days > 0:
            escalation_sequence.append(ReminderStage.DEACTIVATION_NOTICE.value)
        
        config.escalation_sequence = escalation_sequence
        
        # Single transaction - add and commit together
        db.add(config)
        try:
            db.commit()
            db.refresh(config)
        except Exception as e:
            db.rollback()
            # Check if this is a unique constraint violation
            if "reminder_configs_organization_id_key" in str(e) or "duplicate key" in str(e).lower():
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"Reminder configuration already exists for organization {config_data.organization_id}"
                )
            else:
                raise  # Re-raise if it's a different error
        
        # Fetch organization name
        org_service = AdminOrganizationService(db, token=credentials.credentials)
        org_name = 'Unknown Organization'
        
        try:
            org_detail = await org_service.get_organization(config.organization_id)
            org_name = org_detail.name
        except Exception as e:
            logger.warning(f"Failed to fetch organization name for {config.organization_id}: {e}")
        
        config_dict = config.__dict__.copy()
        config_dict.pop('_sa_instance_state', None)
        config_dict['created_at'] = config.created_at.isoformat()
        config_dict['updated_at'] = config.updated_at.isoformat()
        config_dict['organization_name'] = org_name
        
        logger.info(f"Created reminder configuration {config.id} for organization {config_data.organization_id}")
        return ReminderConfigResponse(**config_dict)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating reminder config: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create reminder configuration: {str(e)}"
        )


@router.put("/configs/{config_id}", response_model=ReminderConfigResponse)
async def update_reminder_config(
    config_id: UUID,
    updates: ReminderConfigUpdate,
    current_user: CurrentUser = Depends(require_permission("system_admin.billing")),
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
):
    """
    Update payment reminder configuration
    
    **Required Permission:** system_admin.billing
    """
    try:
        config = db.query(ReminderConfig).filter(ReminderConfig.id == config_id).first()
        
        if not config:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Reminder configuration {config_id} not found"
            )
        
        # Use service to update
        reminder_service = PaymentReminderService(db)
        update_dict = {k: v for k, v in updates.dict().items() if v is not None}
        
        config = reminder_service.update_reminder_config(config.organization_id, update_dict)
        
        # Fetch organization name
        org_service = AdminOrganizationService(db, token=credentials.credentials)
        org_name = 'Unknown Organization'
        
        try:
            org_detail = await org_service.get_organization(config.organization_id)
            org_name = org_detail.name
        except Exception as e:
            logger.warning(f"Failed to fetch organization name for {config.organization_id}: {e}")
        
        config_dict = config.__dict__.copy()
        config_dict.pop('_sa_instance_state', None)
        config_dict['created_at'] = config.created_at.isoformat()
        config_dict['updated_at'] = config.updated_at.isoformat()
        config_dict['organization_name'] = org_name
        
        logger.info(f"Updated reminder configuration {config_id}")
        return ReminderConfigResponse(**config_dict)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating reminder config {config_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update reminder configuration: {str(e)}"
        )


@router.delete("/configs/{config_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_reminder_config(
    config_id: UUID,
    current_user: CurrentUser = Depends(require_permission("system_admin.billing")),
    db: Session = Depends(get_db)
):
    """
    Delete payment reminder configuration
    
    **Required Permission:** system_admin.billing
    """
    try:
        config = db.query(ReminderConfig).filter(ReminderConfig.id == config_id).first()
        
        if not config:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Reminder configuration {config_id} not found"
            )
        
        # Delete associated logs first (if needed)
        db.query(ReminderLog).filter(ReminderLog.reminder_config_id == config_id).delete()
        
        # Delete the config
        db.delete(config)
        db.commit()
        
        logger.info(f"Deleted reminder configuration {config_id}")
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting reminder config {config_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete reminder configuration: {str(e)}"
        )


@router.post("/configs/{config_id}/toggle", response_model=ReminderConfigResponse)
async def toggle_reminder_config(
    config_id: UUID,
    current_user: CurrentUser = Depends(require_permission("system_admin.billing")),
    db: Session = Depends(get_db)
):
    """
    Toggle reminder configuration enabled/disabled status
    
    **Required Permission:** system_admin.billing
    """
    try:
        config = db.query(ReminderConfig).filter(ReminderConfig.id == config_id).first()
        
        if not config:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Reminder configuration {config_id} not found"
            )
        
        # Toggle enabled status
        config.is_enabled = not config.is_enabled
        db.commit()
        db.refresh(config)
        
        config_dict = config.__dict__.copy()
        config_dict.pop('_sa_instance_state', None)
        config_dict['created_at'] = config.created_at.isoformat()
        config_dict['updated_at'] = config.updated_at.isoformat()
        
        logger.info(f"Toggled reminder configuration {config_id} to {'enabled' if config.is_enabled else 'disabled'}")
        return ReminderConfigResponse(**config_dict)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error toggling reminder config {config_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to toggle reminder configuration: {str(e)}"
        )


@router.get("/logs", response_model=PaginatedResponse)
async def list_reminder_logs(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Page size"),
    config_id: Optional[UUID] = Query(None, description="Filter by config ID"),
    invoice_id: Optional[UUID] = Query(None, description="Filter by invoice ID"),
    status: Optional[ReminderStatus] = Query(None, description="Filter by status"),
    stage: Optional[ReminderStage] = Query(None, description="Filter by reminder stage"),
    current_user: CurrentUser = Depends(require_permission("system_admin.billing")),
    db: Session = Depends(get_db)
):
    """
    List payment reminder logs with pagination and filters
    
    **Required Permission:** system_admin.billing
    """
    try:
        # Build query with joins to get organization and invoice details
        from app.models.invoice import Invoice
        
        query = (db.query(ReminderLog, Invoice.invoice_no)
                .join(Invoice, ReminderLog.invoice_id == Invoice.id)
                .order_by(ReminderLog.created_at.desc()))
        
        if config_id:
            query = query.filter(ReminderLog.config_id == config_id)
        
        if invoice_id:
            query = query.filter(ReminderLog.invoice_id == invoice_id)
        
        if status:
            query = query.filter(ReminderLog.status == status)
        
        if stage:
            query = query.filter(ReminderLog.reminder_stage == stage)
        
        # Get total count
        total = query.count()
        
        # Apply pagination
        offset = (page - 1) * page_size
        results = query.offset(offset).limit(page_size).all()
        
        # Convert to response models with organization and invoice details
        log_responses = []
        for result in results:
            log = result[0]  # ReminderLog object
            invoice_no = result[1]  # Invoice number
            
            log_dict = log.__dict__.copy()
            log_dict.pop('_sa_instance_state', None)
            log_dict['created_at'] = log.created_at.isoformat()
            if log.sent_at:
                log_dict['sent_at'] = log.sent_at.isoformat()
            
            # Add invoice and organization details
            log_dict['invoice_number'] = invoice_no
            log_dict['organization_name'] = f"Organization {str(log.organization_id)}"  # Will be improved with actual org lookup
            
            log_responses.append(log_dict)
        
        return PaginatedResponse(
            data=log_responses,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=(total + page_size - 1) // page_size
        )
        
    except Exception as e:
        logger.error(f"Error listing reminder logs: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list reminder logs: {str(e)}"
        )


@router.get("/stats")
async def get_reminder_stats(
    organization_id: Optional[UUID] = Query(None, description="Filter by organization ID"),
    current_user: CurrentUser = Depends(require_permission("system_admin.billing")),
    db: Session = Depends(get_db)
):
    """
    Get payment reminder statistics
    
    **Required Permission:** system_admin.billing
    """
    try:
        reminder_service = PaymentReminderService(db)
        stats = reminder_service.get_reminder_stats(organization_id)
        
        logger.info(f"Retrieved reminder stats for organization {organization_id or 'all'}")
        return stats
        
    except Exception as e:
        logger.error(f"Error getting reminder stats: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get reminder statistics: {str(e)}"
        )


class SendReminderRequest(BaseModel):
    """Request model for sending manual reminders"""
    organization_id: UUID
    invoice_ids: List[UUID]
    reminder_stage: ReminderStage
    custom_message: Optional[str] = None
    override_frequency: bool = False


class SendBatchRequest(BaseModel):
    """Request model for sending batch reminders"""
    organization_ids: List[UUID]
    force_send: bool = False
    dry_run: bool = False


@router.post("/send")
async def send_manual_reminder(
    request: SendReminderRequest,
    current_user: CurrentUser = Depends(require_permission("system_admin.billing")),
    db: Session = Depends(get_db)
):
    """
    Send manual payment reminders for specific invoices
    
    **Required Permission:** system_admin.billing
    """
    try:
        reminder_service = PaymentReminderService(db)
        
        result = await reminder_service.send_manual_reminders(
            organization_id=request.organization_id,
            invoice_ids=request.invoice_ids,
            reminder_stage=request.reminder_stage,
            custom_message=request.custom_message,
            override_frequency=request.override_frequency
        )
        
        logger.info(
            f"Manual reminders sent for organization {request.organization_id}: "
            f"{result.get('sent', 0)} sent, {result.get('failed', 0)} failed"
        )
        
        return result
        
    except Exception as e:
        logger.error(f"Error sending manual reminders: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to send manual reminders: {str(e)}"
        )


@router.post("/send-batch")
async def send_batch_reminders(
    request: SendBatchRequest,
    current_user: CurrentUser = Depends(require_permission("system_admin.billing")),
    db: Session = Depends(get_db)
):
    """
    Send batch reminders for multiple organizations
    
    **Required Permission:** system_admin.billing
    """
    try:
        reminder_service = PaymentReminderService(db)
        
        if request.dry_run:
            result = await reminder_service.preview_batch_reminders(
                organization_ids=request.organization_ids
            )
            result["dry_run"] = True
        else:
            result = await reminder_service.send_batch_reminders(
                organization_ids=request.organization_ids,
                force_send=request.force_send
            )
        
        logger.info(
            f"Batch reminders processed for {len(request.organization_ids)} organizations: "
            f"{result.get('sent', 0)} sent, {result.get('failed', 0)} failed, "
            f"{result.get('skipped', 0)} skipped"
        )
        
        return result
        
    except Exception as e:
        logger.error(f"Error sending batch reminders: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to send batch reminders: {str(e)}"
        )


@router.post("/process-batch")
async def process_batch_reminders(
    organization_ids: Optional[List[UUID]] = None,
    current_user: CurrentUser = Depends(require_permission("system_admin.billing")),
    db: Session = Depends(get_db)
):
    """
    Process automatic batch reminders for organizations (daily automation task)
    
    **Required Permission:** system_admin.billing
    """
    try:
        from app.tasks.billing_automation import BillingAutomationTask
        
        async with BillingAutomationTask(db) as automation_task:
            result = await automation_task.process_daily_reminders()
        
        logger.info(f"Daily reminder processing completed: {result}")
        return result
        
    except Exception as e:
        logger.error(f"Error processing batch reminders: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process batch reminders: {str(e)}"
        )