"""Email service for sending notifications"""

import logging
from email.message import EmailMessage

import aiosmtplib

from app.config import settings
from app.services.invitation_service import INVITATION_EXPIRY_DAYS

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
        logger.info("=" * 60)
        logger.info("Email Service - send_email() called")
        logger.info("=" * 60)
        logger.info(f"Subject: {subject}")
        logger.info(f"Recipient: {recipient}")
        logger.info(f"Body length: {len(body)} characters")
        logger.info(f"Email enabled setting: {settings.email_enabled}")

        if not settings.email_enabled:
            logger.warning(
                f"Email disabled. Would have sent '{subject}' to {recipient}"
            )
            # Log the body in development so the user can see the token
            if settings.environment == "development":
                logger.debug(f"Email body: {body}")
            logger.info("=" * 60)
            return

        logger.info("Email is enabled. Preparing to send...")
        logger.info("SMTP Configuration:")
        logger.info(f"  Host: {settings.smtp_host}")
        logger.info(f"  Port: {settings.smtp_port}")
        logger.info(f"  Username: {settings.smtp_username}")
        logger.info(
            f"  Password: {'SET (length: ' + str(len(settings.smtp_password)) + ')' if settings.smtp_password else 'NOT SET'}"
        )
        logger.info(f"  From Email: {settings.smtp_from_email}")
        logger.info(f"  From Name: {settings.smtp_from_name}")

        message = EmailMessage()
        message["From"] = f"{settings.smtp_from_name} <{settings.smtp_from_email}>"
        message["To"] = recipient
        message["Subject"] = subject
        message.set_content(body)

        try:
            logger.info("Connecting to SMTP server...")

            import ssl

            ssl_context = ssl.create_default_context()
            if not settings.smtp_validate_certs:
                logger.warning("SSL certificate validation is DISABLED for SMTP!")
                ssl_context.check_hostname = False
                ssl_context.verify_mode = ssl.CERT_NONE

            kwargs = {
                "hostname": settings.smtp_host,
                "port": settings.smtp_port,
                "use_tls": settings.smtp_port == 465,
                "start_tls": settings.smtp_port == 587,
                "tls_context": ssl_context,
            }

            logger.info(
                f"Connection parameters: use_tls={kwargs['use_tls']}, start_tls={kwargs['start_tls']}, validate_certs={settings.smtp_validate_certs}"
            )

            if settings.smtp_username and settings.smtp_password:
                kwargs["username"] = settings.smtp_username
                kwargs["password"] = settings.smtp_password
                logger.info("Using authentication (username and password provided)")
            else:
                logger.warning("No authentication credentials provided!")

            logger.info("Attempting to send email...")
            await aiosmtplib.send(message, **kwargs)

            logger.info(f"✅ Email '{subject}' sent successfully to {recipient}")
            logger.info("=" * 60)

        except Exception as e:
            logger.error("=" * 60)
            logger.error(f"❌ Failed to send email to {recipient}")
            logger.error(f"Error type: {type(e).__name__}")
            logger.error(f"Error message: {str(e)}")
            logger.error("=" * 60)
            import traceback

            logger.error(f"Full traceback:\n{traceback.format_exc()}")
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
        # Use URL from settings
        reset_link = f"{settings.password_reset_url}?token={token}"

        body = (
            f"Hello,\n\n"
            f"You requested to reset your password. Click the link below to reset it:\n\n"
            f"{reset_link}\n\n"
            f"This link will expire in {settings.password_reset_token_expire_hours} hour.\n\n"
            f"If you didn't request this, please ignore this email.\n"
        )

        await self.send_email(subject, recipient, body)

    async def send_invitation_email(
        self,
        recipient: str,
        token: str,
        org_name: str,
        inviter_name: str,
        message: str | None = None,
    ):
        """
        Send an organization invitation email.

        Args:
            recipient: Invitee's email address
            token: Invitation token
            org_name: Name of the organization
            inviter_name: Name of the person inviting
            message: Optional personal message
        """
        subject = f"Invitation to join {org_name}"
        # Use URL from settings
        invitation_link = f"{settings.invitation_url}?token={token}"

        body = (
            f"Hello,\n\n"
            f"{inviter_name} has invited you to join {org_name} on Horizon Sync ERP.\n\n"
        )

        if message:
            body += f"Message from {inviter_name}:\n\"{message}\"\n\n"

        body += (
            f"Click the link below to accept the invitation and set up your account:\n\n"
            f"{invitation_link}\n\n"
            f"This invitation will expire in {INVITATION_EXPIRY_DAYS} days.\n\n"
            f"If you weren't expecting this invitation, you can safely ignore this email.\n"
        )

        await self.send_email(subject, recipient, body)
