"""Billing Management API Endpoints for System Administrators

Task 1F-1: API endpoints for subscription invoice creation, billing management,
and cross-organization billing operations for system administrators.
"""

import logging
from datetime import datetime
from decimal import Decimal
from typing import Dict, List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import CurrentUser, require_permission
from app.models.base import BillingCycle
from app.services.admin_invoice_service import AdminInvoiceService
from app.services.subscription_invoice_service import SubscriptionInvoiceService

logger = logging.getLogger(__name__)

# HTTP Bearer token scheme
security = HTTPBearer()

router = APIRouter()


# ── Request/Response Models ─────────────────────────────────────────────

class CreateSubscriptionInvoiceRequest(BaseModel):
    """Request model for creating subscription invoices"""
    organization_id: UUID = Field(..., description="Customer organization ID")
    billing_cycle: BillingCycle = Field(..., description="Billing cycle (monthly, quarterly, yearly)")
    seat_count: int = Field(..., ge=1, description="Number of seats/users")
    credit_usage: Optional[Decimal] = Field(Decimal("0.00"), description="Credit usage amount")
    base_price_per_seat: Optional[Decimal] = Field(Decimal("10.00"), description="Base price per seat")
    credit_rate: Optional[Decimal] = Field(Decimal("0.01"), description="Price per credit unit")


class CreateSetupFeeInvoiceRequest(BaseModel):
    """Request model for creating setup fee invoices"""
    organization_id: UUID = Field(..., description="Customer organization ID")
    setup_fee_amount: Decimal = Field(..., gt=0, description="Setup fee amount")
    description: Optional[str] = Field("Initial setup fee", description="Setup fee description")
    include_onboarding: Optional[bool] = Field(False, description="Include onboarding services")
    onboarding_fee: Optional[Decimal] = Field(Decimal("0.00"), description="Onboarding fee amount")
    notes: Optional[str] = Field(None, description="Invoice notes")


class CreateOverageInvoiceRequest(BaseModel):
    """Request model for creating overage charges"""
    organization_id: UUID = Field(..., description="Customer organization ID")
    overage_type: str = Field(..., description="Type of overage (users, credits, storage, etc)")
    overage_quantity: int = Field(..., gt=0, description="Quantity over limit")
    overage_rate: Decimal = Field(..., gt=0, description="Rate per overage unit")
    billing_period_start: datetime = Field(..., description="Billing period start date")
    billing_period_end: datetime = Field(..., description="Billing period end date")
    notes: Optional[str] = Field(None, description="Invoice notes")


class CreateAddonInvoiceRequest(BaseModel):
    """Request model for creating addon service invoices"""
    organization_id: UUID = Field(..., description="Customer organization ID")
    addon_name: str = Field(..., description="Name of addon service")
    addon_description: str = Field(..., description="Description of addon service")
    addon_price: Decimal = Field(..., gt=0, description="Addon service price")
    billing_cycle: BillingCycle = Field(..., description="Billing cycle for addon")
    start_date: Optional[datetime] = Field(None, description="Addon service start date")
    notes: Optional[str] = Field(None, description="Invoice notes")


class CreateCreditAdjustmentRequest(BaseModel):
    """Request model for creating credit adjustments/refunds"""
    organization_id: UUID = Field(..., description="Customer organization ID") 
    adjustment_type: str = Field(..., description="Type: credit, refund, discount")
    adjustment_amount: Decimal = Field(..., description="Adjustment amount (positive for credits)")
    reason: str = Field(..., description="Reason for adjustment")
    reference_invoice_id: Optional[UUID] = Field(None, description="Reference invoice if applicable")
    notes: Optional[str] = Field(None, description="Additional notes")


class BillingSummaryResponse(BaseModel):
    """Response model for billing summary"""
    organization_id: UUID
    organization_name: str
    billing_status: str
    total_invoices: int
    total_amount: Decimal
    total_paid: Decimal
    total_outstanding: Decimal
    current_subscription: Optional[Dict]
    recent_invoices: List[Dict]
    payment_history: List[Dict]


