"""
System & SMTP settings management router for VendorIQ.
Allows configuring Google SMTP credentials and testing live delivery.
"""
import os
import smtplib
import logging
from typing import Optional
from pydantic import BaseModel, EmailStr
from fastapi import APIRouter, Depends, HTTPException, status
from app.core.security import get_optional_current_user
from app.models.user import User
from app.services.email_service import send_email

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/settings", tags=["Settings"])


class SMTPConfigRequest(BaseModel):
    smtp_host: str = "smtp.gmail.com"
    smtp_port: int = 587
    smtp_username: str
    smtp_password: str
    smtp_from: str
    smtp_from_name: str = "VendorIQ"


class SMTPTestRequest(BaseModel):
    recipient_email: str
    message: Optional[str] = "This is a verification test from VendorIQ Platform via Google SMTP."


@router.get("/smtp")
def get_smtp_status(current_user: Optional[User] = Depends(get_optional_current_user)):
    """Get current SMTP configuration status (passwords obfuscated)."""
    username = os.getenv("SMTP_USERNAME")
    from_email = os.getenv("SMTP_FROM")
    host = os.getenv("SMTP_HOST", "smtp.gmail.com")
    port = os.getenv("SMTP_PORT", "587")
    from_name = os.getenv("SMTP_FROM_NAME", "VendorIQ")

    is_configured = bool(username and os.getenv("SMTP_PASSWORD") and from_email)

    obfuscated_user = None
    if username:
        parts = username.split("@")
        if len(parts) == 2:
            obfuscated_user = f"{parts[0][:2]}***@{parts[1]}"
        else:
            obfuscated_user = f"{username[:2]}***"

    return {
        "is_configured": is_configured,
        "host": host,
        "port": port,
        "username_preview": obfuscated_user,
        "from_address": from_email,
        "from_name": from_name,
        "mode": "STARTTLS",
    }


@router.post("/smtp")
def save_smtp_config(
    data: SMTPConfigRequest,
    current_user: Optional[User] = Depends(get_optional_current_user),
):
    """
    Save Google SMTP credentials to active runtime environment and .env file.
    """
    os.environ["SMTP_HOST"] = data.smtp_host
    os.environ["SMTP_PORT"] = str(data.smtp_port)
    os.environ["SMTP_USERNAME"] = data.smtp_username.strip()
    os.environ["SMTP_PASSWORD"] = data.smtp_password.strip()
    os.environ["SMTP_FROM"] = data.smtp_from.strip()
    os.environ["SMTP_FROM_NAME"] = data.smtp_from_name.strip()

    # Attempt to persist in local .env if present
    env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), ".env")
    try:
        lines = []
        if os.path.exists(env_path):
            with open(env_path, "r", encoding="utf-8") as f:
                lines = f.readlines()

        keys_to_set = {
            "SMTP_HOST": data.smtp_host,
            "SMTP_PORT": str(data.smtp_port),
            "SMTP_USERNAME": data.smtp_username.strip(),
            "SMTP_PASSWORD": data.smtp_password.strip(),
            "SMTP_FROM": data.smtp_from.strip(),
            "SMTP_FROM_NAME": data.smtp_from_name.strip(),
        }

        new_lines = []
        seen_keys = set()
        for line in lines:
            trimmed = line.strip()
            matched = False
            for k, v in keys_to_set.items():
                if trimmed.startswith(f"{k}=") or trimmed.startswith(f"{k} ="):
                    new_lines.append(f"{k}={v}\n")
                    seen_keys.add(k)
                    matched = True
                    break
            if not matched:
                new_lines.append(line)

        for k, v in keys_to_set.items():
            if k not in seen_keys:
                new_lines.append(f"{k}={v}\n")

        with open(env_path, "w", encoding="utf-8") as f:
            f.writelines(new_lines)
    except Exception as e:
        logger.warning("Could not persist SMTP keys to .env: %s", e)

    return {
        "success": True,
        "message": "Google SMTP credentials saved and active.",
        "username": data.smtp_username,
        "from_address": data.smtp_from,
    }


@router.post("/smtp/test")
def test_smtp_delivery(
    data: SMTPTestRequest,
    current_user: Optional[User] = Depends(get_optional_current_user),
):
    """
    Send a live verification email to confirm Google SMTP connection & credentials.
    """
    try:
        send_email(
            recipient=data.recipient_email,
            subject="VendorIQ — Google SMTP Verification Successful",
            html_content=f"""
            <div style="font-family:sans-serif; padding:20px; border:1px solid #e2e8f0; border-radius:8px;">
              <h2 style="color:#2563eb;">VendorIQ Google SMTP Connected</h2>
              <p>Your Google SMTP credentials are authenticated and operational.</p>
              <p><strong>Test Message:</strong> {data.message}</p>
              <hr style="border:0; border-top:1px solid #f1f5f9; margin:16px 0;" />
              <p style="font-size:12px; color:#64748b;">Dispatched securely via Google SMTP with STARTTLS.</p>
            </div>
            """,
            text_content=f"VendorIQ Google SMTP Connected. Test message: {data.message}",
        )
        return {
            "success": True,
            "message": f"Test email successfully delivered to {data.recipient_email} via Google SMTP!",
            "recipient": data.recipient_email,
        }
    except Exception as exc:
        logger.exception("SMTP test delivery failed")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Google SMTP delivery failed: {str(exc)}. Please verify your Gmail address and 16-character App Password.",
        )
