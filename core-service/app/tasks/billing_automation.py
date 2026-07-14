"""Billing Automation Tasks for payment reminders and deactivation

Task 1D-2: Automated background tasks for payment reminder processing,
escalation sequences, and organization deactivation based on overdue invoices.
"""

import asyncio
import logging
from datetime import UTC, datetime, timedelta
from typing import List, Optional
from uuid import UUID

from sqlalchemy import create_engine, or_
from sqlalchemy.orm import sessionmaker

from app.config import settings
from app.models.base import OrganizationStatus
from app.models.reminder_config import ReminderConfig, ReminderStage
from app.services.admin_organization_service import AdminOrganizationService
from app.services.payment_reminder_service import PaymentReminderService

logger = logging.getLogger(__name__)

# Database session for background tasks
engine = create_engine(settings.database_url)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class BillingAutomationTask:
    """Background task processor for automated billing operations
    
    Task 1D-2: Handles scheduled reminder processing and organization management
    """
    
    def __init__(self):
        self.db_session = SessionLocal()
        self.reminder_service = PaymentReminderService(self.db_session)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.db_session.close()

    # ── Daily Reminder Processing ───────────────────────────────────────

    async def process_daily_reminders(self) -> dict:
        """Process daily reminder automation for all organizations
        
        This should be scheduled to run daily (e.g., via cron or task scheduler)
        """
        logger.info("Starting daily reminder processing")
        start_time = datetime.now(UTC)
        
        try:
            # Get active organizations using the AdminOrganizationService
            org_service = AdminOrganizationService(self.db_session)
            organizations_response = await org_service.list_organizations(
                status_filter="active",
                page_size=1000  # Get all active orgs
            )
            active_organizations = organizations_response.organizations
            
            # Get reminder configurations for active organizations
            organization_ids = [org.id for org in active_organizations]
            reminder_configs = (
                self.db_session.query(ReminderConfig)
                .filter(
                    ReminderConfig.organization_id.in_(organization_ids),
                    or_(
                        ReminderConfig.is_enabled == True,
                        ReminderConfig.id.is_(None)  # No config yet, will create default
                    )
                )
                .all()
            )
            
            # Create mapping of org_id to reminder config
            config_by_org = {config.organization_id: config for config in reminder_configs}
            
            # Include organizations without explicit configs (they'll get defaults)
            eligible_org_ids = []
            for org in active_organizations:
                config = config_by_org.get(org.id)
                if config is None or config.is_enabled:
                    eligible_org_ids.append(org.id)
            
            logger.info(f"Processing reminders for {len(eligible_org_ids)} organizations")
            
            # Process batch reminders for eligible organizations
            batch_result = await self.reminder_service.send_batch_reminders(
                organization_ids=eligible_org_ids
            )
            
            # Log results
            elapsed = datetime.now(UTC) - start_time
            logger.info(
                f"Daily reminder processing completed in {elapsed.total_seconds():.1f}s: "
                f"{batch_result['sent']} sent, {batch_result['failed']} failed, "
                f"{batch_result['skipped']} skipped"
            )
            
            return {
                "success": True,
                "started_at": start_time.isoformat(),
                "completed_at": datetime.now(UTC).isoformat(),
                "duration_seconds": elapsed.total_seconds(),
                "organizations_processed": len(eligible_org_ids),
                **batch_result
            }
            
        except Exception as e:
            logger.error(f"Daily reminder processing failed: {e}")
            return {
                "success": False,
                "started_at": start_time.isoformat(),
                "completed_at": datetime.now(UTC).isoformat(),
                "error": str(e)
            }

    # ── Organization Status Management ───────────────────────────────────

    async def check_organization_deactivation(self) -> dict:
        """Check organizations for deactivation based on overdue payments
        
        Task 1D-2: Automated organization deactivation for non-payment
        """
        logger.info("Starting organization deactivation check")
        results = {
            "checked": 0,
            "eligible_for_deactivation": 0,
            "deactivated": 0,
            "warnings_sent": 0,
            "errors": []
        }
        
        try:
            # Get active customer organizations using the AdminOrganizationService
            org_service = AdminOrganizationService(self.db_session)
            organizations_response = await org_service.list_organizations(
                status_filter="active",
                page_size=1000  # Get all active orgs
            )
            # Filter out master organizations (they should never be deactivated)
            active_orgs = [org for org in organizations_response.organizations 
                          if getattr(org, 'organization_type', None) != "master"]
            
            results["checked"] = len(active_orgs)
            
            for org in active_orgs:
                try:
                    await self._process_organization_deactivation_check(org, results)
                except Exception as e:
                    error_msg = f"Error checking org {org.id}: {str(e)}"
                    logger.error(error_msg)
                    results["errors"].append(error_msg)
            
            logger.info(
                f"Organization deactivation check completed: "
                f"{results['deactivated']} deactivated, {results['warnings_sent']} warnings"
            )
            
            return results
            
        except Exception as e:
            logger.error(f"Organization deactivation check failed: {e}")
            results["errors"].append(str(e))
            return results

    async def _process_organization_deactivation_check(self, org, results: dict):
        """Process deactivation check for a single organization"""
        config = self.reminder_service.get_reminder_config(org.id)
        
        if not config.auto_deactivate_enabled:
            return
        
        # Get overdue invoices for this organization
        overdue_invoices = self.reminder_service.get_overdue_invoices(organization_id=org.id)
        
        # Check if any invoices are overdue beyond deactivation threshold
        deactivation_candidates = [
            inv for inv in overdue_invoices 
            if inv["days_overdue"] >= config.auto_deactivate_days
        ]
        
        if not deactivation_candidates:
            return
        
        results["eligible_for_deactivation"] += 1
        
        # Send deactivation warning if not already sent
        await self._send_deactivation_warnings(org.id, deactivation_candidates, config)
        results["warnings_sent"] += 1
        
        # Check if enough time has passed since final warnings
        final_warnings_sent = any(
            self._has_recent_deactivation_warning(inv["id"], config)
            for inv in deactivation_candidates
        )
        
        if final_warnings_sent:
            # Grace period for final warnings (e.g., 7 days)
            grace_period_passed = self._deactivation_grace_period_passed(
                deactivation_candidates, config
            )
            
            if grace_period_passed:
                await self._deactivate_organization(org, deactivation_candidates)
                results["deactivated"] += 1

    async def _send_deactivation_warnings(
        self, org_id: UUID, overdue_invoices: List[dict], config
    ):
        """Send deactivation warning emails for overdue invoices"""
        for invoice_data in overdue_invoices:
            invoice_id = UUID(invoice_data["id"])
            
            # Check if deactivation notice already sent recently
            if self._has_recent_deactivation_warning(invoice_id, config):
                continue
            
            try:
                await self.reminder_service.send_automated_reminder(
                    invoice_id=invoice_id,
                    stage=ReminderStage.DEACTIVATION_NOTICE,
                    config=config,
                    batch_id=None,  # Single processing
                    user_id=None   # System generated
                )
                logger.info(f"Deactivation warning sent for invoice {invoice_id}")
                
            except Exception as e:
                logger.error(f"Failed to send deactivation warning for invoice {invoice_id}: {e}")

    def _has_recent_deactivation_warning(self, invoice_id: str, config) -> bool:
        """Check if deactivation warning was sent recently"""
        from app.models.reminder_config import ReminderLog, ReminderStatus
        
        recent_warning = (
            self.db_session.query(ReminderLog)
            .filter(
                ReminderLog.invoice_id == UUID(invoice_id),
                ReminderLog.reminder_stage == ReminderStage.DEACTIVATION_NOTICE,
                ReminderLog.status == ReminderStatus.SENT,
                ReminderLog.sent_at >= datetime.now(UTC) - timedelta(days=7)  # Within last 7 days
            )
            .first()
        )
        
        return recent_warning is not None

    def _deactivation_grace_period_passed(self, overdue_invoices: List[dict], config) -> bool:
        """Check if grace period has passed after deactivation warnings"""
        from app.models.reminder_config import ReminderLog, ReminderStatus
        
        # Check oldest deactivation warning
        oldest_warning = None
        
        for invoice_data in overdue_invoices:
            warning = (
                self.db_session.query(ReminderLog)
                .filter(
                    ReminderLog.invoice_id == UUID(invoice_data["id"]),
                    ReminderLog.reminder_stage == ReminderStage.DEACTIVATION_NOTICE,
                    ReminderLog.status == ReminderStatus.SENT
                )
                .order_by(ReminderLog.sent_at.asc())
                .first()
            )
            
            if warning and (not oldest_warning or warning.sent_at < oldest_warning.sent_at):
                oldest_warning = warning
        
        if not oldest_warning:
            return False
        
        # Grace period (e.g., 7 days) has passed since first warning
        grace_period_days = 7
        cutoff_date = datetime.now(UTC) - timedelta(days=grace_period_days)
        
        return oldest_warning.sent_at <= cutoff_date

    async def _deactivate_organization(self, org, overdue_invoices: List[dict]):
        """Deactivate organization due to non-payment"""
        logger.info(f"Deactivating organization {org.id} due to overdue payments")
        
        try:
            # Update organization status
            org.billing_status = OrganizationStatus.DEACTIVATED
            org.deactivated_at = datetime.now(UTC)
            org.deactivation_reason = f"Auto-deactivated due to {len(overdue_invoices)} overdue invoices"
            
            # Log deactivation
            from app.models.admin import AdminAuditLog
            audit_log = AdminAuditLog(
                organization_id=org.id,
                action="organization_deactivated",
                resource="organization",
                resource_id=str(org.id),
                details={
                    "reason": "automated_deactivation",
                    "overdue_invoice_count": len(overdue_invoices),
                    "total_overdue_amount": sum(
                        float(inv["outstanding_amount"]) for inv in overdue_invoices
                    ),
                    "days_overdue_range": [inv["days_overdue"] for inv in overdue_invoices]
                },
                performed_by_system=True
            )
            
            self.db_session.add(audit_log)
            self.db_session.commit()
            
            logger.info(f"Organization {org.id} deactivated successfully")
            
        except Exception as e:
            self.db_session.rollback()
            logger.error(f"Failed to deactivate organization {org.id}: {e}")
            raise

    # ── Reminder Statistics & Cleanup ───────────────────────────────────

    async def cleanup_old_reminder_logs(self, days_to_keep: int = 365) -> dict:
        """Clean up old reminder logs to manage database size"""
        cutoff_date = datetime.now(UTC) - timedelta(days=days_to_keep)
        
        from app.models.reminder_config import ReminderLog
        
        old_logs = (
            self.db_session.query(ReminderLog)
            .filter(ReminderLog.created_at < cutoff_date)
            .all()
        )
        
        count = len(old_logs)
        
        if count > 0:
            for log in old_logs:
                self.db_session.delete(log)
            
            self.db_session.commit()
            logger.info(f"Cleaned up {count} old reminder log records")
        
        return {
            "cleaned_up": count,
            "cutoff_date": cutoff_date.isoformat()
        }

    async def generate_reminder_report(self) -> dict:
        """Generate daily reminder processing report"""
        from app.models.reminder_config import ReminderLog, ReminderStatus, ReminderStage
        
        # Get today's reminder activity
        today = datetime.now(UTC).date()
        today_start = datetime.combine(today, datetime.min.time()).replace(tzinfo=UTC)
        today_end = datetime.combine(today, datetime.max.time()).replace(tzinfo=UTC)
        
        logs = (
            self.db_session.query(ReminderLog)
            .filter(ReminderLog.created_at.between(today_start, today_end))
            .all()
        )
        
        # Aggregate statistics
        stats = {
            "date": today.isoformat(),
            "total_reminders": len(logs),
            "by_status": {},
            "by_stage": {},
            "by_organization": {},
            "success_rate": 0.0
        }
        
        # Count by status
        for status in ReminderStatus:
            count = len([log for log in logs if log.status == status])
            stats["by_status"][status.value] = count
        
        # Count by stage
        for stage in ReminderStage:
            count = len([log for log in logs if log.reminder_stage == stage])
            stats["by_stage"][stage.value] = count
        
        # Count by organization
        org_counts = {}
        for log in logs:
            org_id = str(log.organization_id)
            org_counts[org_id] = org_counts.get(org_id, 0) + 1
        stats["by_organization"] = org_counts
        
        # Calculate success rate
        sent_count = stats["by_status"].get("sent", 0)
        if len(logs) > 0:
            stats["success_rate"] = (sent_count / len(logs)) * 100
        
        return stats


