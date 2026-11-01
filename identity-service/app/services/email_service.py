"""Email service for sending notifications.

Transactional emails are sent as ``multipart/alternative``: a plain-text part
for accessibility and old clients, plus a branded HTML part that renders the
organization logo, accent colour and a single clear call-to-action.
"""

import html
import logging
import ssl
from email.message import EmailMessage
from urllib.parse import urlparse

import aiosmtplib

from app.config import settings
from app.services.invitation_service import INVITATION_EXPIRY_DAYS

logger = logging.getLogger(__name__)

# Single brand accent for every transactional email: buttons, links and the
# wordmark. Deliberately fixed (not tenant-configurable) so mail cannot be made
# to imitate another brand's colour scheme.
ACCENT_COLOR = "#2563eb"
DEFAULT_BRAND_NAME = "Ciphercode ERP"

# System font stack — no webfonts, since most mail clients block external CSS.
_FONT_STACK = (
    "-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,Helvetica,Arial,sans-serif"
)


def _brand_name() -> str:
    return settings.email_brand_name or DEFAULT_BRAND_NAME


def _absolute_url(url: str | None) -> str | None:
    """Return a URL that mail clients can actually load, or ``None``.

    Mail clients cannot resolve relative paths, so a stored ``/uploads/x.png``
    logo is prefixed with the public origin of the invitation link.
    """
    if not url:
        return None
    url = url.strip()
    if url.startswith(("http://", "https://")):
        return url
    if url.startswith("/"):
        base = urlparse(settings.invitation_url)
        if base.scheme and base.netloc:
            return f"{base.scheme}://{base.netloc}{url}"
    logger.debug("Ignoring unusable logo URL %r", url)
    return None


def _logo_block(logo_url: str | None) -> str:
    """Render the logo at the top of the email, or a typographic wordmark."""
    resolved = _absolute_url(logo_url)
    if resolved:
        return (
            f'<img src="{html.escape(resolved, quote=True)}" '
            f'alt="{html.escape(_brand_name())}" width="160" '
            'style="display:block;height:auto;max-height:48px;max-width:220px;'
            'border:0;outline:none;text-decoration:none;" />'
        )
    return (
        f'<span style="font-family:{_FONT_STACK};font-size:20px;font-weight:700;'
        f'letter-spacing:-0.3px;color:{ACCENT_COLOR};">'
        f"{html.escape(_brand_name())}</span>"
    )


def _paragraph(content: str) -> str:
    """One body paragraph. ``content`` may contain pre-escaped inline markup."""
    return (
        f'<p style="margin:0 0 14px 0;font-family:{_FONT_STACK};font-size:15px;'
        f'line-height:24px;color:#344054;">{content}</p>'
    )


def _button(label: str, url: str, accent: str) -> str:
    return (
        '<table role="presentation" cellpadding="0" cellspacing="0" border="0" '
        'style="margin:24px 0 16px 0;"><tr>'
        f'<td style="background-color:{accent};border-radius:8px;">'
        f'<a href="{html.escape(url, quote=True)}" target="_blank" '
        'style="display:inline-block;padding:12px 28px;font-family:'
        f"{_FONT_STACK};font-size:15px;font-weight:600;color:#ffffff;"
        'text-decoration:none;border-radius:8px;">'
        f"{html.escape(label)}</a></td></tr></table>"
    )


def _fallback_link(url: str, accent: str) -> str:
    safe = html.escape(url, quote=True)
    return (
        f'<p style="margin:0 0 6px 0;font-family:{_FONT_STACK};font-size:13px;'
        'line-height:20px;color:#667085;">'
        "If the button above does not work, copy this link into your browser:"
        "</p>"
        f'<p style="margin:0 0 20px 0;font-family:{_FONT_STACK};font-size:13px;'
        f'line-height:20px;word-break:break-all;"><a href="{safe}" '
        f'style="color:{accent};text-decoration:underline;">{safe}</a></p>'
    )


def _details_table(rows: list[tuple[str, str]], accent: str) -> str:
    """Small summary card (organization, role, inviter)."""
    pairs = [(key, value) for key, value in rows if value]
    if not pairs:
        return ""
    cells = "".join(
        f'<tr><td style="padding:5px 16px 5px 0;font-family:{_FONT_STACK};'
        f'font-size:13px;line-height:20px;color:#667085;white-space:nowrap;">'
        f"{html.escape(key)}</td>"
        f'<td style="padding:5px 0;font-family:{_FONT_STACK};font-size:13px;'
        f'line-height:20px;color:#101828;">{html.escape(value)}</td></tr>'
        for key, value in pairs
    )
    return (
        '<table role="presentation" width="100%" cellpadding="0" cellspacing="0" '
        'border="0" style="margin:20px 0 4px 0;background-color:#f9fafb;'
        f'border-left:3px solid {accent};border-radius:6px;"><tr>'
        f'<td style="padding:12px 16px;"><table role="presentation" '
        f'cellpadding="0" cellspacing="0" border="0">{cells}</table>'
        "</td></tr></table>"
    )


