import uuid
from app.core.database import SessionLocal
from app.services.batch_service import update_batch_status


def test_batch_crud_and_status_transitions(auth_client):
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

    # 5. Test update_batch_status shared helper transitions
    with SessionLocal() as db:
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
