"""Payment Reminder Service for automated billing reminders

Task 1D-2: Implements payment reminder logic, escalation sequences, and
automated billing notifications using existing email infrastructure.
"""

import logging
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Dict, List, Optional
from uuid import UUID, uuid4

from fastapi import HTTPException, status
from sqlalchemy import and_, func, or_
from sqlalchemy.orm import Session, joinedload

from app.models.invoice import Invoice
from app.models.messaging import MessageTemplate
from app.models.reminder_config import (
    ReminderConfig,
    ReminderLog,
    ReminderStage,
    ReminderStatus,
    ReminderType,
)
from app.services.communication_service import CommunicationService
from app.services.subscription_invoice_service import SubscriptionInvoiceService

logger = logging.getLogger(__name__)


class PaymentReminderService:
    """Service for managing payment reminders and escalation sequences
    
    Task 1D-2: Reuses existing EmailService and CommunicationService for sending reminders
    """

    def __init__(self, db: Session):
        self.db = db
        self.communication_service = CommunicationService(db)
        self.subscription_service = SubscriptionInvoiceService(db)

    # ── Reminder Configuration ──────────────────────────────────────────

    def get_reminder_config(self, organization_id: UUID) -> ReminderConfig:
        """Get reminder configuration for organization, create default if not exists"""
        config = (
            self.db.query(ReminderConfig)
            .filter(ReminderConfig.organization_id == organization_id)
            .first()
        )
        
        if not config:
            config = self.create_default_reminder_config(organization_id)
            
        return config

    def create_default_reminder_config(self, organization_id: UUID) -> ReminderConfig:
        """Create default reminder configuration for organization"""
        config = ReminderConfig(
            organization_id=organization_id,
            reminder_type=ReminderType.AUTO,
            grace_period_days=30,
            first_reminder_days=30,
            second_reminder_days=60,
            final_notice_days=90,
            auto_deactivate_days=120,
            reminder_frequency_days=7,
            max_reminders_per_stage=3,
            escalation_sequence=[
                ReminderStage.FIRST_REMINDER.value,
                ReminderStage.SECOND_REMINDER.value,
                ReminderStage.FINAL_NOTICE.value,
                ReminderStage.DEACTIVATION_NOTICE.value,
            ],
            is_enabled=True,
        )
        
        self.db.add(config)
        self.db.commit()
        self.db.refresh(config)
        
        logger.info(f"Created default reminder config for organization {organization_id}")
        return config

    def update_reminder_config(
        self, organization_id: UUID, updates: Dict
    ) -> ReminderConfig:
        """Update reminder configuration for organization"""
        config = self.get_reminder_config(organization_id)
        
        for field, value in updates.items():
            if hasattr(config, field):
                setattr(config, field, value)
        
        config.updated_at = datetime.now(UTC)
        self.db.commit()
        self.db.refresh(config)
        
        logger.info(f"Updated reminder config for organization {organization_id}")
        return config

    # ── Overdue Invoice Detection ───────────────────────────────────────

    def get_overdue_invoices(
        self, organization_id: Optional[UUID] = None, days_overdue: Optional[int] = None
    ) -> List[Dict]:
        """Get overdue invoices across organizations or for specific organization
        
        Reuses existing SubscriptionInvoiceService logic for overdue detection
        """
        if organization_id:
            # Get overdue invoices for specific organization
            now = datetime.now(UTC)
            
            query = (
                self.db.query(Invoice)
                .filter(
                    Invoice.organization_id == organization_id,
                    Invoice.due_date < now,
                    Invoice.outstanding_amount > 0,
                    Invoice.status.in_(["draft", "pending", "partial"])
                )
            )
            
            if days_overdue:
                cutoff_date = now - timedelta(days=days_overdue)
                query = query.filter(Invoice.due_date <= cutoff_date)
                
            invoices = query.order_by(Invoice.due_date.asc()).all()
            
        else:
            # Use existing subscription service method for cross-org overdue invoices
            invoices_data = self.subscription_service.get_overdue_subscription_invoices()
            return invoices_data
            
        return [self._invoice_to_dict(invoice) for invoice in invoices]

    def _invoice_to_dict(self, invoice: Invoice) -> Dict:
        """Convert invoice to dictionary with reminder context"""
        now = datetime.now(UTC)
        days_overdue = (now.date() - invoice.due_date.date()).days if invoice.due_date else 0
        
        return {
            "id": str(invoice.id),
            "organization_id": str(invoice.organization_id),
            "invoice_no": invoice.invoice_no,
            "party_type": invoice.party_type,
            "party_id": str(invoice.party_id) if invoice.party_id else None,
            "total_amount": str(invoice.total_amount),
            "outstanding_amount": str(invoice.outstanding_amount),
            "due_date": invoice.due_date.isoformat() if invoice.due_date else None,
            "days_overdue": days_overdue,
            "status": invoice.status,
            "invoice_type": invoice.invoice_type,
        }

    # ── Reminder Stage Determination ────────────────────────────────────

    def determine_reminder_stage(
        self, days_overdue: int, config: ReminderConfig
    ) -> Optional[ReminderStage]:
        """Determine appropriate reminder stage based on days overdue and config"""
        if days_overdue < config.first_reminder_days:
            return None  # Not yet due for reminders
        elif days_overdue < config.second_reminder_days:
            return ReminderStage.FIRST_REMINDER
        elif days_overdue < config.final_notice_days:
            return ReminderStage.SECOND_REMINDER
        elif days_overdue < config.auto_deactivate_days:
            return ReminderStage.FINAL_NOTICE
        else:
            return ReminderStage.DEACTIVATION_NOTICE

    def get_last_reminder_for_invoice_stage(
        self, invoice_id: UUID, stage: ReminderStage
    ) -> Optional[ReminderLog]:
        """Get the last reminder sent for a specific invoice and stage"""
        return (
            self.db.query(ReminderLog)
            .filter(
                ReminderLog.invoice_id == invoice_id,
                ReminderLog.reminder_stage == stage,
                ReminderLog.status == ReminderStatus.SENT
            )
            .order_by(ReminderLog.sent_at.desc())
            .first()
        )

    def should_send_reminder(
        self, invoice_data: Dict, config: ReminderConfig, stage: ReminderStage
    ) -> bool:
        """Check if reminder should be sent for invoice at given stage"""
        if not config.is_enabled:
            return False
            
        invoice_id = UUID(invoice_data["id"])
        days_overdue = invoice_data["days_overdue"]
        
        # Check if we've exceeded max reminders for this stage
        reminder_count = (
            self.db.query(func.count(ReminderLog.id))
            .filter(
                ReminderLog.invoice_id == invoice_id,
                ReminderLog.reminder_stage == stage,
                ReminderLog.status == ReminderStatus.SENT
            )
            .scalar()
        )
        
        if reminder_count >= config.max_reminders_per_stage:
            return False
            
        # Check if enough time has passed since last reminder
        last_reminder = self.get_last_reminder_for_invoice_stage(invoice_id, stage)
        if last_reminder:
            days_since_last = (datetime.now(UTC) - last_reminder.sent_at).days
            if days_since_last < config.reminder_frequency_days:
                return False
                
        return True

    # ── Email Template & Content ────────────────────────────────────────

    def get_reminder_template(
        self, organization_id: UUID, stage: ReminderStage, config: ReminderConfig
    ) -> Optional[MessageTemplate]:
        """Get email template for reminder stage"""
        # Map reminder stage to template name from config
        template_mapping = {
            ReminderStage.FIRST_REMINDER: config.first_reminder_template,
            ReminderStage.SECOND_REMINDER: config.second_reminder_template,
            ReminderStage.FINAL_NOTICE: config.final_notice_template,
            ReminderStage.DEACTIVATION_NOTICE: config.deactivation_notice_template,
        }
        
        template_name = template_mapping.get(stage)
        if not template_name:
            return None
            
        template = (
            self.db.query(MessageTemplate)
            .filter(
                MessageTemplate.organization_id == organization_id,
                MessageTemplate.template_name == template_name,
                MessageTemplate.channel == "email"
            )
            .first()
        )
        
        return template

    def generate_reminder_content(
        self, invoice_data: Dict, stage: ReminderStage, template: Optional[MessageTemplate] = None
    ) -> Dict[str, str]:
        """Generate reminder email subject and content"""
        invoice_no = invoice_data["invoice_no"]
        outstanding_amount = invoice_data["outstanding_amount"]
        days_overdue = invoice_data["days_overdue"]
        due_date = invoice_data["due_date"]
        
        stage_names = {
            ReminderStage.FIRST_REMINDER: "Payment Reminder",
            ReminderStage.SECOND_REMINDER: "Second Payment Notice", 
            ReminderStage.FINAL_NOTICE: "Final Payment Notice",
            ReminderStage.DEACTIVATION_NOTICE: "Account Deactivation Notice",
        }
        
        stage_name = stage_names.get(stage, "Payment Reminder")
        
        if template:
            # Use template content with variable substitution
            subject = f"{stage_name} - Invoice {invoice_no}"
            content = template.template_text.format(
                invoice_no=invoice_no,
                outstanding_amount=outstanding_amount,
                days_overdue=days_overdue,
                due_date=due_date,
                stage_name=stage_name
            )
        else:
            # Default fallback content
            subject = f"{stage_name} - Invoice {invoice_no}"
            content = f"""
Dear Customer,

This is a {stage_name.lower()} for Invoice {invoice_no}.

Invoice Details:
- Invoice Number: {invoice_no}
- Outstanding Amount: ${outstanding_amount}
- Days Overdue: {days_overdue} days
- Original Due Date: {due_date}

Please remit payment at your earliest convenience to avoid any service disruption.

Thank you for your attention to this matter.

Best regards,
Billing Department
            """.strip()
        
        return {
            "subject": subject,
            "content": content
        }

    # ── Manual Reminder Sending ─────────────────────────────────────────

    async def send_manual_reminder(
        self, invoice_id: UUID, user_id: UUID, stage: Optional[ReminderStage] = None
    ) -> Dict:
        """Send manual reminder for specific invoice
        
        Task 1D-2: Reuses existing CommunicationService for email sending
        """
        # Get invoice details
        invoice = (
            self.db.query(Invoice)
            .options(joinedload(Invoice.organization))  # Assumes relationship exists
            .filter(Invoice.id == invoice_id)
            .first()
        )
        
        if not invoice:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Invoice not found"
            )
            
        invoice_data = self._invoice_to_dict(invoice)
        config = self.get_reminder_config(invoice.organization_id)
        
        # Determine stage if not provided
        if not stage:
            stage = self.determine_reminder_stage(invoice_data["days_overdue"], config)
            if not stage:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invoice is not overdue enough for reminders"
                )
        
        # Get email template and generate content
        template = self.get_reminder_template(invoice.organization_id, stage, config)
        content = self.generate_reminder_content(invoice_data, stage, template)
        
        # Resolve recipient email (reuse logic from AdminInvoiceService)
        recipient_email, recipient_name = self._resolve_invoice_recipient(invoice)
        
        if not recipient_email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Recipient email not found for invoice"
            )
        
        # Create reminder log entry
        reminder_log = ReminderLog(
            organization_id=invoice.organization_id,
            invoice_id=invoice.id,
            config_id=config.id,
            reminder_stage=stage,
            reminder_type=ReminderType.MANUAL,
            recipient_email=recipient_email,
            recipient_name=recipient_name,
            subject=content["subject"],
            template_used=template.template_name if template else None,
            status=ReminderStatus.PENDING,
            invoice_amount=str(invoice.total_amount),
            outstanding_amount=str(invoice.outstanding_amount),
            days_overdue=invoice_data["days_overdue"],
            due_date=invoice.due_date,
            triggered_by="manual",
            user_id=user_id,
            stage_attempt_number=1,
        )
        
        self.db.add(reminder_log)
        self.db.flush()  # Get the ID
        
        try:
            # Send email using existing CommunicationService
            result = await self.communication_service.send_email(
                to=recipient_email,
                subject=content["subject"],
                message=content["content"],
                organization_id=invoice.organization_id,
                user_id=user_id,
                doc_type="payment_reminder",
                doc_id=str(invoice.id),
                doc_no=invoice.invoice_no,
            )
            
            # Update reminder log with success
            reminder_log.status = ReminderStatus.SENT
            reminder_log.sent_at = datetime.now(UTC)
            reminder_log.email_response = result
            
            # Calculate next reminder due date
            next_reminder_date = datetime.now(UTC) + timedelta(days=config.reminder_frequency_days)
            reminder_log.next_reminder_due = next_reminder_date
            
            self.db.commit()
            
            logger.info(f"Manual reminder sent for invoice {invoice_id}, stage {stage}")
            
            return {
                "success": True,
                "reminder_id": str(reminder_log.id),
                "stage": stage.value,
                "recipient": recipient_email,
                "scheduled_next": next_reminder_date.isoformat(),
            }
            
        except Exception as e:
            # Update log with failure
            reminder_log.status = ReminderStatus.FAILED
            reminder_log.error_message = str(e)
            self.db.commit()
            
            logger.error(f"Failed to send manual reminder for invoice {invoice_id}: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to send reminder: {str(e)}"
            )

    def _resolve_invoice_recipient(self, invoice: Invoice) -> tuple[Optional[str], Optional[str]]:
        """Resolve recipient email and name for invoice (reuses AdminInvoiceService logic)"""
        from app.models.customer import Customer
        from app.models.supplier import Supplier
        
        party_email = None
        party_name = None
        party_type = (invoice.party_type or "").lower()
        
        if party_type == "customer" and invoice.party_id:
            customer = self.db.query(Customer).filter(Customer.id == invoice.party_id).first()
            if customer:
                party_email = customer.email
                party_name = customer.customer_name
        elif party_type == "supplier" and invoice.party_id:
            supplier = self.db.query(Supplier).filter(Supplier.id == invoice.party_id).first()
            if supplier:
                party_email = supplier.email
                party_name = supplier.supplier_name
                
        return party_email, party_name

    # ── Batch Reminder Processing ───────────────────────────────────────

    async def send_batch_reminders(
        self, organization_ids: Optional[List[UUID]] = None, user_id: Optional[UUID] = None
    ) -> Dict:
        """Send reminders for all eligible overdue invoices
        
        Task 1D-2: Automated batch processing for reminder escalation
        """
        batch_id = uuid4()
        results = {
            "batch_id": str(batch_id),
            "started_at": datetime.now(UTC).isoformat(),
            "processed": 0,
            "sent": 0,
            "failed": 0,
            "skipped": 0,
            "details": []
        }
        
        # Get overdue invoices for processing
        if organization_ids:
            overdue_invoices = []
            for org_id in organization_ids:
                org_invoices = self.get_overdue_invoices(organization_id=org_id)
                overdue_invoices.extend(org_invoices)
        else:
            overdue_invoices = self.get_overdue_invoices()  # All organizations
            
        logger.info(f"Starting batch reminder processing for {len(overdue_invoices)} overdue invoices")
        
        for invoice_data in overdue_invoices:
            results["processed"] += 1
            
            try:
                organization_id = UUID(invoice_data["organization_id"])
                invoice_id = UUID(invoice_data["id"])
                days_overdue = invoice_data["days_overdue"]
                
                # Get reminder configuration
                config = self.get_reminder_config(organization_id)
                
                # Determine appropriate stage
                stage = self.determine_reminder_stage(days_overdue, config)
                if not stage:
                    results["skipped"] += 1
                    results["details"].append({
                        "invoice_id": str(invoice_id),
                        "status": "skipped",
                        "reason": "Not overdue enough for reminders"
                    })
                    continue
                
                # Check if reminder should be sent
                if not self.should_send_reminder(invoice_data, config, stage):
                    results["skipped"] += 1
                    results["details"].append({
                        "invoice_id": str(invoice_id),
                        "status": "skipped",
                        "reason": "Frequency limits or max attempts reached"
                    })
                    continue
                
                # Send reminder
                try:
                    reminder_result = await self.send_automated_reminder(
                        invoice_id, stage, config, batch_id, user_id
                    )
                    
                    results["sent"] += 1
                    results["details"].append({
                        "invoice_id": str(invoice_id),
                        "status": "sent",
                        "stage": stage.value,
                        "reminder_id": reminder_result["reminder_id"]
                    })
                    
                except Exception as e:
                    results["failed"] += 1
                    results["details"].append({
                        "invoice_id": str(invoice_id),
                        "status": "failed",
                        "error": str(e)
                    })
                    logger.error(f"Failed to send reminder for invoice {invoice_id}: {e}")
                    
            except Exception as e:
                results["failed"] += 1
                results["details"].append({
                    "invoice_id": invoice_data.get("id", "unknown"),
                    "status": "failed",
                    "error": f"Processing error: {str(e)}"
                })
                logger.error(f"Error processing invoice {invoice_data.get('id')}: {e}")
        
        results["completed_at"] = datetime.now(UTC).isoformat()
        logger.info(f"Batch reminder processing completed: {results['sent']} sent, {results['failed']} failed, {results['skipped']} skipped")
        
        return results

    async def send_automated_reminder(
        self, invoice_id: UUID, stage: ReminderStage, config: ReminderConfig, 
        batch_id: UUID, user_id: Optional[UUID] = None
    ) -> Dict:
        """Send automated reminder for invoice (internal method for batch processing)"""
        # Get invoice
        invoice = self.db.query(Invoice).filter(Invoice.id == invoice_id).first()
        if not invoice:
            raise ValueError(f"Invoice {invoice_id} not found")
            
        invoice_data = self._invoice_to_dict(invoice)
        
        # Get template and content
        template = self.get_reminder_template(invoice.organization_id, stage, config)
        content = self.generate_reminder_content(invoice_data, stage, template)
        
        # Resolve recipient
        recipient_email, recipient_name = self._resolve_invoice_recipient(invoice)
        if not recipient_email:
            raise ValueError(f"No recipient email found for invoice {invoice_id}")
        
        # Get current stage attempt number
        current_attempts = (
            self.db.query(func.count(ReminderLog.id))
            .filter(
                ReminderLog.invoice_id == invoice_id,
                ReminderLog.reminder_stage == stage,
                ReminderLog.status == ReminderStatus.SENT
            )
            .scalar()
        )
        
        # Create reminder log
        reminder_log = ReminderLog(
            organization_id=invoice.organization_id,
            invoice_id=invoice_id,
            config_id=config.id,
            reminder_stage=stage,
            reminder_type=ReminderType.AUTO,
            recipient_email=recipient_email,
            recipient_name=recipient_name,
            subject=content["subject"],
            template_used=template.template_name if template else None,
            status=ReminderStatus.PENDING,
            invoice_amount=str(invoice.total_amount),
            outstanding_amount=str(invoice.outstanding_amount),
            days_overdue=invoice_data["days_overdue"],
            due_date=invoice.due_date,
            triggered_by="automated",
            user_id=user_id,
            batch_id=batch_id,
            stage_attempt_number=current_attempts + 1,
        )
        
        self.db.add(reminder_log)
        self.db.flush()
        
        # Send email
        result = await self.communication_service.send_email(
            to=recipient_email,
            subject=content["subject"],
            message=content["content"],
            organization_id=invoice.organization_id,
            user_id=user_id,
            doc_type="payment_reminder",
            doc_id=str(invoice_id),
            doc_no=invoice.invoice_no,
        )
        
        # Update log
        reminder_log.status = ReminderStatus.SENT
        reminder_log.sent_at = datetime.now(UTC)
        reminder_log.email_response = result
        reminder_log.next_reminder_due = datetime.now(UTC) + timedelta(days=config.reminder_frequency_days)
        
        self.db.commit()
        
        return {"reminder_id": str(reminder_log.id), "recipient": recipient_email}

    # ── Reminder History & Analytics ─────────────────────────────────────

    def get_reminder_history(
        self, 
        organization_id: Optional[UUID] = None,
        invoice_id: Optional[UUID] = None,
        limit: int = 100
    ) -> List[Dict]:
        """Get reminder sending history with filters"""
        query = self.db.query(ReminderLog).options(joinedload(ReminderLog.invoice))
        
        if organization_id:
            query = query.filter(ReminderLog.organization_id == organization_id)
        if invoice_id:
            query = query.filter(ReminderLog.invoice_id == invoice_id)
            
        logs = query.order_by(ReminderLog.created_at.desc()).limit(limit).all()
        
        return [
            {
                "id": str(log.id),
                "invoice_id": str(log.invoice_id),
                "organization_id": str(log.organization_id),
                "stage": log.reminder_stage.value,
                "status": log.status.value,
                "recipient": log.recipient_email,
                "subject": log.subject,
                "sent_at": log.sent_at.isoformat() if log.sent_at else None,
                "days_overdue": log.days_overdue,
                "outstanding_amount": log.outstanding_amount,
                "attempt_number": log.stage_attempt_number,
                "triggered_by": log.triggered_by,
            }
            for log in logs
        ]

    def get_reminder_stats(self, organization_id: Optional[UUID] = None) -> Dict:
        """Get reminder statistics for dashboard"""
        query = self.db.query(ReminderLog)
        
        if organization_id:
            query = query.filter(ReminderLog.organization_id == organization_id)
            
        # Get counts by status
        stats = {}
        for status in ReminderStatus:
            count = query.filter(ReminderLog.status == status).count()
            stats[f"{status.value}_count"] = count
            
        # Get counts by stage  
        for stage in ReminderStage:
            count = query.filter(ReminderLog.reminder_stage == stage).count()
            stats[f"{stage.value}_count"] = count
            
        return stats