import logging
from datetime import datetime, timezone
from typing import Any, Optional

from fastapi import APIRouter, Body, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.batch import Batch
from app.models.decision import BatchDecision, EmailEvent
from app.models.intelligence import BatchIntelligence
from app.models.raw_material import RawMaterial
from app.models.vendor import Vendor
from app.services.audit_service import record_audit_event
from app.services.decision_service import evaluate_decision
from app.services.email_service import EmailDeliveryError, send_email
from app.services.email_templates import render_decision_email

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/batches", tags=["Batch Decisions"])
email_router = APIRouter(prefix="/email-events", tags=["Email Events"])


class DecisionRequest(BaseModel):
    company_id: Optional[str] = None
    company_thresholds: dict[str, Any] = Field(default_factory=dict)


class DecisionResponse(BaseModel):
    decision: str
    risk_score: float
    reason: str
    recommended_actions: list[str]
    reference_id: int
    email_status: str


class EmailRetryResponse(BaseModel):
    id: int
    status: str
    error_message: Optional[str] = None


def _check_status(check: dict[str, Any]) -> Optional[bool]:
    result = check.get("status")
    if result == "PASS":
        return True
    if result == "FAIL":
        return False
    return None


def _extract_assessment(
    validation_result: dict[str, Any],
    company_thresholds: dict[str, Any],
) -> tuple[dict[str, Any], Optional[bool], dict[str, Any]]:
    checks = validation_result.get("checks", [])
    validation_results: dict[str, Any] = {}
    specification_check_names = company_thresholds.get(
        "material_specification_checks",
        ["purity", "moisture", "heavy_metals", "microbial_tamc", "material_shelf_life"],
    )
    if not isinstance(specification_check_names, (list, tuple)):
        raise HTTPException(status_code=422, detail="material_specification_checks must be a list.")

    spec_outcomes: list[Optional[bool]] = []
    document_checks: list[dict[str, Any]] = []
    for check in checks:
        if not isinstance(check, dict) or not isinstance(check.get("name"), str):
            continue
        name = check["name"]
        outcome = _check_status(check)
        validation_results[name] = {
            "passed": outcome,
            "status": check.get("status"),
            "reason": check.get("reason", ""),
        }
        if name in specification_check_names:
            spec_outcomes.append(outcome)
        if name.startswith("document_present_"):
            document_checks.append(check)

    if any(outcome is False for outcome in spec_outcomes):
        material_specification: Optional[bool] = False
    elif spec_outcomes and all(outcome is True for outcome in spec_outcomes):
        material_specification = True
    else:
        material_specification = None

    missing_documents = [
        check["name"].removeprefix("document_present_").upper()
        for check in document_checks
        if _check_status(check) is not True
    ]
    if document_checks:
        completeness = (
            sum(_check_status(check) is True for check in document_checks) / len(document_checks)
        )
    else:
        completeness = 1.0

    document_completeness = {
        "completeness": completeness,
        "missing_documents": missing_documents,
    }
    return validation_results, material_specification, document_completeness


def _text_content(
    decision: str, reason: str, actions: list[str], batch_number: str
) -> str:
    lines = [f"VendorIQ batch {batch_number}: {decision}", reason]
    if actions:
        lines.extend(["Recommended actions:", *(f"- {action}" for action in actions)])
    if decision == "NEEDS_REVIEW":
        lines.append("This batch requires manual review before final approval.")
    return "\n".join(lines)


def _deliver_event(db: Session, event: EmailEvent) -> None:
    if not event.recipient_email:
        event.status = "FAILED"
        event.error_message = "Vendor contact email is not configured."
        db.commit()
        return
    try:
        send_email(
            event.recipient_email,
            event.subject,
            event.html_content,
            event.text_content,
        )
    except EmailDeliveryError as exc:
        event.status = "FAILED"
        event.error_message = str(exc)
        db.commit()
        logger.error("Email event %s failed; its batch decision remains stored.", event.id)
        return

    event.status = "SENT"
    event.sent_at = datetime.now(timezone.utc).replace(tzinfo=None)
    event.error_message = None
    db.commit()
    record_audit_event(
        db,
        "Email Sent",
        company_id=event.company_id,
        vendor_id=event.vendor_id,
        batch_id=event.batch_id,
        details={"email_event_id": event.id, "email_type": event.email_type},
    )


