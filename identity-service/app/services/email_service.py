"""Email service for sending notifications"""

import logging
from email.message import EmailMessage

import aiosmtplib

from app.config import settings

logger = logging.getLogger(__name__)


class EmailService:
    """Service for sending emails via SMTP"""

    async def send_email(self, subject: str, recipient: str, body: str):
        """
        Send an email notification.

        Args:
            subject: Email subject
            recipient: Recipient email address
            body: Email body (plain text)
        """
        if not settings.email_enabled:
            logger.info(f"Email disabled. Would have sent '{subject}' to {recipient}")
            # Log the body in development so the user can see the token
            if settings.environment == "development":
                logger.debug(f"Email body: {body}")
            return

        message = EmailMessage()
        message["From"] = f"{settings.smtp_from_name} <{settings.smtp_from_email}>"
        message["To"] = recipient
        message["Subject"] = subject
        message.set_content(body)

        try:
            kwargs = {
                "hostname": settings.smtp_host,
                "port": settings.smtp_port,
                "use_tls": settings.smtp_port == 465,
                "start_tls": settings.smtp_port == 587,
            }

            if settings.smtp_username and settings.smtp_password:
                kwargs["username"] = settings.smtp_username
                kwargs["password"] = settings.smtp_password

            await aiosmtplib.send(message, **kwargs)
            logger.info(f"Email '{subject}' sent successfully to {recipient}")

        except Exception as e:
            logger.error(f"Failed to send email to {recipient}: {str(e)}")
            # Don't raise the exception to avoid breaking the API flow,
            # as the token is already stored in the DB.

    async def send_password_reset_email(self, recipient: str, token: str):
        """
        Send a password reset email with the secure token.

        Args:
            recipient: User's email address
            token: Password reset token
        """
        subject = "Password Reset Request"
        # In a real app, you would use a proper URL from your frontend
        reset_link = f"https://yourapp.com/reset-password?token={token}"

        body = (
            f"Hello,\n\n"
            f"You requested to reset your password. Click the link below to reset it:\n\n"
            f"{reset_link}\n\n"
            f"This link will expire in {settings.password_reset_token_expire_hours} hour.\n\n"
            f"If you didn't request this, please ignore this email.\n"
        )

        await self.send_email(subject, recipient, body)