class AssignCustomerRequest(BaseModel):
    """Request model for assigning customer to master organization"""
    customer_organization_id: UUID = Field(..., description="Customer organization ID")
    master_organization_id: UUID = Field(..., description="Master organization ID")


class SetupSystemAdminRequest(BaseModel):
    """Request model for setting up system admin user"""
    user_id: UUID = Field(..., description="User ID to assign as system admin")
    master_organization_id: UUID = Field(..., description="Master organization ID")
    admin_type: str = Field("system_admin_master", description="Type of system admin role")


# ── Subscription Invoice Management ─────────────────────────────────────

@router.post("/subscription-invoice", response_model=Dict, status_code=status.HTTP_201_CREATED)
async def create_subscription_invoice(
    request: CreateSubscriptionInvoiceRequest,
    db: Session = Depends(get_db),
    current_user = Depends(require_permission("system_admin.billing"))
):
    """Create subscription invoice for customer organization
    
    Creates monthly, quarterly, or yearly subscription invoice with:
    - Base seat charges
    - Credit usage charges  
    - Custom line items
    - Automatic payment terms calculation
    """
    try:
        service = SubscriptionInvoiceService(db)
        
        invoice = service.create_subscription_invoice(
            organization_id=request.organization_id,
            billing_cycle=request.billing_cycle,
            seat_count=request.seat_count,
            credit_usage=request.credit_usage,
            base_price_per_seat=request.base_price_per_seat,
            credit_rate=request.credit_rate,
            created_by=current_user.id
        )
        
        logger.info(f"Created subscription invoice {invoice['id']} for org {request.organization_id}")
        return invoice
        
    except Exception as e:
        logger.error(f"Failed to create subscription invoice: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create subscription invoice: {str(e)}"
        )


@router.post("/setup-fee-invoice", response_model=Dict, status_code=status.HTTP_201_CREATED)
async def create_setup_fee_invoice(
    request: CreateSetupFeeInvoiceRequest,
    db: Session = Depends(get_db),
    current_user = Depends(require_permission("system_admin.billing"))
):
    """Create setup fee invoice for new customer organization
    
    Creates one-time setup fee invoice for organization onboarding
    """
    try:
        service = SubscriptionInvoiceService(db)
        
        line_items = [
            {
                "description": request.description,
                "quantity": 1,
                "unit_price": request.setup_fee_amount,
                "total_amount": request.setup_fee_amount
            }
        ]
        
        if request.include_onboarding and request.onboarding_fee > 0:
            line_items.append({
                "description": "Onboarding and training services",
                "quantity": 1,
                "unit_price": request.onboarding_fee,
                "total_amount": request.onboarding_fee
            })
        
        invoice = service.create_setup_fee_invoice(
            organization_id=request.organization_id,
            setup_fee_amount=request.setup_fee_amount,
            onboarding_fee=request.onboarding_fee if request.include_onboarding else Decimal("0"),
            line_items=line_items,
            notes=request.notes,
            created_by=current_user.id
        )
        
        logger.info(f"Created setup fee invoice {invoice['id']} for org {request.organization_id}")
        return invoice
        
    except Exception as e:
        logger.error(f"Failed to create setup fee invoice: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create setup fee invoice: {str(e)}"
        )


@router.post("/overage-invoice", response_model=Dict, status_code=status.HTTP_201_CREATED)
async def create_overage_invoice(
    request: CreateOverageInvoiceRequest,
    db: Session = Depends(get_db), 
    current_user = Depends(require_permission("system_admin.billing"))
):
    """Create overage charges invoice for usage exceeding limits
    
    Creates invoice for organizations exceeding their seat, credit, or other limits
    """
    try:
        service = SubscriptionInvoiceService(db)
        
        invoice = service.create_overage_invoice(
            organization_id=request.organization_id,
            overage_type=request.overage_type,
            overage_quantity=request.overage_quantity,
            overage_rate=request.overage_rate,
            billing_period_start=request.billing_period_start,
            billing_period_end=request.billing_period_end,
            notes=request.notes,
            created_by=current_user.id
        )
        
        logger.info(f"Created overage invoice {invoice['id']} for org {request.organization_id}")
        return invoice
        
    except Exception as e:
        logger.error(f"Failed to create overage invoice: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create overage invoice: {str(e)}"
        )