@router.post(
    "/{batch_id}/decision",
    response_model=DecisionResponse,
    status_code=status.HTTP_200_OK,
)
def create_batch_decision(
    batch_id: int,
    request: DecisionRequest = Body(default=DecisionRequest()),
    db: Session = Depends(get_db),
) -> DecisionResponse:
    batch = db.query(Batch).filter(Batch.id == batch_id).first()
    if batch is None:
        raise HTTPException(status_code=404, detail=f"Batch with id {batch_id} not found.")
    vendor = db.query(Vendor).filter(Vendor.id == batch.vendor_id).first()
    material = db.query(RawMaterial).filter(RawMaterial.id == batch.raw_material_id).first()
    intelligence = (
        db.query(BatchIntelligence)
        .filter(BatchIntelligence.batch_id == batch.id)
        .first()
    )
    if intelligence is None or not intelligence.validation_result or not intelligence.ml_prediction:
        raise HTTPException(
            status_code=409,
            detail="Process and predict batch intelligence before requesting a decision.",
        )

    validation = intelligence.validation_result
    prediction = intelligence.ml_prediction
    risk_score = prediction.get("risk_score")
    risk_level = prediction.get("risk_level")
    if not isinstance(risk_score, (int, float)) or not isinstance(risk_level, str):
        raise HTTPException(status_code=409, detail="Stored risk prediction is incomplete.")
    if not isinstance(validation, dict) or not isinstance(validation.get("checks", []), list):
        raise HTTPException(status_code=409, detail="Stored validation results are invalid.")

    validation_results, material_specification, document_completeness = _extract_assessment(
        validation, request.company_thresholds
    )
    thresholds = request.company_thresholds
    if "mandatory_validation_checks" not in thresholds:
        thresholds["mandatory_validation_checks"] = []
    try:
        result = evaluate_decision(
            validation_results=validation_results,
            risk_score=float(risk_score),
            risk_level=risk_level,
            document_completeness=document_completeness,
            material_specification=material_specification,
            company_thresholds=thresholds,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    decision = BatchDecision(
        batch_id=batch.id,
        company_id=request.company_id,
        decision=result.decision,
        risk_score=float(risk_score),
        risk_level=risk_level,
        reason=result.reason,
        recommended_actions=result.recommended_actions,
    )
    db.add(decision)
    db.flush()
    batch.status = result.decision
    record_audit_event(
        db,
        "Decision Made",
        company_id=request.company_id,
        vendor_id=batch.vendor_id,
        batch_id=batch.id,
        details={"decision": result.decision, "reference_id": decision.id},
        commit=False,
    )
    db.commit()
    db.refresh(decision)

    kimi_analysis = intelligence.kimi_analysis or {}
    kimi_summary = kimi_analysis.get("summary", "")
    subject, html_content = render_decision_email(
        result.decision,
        batch_number=batch.batch_number,
        vendor_name=vendor.name if vendor else "Vendor",
        material=material.name if material else "Material",
        risk_score=risk_score,
        risk_level=risk_level,
        validation_summary=[
            f"{check.get('name', 'Check').replace('_', ' ').title()}: {check.get('status', 'UNKNOWN')}"
            for check in validation.get("checks", [])
        ],
        validation_results=validation_results,
        kimi_summary=kimi_summary,
        primary_issues=validation.get("missing_information", []),
        uncertain_checks=[
            item["name"]
            for item in validation.get("checks", [])
            if item.get("status") in {"MISSING", "NEEDS_REVIEW"}
        ],
        missing_information=document_completeness["missing_documents"],
        reason=result.reason,
        recommended_actions=result.recommended_actions,
        reference_id=decision.id,
        timestamp=datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
    )
    recipient = vendor.contact_email if vendor and vendor.contact_email else ""
    event = EmailEvent(
        company_id=request.company_id,
        vendor_id=batch.vendor_id,
        batch_id=batch.id,
        decision_id=decision.id,
        recipient_email=recipient,
        subject=subject,
        email_type=result.decision,
        status="PENDING",
        provider="GOOGLE_SMTP",
        html_content=html_content,
        text_content=_text_content(
            result.decision, result.reason, result.recommended_actions, batch.batch_number
        ),
    )
    db.add(event)
    db.commit()
    db.refresh(event)
    _deliver_event(db, event)

    return DecisionResponse(
        decision=result.decision,
        risk_score=float(risk_score),
        reason=result.reason,
        recommended_actions=result.recommended_actions,
        reference_id=decision.id,
        email_status=event.status,
    )


@email_router.post("/{event_id}/retry", response_model=EmailRetryResponse)
def retry_email_event(
    event_id: int,
    db: Session = Depends(get_db),
) -> EmailRetryResponse:
    updated = (
        db.query(EmailEvent)
        .filter(EmailEvent.id == event_id, EmailEvent.status == "FAILED")
        .update(
            {EmailEvent.status: "PENDING", EmailEvent.error_message: None},
            synchronize_session=False,
        )
    )
    if not updated:
        event = db.query(EmailEvent).filter(EmailEvent.id == event_id).first()
        if event is None:
            raise HTTPException(status_code=404, detail="Email event not found.")
        raise HTTPException(
            status_code=409,
            detail=f"Only FAILED email events can be retried; current status is {event.status}.",
        )
    db.commit()
    event = db.query(EmailEvent).filter(EmailEvent.id == event_id).first()
    if event is None:
        raise HTTPException(status_code=404, detail="Email event not found after retry claim.")

    _deliver_event(db, event)
    db.refresh(event)
    return EmailRetryResponse(
        id=event.id,
        status=event.status,
        error_message=event.error_message,
    )
