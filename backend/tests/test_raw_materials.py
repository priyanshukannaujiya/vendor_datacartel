import uuid


def test_raw_material_crud(auth_client):
    uid = uuid.uuid4().hex[:6]
    material_payload = {
        "name": f"Material {uid}",
        "code": f"MAT-{uid}",
        "category": "Active Ingredients",
        "specification": {
            "parameters": [
                {
                    "name": "purity",
                    "operator": ">=",
                    "value": 99.0,
                    "unit": "%",
                    "mandatory": True,
                }
            ],
            "moisture_max": 0.5,
        },
        "required_documents": ["COA", "SDS", "GMP"],
    }

    # 1. Create raw material
    create_res = auth_client.post("/api/raw-materials", json=material_payload)
    assert create_res.status_code == 201, create_res.text
    material_data = create_res.json()
    material_id = material_data["id"]
    assert material_data["code"] == material_payload["code"]

    # 2. Duplicate material code in same company returns 409 Conflict
    dup_res = auth_client.post("/api/raw-materials", json=material_payload)
    assert dup_res.status_code == 409
    assert dup_res.json()["error"]["code"] == "CONFLICT"

    # 3. Get raw material by ID
    get_res = auth_client.get(f"/api/raw-materials/{material_id}")
    assert get_res.status_code == 200, get_res.text
    assert get_res.json()["id"] == material_id
    assert get_res.json()["specification"]["parameters"][0]["name"] == "purity"

    # 4. List raw materials with search
    list_res = auth_client.get(f"/api/raw-materials?search=MAT-{uid}")
    assert list_res.status_code == 200
    assert len(list_res.json()["items"]) == 1

    # 5. Update raw material
    update_res = auth_client.put(
        f"/api/raw-materials/{material_id}",
        json={"description": "Updated high grade material"},
    )
    assert update_res.status_code == 200
    assert update_res.json()["description"] == "Updated high grade material"