# ── Standalone Task Functions ──────────────────────────────────────────

async def run_daily_reminders():
    """Standalone function for daily reminder processing (cron/scheduler entry point)"""
    async with BillingAutomationTask() as task:
        return await task.process_daily_reminders()

async def run_deactivation_check():
    """Standalone function for organization deactivation check"""
    async with BillingAutomationTask() as task:
        return await task.check_organization_deactivation()

async def run_log_cleanup(days_to_keep: int = 365):
    """Standalone function for reminder log cleanup"""
    async with BillingAutomationTask() as task:
        return await task.cleanup_old_reminder_logs(days_to_keep)

async def run_reminder_report():
    """Standalone function for generating daily report"""
    async with BillingAutomationTask() as task:
        return await task.generate_reminder_report()


# ── Task Scheduler Integration ─────────────────────────────────────────

def schedule_billing_automation_tasks():
    """Configure scheduled tasks for billing automation
    
    This function can be called at application startup to configure
    recurring background tasks using whatever task scheduler is preferred
    (Celery, APScheduler, etc.)
    """
    logger.info("Billing automation tasks initialized")
    
    # Example task schedule configuration (adjust based on scheduler used):
    # - Daily reminders: Every day at 9:00 AM
    # - Deactivation check: Every day at 6:00 AM  
    # - Log cleanup: Every Sunday at 2:00 AM
    # - Report generation: Every day at 11:59 PM
    
    tasks = [
        {
            "name": "daily_reminders",
            "function": run_daily_reminders,
            "schedule": "0 9 * * *",  # Daily at 9 AM
            "description": "Process daily payment reminders"
        },
        {
            "name": "deactivation_check", 
            "function": run_deactivation_check,
            "schedule": "0 6 * * *",  # Daily at 6 AM
            "description": "Check organizations for deactivation"
        },
        {
            "name": "log_cleanup",
            "function": lambda: run_log_cleanup(365),
            "schedule": "0 2 * * 0",  # Weekly on Sunday at 2 AM
            "description": "Clean up old reminder logs"
        },
        {
            "name": "reminder_report",
            "function": run_reminder_report,
            "schedule": "59 23 * * *",  # Daily at 11:59 PM
            "description": "Generate daily reminder report"
        }
    ]
    
    return tasks


if __name__ == "__main__":
    # For testing purposes - run daily reminders
    import asyncio
    asyncio.run(run_daily_reminders())