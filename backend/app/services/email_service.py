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


import json
import urllib.request
import urllib.error


def _send_via_resend(
    api_key: str,
    from_name: str,
    from_address: str,
    recipient: str,
    subject: str,
    html_content: str,
    text_content: str | None,
) -> None:
    """Send email via Resend HTTP REST API over standard HTTPS (port 443)."""
    # Resend free domain onboarding@resend.dev works out-of-the-box without domain DNS verification
    sender = (
        f"{from_name} <onboarding@resend.dev>"
        if "resend.dev" in from_address or "gmail" in from_address
        else f"{from_name} <{from_address}>"
    )
    payload = {
        "from": sender,
        "to": [recipient],
        "subject": subject,
        "html": html_content,
        "text": text_content or "VendorIQ compliance notification",
    }
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        "https://api.resend.com/emails",
        data=data,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "User-Agent": "VendorIQ/1.0",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            logger.info("Email submitted via Resend HTTPS API to %s (status %s)", recipient, resp.status)
    except urllib.error.HTTPError as exc:
        err_body = exc.read().decode("utf-8", errors="replace")
        logger.error("Resend API delivery error: %s - %s", exc, err_body)
        raise EmailDeliveryError(f"Resend HTTP API delivery failed: {err_body}") from exc


def _send_via_brevo(
    api_key: str,
    from_name: str,
    from_address: str,
    recipient: str,
    subject: str,
    html_content: str,
    text_content: str | None,
) -> None:
    """Send email via Brevo HTTP REST API over standard HTTPS (port 443)."""
    payload = {
        "sender": {"name": from_name, "email": from_address},
        "to": [{"email": recipient}],
        "subject": subject,
        "htmlContent": html_content,
        "textContent": text_content or "VendorIQ compliance notification",
    }
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        "https://api.brevo.com/v3/smtp/email",
        data=data,
        headers={
            "api-key": api_key,
            "Content-Type": "application/json",
            "User-Agent": "VendorIQ/1.0",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            logger.info("Email submitted via Brevo HTTPS API to %s (status %s)", recipient, resp.status)
    except urllib.error.HTTPError as exc:
        err_body = exc.read().decode("utf-8", errors="replace")
        logger.error("Brevo API delivery error: %s - %s", exc, err_body)
        raise EmailDeliveryError(f"Brevo HTTP API delivery failed: {err_body}") from exc


def send_email(
    recipient: str,
    subject: str,
    html_content: str,
    text_content: str | None = None,
) -> None:
    """Send one message using either HTTP Email API (Resend/Brevo) or Google SMTP."""
    resend_api_key = (os.getenv("RESEND_API_KEY") or "").strip()
    brevo_api_key = (os.getenv("BREVO_API_KEY") or "").strip()
    from_address = _clean_header(os.getenv("SMTP_FROM"))
    from_name = _clean_header(os.getenv("SMTP_FROM_NAME", "VendorIQ"))

    clean_recipient = _clean_header(recipient)
    clean_subject = _clean_header(subject)

    if not clean_recipient:
        raise EmailDeliveryError("Recipient email address must not be empty.")

    # 1. Primary HTTP-based API if configured (bypasses Render/cloud SMTP firewall restrictions)
    if resend_api_key:
        logger.info("Dispatching email via Resend HTTP REST API (port 443)...")
        _send_via_resend(resend_api_key, from_name, from_address or "heypk4@gmail.com", clean_recipient, clean_subject, html_content, text_content)
        return

    if brevo_api_key:
        logger.info("Dispatching email via Brevo HTTP REST API (port 443)...")
        _send_via_brevo(brevo_api_key, from_name, from_address or "heypk4@gmail.com", clean_recipient, clean_subject, html_content, text_content)
        return

    # 2. Standard SMTP Dispatch (Google SMTP)
    host = _clean_header(os.getenv("SMTP_HOST", "smtp.gmail.com"))
    port_value = _clean_header(os.getenv("SMTP_PORT", "587"))
    username = _clean_header(os.getenv("SMTP_USERNAME"))
    password = (os.getenv("SMTP_PASSWORD") or "").strip()

    if not username or not password or not from_address:
        raise EmailDeliveryError(
            "SMTP_USERNAME, SMTP_PASSWORD, and SMTP_FROM must be configured."
        )

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
            with smtplib.SMTP_SSL(host, port, timeout=30) as smtp:
                smtp.ehlo()
                smtp.login(username, password)
                smtp.send_message(message)
        else:
            with smtplib.SMTP(host, port, timeout=30) as smtp:
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
                with smtplib.SMTP_SSL(host, 465, timeout=15) as ssl_smtp:
                    ssl_smtp.ehlo()
                    ssl_smtp.login(username, password)
                    ssl_smtp.send_message(message)
                logger.info("Email successfully submitted via Google SMTP_SSL (port 465) to %s", clean_recipient)
                return
            except Exception as ssl_exc:
                logger.warning("SMTP_SSL fallback on port 465 also failed: %s", ssl_exc)

        err_str = str(exc)
        if "101" in err_str or "unreachable" in err_str.lower():
            logger.error("Cloud provider firewall blocked outbound SMTP: %s", exc)
            raise EmailDeliveryError(
                "Render Free tier blocks outbound SMTP ports (25, 465, 587). "
                "To deliver live emails from Render, add RESEND_API_KEY (free at resend.com) to your Render environment variables, "
                "or upgrade your Render service to Starter ($7/mo) to unlock SMTP ports."
            ) from exc

        logger.exception("Google SMTP delivery failed for recipient %s", clean_recipient)
        raise EmailDeliveryError(f"Google SMTP delivery failed: {exc}") from exc

    logger.info("Email submitted via Google SMTP to %s", clean_recipient)