@router.post("/addon-invoice", response_model=Dict, status_code=status.HTTP_201_CREATED)
async def create_addon_invoice(
    request: CreateAddonInvoiceRequest,
    db: Session = Depends(get_db),
    current_user = Depends(require_permission("system_admin.billing"))
):
    """Create addon service invoice for additional features/services
    
    Creates invoice for premium features, additional services, or add-on modules
    """
    try:
        service = SubscriptionInvoiceService(db)
        
        invoice = service.create_addon_invoice(
            organization_id=request.organization_id,
            addon_name=request.addon_name,
            addon_description=request.addon_description,
            addon_price=request.addon_price,
            billing_cycle=request.billing_cycle,
            start_date=request.start_date,
            notes=request.notes,
            created_by=current_user.id
        )
        
        logger.info(f"Created addon invoice {invoice['id']} for org {request.organization_id}")
        return invoice
        
    except Exception as e:
        logger.error(f"Failed to create addon invoice: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create addon invoice: {str(e)}"
        )


@router.post("/credit-adjustment-invoice", response_model=Dict, status_code=status.HTTP_201_CREATED)
async def create_credit_adjustment_invoice(
    request: CreateCreditAdjustmentRequest,
    db: Session = Depends(get_db),
    current_user = Depends(require_permission("system_admin.billing"))
):
    """Create credit adjustment or refund invoice
    
    Creates credit notes, refunds, or billing adjustments for customer organizations
    """
    try:
        service = SubscriptionInvoiceService(db)
        
        invoice = service.create_credit_adjustment_invoice(
            organization_id=request.organization_id,
            adjustment_type=request.adjustment_type,
            adjustment_amount=request.adjustment_amount,
            reason=request.reason,
            reference_invoice_id=request.reference_invoice_id,
            notes=request.notes,
            created_by=current_user.id
        )
        
        logger.info(f"Created credit adjustment invoice {invoice['id']} for org {request.organization_id}")
        return invoice
        
    except Exception as e:
        logger.error(f"Failed to create credit adjustment invoice: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create credit adjustment invoice: {str(e)}"
        )


# ── Billing Summary & Organization Management ───────────────────────────

@router.get("/summary", response_model=Dict)
async def get_overall_billing_summary(
    db: Session = Depends(get_db),
    current_user = Depends(require_permission("system_admin.billing"))
):
    """Get overall billing summary for all customer organizations
    
    Returns aggregate billing metrics across all customers for admin dashboard
    """
    try:
        admin_service = AdminInvoiceService(db)
        
        # Get aggregate billing metrics
        summary = {
            "total_customers": 0,
            "total_invoices": 0,
            "total_revenue": 0,
            "total_outstanding": 0,
            "overdue_invoices": 0,
            "recent_invoices": [],
            "status_breakdown": {
                "draft": 0,
                "sent": 0,
                "paid": 0,
                "overdue": 0,
                "cancelled": 0
            }
        }
        
        # Get invoice metrics using raw SQL for better performance
        metrics_query = """
        SELECT 
            COUNT(DISTINCT organization_id) as total_customers,
            COUNT(*) as total_invoices,
            SUM(grand_total) as total_revenue,
            SUM(outstanding_amount) as total_outstanding,
            SUM(CASE WHEN status = 'overdue' THEN 1 ELSE 0 END) as overdue_invoices,
            status,
            COUNT(*) as status_count
        FROM invoices
        WHERE invoice_type = 'sales'
        GROUP BY status
        """
        
        from sqlalchemy import text
        result = db.execute(text("""
            SELECT 
                COUNT(DISTINCT organization_id) as total_customers,
                COUNT(*) as total_invoices,
                COALESCE(SUM(grand_total), 0) as total_revenue,
                COALESCE(SUM(outstanding_amount), 0) as total_outstanding,
                SUM(CASE WHEN status = 'overdue' THEN 1 ELSE 0 END) as overdue_invoices
            FROM invoices
            WHERE invoice_type = 'sales'
        """)).first()
        
        if result:
            summary.update({
                "total_customers": result.total_customers or 0,
                "total_invoices": result.total_invoices or 0, 
                "total_revenue": float(result.total_revenue or 0),
                "total_outstanding": float(result.total_outstanding or 0),
                "overdue_invoices": result.overdue_invoices or 0
            })
        
        # Get status breakdown
        status_result = db.execute(text("""
            SELECT status, COUNT(*) as status_count 
            FROM invoices 
            WHERE invoice_type = 'sales'
            GROUP BY status
        """)).fetchall()
        
        for row in status_result:
            if row.status in summary["status_breakdown"]:
                summary["status_breakdown"][row.status] = row.status_count
        
        # Get recent invoices
        recent_result = db.execute(text("""
            SELECT id, invoice_no, organization_id, grand_total, status, posting_date
            FROM invoices
            WHERE invoice_type = 'sales'
            ORDER BY posting_date DESC
            LIMIT 10
        """)).fetchall()
        
        summary["recent_invoices"] = [
            {
                "id": str(row.id),
                "invoice_no": row.invoice_no,
                "organization_id": str(row.organization_id),
                "amount": float(row.grand_total),
                "status": row.status,
                "date": row.posting_date.isoformat() if row.posting_date else None
            }
            for row in recent_result
        ]
        
        logger.info(f"Generated overall billing summary with {summary['total_invoices']} invoices")
        return summary
        
    except Exception as e:
        logger.error(f"Failed to get overall billing summary: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get billing summary: {str(e)}"
        )


