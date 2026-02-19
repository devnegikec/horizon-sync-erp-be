"""Email service for sending notifications and documents"""

import logging
import mimetypes
import ssl
from email.message import EmailMessage
from pathlib import Path

import aiosmtplib

from app.config import settings

logger = logging.getLogger(__name__)


class EmailService:
    """Service for sending emails via SMTP with attachment support"""

    async def send_email(
        self,
        subject: str,
        recipient: str,
        body: str,
        cc: list[str] | None = None,
        attachments: list[dict] | None = None,
        html_body: str | None = None,
    ) -> dict:
        """
        Send an email with optional CC and attachments.

        Args:
            subject: Email subject
            recipient: Primary recipient email address
            body: Email body (plain text)
            cc: List of CC email addresses
            attachments: List of attachment dicts with 'filename', 'content', 'content_type'
            html_body: Optional HTML version of the email body

        Returns:
            dict with status and message

        Raises:
            Exception: If email sending fails
        """
        logger.info("=" * 60)
        logger.info("Email Service - send_email() called")
        logger.info("=" * 60)
        logger.info(f"Subject: {subject}")
        logger.info(f"Recipient: {recipient}")
        logger.info(f"CC: {cc}")
        logger.info(f"Body length: {len(body)} characters")
        logger.info(f"Attachments: {len(attachments) if attachments else 0}")
        logger.info(f"Email enabled setting: {settings.email_enabled}")

        if not settings.email_enabled:
            logger.warning(
                f"Email disabled. Would have sent '{subject}' to {recipient}"
            )
            if settings.environment == "development":
                logger.debug(f"Email body: {body}")
            logger.info("=" * 60)
            return {
                "status": "disabled",
                "message": "Email sending is disabled in configuration",
            }

        logger.info("Email is enabled. Preparing to send...")
        logger.info("SMTP Configuration:")
        logger.info(f"  Host: {settings.smtp_host}")
        logger.info(f"  Port: {settings.smtp_port}")
        logger.info(f"  Username: {settings.smtp_username}")
        logger.info(
            f"  Password: {'SET' if settings.smtp_password else 'NOT SET'}"
        )
        logger.info(f"  From Email: {settings.smtp_from_email}")
        logger.info(f"  From Name: {settings.smtp_from_name}")

        # Create message
        message = EmailMessage()
        message["From"] = f"{settings.smtp_from_name} <{settings.smtp_from_email}>"
        message["To"] = recipient
        message["Subject"] = subject

        # Add CC if provided
        if cc:
            message["Cc"] = ", ".join(cc)

        # Set content
        message.set_content(body)

        # Add HTML alternative if provided
        if html_body:
            message.add_alternative(html_body, subtype="html")

        # Add attachments if provided
        if attachments:
            for attachment in attachments:
                filename = attachment.get("filename", "attachment")
                content = attachment.get("content")
                content_type = attachment.get("content_type")

                if not content:
                    logger.warning(f"Skipping attachment {filename} - no content")
                    continue

                # Auto-detect content type if not provided
                if not content_type:
                    content_type, _ = mimetypes.guess_type(filename)
                    if not content_type:
                        content_type = "application/octet-stream"

                # Parse maintype and subtype
                maintype, subtype = content_type.split("/", 1)

                logger.info(
                    f"Adding attachment: {filename} ({content_type}, {len(content)} bytes)"
                )

                message.add_attachment(
                    content,
                    maintype=maintype,
                    subtype=subtype,
                    filename=filename,
                )

        try:
            logger.info("Connecting to SMTP server...")

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
                f"Connection parameters: use_tls={kwargs['use_tls']}, start_tls={kwargs['start_tls']}"
            )

            if settings.smtp_username and settings.smtp_password:
                kwargs["username"] = settings.smtp_username
                kwargs["password"] = settings.smtp_password
                logger.info("Using authentication")
            else:
                logger.warning("No authentication credentials provided!")

            logger.info("Attempting to send email...")
            await aiosmtplib.send(message, **kwargs)

            logger.info(f"✅ Email '{subject}' sent successfully to {recipient}")
            logger.info("=" * 60)

            return {
                "status": "sent",
                "message": f"Email sent successfully to {recipient}",
            }

        except Exception as e:
            logger.error("=" * 60)
            logger.error(f"❌ Failed to send email to {recipient}")
            logger.error(f"Error type: {type(e).__name__}")
            logger.error(f"Error message: {str(e)}")
            logger.error("=" * 60)
            import traceback

            logger.error(f"Full traceback:\n{traceback.format_exc()}")
            raise Exception(f"Failed to send email: {str(e)}")
