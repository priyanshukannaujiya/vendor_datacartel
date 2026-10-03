import uuid
import pytest
from fastapi.testclient import TestClient
from app.main import app


def create_authenticated_user_client():
    """Create an authenticated TestClient with an isolated tenant."""
    client = TestClient(app)
    uid = uuid.uuid4().hex[:8]
    reg_payload = {
        "company_name": f"Company {uid}",
        "full_name": f"User {uid}",
        "email": f"user_{uid}@example.com",
        "password": "Password123!",
    }
    res = client.post("/api/auth/register", json=reg_payload)
    assert res.status_code == 201, res.text
    login_res = client.post(
        "/api/auth/login",
        json={"email": reg_payload["email"], "password": reg_payload["password"]},
    )
    assert login_res.status_code == 200, login_res.text
    token = login_res.json()["access_token"]
    client.headers = {"Authorization": f"Bearer {token}"}
    return client


@pytest.fixture
def auth_client():
    return create_authenticated_user_client()
