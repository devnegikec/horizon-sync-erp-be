"""Organization Deactivation Management API Endpoints 

Task 1E-1 & 1F-2: API endpoints for organization deactivation workflow,
status management, and automated billing enforcement for system administrators.
"""

import logging
from datetime import datetime
from typing import Dict, List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import require_permission
from app.models.organization import BillingStatus
from app.services.organization_deactivation_service import (
    OrganizationDeactivationService,
    DeactivationType
)

logger = logging.getLogger(__name__)

router = APIRouter()


# ── Request/Response Models ─────────────────────────────────────────────

class ExpireTrialRequest(BaseModel):
    """Request model for expiring organization trial"""
    reason: Optional[str] = Field("Trial period expired", description="Reason for trial expiration")
    send_notification: bool = Field(True, description="Send expiration notification email")


class ExpireSubscriptionRequest(BaseModel):
    """Request model for expiring organization subscription"""
    reason: Optional[str] = Field("Subscription expired", description="Reason for subscription expiration")
    send_notification: bool = Field(True, description="Send expiration notification email")


class SuspendOrganizationRequest(BaseModel):
    """Request model for suspending organization for non-payment"""
    days_overdue: int = Field(..., ge=1, description="Number of days payment is overdue")
    suspension_reason: Optional[str] = Field(None, description="Additional suspension reason")
    send_notification: bool = Field(True, description="Send suspension notification email")


class CancelSubscriptionRequest(BaseModel):
    """Request model for cancelling organization subscription"""
    cancellation_reason: str = Field(..., description="Reason for cancellation")
    effective_date: Optional[datetime] = Field(None, description="When cancellation takes effect")
    grace_period_days: int = Field(30, ge=0, le=90, description="Grace period before deactivation")
    send_notification: bool = Field(True, description="Send cancellation notification email")


class ReactivateOrganizationRequest(BaseModel):
    """Request model for reactivating organization"""
    new_subscription_end_date: datetime = Field(..., description="New subscription end date")
    reactivation_notes: Optional[str] = Field(None, description="Notes about reactivation")
    send_notification: bool = Field(True, description="Send reactivation notification email")


class DeactivationActionResponse(BaseModel):
    """Response model for deactivation actions"""
    organization_id: UUID
    organization_name: str
    action_type: str
    previous_status: str
    new_status: str
    action_date: datetime
    performed_by: UUID
    reason: Optional[str]
    additional_info: Optional[Dict]


class DeactivationSummaryResponse(BaseModel):
    """Response model for deactivation summary"""
    total_organizations: int
    trial_expired_count: int
    subscription_expired_count: int
    overdue_payment_count: int
    suspended_count: int
    cancelled_count: int
    last_check_date: Optional[datetime]
    actions_pending: List[DeactivationActionResponse]


class OrganizationStatusResponse(BaseModel):
    """Response model for organization status"""
    organization_id: UUID
    organization_name: str
    current_status: str
    billing_status: Optional[str]
    trial_end_date: Optional[datetime]
    subscription_end_date: Optional[datetime]
    last_payment_date: Optional[datetime]
    next_billing_date: Optional[datetime]
    days_since_last_payment: Optional[int]
    deactivation_history: List[Dict]


class OrganizationActionItem(BaseModel):
    """Single organization requiring action"""
    organization_id: UUID
    organization_name: str
    days_expired: Optional[int] = None
    days_overdue: Optional[int] = None  
    amount_due: Optional[float] = None


class OrganizationsRequiringActionResponse(BaseModel):
    """Response model for organizations requiring action"""
    trial_expired: List[OrganizationActionItem]
    subscription_expired: List[OrganizationActionItem]  
    payment_overdue: List[OrganizationActionItem]


class ReactivationResponse(BaseModel):
    """Response model for organization reactivation"""
    organization_id: UUID
    organization_name: str
    previous_status: str
    new_status: str
    reactivation_date: datetime
    new_subscription_end_date: datetime
    reactivated_by: UUID
    reactivation_notes: Optional[str]


# ── Automated Monitoring & Checks ──────────────────────────────────────

