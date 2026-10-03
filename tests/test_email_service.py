import smtplib
from unittest.mock import MagicMock, patch

import pytest

from app.services.email_service import EmailDeliveryError, send_email
from app.services.email_templates import render_decision_email


SMTP_ENV = {
    "SMTP_HOST": "smtp.gmail.com",
    "SMTP_PORT": "587",
    "SMTP_USERNAME": "sender@example.com",
    "SMTP_PASSWORD": "test-app-password",
    "SMTP_FROM": "sender@example.com",
    "SMTP_FROM_NAME": "VendorIQ",
}


def test_send_email_uses_starttls_and_authentication():
    smtp = MagicMock()
    smtp_context = MagicMock()
    smtp_context.__enter__.return_value = smtp
    with patch.dict("os.environ", SMTP_ENV, clear=True), patch(
        "app.services.email_service.smtplib.SMTP", return_value=smtp_context
    ) as smtp_factory:
        send_email("recipient@example.com", "Subject", "<p>Hello</p>", "Hello")

    smtp_factory.assert_called_once_with("smtp.gmail.com", 587, timeout=30)
    smtp.starttls.assert_called_once()
    smtp.login.assert_called_once_with("sender@example.com", "test-app-password")
    smtp.send_message.assert_called_once()
    message = smtp.send_message.call_args.args[0]
    assert message["To"] == "recipient@example.com"
    assert message.get_body(preferencelist=("plain",)).get_content().strip() == "Hello"
    assert message.get_body(preferencelist=("html",)).get_content().strip() == "<p>Hello</p>"


def test_smtp_failure_raises_delivery_error():
    smtp = MagicMock()
    smtp.starttls.side_effect = smtplib.SMTPConnectError(421, b"unavailable")
    smtp_context = MagicMock()
    smtp_context.__enter__.return_value = smtp
    with patch.dict("os.environ", SMTP_ENV, clear=True), patch(
        "app.services.email_service.smtplib.SMTP", return_value=smtp_context
    ), pytest.raises(EmailDeliveryError, match="delivery failed"):
        send_email("recipient@example.com", "Subject", "<p>Hello</p>")


def test_missing_smtp_configuration_is_explicit():
    with patch.dict("os.environ", {}, clear=True), pytest.raises(
        EmailDeliveryError, match="must be configured"
    ):
        send_email("recipient@example.com", "Subject", "<p>Hello</p>")


@pytest.mark.parametrize(
    ("decision", "required_text"),
    [
        ("APPROVED", "APPROVED"),
        ("REJECTED", "REJECTED"),
        ("NEEDS_REVIEW", "This batch requires manual review before final approval."),
    ],
)
def test_decision_email_templates_render_status_and_batch(decision, required_text):
    _, content = render_decision_email(
        decision,
        batch_number="B-104",
        vendor_name="Acme Supply",
        material="Steel",
        risk_score=18,
        risk_level="LOW",
        validation_summary=["COA validated"],
        validation_results={"coa": True},
        kimi_summary="Assessment summary",
        primary_issues=[],
        uncertain_checks=[],
        reason="Configured checks passed.",
        recommended_actions=["Contact quality team"],
        reference_id="ref-1",
        timestamp="2026-10-03 00:00 UTC",
    )

    assert required_text in content
    assert "B-104" in content
    assert "Assessment summary" in content
    assert "ref-1" in content
