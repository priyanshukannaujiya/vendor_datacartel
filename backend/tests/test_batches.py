import uuid
import pytest
from pydantic import ValidationError
from app.core.database import SessionLocal
from app.services.batch_service import update_batch_status
from app.schemas.batch import BatchDecisionRequest


def test_manual_override_requires_decision_and_audit_notes():
    with pytest.raises(ValidationError):
        BatchDecisionRequest.model_validate({"manual_override": True, "decision": "APPROVED"})

    request = BatchDecisionRequest.model_validate({
        "manual_override": True,
        "decision": "APPROVED",
        "notes": "Approved under deviation review.",
    })
    assert request.manual_override is True
    assert request.decision == "APPROVED"


@pytest.mark.parametrize(
    ("smtp_error", "expected_status"),
    [(None, "SENT"), (RuntimeError("SMTP unavailable"), "FAILED")],
)
def test_document_request_email_reports_and_stores_delivery_status(
    client,
    db_session,
    sample_batch,
    monkeypatch,
    smtp_error,
    expected_status,
):
    from app.models.decision import EmailEvent

    def fake_send_email(**_kwargs):
        if smtp_error:
            raise smtp_error

    monkeypatch.setattr("app.routers.batches.send_email", fake_send_email)
    response = client.post(
        f"/api/batches/{sample_batch.id}/request-documents",
        json={"custom_email": "qa@example.com"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["email_status"] == expected_status
    assert payload["success"] is (expected_status == "SENT")
    if expected_status == "FAILED":
        assert "delivery failed" in payload["message"].lower()

    event = db_session.query(EmailEvent).filter(
        EmailEvent.batch_id == sample_batch.id
    ).one()
    assert event.status == expected_status
    assert event.recipient_email == "qa@example.com"


def test_batch_crud_and_status_transitions(auth_client, db_session):
    uid = uuid.uuid4().hex[:6]

    # 1. Setup vendor and raw material
    vendor_res = auth_client.post(
        "/api/vendors",
        json={"vendor_name": f"Supplier {uid}", "is_active": True},
    )
    assert vendor_res.status_code == 201
    vendor_id = vendor_res.json()["id"]

    mat_res = auth_client.post(
        "/api/raw-materials",
        json={"name": f"Chemical {uid}", "code": f"CHEM-{uid}"},
    )
    assert mat_res.status_code == 201
    material_id = mat_res.json()["id"]

    # Link vendor and raw material
    vm_res = auth_client.post(
        "/api/vendor-materials",
        json={"vendor_id": vendor_id, "raw_material_id": material_id, "is_approved": True},
    )
    assert vm_res.status_code == 201

    # 2. Create batch
    batch_payload = {
        "vendor_id": vendor_id,
        "raw_material_id": material_id,
        "batch_number": f"BATCH-{uid}",
        "quantity": 500.0,
        "unit": "kg",
        "price": 2500.0,
    }
    create_res = auth_client.post("/api/batches", json=batch_payload)
    assert create_res.status_code == 201, create_res.text
    batch_data = create_res.json()
    batch_id = batch_data["id"]
    assert batch_data["status"] == "RECEIVED"
    assert batch_data["batch_number"] == f"BATCH-{uid}"

    # 3. Duplicate batch number for same vendor returns 409 Conflict
    dup_res = auth_client.post("/api/batches", json=batch_payload)
    assert dup_res.status_code == 409
    assert dup_res.json()["error"]["code"] == "CONFLICT"

    # 4. Get batch by ID
    get_res = auth_client.get(f"/api/batches/{batch_id}")
    assert get_res.status_code == 200
    assert get_res.json()["id"] == batch_id
    detail = get_res.json()
    assert detail["quality_checks"]["all_checks"] == []
    assert detail["risk_prediction"] is None
    assert detail["kimi_analysis"] is None
    assert detail["final_decision"] is None
    assert [event["event_type"] for event in detail["audit_timeline"]] == ["Batch Received"]

    # 5. Test update_batch_status shared helper transitions
    db = db_session
    # Dev 2 pipeline steps
    b = update_batch_status(db, batch_id, "PROCESSING")
    assert b.status == "PROCESSING"

    b = update_batch_status(db, batch_id, "VALIDATED")
    assert b.status == "VALIDATED"

    b = update_batch_status(db, batch_id, "PREDICTED")
    assert b.status == "PREDICTED"

    # Dev 3 decision engine step
    b = update_batch_status(db, batch_id, "APPROVED")
    assert b.status == "APPROVED"

    # Verify updated status reflects on API
    get_updated = auth_client.get(f"/api/batches/{batch_id}")
    assert get_updated.status_code == 200
    assert get_updated.json()["status"] == "APPROVED"
