"""Task automation package for background jobs and scheduled tasks"""

from app.tasks.billing_automation import (
    BillingAutomationTask,
    generate_qr_block_task,
    run_daily_reminders,
    run_deactivation_check,
    run_log_cleanup,
    run_reminder_report,
    schedule_billing_automation_tasks,
)

__all__ = [
    "BillingAutomationTask",
    "generate_qr_block_task",
    "run_daily_reminders",
    "run_deactivation_check", 
    "run_log_cleanup",
    "run_reminder_report",
    "schedule_billing_automation_tasks",
]
