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


def _clean_header(val: str | None) -> str:
    """Sanitize header string by removing linefeed and carriage return characters."""
    if not val:
        return ""
    # Strip any \r or \n to comply with RFC 5322 & Python EmailMessage policy
    return "".join(c for c in str(val) if c not in "\r\n").strip()


def send_email(
    recipient: str,
    subject: str,
    html_content: str,
    text_content: str | None = None,
) -> None:
    """Send one message using authenticated Google SMTP with STARTTLS."""
    host = _clean_header(os.getenv("SMTP_HOST", "smtp.gmail.com"))
    port_value = _clean_header(os.getenv("SMTP_PORT", "587"))
    username = _clean_header(os.getenv("SMTP_USERNAME"))
    password = (os.getenv("SMTP_PASSWORD") or "").strip()
    from_address = _clean_header(os.getenv("SMTP_FROM"))
    from_name = _clean_header(os.getenv("SMTP_FROM_NAME", "VendorIQ"))

    clean_recipient = _clean_header(recipient)
    clean_subject = _clean_header(subject)

    if not username or not password or not from_address:
        raise EmailDeliveryError(
            "SMTP_USERNAME, SMTP_PASSWORD, and SMTP_FROM must be configured."
        )
    if not clean_recipient:
        raise EmailDeliveryError("Recipient email address must not be empty.")

    try:
        port = int(port_value)
    except ValueError as exc:
        raise EmailDeliveryError("SMTP_PORT must be a valid integer.") from exc

    message = EmailMessage()
    message["Subject"] = clean_subject
    message["From"] = formataddr((from_name, from_address))
    message["To"] = clean_recipient
    message.set_content(text_content or "This message contains an HTML assessment.")
    message.add_alternative(html_content, subtype="html")

    try:
        if port == 465:
            with smtplib.SMTP_SSL(host, port, timeout=12) as smtp:
                smtp.ehlo()
                smtp.login(username, password)
                smtp.send_message(message)
        else:
            with smtplib.SMTP(host, port, timeout=12) as smtp:
                smtp.ehlo()
                smtp.starttls()
                smtp.ehlo()
                smtp.login(username, password)
                smtp.send_message(message)
    except (smtplib.SMTPException, OSError) as exc:
        # Fallback to Gmail SSL port 465 if port 587 timed out or is blocked on cloud host
        if port != 465 and "smtp.gmail.com" in host:
            logger.info("Port 587 failed (%s), attempting Gmail SMTP_SSL on port 465...", exc)
            try:
                with smtplib.SMTP_SSL(host, 465, timeout=12) as ssl_smtp:
                    ssl_smtp.ehlo()
                    ssl_smtp.login(username, password)
                    ssl_smtp.send_message(message)
                logger.info("Email successfully submitted via Google SMTP_SSL (port 465) to %s", clean_recipient)
                return
            except Exception as ssl_exc:
                logger.warning("SMTP_SSL fallback on port 465 also failed: %s", ssl_exc)

        logger.exception("Google SMTP delivery failed for recipient %s", clean_recipient)
        raise EmailDeliveryError(f"Google SMTP delivery failed: {exc}") from exc

    logger.info("Email submitted via Google SMTP to %s", clean_recipient)