@router.get("/summary/{customer_id}", response_model=BillingSummaryResponse)
async def get_billing_summary(
    customer_id: UUID,
    db: Session = Depends(get_db),
    current_user = Depends(require_permission("system_admin.billing"))
):
    """Get comprehensive billing summary for customer organization
    
    Returns billing status, invoice totals, payment history, and subscription info
    """
    try:
        admin_service = AdminInvoiceService(db)
        
        summary = admin_service.get_organization_billing_summary(
            organization_id=customer_id,
            requested_by=current_user.id
        )
        
        return BillingSummaryResponse(**summary)
        
    except Exception as e:
        logger.error(f"Failed to get billing summary for org {customer_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get billing summary: {str(e)}"
        )


@router.get("/customer-organizations", response_model=List[Dict])
async def get_customer_organizations(
    billing_status: Optional[str] = Query(None, description="Filter by billing status"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    credentials: HTTPAuthorizationCredentials = Depends(security),
    _current_user: CurrentUser = Depends(require_permission("system_admin.org_manager"))
):
    """Get list of customer organizations accessible to system admin
    
    Returns paginated list of organizations with billing information
    """
    try:
        from app.services.admin_organization_service import AdminOrganizationService
        
        org_service = AdminOrganizationService(db, token=credentials.credentials)
        
        # Calculate page number from offset/limit
        page = (offset // limit) + 1
        
        organizations_response = await org_service.list_organizations(
            status_filter=billing_status,
            page=page,
            page_size=limit
        )
        
        result = []
        for org in organizations_response.organizations:
            result.append({
                "organization_id": org.id,
                "organization_name": org.name,
                "billing_status": getattr(org, 'billing_status', None),
                "subscription_start_date": getattr(org, 'subscription_start_date', None),
                "subscription_end_date": getattr(org, 'subscription_end_date', None),
                "seat_limit": getattr(org, 'max_users', None),
                "credit_limit": getattr(org, 'max_credits', None),
                "billing_contact_email": getattr(org, 'billing_contact_email', None),
                "billing_cycle": getattr(org, 'billing_cycle', None),
                "customer_since": getattr(org, 'customer_since', None),
                "last_billed_date": getattr(org, 'last_billed_date', None),
                "next_billing_date": getattr(org, 'next_billing_date', None)
            })
        
        return result
        
    except Exception as e:
        logger.error(f"Failed to get customer organizations: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get customer organizations: {str(e)}"
        )


@router.post("/assign-customer-to-master", response_model=Dict)
async def assign_customer_to_master(
    request: AssignCustomerRequest,
    db: Session = Depends(get_db),
    credentials: HTTPAuthorizationCredentials = Depends(security),
    current_user: CurrentUser = Depends(require_permission("system_admin.org_manager"))
):
    """Assign customer organization to master organization for billing management
    
    Links customer organization to master organization for system admin access
    """
    try:
        # TODO: Implement API call to identity-service for cross-org assignment
        # This should call the SystemAdminPermissionService via HTTP API
        logger.info(f"Assignment request: customer={request.customer_organization_id}, master={request.master_organization_id}")
        
        # For now, return success - this needs proper implementation
        return {
            "customer_organization_id": request.customer_organization_id,
            "customer_organization_name": f"Organization {request.customer_organization_id}",
            "master_organization_id": request.master_organization_id,
            "assigned_by": current_user.id,
            "assignment_date": datetime.now(),
            "status": "pending_implementation"
        }
        
    except Exception as e:
        logger.error(f"Failed to assign customer to master: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to assign customer to master: {str(e)}"
        )


@router.post("/setup-system-admin", response_model=Dict)
async def setup_system_admin(
    request: SetupSystemAdminRequest,
    db: Session = Depends(get_db),
    current_user = Depends(require_permission("system_admin.master"))
):
    """Assign system admin role to user in master organization
    
    Sets up user with system admin permissions for cross-organization management
    """
    try:
        # TODO: Implement API call to identity-service for system admin setup
        # This should call the SystemAdminPermissionService via HTTP API
        logger.info(f"System admin setup request: user={request.user_id}, master_org={request.master_organization_id}")
        
        # For now, return success - this needs proper implementation
        return {
            "user_id": request.user_id,
            "master_organization_id": request.master_organization_id,
            "admin_type": request.admin_type,
            "role_assignment_id": "pending",
            "permissions_granted": [],
            "assigned_by": current_user.id,
            "assignment_date": datetime.now(),
            "status": "pending_implementation"
        }
        
    except Exception as e:
        logger.error(f"Failed to setup system admin: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to setup system admin: {str(e)}"
        )


# ── Tier Update ──────────────────────────────────────────────────────────

class UpdateTierRequest(BaseModel):
    new_tier: str = Field(..., pattern="^(basic|pro|enterprise)$")
    effective_date: str | None = None
    prorated: bool = False
    reason: str | None = None


@router.post("/organizations/{organization_id}/update-tier")
async def update_organization_tier(
    organization_id: UUID,
    request: UpdateTierRequest,
    db: Session = Depends(get_db),
    credentials: HTTPAuthorizationCredentials = Depends(security),
    _current_user: CurrentUser = Depends(require_permission("system_admin.billing")),
):
    """Update an organization's subscription tier (basic/pro/enterprise).

    Updates billing fields on the identity-service organization record.
    """
    try:
        from app.config import settings
        from sqlalchemy import create_engine, text

        # Tier → defaults mapping
        tier_config = {
            "basic": {"max_users": 10, "max_credits": 1000},
            "pro": {"max_users": 50, "max_credits": 5000},
            "enterprise": {"max_users": 500, "max_credits": 50000},
        }
        cfg = tier_config[request.new_tier]

        # Update directly in identity DB
        if not settings.identity_database_url:
            raise HTTPException(status_code=500, detail="Identity database not configured")

        engine = create_engine(settings.identity_database_url, pool_size=2, max_overflow=0)
        with engine.connect() as conn:
            result = conn.execute(
                text(
                    "UPDATE organizations SET max_users = :max_users, max_credits = :max_credits, "
                    "billing_status = 'active', updated_at = NOW() "
                    "WHERE id = :org_id RETURNING name"
                ),
                {"max_users": cfg["max_users"], "max_credits": cfg["max_credits"], "org_id": str(organization_id)},
            )
            row = result.fetchone()
            conn.commit()

        if not row:
            raise HTTPException(status_code=404, detail="Organization not found")

        return {
            "success": True,
            "message": f"Tier updated to {request.new_tier} for {row[0]}",
            "organization_id": str(organization_id),
            "new_tier": request.new_tier,
            "max_users": cfg["max_users"],
            "max_credits": cfg["max_credits"],
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update tier for {organization_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to update tier: {str(e)}")
