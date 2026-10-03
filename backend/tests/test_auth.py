import uuid
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_register_login_me_flow():
    # 1. Register a new unique company and user
    uid = uuid.uuid4().hex[:8]
    register_payload = {
        "company_name": f"Test Company {uid}",
        "full_name": f"Tester {uid}",
        "email": f"test_{uid}@example.com",
        "password": "Password123!",
    }
    reg_res = client.post("/api/auth/register", json=register_payload)
    assert reg_res.status_code == 201, reg_res.text
    user_data = reg_res.json()
    assert user_data["email"] == register_payload["email"]
    assert "password_hash" not in user_data

    # 2. Duplicate registration should return 409 Conflict
    dup_res = client.post("/api/auth/register", json=register_payload)
    assert dup_res.status_code == 409
    assert dup_res.json()["error"]["code"] == "CONFLICT"

    # 3. Login with credentials
    login_payload = {
        "email": register_payload["email"],
        "password": register_payload["password"],
    }
    login_res = client.post("/api/auth/login", json=login_payload)
    assert login_res.status_code == 200, login_res.text
    token_data = login_res.json()
    assert "access_token" in token_data
    token = token_data["access_token"]

    # 4. Access /auth/me with valid Bearer token
    headers = {"Authorization": f"Bearer {token}"}
    me_res = client.get("/api/auth/me", headers=headers)
    assert me_res.status_code == 200, me_res.text
    me_data = me_res.json()
    assert me_data["user"]["email"] == register_payload["email"]
    assert me_data["company"]["name"] == register_payload["company_name"]

    # 5. Access /auth/me without token should return 401 Unauthorized
    unauth_res = client.get("/api/auth/me")
    assert unauth_res.status_code == 401
    assert unauth_res.json()["error"]["code"] == "UNAUTHORIZED"
