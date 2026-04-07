"""Organization Deactivation Service for B2B Billing System

Task 1E-1: Implements organization deactivation workflow with automated monitoring,
escalation sequences, and reactivation capabilities for subscription billing.
"""

import logging
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from enum import Enum
from typing import Dict, List, Optional
from uuid import UUID

from fastapi import HTTPException, status  
from sqlalchemy import and_, or_
from sqlalchemy.orm import Session

from app.models.organization import Organization, OrganizationType, BillingStatus
# Note: Communication and payment reminder services are in core service
# For now, using simplified notification approach

logger = logging.getLogger(__name__)


class DeactivationType(str, Enum):
    """Types of organization deactivation"""
    TRIAL_EXPIRED = "trial_expired"
    SUBSCRIPTION_EXPIRED = "subscription_expired"
    NONPAYMENT_SUSPENSION = "nonpayment_suspension"
    MANUAL_CANCELLATION = "manual_cancellation"
    POLICY_VIOLATION = "policy_violation"


class DeactivationStatus(str, Enum):
    """Status of deactivation process"""
    PENDING = "pending"
    WARNING_SENT = "warning_sent" 
    GRACE_PERIOD = "grace_period"
    DEACTIVATED = "deactivated"
    REACTIVATED = "reactivated"


class OrganizationDeactivationService:
    """Service for managing organization deactivation and reactivation workflows"""

    def __init__(self, db: Session):
        self.db = db
        # Note: Communication and reminder services are in core service
        # Using simplified notification logging for now

    # ── Automated Deactivation Monitoring ───────────────────────────────

    def check_organizations_for_deactivation(self) -> List[Dict]:
        """Daily check for organizations that need deactivation action
        
        Returns list of actions needed for different deactivation scenarios
        """
        logger.info("Starting daily organization deactivation check")
        
        actions_needed = []
        current_date = datetime.now(UTC).date()
        
        # Check trial expirations
        trial_expired = self._get_trial_expired_organizations(current_date)
        for org in trial_expired:
            actions_needed.append({
                "organization_id": org.id,
                "organization_name": org.name,
                "action": "EXPIRE_TRIAL",
                "reason": "Trial period expired",
                "expired_date": org.trial_end_date,
                "days_expired": (current_date - org.trial_end_date).days if org.trial_end_date else 0
            })

        # Check subscription expirations  
        subscription_expired = self._get_subscription_expired_organizations(current_date)
        for org in subscription_expired:
            actions_needed.append({
                "organization_id": org.id,
                "organization_name": org.name,
                "action": "EXPIRE_SUBSCRIPTION", 
                "reason": "Subscription expired",
                "expired_date": org.subscription_end_date,
                "days_expired": (current_date - org.subscription_end_date).days if org.subscription_end_date else 0
            })

        # Check organizations overdue for payment (30, 60, 90+ days)
        overdue_orgs = self._get_overdue_payment_organizations(current_date)
        for org_data in overdue_orgs:
            org = org_data["organization"]
            days_overdue = org_data["days_overdue"]
            
            if days_overdue >= 90:
                action = "SUSPEND_FOR_NONPAYMENT"
                reason = f"Payment overdue for {days_overdue} days - suspension required"
            elif days_overdue >= 60:
                action = "SEND_FINAL_NOTICE"
                reason = f"Payment overdue for {days_overdue} days - final notice"
            elif days_overdue >= 30:
                action = "SEND_PAYMENT_REMINDER"
                reason = f"Payment overdue for {days_overdue} days - reminder needed"
            else:
                continue
                
            actions_needed.append({
                "organization_id": org.id,
                "organization_name": org.name,
                "action": action,
                "reason": reason,
                "days_overdue": days_overdue,
                "last_payment_date": org.last_billed_date
            })

        logger.info(f"Found {len(actions_needed)} organizations requiring deactivation action")
        return actions_needed

    # ── Specific Deactivation Methods ───────────────────────────────────

    def expire_trial_organization(self, organization_id: UUID, expired_by: Optional[UUID] = None) -> Dict:
        """Expire organization trial and move to subscription required status
        
        Args:
            organization_id: Organization to expire trial for
            expired_by: System admin performing the action (None for automated)
            
        Returns:
            Dictionary with expiration details and next steps
        """
        org = self._get_organization(organization_id)
        
        # Validate organization is in trial
        if org.billing_status != BillingStatus.TRIAL:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Organization is not in trial status (current: {org.billing_status})"
            )
        
        # Update organization status
        original_status = org.billing_status
        org.billing_status = BillingStatus.EXPIRED
        org.subscription_end_date = datetime.now(UTC).date()
        
        self.db.commit()
        self.db.refresh(org)
        
        # Send trial expiration notification
        self._send_deactivation_notification(
            org, DeactivationType.TRIAL_EXPIRED, expired_by
        )
        
        logger.info(f"Expired trial for organization {organization_id} by {expired_by or 'system'}")
        
        return {
            "organization_id": organization_id,
            "organization_name": org.name,
            "deactivation_type": DeactivationType.TRIAL_EXPIRED,
            "previous_status": original_status,
            "new_status": org.billing_status,
            "deactivated_by": expired_by,
            "deactivation_date": org.subscription_end_date,
            "next_steps": "Requires subscription activation to reactivate"
        }

    def expire_subscription_organization(self, organization_id: UUID, expired_by: Optional[UUID] = None) -> Dict:
        """Expire organization subscription and deactivate access
        
        Args:
            organization_id: Organization to expire subscription for  
            expired_by: System admin performing the action (None for automated)
            
        Returns:
            Dictionary with expiration details and reactivation requirements
        """
        org = self._get_organization(organization_id)
        
        # Validate organization has subscription
        if org.billing_status not in [BillingStatus.ACTIVE, BillingStatus.OVERDUE]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Organization does not have active subscription (current: {org.billing_status})"
            )
        
        # Update organization status
        original_status = org.billing_status
        org.billing_status = BillingStatus.EXPIRED
        
        self.db.commit()
        self.db.refresh(org)
        
        # Send subscription expiration notification
        self._send_deactivation_notification(
            org, DeactivationType.SUBSCRIPTION_EXPIRED, expired_by
        )
        
        logger.info(f"Expired subscription for organization {organization_id} by {expired_by or 'system'}")
        
        return {
            "organization_id": organization_id,
            "organization_name": org.name,
            "deactivation_type": DeactivationType.SUBSCRIPTION_EXPIRED,
            "previous_status": original_status,
            "new_status": org.billing_status,
            "deactivated_by": expired_by,
            "deactivation_date": datetime.now(UTC).date(),
            "next_steps": "Requires subscription renewal to reactivate"
        }

    def suspend_organization_for_nonpayment(
        self, 
        organization_id: UUID, 
        days_overdue: int,
        suspended_by: Optional[UUID] = None
    ) -> Dict:
        """Suspend organization for non-payment after reminder escalation
        
        Args:
            organization_id: Organization to suspend
            days_overdue: Number of days payment is overdue
            suspended_by: System admin performing suspension (None for automated)
            
        Returns:
            Dictionary with suspension details and reactivation requirements
        """
        org = self._get_organization(organization_id)
        
        # Validate organization is overdue
        if org.billing_status != BillingStatus.OVERDUE:
            # Auto-update to overdue if not already set
            org.billing_status = BillingStatus.OVERDUE
        
        # Update to suspended status
        original_status = org.billing_status
        org.billing_status = BillingStatus.SUSPENDED
        
        self.db.commit()
        self.db.refresh(org)
        
        # Send suspension notification
        self._send_deactivation_notification(
            org, DeactivationType.NONPAYMENT_SUSPENSION, suspended_by,
            additional_context={"days_overdue": days_overdue}
        )
        
        logger.info(f"Suspended organization {organization_id} for {days_overdue} days overdue by {suspended_by or 'system'}")
        
        return {
            "organization_id": organization_id,
            "organization_name": org.name,
            "deactivation_type": DeactivationType.NONPAYMENT_SUSPENSION,
            "previous_status": original_status,
            "new_status": org.billing_status,
            "days_overdue": days_overdue,
            "suspended_by": suspended_by,
            "suspension_date": datetime.now(UTC).date(),
            "next_steps": "Requires payment and manual reactivation approval"
        }

    def cancel_organization_subscription(
        self, 
        organization_id: UUID,
        cancellation_reason: str,
        effective_date: Optional[datetime] = None,
        cancelled_by: Optional[UUID] = None
    ) -> Dict:
        """Cancel organization subscription (user-initiated or policy violation)
        
        Args:
            organization_id: Organization to cancel
            cancellation_reason: Reason for cancellation
            effective_date: When cancellation takes effect (default: immediate)
            cancelled_by: User or admin cancelling subscription
            
        Returns:
            Dictionary with cancellation details and grace period info
        """
        org = self._get_organization(organization_id)
        
        effective_date = effective_date or datetime.now(UTC)
        grace_period_end = effective_date + timedelta(days=30)  # 30-day grace period
        
        # Update organization status
        original_status = org.billing_status
        org.billing_status = BillingStatus.CANCELLED
        org.subscription_end_date = effective_date.date()
        
        self.db.commit()
        self.db.refresh(org)
        
        # Send cancellation notification
        self._send_deactivation_notification(
            org, DeactivationType.MANUAL_CANCELLATION, cancelled_by,
            additional_context={
                "cancellation_reason": cancellation_reason,
                "grace_period_end": grace_period_end.date()
            }
        )
        
        logger.info(f"Cancelled subscription for organization {organization_id}: {cancellation_reason}")
        
        return {
            "organization_id": organization_id,
            "organization_name": org.name,
            "deactivation_type": DeactivationType.MANUAL_CANCELLATION,
            "previous_status": original_status,
            "new_status": org.billing_status,
            "cancellation_reason": cancellation_reason,
            "effective_date": effective_date.date(),
            "grace_period_end": grace_period_end.date(),
            "cancelled_by": cancelled_by,
            "next_steps": f"Access continues until {grace_period_end.date()}, then requires new subscription"
        }

    # ── Reactivation Methods ────────────────────────────────────────────

    def reactivate_organization(
        self, 
        organization_id: UUID,
        new_subscription_end_date: datetime,
        reactivated_by: UUID,
        reactivation_notes: Optional[str] = None
    ) -> Dict:
        """Reactivate deactivated organization with new subscription period
        
        Args:
            organization_id: Organization to reactivate
            new_subscription_end_date: New subscription end date
            reactivated_by: System admin reactivating the organization
            reactivation_notes: Optional notes about reactivation
            
        Returns:
            Dictionary with reactivation details
        """
        org = self._get_organization(organization_id)
        
        # Validate organization can be reactivated
        if org.billing_status not in [
            BillingStatus.EXPIRED, BillingStatus.SUSPENDED, 
            BillingStatus.CANCELLED, BillingStatus.OVERDUE
        ]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Organization cannot be reactivated from status: {org.billing_status}"
            )
        
        # Update organization to active status
        original_status = org.billing_status 
        org.billing_status = BillingStatus.ACTIVE
        org.subscription_start_date = datetime.now(UTC).date()
        org.subscription_end_date = new_subscription_end_date.date()
        org.next_billing_date = new_subscription_end_date.date()
        
        self.db.commit()
        self.db.refresh(org)
        
        # Send reactivation notification
        self._send_reactivation_notification(org, reactivated_by, reactivation_notes)
        
        logger.info(f"Reactivated organization {organization_id} until {new_subscription_end_date.date()} by {reactivated_by}")
        
        return {
            "organization_id": organization_id,
            "organization_name": org.name,
            "previous_status": original_status,
            "new_status": org.billing_status,
            "subscription_start_date": org.subscription_start_date,
            "subscription_end_date": org.subscription_end_date,
            "reactivated_by": reactivated_by,
            "reactivation_date": datetime.now(UTC).date(),
            "reactivation_notes": reactivation_notes
        }

    # ── Status and Reporting Methods ─────────────────────────────────────

    def get_deactivation_summary(self) -> Dict:
        """Get summary of organization statuses for admin dashboard
        
        Returns counts and details for different billing statuses
        """
        # Count organizations by billing status
        status_counts = {}
        for status in BillingStatus:
            count = (
                self.db.query(Organization)
                .filter(
                    Organization.billing_status == status,
                    Organization.organization_type == OrganizationType.CUSTOMER
                )
                .count()
            )
            status_counts[status.value] = count
        
        # Get organizations needing attention
        current_date = datetime.now(UTC).date()
        
        # Trial expiring soon (next 7 days)
        trial_expiring_soon = (
            self.db.query(Organization)
            .filter(
                Organization.billing_status == BillingStatus.TRIAL,
                Organization.trial_end_date.between(
                    current_date, current_date + timedelta(days=7)
                )
            )
            .count() 
        )
        
        # Subscriptions expiring soon (next 30 days)
        subscription_expiring_soon = (
            self.db.query(Organization)
            .filter(
                Organization.billing_status == BillingStatus.ACTIVE,
                Organization.subscription_end_date.between(
                    current_date, current_date + timedelta(days=30)
                )
            )
            .count()
        )
        
        return {
            "status_counts": status_counts,
            "alerts": {
                "trial_expiring_soon_7days": trial_expiring_soon,
                "subscription_expiring_soon_30days": subscription_expiring_soon,
                "total_deactivated": (
                    status_counts.get(BillingStatus.EXPIRED.value, 0) + 
                    status_counts.get(BillingStatus.SUSPENDED.value, 0) +
                    status_counts.get(BillingStatus.CANCELLED.value, 0)
                ),
                "overdue_requiring_action": status_counts.get(BillingStatus.OVERDUE.value, 0)
            },
            "last_updated": datetime.now(UTC)
        }

    # ── Internal Helper Methods ─────────────────────────────────────────

    def _get_organization(self, organization_id: UUID) -> Organization:
        """Get organization by ID with validation"""
        org = (
            self.db.query(Organization)
            .filter(Organization.id == organization_id)
            .first()
        )
        
        if not org:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Organization not found"
            )
        
        return org

    def _get_trial_expired_organizations(self, current_date: datetime.date) -> List[Organization]:
        """Get organizations with expired trials"""
        return (
            self.db.query(Organization)
            .filter(
                Organization.billing_status == BillingStatus.TRIAL,
                Organization.trial_end_date < current_date,
                Organization.organization_type == OrganizationType.CUSTOMER
            )
            .all()
        )

    def _get_subscription_expired_organizations(self, current_date: datetime.date) -> List[Organization]:
        """Get organizations with expired subscriptions"""
        return (
            self.db.query(Organization)
            .filter(
                Organization.billing_status.in_([BillingStatus.ACTIVE, BillingStatus.OVERDUE]),
                Organization.subscription_end_date < current_date,
                Organization.organization_type == OrganizationType.CUSTOMER
            )
            .all()
        )

    def _get_overdue_payment_organizations(self, current_date: datetime.date) -> List[Dict]:
        """Get organizations with overdue payments and calculate days overdue"""
        overdue_orgs = (
            self.db.query(Organization)
            .filter(
                Organization.billing_status == BillingStatus.OVERDUE,
                Organization.next_billing_date < current_date,
                Organization.organization_type == OrganizationType.CUSTOMER
            )
            .all()
        )
        
        result = []
        for org in overdue_orgs:
            if org.next_billing_date:
                days_overdue = (current_date - org.next_billing_date).days
                result.append({
                    "organization": org,
                    "days_overdue": days_overdue
                })
        
        return result

    def _send_deactivation_notification(
        self, 
        organization: Organization, 
        deactivation_type: DeactivationType,
        deactivated_by: Optional[UUID] = None,
        additional_context: Optional[Dict] = None
    ):
        """Send email notification about organization deactivation"""
        try:
            # Use existing communication service to send deactivation email
            context = {
                "organization_name": organization.name,
                "deactivation_type": deactivation_type.value,
                "deactivation_date": datetime.now(UTC).date(),
                "deactivated_by": "System" if not deactivated_by else "Administrator"
            }
            
            if additional_context:
                context.update(additional_context)
            
            # Send to organization admins
            self.communication_service.send_organization_notification(
                organization_id=organization.id,
                template_name=f"organization_deactivation_{deactivation_type.value}",
                context=context,
                recipient_roles=["organization_admin", "billing_contact"]
            )
            
            logger.info(f"Sent deactivation notification for org {organization.id} type {deactivation_type}")
            
        except Exception as e:
            logger.error(f"Failed to send deactivation notification: {e}")
            # Don't fail the deactivation process if notification fails

    def _send_reactivation_notification(
        self, 
        organization: Organization,
        reactivated_by: UUID,
        reactivation_notes: Optional[str]
    ):
        """Send email notification about successful reactivation"""
        try:
            context = {
                "organization_name": organization.name,
                "reactivation_date": datetime.now(UTC).date(),
                "subscription_end_date": organization.subscription_end_date,
                "reactivated_by": "Administrator",
                "notes": reactivation_notes or "No additional notes"
            }
            
            # Send to organization admins
            self.communication_service.send_organization_notification(
                organization_id=organization.id,
                template_name="organization_reactivation",
                context=context,
                recipient_roles=["organization_admin", "billing_contact"]
            )
            
            logger.info(f"Sent reactivation notification for org {organization.id}")
            
        except Exception as e:
            logger.error(f"Failed to send reactivation notification: {e}")
            # Don't fail the reactivation process if notification fails