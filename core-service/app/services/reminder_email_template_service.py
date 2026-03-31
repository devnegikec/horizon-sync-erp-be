"""Email Template Management Service for Payment Reminders

Task 1D-1: Manages email templates for different reminder stages,
reusing existing MessageTemplate infrastructure.
"""

import logging
from typing import Dict, List, Optional
from uuid import UUID

from sqlalchemy.orm import Session

from app.models.messaging import MessageTemplate
from app.models.reminder_config import ReminderStage

logger = logging.getLogger(__name__)


class ReminderEmailTemplateService:
    """Service for managing payment reminder email templates
    
    Task 1D-1: Extends existing MessageTemplate functionality for reminders
    """

    def __init__(self, db: Session):
        self.db = db

    # ── Template Creation & Management ───────────────────────────────────

    def create_default_reminder_templates(self, organization_id: UUID) -> List[MessageTemplate]:
        """Create default email templates for all reminder stages"""
        templates = []
        
        template_definitions = self._get_default_template_definitions()
        
        for template_name, template_data in template_definitions.items():
            # Check if template already exists
            existing = (
                self.db.query(MessageTemplate)
                .filter(
                    MessageTemplate.organization_id == organization_id,
                    MessageTemplate.template_name == template_name,
                    MessageTemplate.channel == "email"
                )
                .first()
            )
            
            if existing:
                logger.info(f"Template {template_name} already exists for org {organization_id}")
                templates.append(existing)
                continue
            
            # Create new template
            template = MessageTemplate(
                organization_id=organization_id,
                template_name=template_name,
                channel="email",
                template_type="TR",  # Transactional
                message=template_data["subject"],
                template_text=template_data["content"],
                status="Approved",
                service_type="T",  # Transactional
                extra_data={
                    "category": "payment_reminder",
                    "stage": template_data["stage"],
                    "description": template_data["description"]
                }
            )
            
            self.db.add(template)
            templates.append(template)
            logger.info(f"Created reminder template: {template_name}")
        
        self.db.commit()
        return templates

    def _get_default_template_definitions(self) -> Dict[str, Dict]:
        """Get default email template definitions for all reminder stages"""
        return {
            "payment_reminder_first": {
                "stage": ReminderStage.FIRST_REMINDER.value,
                "subject": "Payment Reminder - Invoice {invoice_no}",
                "description": "First payment reminder for overdue invoices",
                "content": """Dear Valued Customer,

We hope this message finds you well. This is a friendly reminder regarding Invoice {invoice_no}, which is now {days_overdue} days past its due date of {due_date}.

Invoice Details:
• Invoice Number: {invoice_no}
• Outstanding Amount: ${outstanding_amount}
• Original Due Date: {due_date}
• Days Overdue: {days_overdue} days

To avoid any interruption to your service and maintain your account in good standing, please remit payment at your earliest convenience.

Payment Options:
• Online payment portal: [Your Payment Portal URL]
• Bank transfer: [Bank Details]
• Check payment: [Mailing Address]

If you have already sent payment, please disregard this notice. If you have any questions regarding this invoice or need to discuss payment arrangements, please contact our billing department.

We appreciate your prompt attention to this matter and thank you for your continued business.

Best regards,
Accounts Receivable Department
{organization_name}

---
This is an automated reminder. Please do not reply to this email."""
            },
            
            "payment_reminder_second": {
                "stage": ReminderStage.SECOND_REMINDER.value,
                "subject": "Second Payment Notice - Invoice {invoice_no} - Action Required",
                "description": "Second payment reminder with increased urgency",
                "content": """Dear Customer,

This is your SECOND NOTICE regarding the overdue payment for Invoice {invoice_no}.

URGENT: Your account is now {days_overdue} days past due. Immediate action is required to bring your account current and avoid service disruption.

Invoice Details:
• Invoice Number: {invoice_no}
• Outstanding Amount: ${outstanding_amount}
• Original Due Date: {due_date}
• Days Overdue: {days_overdue} days

IMMEDIATE ACTION REQUIRED:
Please remit payment within the next 7 days to avoid potential service suspension and additional late fees.

Payment Options:
• Online payment (fastest): [Your Payment Portal URL]
• Phone payment: [Phone Number]
• Bank transfer: [Bank Details]
• Overnight check: [Express Mailing Address]

Account Review:
If there are any disputes regarding this invoice or if you need to establish a payment plan, please contact our billing department immediately at [Phone] or [Email].

Late Fee Notice: Continued non-payment may result in additional late fees and collection activities as outlined in your service agreement.

We value your business and want to work with you to resolve this matter promptly.

Urgent regards,
Billing Department
{organization_name}

---
This is an automated notice. For immediate assistance, please contact our billing department."""
            },
            
            "payment_reminder_final": {
                "stage": ReminderStage.FINAL_NOTICE.value,
                "subject": "FINAL NOTICE - Invoice {invoice_no} - Immediate Payment Required",
                "description": "Final payment notice before collection or service suspension",
                "content": """FINAL NOTICE

Dear Customer,

This is your FINAL NOTICE regarding Invoice {invoice_no}. Your account is seriously past due and requires immediate attention.

CRITICAL ACCOUNT STATUS:
• Invoice Number: {invoice_no}
• Outstanding Amount: ${outstanding_amount}
• Original Due Date: {due_date}
• Days Overdue: {days_overdue} days

IMMEDIATE PAYMENT REQUIRED:
Payment must be received within 7 days of this notice to avoid:
• Service suspension or termination
• Account referral to collections
• Additional collection fees and legal costs
• Negative impact on credit rating

PAYMENT OPTIONS - ACT NOW:
• Online payment: [Your Payment Portal URL]
• Phone payment: [Phone Number] 
• Wire transfer: [Wire Instructions]
• Overnight payment: [Express Address]

LAST OPPORTUNITY:
If payment is not received or payment arrangements are not made within 7 days, your account will be:
1. Suspended from all services
2. Referred to our collections department
3. Subject to additional fees and legal action

Contact our billing department IMMEDIATELY at [Phone] or [Email] if:
• You need to dispute this invoice
• You require payment plan arrangements
• You need assistance with payment methods

This is your final opportunity to resolve this matter before further action is taken.

Final Notice,
Collections Department  
{organization_name}

---
AUTOMATED FINAL NOTICE - Immediate response required."""
            },
            
            "payment_reminder_deactivation": {
                "stage": ReminderStage.DEACTIVATION_NOTICE.value,
                "subject": "ACCOUNT DEACTIVATION NOTICE - Invoice {invoice_no} - Service Suspension Imminent",
                "description": "Final warning before automatic account deactivation",
                "content": """ACCOUNT DEACTIVATION NOTICE

Dear Customer,

Your account is scheduled for deactivation due to non-payment of Invoice {invoice_no}.

ACCOUNT DEACTIVATION IMMINENT:
• Invoice Number: {invoice_no}
• Outstanding Amount: ${outstanding_amount}
• Days Overdue: {days_overdue} days
• Service Suspension Date: [72 hours from this notice]

FINAL WARNING:
Your account will be automatically deactivated within 72 hours unless payment is received or acceptable payment arrangements are confirmed in writing.

Upon deactivation:
• All services will be immediately suspended
• Account will be transferred to collections
• Reconnection fees will apply for future service restoration
• Credit reporting may be affected

EMERGENCY PAYMENT OPTIONS:
• Immediate online payment: [Payment Portal]
• Emergency phone payment: [24/7 Phone Line]
• Wire transfer (same day): [Wire Instructions]

LAST CHANCE CONTACT:
If you need to make immediate payment arrangements, contact our emergency billing line at [Emergency Phone] or email [Emergency Email].

This is an automated system notice. Deactivation will proceed automatically unless payment or confirmed arrangements are received.

URGENT - DO NOT IGNORE THIS NOTICE

System Billing Department
{organization_name}

---
AUTOMATED DEACTIVATION NOTICE - System action will proceed automatically"""
            }
        }

    # ── Template Retrieval & Management ─────────────────────────────────

    def get_reminder_template(
        self, organization_id: UUID, stage: ReminderStage
    ) -> Optional[MessageTemplate]:
        """Get reminder template for specific stage"""
        stage_template_map = {
            ReminderStage.FIRST_REMINDER: "payment_reminder_first",
            ReminderStage.SECOND_REMINDER: "payment_reminder_second", 
            ReminderStage.FINAL_NOTICE: "payment_reminder_final",
            ReminderStage.DEACTIVATION_NOTICE: "payment_reminder_deactivation",
        }
        
        template_name = stage_template_map.get(stage)
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
        
        # If template doesn't exist, create defaults
        if not template:
            logger.info(f"Creating default templates for organization {organization_id}")
            templates = self.create_default_reminder_templates(organization_id)
            template = next(
                (t for t in templates if t.template_name == template_name), 
                None
            )
        
        return template

    def list_reminder_templates(self, organization_id: UUID) -> List[MessageTemplate]:
        """List all reminder templates for organization"""
        templates = (
            self.db.query(MessageTemplate)
            .filter(
                MessageTemplate.organization_id == organization_id,
                MessageTemplate.channel == "email",
                MessageTemplate.template_name.like("payment_reminder_%")
            )
            .order_by(MessageTemplate.template_name)
            .all()
        )
        
        return templates

    def update_reminder_template(
        self, organization_id: UUID, template_name: str, updates: Dict
    ) -> MessageTemplate:
        """Update existing reminder template"""
        template = (
            self.db.query(MessageTemplate)
            .filter(
                MessageTemplate.organization_id == organization_id,
                MessageTemplate.template_name == template_name,
                MessageTemplate.channel == "email"
            )
            .first()
        )
        
        if not template:
            raise ValueError(f"Template {template_name} not found for organization")
            
        # Update allowed fields
        updateable_fields = ["message", "template_text", "status", "extra_data"]
        for field, value in updates.items():
            if field in updateable_fields and hasattr(template, field):
                setattr(template, field, value)
        
        self.db.commit()
        self.db.refresh(template)
        
        logger.info(f"Updated reminder template: {template_name}")
        return template

    def delete_reminder_template(self, organization_id: UUID, template_name: str) -> bool:
        """Delete reminder template (soft delete)"""
        template = (
            self.db.query(MessageTemplate)
            .filter(
                MessageTemplate.organization_id == organization_id,
                MessageTemplate.template_name == template_name,
                MessageTemplate.channel == "email"
            )
            .first()
        )
        
        if not template:
            return False
            
        # Soft delete by setting deleted_at
        from datetime import UTC, datetime
        template.deleted_at = datetime.now(UTC)
        self.db.commit()
        
        logger.info(f"Deleted reminder template: {template_name}")
        return True

    # ── Template Validation ─────────────────────────────────────────────

    def validate_template_variables(self, template_text: str) -> Dict:
        """Validate that template contains required variables"""
        required_variables = [
            "invoice_no", "outstanding_amount", "days_overdue", "due_date"
        ]
        
        missing_variables = []
        for var in required_variables:
            if f"{{{var}}}" not in template_text:
                missing_variables.append(var)
        
        return {
            "valid": len(missing_variables) == 0,
            "missing_variables": missing_variables,
            "found_variables": [
                var for var in required_variables 
                if f"{{{var}}}" in template_text
            ]
        }

    def preview_template_content(
        self, template: MessageTemplate, sample_data: Dict
    ) -> Dict[str, str]:
        """Preview template with sample data"""
        try:
            subject = template.message.format(**sample_data)
            content = template.template_text.format(**sample_data)
            
            return {
                "subject": subject,
                "content": content,
                "success": True
            }
        except KeyError as e:
            return {
                "subject": "",
                "content": "",
                "success": False,
                "error": f"Missing template variable: {str(e)}"
            }

    # ── Integration Helpers ──────────────────────────────────────────────

    def ensure_organization_templates(self, organization_id: UUID) -> List[MessageTemplate]:
        """Ensure organization has all required reminder templates"""
        existing_templates = self.list_reminder_templates(organization_id)
        
        if len(existing_templates) < 4:  # Should have 4 reminder stages
            logger.info(f"Creating missing reminder templates for org {organization_id}")
            return self.create_default_reminder_templates(organization_id)
        
        return existing_templates

    def get_template_usage_stats(self, organization_id: UUID) -> Dict:
        """Get statistics on template usage"""
        from app.models.reminder_config import ReminderLog
        
        stats = {}
        templates = self.list_reminder_templates(organization_id)
        
        for template in templates:
            usage_count = (
                self.db.query(ReminderLog)
                .filter(
                    ReminderLog.organization_id == organization_id,
                    ReminderLog.template_used == template.template_name
                )
                .count()
            )
            
            stats[template.template_name] = {
                "template_id": str(template.id),
                "usage_count": usage_count,
                "last_updated": template.updated_at.isoformat() if template.updated_at else None,
                "status": template.status
            }
        
        return stats