def _layout(
    *,
    accent: str,
    logo_url: str | None,
    heading: str,
    preheader: str,
    content_html: str,
    footer_html: str,
) -> str:
    """Wrap content in a table-based, mail-client-safe HTML shell."""
    return f"""<!DOCTYPE html>
<html lang="en" xmlns="http://www.w3.org/1999/xhtml">
<head>
<meta charset="utf-8" />
<meta name="viewport" content="width=device-width, initial-scale=1" />
<meta name="x-apple-disable-message-reformatting" />
<title>{html.escape(heading)}</title>
</head>
<body style="margin:0;padding:0;background-color:#f4f5f7;">
<div style="display:none;max-height:0;overflow:hidden;opacity:0;color:#f4f5f7;
font-size:1px;line-height:1px;">{html.escape(preheader)}</div>
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0"
style="background-color:#f4f5f7;">
<tr><td align="center" style="padding:32px 12px;">
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0"
style="max-width:600px;background-color:#ffffff;border:1px solid #eaecf0;
border-radius:12px;font-family:{_FONT_STACK};">
<tr><td style="height:4px;line-height:4px;font-size:0;background-color:{accent};
border-radius:12px 12px 0 0;">&nbsp;</td></tr>
<tr><td style="padding:28px 32px 0 32px;">{_logo_block(logo_url)}</td></tr>
<tr><td style="padding:20px 32px 0 32px;">
<h1 style="margin:0 0 16px 0;font-family:{_FONT_STACK};font-size:22px;
line-height:30px;font-weight:600;color:#101828;">{html.escape(heading)}</h1>
{content_html}
</td></tr>
<tr><td style="padding:24px 32px 28px 32px;">
<div style="border-top:1px solid #eaecf0;padding-top:16px;font-family:{_FONT_STACK};
font-size:12px;line-height:18px;color:#98a2b3;">{footer_html}</div>
</td></tr>
</table>
</td></tr>
</table>
</body>
</html>"""


def _support_line() -> str:
    if not settings.email_support_email:
        return ""
    address = html.escape(settings.email_support_email)
    return (
        f' &middot; <a href="mailto:{html.escape(settings.email_support_email, quote=True)}" '
        f'style="color:#98a2b3;text-decoration:underline;">{address}</a>'
    )


