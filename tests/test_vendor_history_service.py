import pytest
import datetime
from app.services.vendor_history_service import vendor_history_service
from app.models.vendor import Vendor
from app.models.raw_material import RawMaterial
from app.models.batch import Batch
from app.models.document import Document


def test_vendor_history_with_multiple_batches(db_session, sample_vendor, sample_material):
    # Insert 5 historical batches
    # 4 APPROVED, 1 REJECTED
    purities = [99.2, 99.4, 99.1, 99.5, 98.0]
    lead_times = [12.0, 14.0, 13.0, 15.0, 18.0]
    prices = [100.0, 102.0, 99.0, 101.0, 105.0]

    for i in range(5):
        b = Batch(
            batch_number=f"HIST-BATCH-{i+1}",
            vendor_id=sample_vendor.id,
            raw_material_id=sample_material.id,
            quantity=2000.0,
            price_per_unit=prices[i],
            lead_time_actual=lead_times[i],
            purity_reported=purities[i],
            status="APPROVED" if i < 4 else "REJECTED",
        )
        db_session.add(b)
        db_session.commit()
        # Add a document for each batch
        doc = Document(
            batch_id=b.id,
            vendor_id=sample_vendor.id,
            filename=f"coa_{i}.pdf",
            file_path=f"/dummy/coa_{i}.pdf",
            document_type="COA"
        )
        db_session.add(doc)

    db_session.commit()

    current_batch = Batch(
        id=999,
        batch_number="CURRENT-TEST-BATCH",
        vendor_id=sample_vendor.id,
        raw_material_id=sample_material.id,
        quantity=3000.0,
        purity_reported=99.3,
    )

    metrics = vendor_history_service.analyze_vendor_history(
        db=db_session,
        vendor_id=sample_vendor.id,
        current_batch=current_batch
    )

    assert metrics.vendor_id == sample_vendor.id
    assert metrics.previous_batches == 5
    # 4/5 approved = 0.8
    assert metrics.approval_rate == 0.80
    assert metrics.rejection_rate == 0.20
    assert metrics.incident_count == 1
    # Average purity = sum(purities)/5 = 495.2 / 5 = 99.04
    assert round(metrics.average_purity, 2) == 99.04
    assert metrics.purity_variance > 0
    assert metrics.average_lead_time == 14.4
    assert "purity_diff_from_history" in metrics.comparison_notes


def test_vendor_history_zero_batches_new_vendor(db_session):
    # Brand new vendor without prior records
    new_vendor = Vendor(
        name="Novus Bio Supps",
        code="VEND-NEW-99",
        tier="TIER_3",
        status="ACTIVE",
        delivery_reliability=0.88,
        capacity=50000.0,
    )
    db_session.add(new_vendor)
    db_session.commit()

    metrics = vendor_history_service.analyze_vendor_history(
        db=db_session,
        vendor_id=new_vendor.id,
    )

    assert metrics.previous_batches == 0
    assert metrics.approval_rate == 0.0
    assert metrics.rejection_rate == 0.0
    assert metrics.purity_variance == 0.0
    assert metrics.comparison_notes["status"] == "INSUFFICIENT_HISTORY"


def test_vendor_history_single_batch(db_session, sample_vendor, sample_material):
    # Single batch test: should avoid sample variance division by zero
    b = Batch(
        batch_number="HIST-SINGLE-01",
        vendor_id=sample_vendor.id,
        raw_material_id=sample_material.id,
        purity_reported=99.5,
        status="APPROVED",
    )
    db_session.add(b)
    db_session.commit()

    metrics = vendor_history_service.analyze_vendor_history(
        db=db_session,
        vendor_id=sample_vendor.id,
    )

    assert metrics.previous_batches == 1
    assert metrics.purity_variance == 0.0
    assert metrics.average_purity == 99.5
    assert metrics.approval_rate == 1.0