@router.get("/check-deactivations", response_model=List[DeactivationActionResponse])
async def check_organizations_for_deactivation(
    db: Session = Depends(get_db),
    current_user = Depends(require_permission("system_admin.org_manager"))
):
    """Check all organizations for required deactivation actions
    
    Daily automated check for:
    - Expired trials
    - Expired subscriptions  
    - Overdue payments requiring escalation
    - Organizations needing suspension
    """
    try:
        service = OrganizationDeactivationService(db)
        
        actions_needed = service.check_organizations_for_deactivation()
        
        logger.info(f"Found {len(actions_needed)} organizations requiring deactivation action")
        return actions_needed
        
    except Exception as e:
        logger.error(f"Failed to check organizations for deactivation: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to check deactivation requirements: {str(e)}"
        )


@router.get("/deactivation-summary", response_model=DeactivationSummaryResponse)
async def get_deactivation_summary(
    db: Session = Depends(get_db),
    current_user = Depends(require_permission("system_admin.reporting"))
):
    """Get summary of organization billing statuses and deactivation alerts
    
    Returns dashboard data for system admin overview:
    - Organization counts by billing status
    - Upcoming expirations and alerts
    - Organizations requiring immediate action
    """
    try:
        service = OrganizationDeactivationService(db)
        
        summary = service.get_deactivation_summary()
        
        return summary
        
    except Exception as e:
        logger.error(f"Failed to get deactivation summary: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get deactivation summary: {str(e)}"
        )


@router.get("/organizations-requiring-action", response_model=OrganizationsRequiringActionResponse)
async def get_organizations_requiring_action(
    db: Session = Depends(get_db),
    current_user = Depends(require_permission("system_admin.org_manager"))
):
    """Get organizations that require deactivation actions
    
    Returns categorized lists of organizations needing attention:
    - Trial expired organizations
    - Subscription expired organizations  
    - Organizations with overdue payments
    """
    try:
        service = OrganizationDeactivationService(db)
        
        organizations_data = service.get_organizations_requiring_action()
        
        return organizations_data
        
    except Exception as e:
        logger.error(f"Failed to get organizations requiring action: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get organizations requiring action: {str(e)}"
        )


# ── Trial Management ────────────────────────────────────────────────────

@router.post("/expire-trial/{organization_id}", response_model=DeactivationActionResponse)
async def expire_trial(
    organization_id: UUID,
    request: ExpireTrialRequest,
    db: Session = Depends(get_db),
    current_user = Depends(require_permission("system_admin.org_manager"))
):
    """Expire organization trial and move to subscription required status
    
    Marks trial as expired and prevents further access until subscription is activated
    """
    try:
        service = OrganizationDeactivationService(db)
        
        result = service.expire_trial_organization(
            organization_id=organization_id,
            expired_by=current_user.id
        )
        
        logger.info(f"Expired trial for organization {organization_id} by user {current_user.id}")
        
        return DeactivationActionResponse(
            organization_id=result["organization_id"],
            organization_name=result["organization_name"],
            action_type=result["deactivation_type"],
            previous_status=result["previous_status"],
            new_status=result["new_status"],
            action_date=datetime.now(),
            performed_by=current_user.id,
            reason=request.reason,
            additional_info={
                "deactivation_date": result["deactivation_date"],
                "next_steps": result["next_steps"]
            }
        )
        
    except Exception as e:
        logger.error(f"Failed to expire trial for organization {organization_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to expire trial: {str(e)}"
        )


# ── Subscription Management ─────────────────────────────────────────────

@router.post("/expire-subscription/{organization_id}", response_model=DeactivationActionResponse)
async def expire_subscription(
    organization_id: UUID,
    request: ExpireSubscriptionRequest,
    db: Session = Depends(get_db),
    current_user = Depends(require_permission("system_admin.org_manager"))
):
    """Expire organization subscription and deactivate access
    
    Marks subscription as expired and blocks organization access until renewal
    """
    try:
        service = OrganizationDeactivationService(db)
        
        result = service.expire_subscription_organization(
            organization_id=organization_id,
            expired_by=current_user.id
        )
        
        logger.info(f"Expired subscription for organization {organization_id} by user {current_user.id}")
        
        return DeactivationActionResponse(
            organization_id=result["organization_id"],
            organization_name=result["organization_name"],
            action_type=result["deactivation_type"],
            previous_status=result["previous_status"],
            new_status=result["new_status"],
            action_date=datetime.now(),
            performed_by=current_user.id,
            reason=request.reason,
            additional_info={
                "deactivation_date": result["deactivation_date"],
                "next_steps": result["next_steps"]
            }
        )
        
    except Exception as e:
        logger.error(f"Failed to expire subscription for organization {organization_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to expire subscription: {str(e)}"
        )


