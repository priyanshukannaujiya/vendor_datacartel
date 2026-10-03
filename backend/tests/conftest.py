import uuid
import datetime
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from fastapi.testclient import TestClient

from app.core.database import Base, get_db
from app.models.company import Company
from app.models.vendor import Vendor
from app.models.raw_material import RawMaterial
from app.models.batch import Batch
from app.models.document import Document
from app.models.intelligence import BatchIntelligence
from app.main import app

# In-memory SQLite engine for unit tests
test_engine = create_engine(
    "sqlite://",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)


@pytest.fixture(scope="function")
def db_session():
    """Provides an isolated in-memory test database session."""
    Base.metadata.create_all(bind=test_engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=test_engine)


@pytest.fixture(scope="function")
def client(db_session):
    """FastAPI TestClient with overridden get_db dependency."""
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
def sample_company(db_session):
    company = Company(id=uuid.uuid4(), name=f"Test Company {uuid.uuid4().hex[:6]}")
    db_session.add(company)
    db_session.commit()
    db_session.refresh(company)
    return company


@pytest.fixture
def sample_vendor(db_session, sample_company) -> Vendor:
    vendor = Vendor(
        id=uuid.uuid4(),
        company_id=sample_company.id,
        vendor_name="Apex Pharma Chemicals Ltd",
        email="qa@apexpharma.com",
        tier="TIER_1",
        status="ACTIVE",
        certification_status="GMP_CERTIFIED",
        delivery_reliability=0.96,
        capacity=100000.0,
        risk_score=15.0,
    )
    db_session.add(vendor)
    db_session.commit()
    db_session.refresh(vendor)
    return vendor


@pytest.fixture
def sample_material(db_session, sample_company) -> RawMaterial:
    material = RawMaterial(
        id=uuid.uuid4(),
        company_id=sample_company.id,
        name="L-Ascorbic Acid USP",
        code=f"RM-ASC-{uuid.uuid4().hex[:4]}",
        purity_min=99.0,
        moisture_max=0.5,
        heavy_metals_max_ppm=5.0,
        microbial_limit_cfu_g=50.0,
    )
    db_session.add(material)
    db_session.commit()
    db_session.refresh(material)
    return material


@pytest.fixture
def sample_batch(db_session, sample_company, sample_vendor, sample_material) -> Batch:
    batch = Batch(
        id=uuid.uuid4(),
        company_id=sample_company.id,
        vendor_id=sample_vendor.id,
        raw_material_id=sample_material.id,
        batch_number=f"BATCH-{uuid.uuid4().hex[:6]}",
        quantity=1000.0,
        unit="kg",
        price=100.0,
        purity_reported=99.3,
        status="RECEIVED",
    )
    db_session.add(batch)
    db_session.commit()
    db_session.refresh(batch)
    return batch


def create_authenticated_user_client(db_session=None):
    """Create an authenticated TestClient with an isolated tenant in test SQLite."""
    if db_session is None:
        Base.metadata.create_all(bind=test_engine)
        session = TestingSessionLocal()
        def override_get_db():
            try:
                yield session
            finally:
                pass
        app.dependency_overrides[get_db] = override_get_db
    else:
        def override_get_db():
            try:
                yield db_session
            finally:
                pass
        app.dependency_overrides[get_db] = override_get_db

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
def auth_client(db_session):
    client = create_authenticated_user_client(db_session)
    yield client
    app.dependency_overrides.clear()