class EmailService:
    """Service for sending emails via SMTP"""

    async def send_email(
        self,
        subject: str,
        recipient: str,
        body: str,
        html_body: str | None = None,
    ):
        """
        Send an email notification.

        Args:
            subject: Email subject
            recipient: Recipient email address
            body: Email body (plain text)
            html_body: Optional HTML body. When provided the message is sent as
                multipart/alternative and the HTML part is preferred by clients
                that render it, while ``body`` stays as the fallback.
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
        if html_body:
            message.add_alternative(html_body, subtype="html")

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
        accent = ACCENT_COLOR
        brand_name = _brand_name()
        subject = f"Reset your {brand_name} password"
        reset_link = f"{settings.password_reset_url}?token={token}"
        expiry_hours = settings.password_reset_token_expire_hours
        expiry_text = f"{expiry_hours} hour{'s' if expiry_hours != 1 else ''}"

        body = (
            "Hello,\n\n"
            "We received a request to reset the password for your account.\n\n"
            "Reset your password:\n"
            f"{reset_link}\n\n"
            f"This link expires in {expiry_text}.\n\n"
            "If you did not request a password reset, you can safely ignore this "
            "email - your password will remain unchanged.\n"
        )

        content_html = (
            _paragraph("Hello,")
            + _paragraph(
                "We received a request to reset the password for your account."
            )
            + _button("Reset password", reset_link, accent)
            + _fallback_link(reset_link, accent)
            + _paragraph(
                f"This link expires in <strong>{html.escape(expiry_text)}</strong>. "
                "If you did not request a password reset, you can safely ignore "
                "this email &mdash; your password will remain unchanged."
            )
        )
        html_body = _layout(
            accent=accent,
            logo_url=settings.email_brand_logo_url or None,
            heading="Reset your password",
            preheader=f"Use this link within {expiry_text} to reset your password.",
            content_html=content_html,
            footer_html=(
                "This is an automated security message; please do not reply to it."
                f"<br />{html.escape(brand_name)}{_support_line()}"
            ),
        )

        await self.send_email(subject, recipient, body, html_body=html_body)

    async def send_invitation_email(
        self,
        recipient: str,
        token: str,
        org_name: str,
        inviter_name: str,
        message: str | None = None,
        role_name: str | None = None,
        recipient_name: str | None = None,
        org_logo_url: str | None = None,
    ):
        """
        Send an organization invitation email.

        Args:
            recipient: Invitee's email address
            token: Invitation token
            org_name: Name of the organization
            inviter_name: Name of the person inviting
            message: Optional personal message
            role_name: Optional role name assigned to the invitee
            recipient_name: Optional invitee name used in the greeting
            org_logo_url: Optional logo URL shown at the top of the email
        """
        brand_name = _brand_name()
        accent = ACCENT_COLOR
        logo_url = _absolute_url(org_logo_url) or _absolute_url(
            settings.email_brand_logo_url
        )
        invitation_link = f"{settings.invitation_url}?token={token}"

        greeting_name = (recipient_name or "").strip() or recipient.split("@")[0]
        role_part = f" as {role_name}" if role_name else ""
        subject = f"You've been invited to join {org_name}"

        # ── Plain-text part ─────────────────────────────────────────────────
        message_block = (
            f'\nMessage from {inviter_name}:\n"{message}"\n' if message else ""
        )
        role_line = f"Your role: {role_name}\n" if role_name else ""
        support_line = (
            f"\nNeed help? Contact {settings.email_support_email}.\n"
            if settings.email_support_email
            else ""
        )
        body = (
            f"Hi {greeting_name},\n\n"
            f"{inviter_name} has invited you to join {org_name}{role_part} "
            f"on {brand_name}.\n"
            f"{message_block}"
            "\nAccept the invitation and set up your account:\n"
            f"{invitation_link}\n\n"
            f"{role_line}"
            f"This invitation expires in {INVITATION_EXPIRY_DAYS} days.\n\n"
            "If you weren't expecting this invitation, you can safely ignore this "
            "email - no account is created until you accept it.\n"
            f"{support_line}"
        )

        # ── HTML part ──────────────────────────────────────────────────────
        message_html = (
            '<table role="presentation" width="100%" cellpadding="0" '
            'cellspacing="0" border="0" style="margin:0 0 16px 0;"><tr>'
            '<td style="border-left:3px solid #e4e7ec;padding:2px 0 2px 14px;">'
            f'<p style="margin:0;font-family:{_FONT_STACK};font-size:14px;'
            'line-height:22px;font-style:italic;color:#475467;">'
            f"&ldquo;{html.escape(message)}&rdquo;</p></td></tr></table>"
            if message
            else ""
        )
        content_html = (
            _paragraph(f"Hi {html.escape(greeting_name)},")
            + _paragraph(
                f"<strong>{html.escape(inviter_name)}</strong> has invited you to "
                f"join <strong>{html.escape(org_name)}</strong>"
                f"{html.escape(role_part)} on {html.escape(brand_name)}."
            )
            + message_html
            + _details_table(
                [
                    ("Organization", org_name),
                    ("Role", role_name or "Team member"),
                    ("Invited by", inviter_name),
                ],
                accent,
            )
            + _button("Accept invitation", invitation_link, accent)
            + _fallback_link(invitation_link, accent)
            + _paragraph(
                f"This invitation expires in <strong>{INVITATION_EXPIRY_DAYS} "
                "days</strong>. If you weren't expecting it, you can safely "
                "ignore this email &mdash; no account is created until you accept."
            )
        )
        html_body = _layout(
            accent=accent,
            logo_url=logo_url,
            heading=f"You're invited to join {org_name}",
            preheader=(
                f"{inviter_name} invited you to join {org_name} on {brand_name}. "
                f"This invitation expires in {INVITATION_EXPIRY_DAYS} days."
            ),
            content_html=content_html,
            footer_html=(
                f"You received this email because {html.escape(inviter_name)} "
                f"invited {html.escape(recipient)} to {html.escape(org_name)}."
                f"<br />{html.escape(brand_name)}{_support_line()}"
            ),
        )

        await self.send_email(subject, recipient, body, html_body=html_body)