@router.post("/suspend/{organization_id}", response_model=DeactivationActionResponse)
async def suspend_organization(
    organization_id: UUID,
    request: SuspendOrganizationRequest,
    db: Session = Depends(get_db),
    current_user = Depends(require_permission("system_admin.org_manager"))
):
    """Suspend organization for non-payment after reminder escalation
    
    Suspends organization access due to overdue payments, typically after 90+ days overdue
    """
    try:
        service = OrganizationDeactivationService(db)
        
        result = service.suspend_organization_for_nonpayment(
            organization_id=organization_id,
            days_overdue=request.days_overdue,
            suspended_by=current_user.id
        )
        
        logger.info(f"Suspended organization {organization_id} for {request.days_overdue} days overdue")
        
        return DeactivationActionResponse(
            organization_id=result["organization_id"],
            organization_name=result["organization_name"],
            action_type=result["deactivation_type"],
            previous_status=result["previous_status"],
            new_status=result["new_status"],
            action_date=datetime.now(),
            performed_by=current_user.id,
            reason=request.suspension_reason or f"Payment overdue for {request.days_overdue} days",
            additional_info={
                "days_overdue": result["days_overdue"],
                "suspension_date": result["suspension_date"],
                "next_steps": result["next_steps"]
            }
        )
        
    except Exception as e:
        logger.error(f"Failed to suspend organization {organization_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to suspend organization: {str(e)}"
        )


@router.post("/cancel/{organization_id}", response_model=DeactivationActionResponse)
async def cancel_subscription(
    organization_id: UUID,
    request: CancelSubscriptionRequest,
    db: Session = Depends(get_db),
    current_user = Depends(require_permission("system_admin.org_manager"))
):
    """Cancel organization subscription with grace period
    
    Cancels subscription (user-initiated or policy violation) with configurable grace period
    """
    try:
        service = OrganizationDeactivationService(db)
        
        result = service.cancel_organization_subscription(
            organization_id=organization_id,
            cancellation_reason=request.cancellation_reason,
            effective_date=request.effective_date,
            cancelled_by=current_user.id
        )
        
        logger.info(f"Cancelled subscription for organization {organization_id}: {request.cancellation_reason}")
        
        return DeactivationActionResponse(
            organization_id=result["organization_id"],
            organization_name=result["organization_name"],
            action_type=result["deactivation_type"],
            previous_status=result["previous_status"],
            new_status=result["new_status"],
            action_date=datetime.now(),
            performed_by=current_user.id,
            reason=request.cancellation_reason,
            additional_info={
                "effective_date": result["effective_date"],
                "grace_period_end": result["grace_period_end"],
                "next_steps": result["next_steps"]
            }
        )
        
    except Exception as e:
        logger.error(f"Failed to cancel subscription for organization {organization_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to cancel subscription: {str(e)}"
        )


# ── Reactivation Management ─────────────────────────────────────────────

@router.post("/reactivate/{organization_id}", response_model=ReactivationResponse)
async def reactivate_organization(
    organization_id: UUID,
    request: ReactivateOrganizationRequest,
    db: Session = Depends(get_db),
    current_user = Depends(require_permission("system_admin.org_manager"))
):
    """Reactivate deactivated organization with new subscription period
    
    Reactivates organization after payment or manual approval with new subscription dates
    """
    try:
        service = OrganizationDeactivationService(db)
        
        result = service.reactivate_organization(
            organization_id=organization_id,
            new_subscription_end_date=request.new_subscription_end_date,
            reactivated_by=current_user.id,
            reactivation_notes=request.reactivation_notes
        )
        
        logger.info(f"Reactivated organization {organization_id} until {request.new_subscription_end_date}")
        
        return {
            "organization_id": result["organization_id"],
            "organization_name": result["organization_name"],
            "action_type": "reactivation",
            "previous_status": result["previous_status"],
            "new_status": result["new_status"],
            "subscription_start_date": result["subscription_start_date"],
            "subscription_end_date": result["subscription_end_date"],
            "reactivated_by": current_user.id,
            "reactivation_date": result["reactivation_date"],
            "reactivation_notes": result["reactivation_notes"],
            "status": "success"
        }
        
    except Exception as e:
        logger.error(f"Failed to reactivate organization {organization_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to reactivate organization: {str(e)}"
        )


