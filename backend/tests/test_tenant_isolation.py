"""
Rigorous tenant isolation verification tests for VendorIQ.
Follows VendorIQ PRD Section 9 & 26.
Proves Company A cannot access or mutate Company B's resources:
- vendors
- raw materials
- vendor-material links
- batches
"""
import uuid
from tests.conftest import create_authenticated_user_client


def test_cross_tenant_isolation():
    # Setup Tenant A and Tenant B
    client_a = create_authenticated_user_client()
    client_b = create_authenticated_user_client()

    uid_b = uuid.uuid4().hex[:6]

    # Tenant B creates resources
    # 1. Vendor B
    vb_res = client_b.post(
        "/api/vendors",
        json={"vendor_name": f"Vendor B {uid_b}", "country": "Switzerland"},
    )
    assert vb_res.status_code == 201
    vendor_b_id = vb_res.json()["id"]

    # 2. Raw Material B
    mb_res = client_b.post(
        "/api/raw-materials",
        json={"name": f"Material B {uid_b}", "code": f"MAT-B-{uid_b}"},
    )
    assert mb_res.status_code == 201
    material_b_id = mb_res.json()["id"]

    # 3. Vendor Material B
    vmb_res = client_b.post(
        "/api/vendor-materials",
        json={"vendor_id": vendor_b_id, "raw_material_id": material_b_id, "is_approved": True},
    )
    assert vmb_res.status_code == 201
    vm_b_id = vmb_res.json()["id"]

    # 4. Batch B
    bb_res = client_b.post(
        "/api/batches",
        json={
            "vendor_id": vendor_b_id,
            "raw_material_id": material_b_id,
            "batch_number": f"BATCH-B-{uid_b}",
            "quantity": 100.0,
        },
    )
    assert bb_res.status_code == 201
    batch_b_id = bb_res.json()["id"]

    # =========================================================================
    # TENANT A PROHIBITIONS (Must return 404 NOT_FOUND)
    # =========================================================================

    # 1. Tenant A cannot GET Tenant B's vendor
    res = client_a.get(f"/api/vendors/{vendor_b_id}")
    assert res.status_code == 404
    assert res.json()["error"]["code"] == "NOT_FOUND"

    # 2. Tenant A cannot UPDATE Tenant B's vendor
    res = client_a.put(f"/api/vendors/{vendor_b_id}", json={"vendor_name": "Hijacked"})
    assert res.status_code == 404

    # 3. Tenant A cannot DELETE Tenant B's vendor
    res = client_a.delete(f"/api/vendors/{vendor_b_id}")
    assert res.status_code == 404

    # 4. Tenant A cannot GET Tenant B's raw material
    res = client_a.get(f"/api/raw-materials/{material_b_id}")
    assert res.status_code == 404
    assert res.json()["error"]["code"] == "NOT_FOUND"

    # 5. Tenant A cannot UPDATE Tenant B's raw material
    res = client_a.put(f"/api/raw-materials/{material_b_id}", json={"name": "Hijacked"})
    assert res.status_code == 404

    # 6. Tenant A cannot UPDATE Tenant B's vendor-material mapping
    res = client_a.put(f"/api/vendor-materials/{vm_b_id}", json={"is_approved": False})
    assert res.status_code == 404

    # 7. Tenant A cannot GET Tenant B's batch
    res = client_a.get(f"/api/batches/{batch_b_id}")
    assert res.status_code == 404
    assert res.json()["error"]["code"] == "NOT_FOUND"

    # 8. Tenant A cannot create a batch using Tenant B's vendor or material
    res = client_a.post(
        "/api/batches",
        json={
            "vendor_id": vendor_b_id,
            "raw_material_id": material_b_id,
            "batch_number": "BATCH-SNEAKY",
        },
    )
    assert res.status_code == 404

    # 9. Tenant A's listing endpoints must never leak Tenant B's records
    vendors_a = client_a.get("/api/vendors")
    assert all(item["id"] != vendor_b_id for item in vendors_a.json()["items"])

    materials_a = client_a.get("/api/raw-materials")
    assert all(item["id"] != material_b_id for item in materials_a.json()["items"])

    batches_a = client_a.get("/api/batches")
    assert all(item["id"] != batch_b_id for item in batches_a.json()["items"])
