from unittest.mock import patch

import pytest

from app.models.decision import AuditEvent, BatchDecision, EmailEvent
from app.models.intelligence import BatchIntelligence
from app.services.email_service import EmailDeliveryError


def prepared_intelligence(db_session, sample_batch, **overrides):
    values = {
        "validation_result": {
            "overall_status": "PASS",
            "checks": [
                {"name": "document_present_coa", "status": "PASS", "reason": "COA available"},
                {"name": "purity", "status": "PASS", "reason": "Purity met the material spec"},
            ],
            "missing_information": [],
        },
        "vendor_history": {"documentation_completeness": 1.0},
        "ml_prediction": {"risk_score": 18.0, "risk_level": "LOW"},
        "kimi_analysis": {"summary": "Assessment summary", "recommended_actions": []},
    }
    values.update(overrides)
    intelligence = BatchIntelligence(batch_id=sample_batch.id, **values)
    db_session.add(intelligence)
    db_session.commit()
    return intelligence


def thresholds(**overrides):
    values = {
        "mandatory_validation_checks": ["purity"],
        "critical_document_types": ["COA"],
        "max_approval_risk_score": 25,
        "approval_risk_levels": ["LOW"],
    }
    values.update(overrides)
    return values


def test_decision_api_approves_batch_and_stores_event(
    client, db_session, sample_batch, sample_vendor
):
    prepared_intelligence(db_session, sample_batch)
    with patch("app.api.routes.decisions.send_email") as send:
        response = client.post(
            f"/api/batches/{sample_batch.id}/decision",
            json={"company_id": "company-1", "company_thresholds": thresholds()},
        )

    assert response.status_code == 200
    assert response.json()["decision"] == "APPROVED"
    assert response.json()["email_status"] == "SENT"
    send.assert_called_once()
    event = db_session.query(EmailEvent).one()
    assert event.email_type == "APPROVED"
    assert event.status == "SENT"
    assert event.provider == "GOOGLE_SMTP"
    assert event.recipient_email == sample_vendor.contact_email
    assert db_session.query(BatchDecision).one().decision == "APPROVED"
    assert sample_batch.status == "APPROVED"
    assert db_session.query(AuditEvent).filter_by(event_type="Decision Made").count() == 1
    assert db_session.query(AuditEvent).filter_by(event_type="Email Sent").count() == 1


def test_missing_critical_document_requires_review(client, db_session, sample_batch):
    prepared_intelligence(
        db_session,
        sample_batch,
        validation_result={
            "checks": [
                {"name": "document_present_coa", "status": "FAIL", "reason": "COA missing"},
                {"name": "purity", "status": "PASS", "reason": "Purity passed"},
            ],
            "missing_information": ["COA is missing"],
        },
    )
    with patch("app.api.routes.decisions.send_email"):
        response = client.post(
            f"/api/batches/{sample_batch.id}/decision",
            json={"company_thresholds": thresholds()},
        )

    assert response.status_code == 200
    assert response.json()["decision"] == "NEEDS_REVIEW"
    assert "COA" in response.json()["reason"]


def test_failed_material_specification_rejects(client, db_session, sample_batch):
    prepared_intelligence(
        db_session,
        sample_batch,
        validation_result={
            "checks": [
                {"name": "document_present_coa", "status": "PASS", "reason": "COA available"},
                {"name": "purity", "status": "FAIL", "reason": "Purity below configured spec"},
            ],
            "missing_information": [],
        },
    )
    with patch("app.api.routes.decisions.send_email"):
        response = client.post(
            f"/api/batches/{sample_batch.id}/decision",
            json={"company_thresholds": thresholds()},
        )

    assert response.status_code == 200
    assert response.json()["decision"] == "REJECTED"


def test_failed_delivery_preserves_decision_and_retry_sends_email(
    client, db_session, sample_batch
):
    prepared_intelligence(db_session, sample_batch)
    with patch(
        "app.api.routes.decisions.send_email",
        side_effect=EmailDeliveryError("Google SMTP delivery failed."),
    ):
        response = client.post(
            f"/api/batches/{sample_batch.id}/decision",
            json={"company_thresholds": thresholds()},
        )

    assert response.status_code == 200
    assert response.json()["decision"] == "APPROVED"
    assert response.json()["email_status"] == "FAILED"
    decision = db_session.query(BatchDecision).one()
    event = db_session.query(EmailEvent).one()
    assert decision.decision == "APPROVED"
    assert event.status == "FAILED"
    assert event.error_message == "Google SMTP delivery failed."

    with patch("app.api.routes.decisions.send_email") as send:
        retry = client.post(f"/api/email-events/{event.id}/retry")

    assert retry.status_code == 200
    assert retry.json()["status"] == "SENT"
    send.assert_called_once()
    assert db_session.query(BatchDecision).one().decision == "APPROVED"
    assert db_session.query(AuditEvent).filter_by(event_type="Email Sent").count() == 1


def test_retry_rejects_already_sent_event(client, db_session, sample_batch):
    prepared_intelligence(db_session, sample_batch)
    with patch("app.api.routes.decisions.send_email"):
        response = client.post(
            f"/api/batches/{sample_batch.id}/decision",
            json={"company_thresholds": thresholds()},
        )
    event = db_session.query(EmailEvent).one()

    retry = client.post(f"/api/email-events/{event.id}/retry")

    assert response.status_code == 200
    assert retry.status_code == 409


def test_decision_requires_pipeline_assessment(client, sample_batch):
    response = client.post(
        f"/api/batches/{sample_batch.id}/decision",
        json={"company_thresholds": thresholds()},
    )

    assert response.status_code == 409


@pytest.mark.parametrize("batch_id", [999999])
def test_unknown_batch_is_not_found(client, batch_id):
    response = client.post(f"/api/batches/{batch_id}/decision", json={})

    assert response.status_code == 404
