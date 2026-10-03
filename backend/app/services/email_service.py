"""Google SMTP delivery service."""

from __future__ import annotations

import logging
import os
import smtplib
from email.message import EmailMessage
from email.utils import formataddr

from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)


class EmailDeliveryError(RuntimeError):
    """Raised when an email cannot be submitted to the configured SMTP server."""


def send_email(
    recipient: str,
    subject: str,
    html_content: str,
    text_content: str | None = None,
) -> None:
    """Send one message using authenticated Google SMTP with STARTTLS."""
    host = os.getenv("SMTP_HOST", "smtp.gmail.com")
    port_value = os.getenv("SMTP_PORT", "587")
    username = os.getenv("SMTP_USERNAME")
    password = os.getenv("SMTP_PASSWORD")
    from_address = os.getenv("SMTP_FROM")
    from_name = os.getenv("SMTP_FROM_NAME", "VendorIQ")

    if not username or not password or not from_address:
        raise EmailDeliveryError(
            "SMTP_USERNAME, SMTP_PASSWORD, and SMTP_FROM must be configured."
        )
    try:
        port = int(port_value)
    except ValueError as exc:
        raise EmailDeliveryError("SMTP_PORT must be a valid integer.") from exc

    message = EmailMessage()
    message["Subject"] = subject
    message["From"] = formataddr((from_name, from_address))
    message["To"] = recipient
    message.set_content(text_content or "This message contains an HTML assessment.")
    message.add_alternative(html_content, subtype="html")

    try:
        with smtplib.SMTP(host, port, timeout=30) as smtp:
            smtp.ehlo()
            smtp.starttls()
            smtp.ehlo()
            smtp.login(username, password)
            smtp.send_message(message)
    except (smtplib.SMTPException, OSError) as exc:
        logger.exception("Google SMTP delivery failed for recipient %s", recipient)
        raise EmailDeliveryError("Google SMTP delivery failed.") from exc

    logger.info("Email submitted via Google SMTP to %s", recipient)
