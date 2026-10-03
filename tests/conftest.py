import os
import datetime
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from fastapi.testclient import TestClient

from app.core.database import Base, get_db
from app.models.vendor import Vendor
from app.models.raw_material import RawMaterial
from app.models.batch import Batch
from app.models.document import Document
from app.models.intelligence import BatchIntelligence
from app.main import app

from sqlalchemy.pool import StaticPool

# In-memory SQLite engine using StaticPool to ensure table state persists across connections
test_engine = create_engine(
    "sqlite://",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)


@pytest.fixture(scope="function")
def db_session():
    """Provides a fresh, clean database session for each test."""
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
def sample_vendor(db_session) -> Vendor:
    vendor = Vendor(
        name="Apex Pharma Chemicals Ltd",
        code="VEND-APEX-001",
        contact_email="qa@apexpharma.com",
        tier="TIER_1",
        status="ACTIVE",
        certification_status="GMP_CERTIFIED",
        delivery_reliability=0.96,
        capacity=150000.0,
    )
    db_session.add(vendor)
    db_session.commit()
    db_session.refresh(vendor)
    return vendor


@pytest.fixture
def sample_material(db_session) -> RawMaterial:
    material = RawMaterial(
        name="Paracetamol Active Pharmaceutical Ingredient",
        code="MAT-APAP-USP",
        cas_number="103-90-2",
        purity_min=99.0,
        moisture_max=0.5,
        heavy_metals_max_ppm=10.0,
        microbial_limit_cfu_g=100.0,
        storage_conditions="Store below 25C in tight, light-resistant container",
        lead_time_days=14.0,
        base_price=120.0,
    )
    db_session.add(material)
    db_session.commit()
    db_session.refresh(material)
    return material


@pytest.fixture
def sample_batch(db_session, sample_vendor, sample_material) -> Batch:
    batch = Batch(
        batch_number="BATCH-2026-X01",
        vendor_id=sample_vendor.id,
        raw_material_id=sample_material.id,
        quantity=5000.0,
        unit="kg",
        price_per_unit=120.0,
        lead_time_actual=13.0,
        manufacturing_date=datetime.datetime(2026, 1, 15),
        expiry_date=datetime.datetime(2028, 1, 14),
        status="PENDING",
        purity_reported=99.4,
    )
    db_session.add(batch)
    db_session.commit()
    db_session.refresh(batch)
    return batch
