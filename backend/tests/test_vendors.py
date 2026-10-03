import uuid


def test_vendor_crud(auth_client):
    # 1. Create vendor
    uid = uuid.uuid4().hex[:6]
    vendor_payload = {
        "vendor_name": f"Vendor {uid}",
        "country": "Germany",
        "supplier_category": "Active Ingredients",
        "contact_name": "Hans Muller",
        "email": f"hans_{uid}@example.com",
    }
    create_res = auth_client.post("/api/vendors", json=vendor_payload)
    assert create_res.status_code == 201, create_res.text
    vendor_data = create_res.json()
    vendor_id = vendor_data["id"]
    assert vendor_data["vendor_name"] == vendor_payload["vendor_name"]

    # 2. Get vendor by ID
    get_res = auth_client.get(f"/api/vendors/{vendor_id}")
    assert get_res.status_code == 200, get_res.text
    assert get_res.json()["id"] == vendor_id

    # 3. List vendors with search
    list_res = auth_client.get(f"/api/vendors?search={uid}")
    assert list_res.status_code == 200, list_res.text
    items = list_res.json()["items"]
    assert len(items) == 1
    assert items[0]["id"] == vendor_id

    # 4. Update vendor
    update_res = auth_client.put(
        f"/api/vendors/{vendor_id}",
        json={"contact_name": "Hans Updated"},
    )
    assert update_res.status_code == 200
    assert update_res.json()["contact_name"] == "Hans Updated"

    # 5. Soft-delete vendor
    del_res = auth_client.delete(f"/api/vendors/{vendor_id}")
    assert del_res.status_code == 200

    # 6. Deleted vendor should no longer appear in normal lists or be accessible by ID
    list_after_del = auth_client.get(f"/api/vendors?search={uid}")
    assert len(list_after_del.json()["items"]) == 0

    get_after_del = auth_client.get(f"/api/vendors/{vendor_id}")
    assert get_after_del.status_code == 404