# ── Bulk Operations & Status Management ─────────────────────────────────

@router.post("/bulk-suspension", response_model=List[DeactivationActionResponse])
async def bulk_suspend_organizations(
    organization_ids: List[UUID],
    days_overdue: int = Query(..., ge=1, description="Days overdue for all organizations"),
    suspension_reason: Optional[str] = Query("Bulk suspension for non-payment"),
    db: Session = Depends(get_db),
    current_user = Depends(require_permission("system_admin.master"))
):
    """Bulk suspend multiple organizations for non-payment
    
    Suspends multiple organizations at once (for mass non-payment enforcement)
    """
    try:
        service = OrganizationDeactivationService(db)
        
        results = []
        for org_id in organization_ids:
            try:
                result = service.suspend_organization_for_nonpayment(
                    organization_id=org_id,
                    days_overdue=days_overdue,
                    suspended_by=current_user.id
                )
                
                results.append({
                    "organization_id": result["organization_id"],
                    "organization_name": result["organization_name"],
                    "status": "success",
                    "days_overdue": result["days_overdue"]
                })
                
            except Exception as e:
                results.append({
                    "organization_id": org_id,
                    "status": "failed",
                    "error": str(e)
                })
        
        logger.info(f"Bulk suspended {len(organization_ids)} organizations")
        return results
        
    except Exception as e:
        logger.error(f"Failed bulk suspension: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed bulk suspension: {str(e)}"
        )


@router.get("/organization-status/{organization_id}", response_model=OrganizationStatusResponse)
async def get_organization_deactivation_status(
    organization_id: UUID,
    db: Session = Depends(get_db),
    current_user = Depends(require_permission("system_admin.org_manager"))
):
    """Get detailed deactivation status for specific organization
    
    Returns comprehensive status including billing info, deactivation risk, and history
    """
    try:
        from app.models.organization import Organization
        
        org = (
            db.query(Organization)
            .filter(Organization.id == organization_id)
            .first()
        )
        
        if not org:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Organization not found"
            )
        
        # Calculate deactivation risk
        current_date = datetime.now().date()
        risk_level = "low"
        risk_reason = "Organization is in good standing"
        
        if org.billing_status == BillingStatus.TRIAL and org.trial_end_date:
            days_until_trial_end = (org.trial_end_date - current_date).days
            if days_until_trial_end <= 0:
                risk_level = "critical"
                risk_reason = f"Trial expired {abs(days_until_trial_end)} days ago"
            elif days_until_trial_end <= 7:
                risk_level = "high"
                risk_reason = f"Trial expires in {days_until_trial_end} days"
        
        elif org.billing_status == BillingStatus.OVERDUE and org.next_billing_date:
            days_overdue = (current_date - org.next_billing_date).days
            if days_overdue >= 90:
                risk_level = "critical"
                risk_reason = f"Payment overdue for {days_overdue} days - immediate suspension required"
            elif days_overdue >= 60:
                risk_level = "high"
                risk_reason = f"Payment overdue for {days_overdue} days - final notice required"
            elif days_overdue >= 30:
                risk_level = "medium"
                risk_reason = f"Payment overdue for {days_overdue} days - reminder required"
        
        return {
            "organization_id": org.id,
            "organization_name": org.name,
            "billing_status": org.billing_status.value if org.billing_status else None,
            "subscription_start_date": org.subscription_start_date,
            "subscription_end_date": org.subscription_end_date,
            "trial_end_date": org.trial_end_date,
            "next_billing_date": org.next_billing_date,
            "last_billed_date": org.last_billed_date,
            "deactivation_risk": {
                "level": risk_level,
                "reason": risk_reason
            },
            "status_history": {
                "customer_since": org.customer_since,
                "current_status_since": org.subscription_start_date or org.customer_since
            }
        }
        
    except Exception as e:
        logger.error(f"Failed to get organization status {organization_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get organization status: {str(e)}"
        )