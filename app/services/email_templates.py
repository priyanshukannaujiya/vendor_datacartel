"""Render VendorIQ email templates."""

from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader, select_autoescape

TEMPLATE_DIRECTORY = Path(__file__).resolve().parents[1] / "templates" / "emails"
_environment = Environment(
    loader=FileSystemLoader(TEMPLATE_DIRECTORY),
    autoescape=select_autoescape(["html"]),
)

TEMPLATE_BY_DECISION = {
    "APPROVED": ("approved.html", "APPROVED"),
    "REJECTED": ("rejected.html", "REJECTED"),
    "NEEDS_REVIEW": ("needs_review.html", "NEEDS_REVIEW"),
}


def render_decision_email(decision: str, **context: Any) -> tuple[str, str]:
    """Return the subject and HTML body for a stored batch decision."""
    try:
        template_name, email_type = TEMPLATE_BY_DECISION[decision]
    except KeyError as exc:
        raise ValueError(f"Unsupported decision email type: {decision}") from exc
    template_context = {
        "email_type": email_type,
        "reference_id": context.get("reference_id", ""),
        **context,
    }
    subject_template = _environment.from_string(
        {
            "APPROVED": "VendorIQ — Batch {{ batch_number }} Approved",
            "REJECTED": "VendorIQ — Batch {{ batch_number }} Assessment Result",
            "NEEDS_REVIEW": "VendorIQ — Additional Review Required | {{ batch_number }}",
        }[email_type]
    )
    subject = subject_template.render(**template_context)
    html_content = _environment.get_template(template_name).render(**template_context)
    return subject, html_content
