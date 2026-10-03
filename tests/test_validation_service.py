import datetime
import pytest

from app.services.validation_service import BatchValidationService
from app.schemas.validation import OverallValidationStatus, CheckStatus
from app.schemas.document import DocumentProcessResult, DocumentType, DocumentExtractionStatus
from app.models.batch import Batch
from app.models.raw_material import RawMaterial
from app.models.vendor import Vendor


@pytest.fixture
def validation_service():
    return BatchValidationService()


@pytest.fixture
def base_material():
    return RawMaterial(
        id=1,
        name="Paracetamol Active Substance",
        code="MAT-01",
        purity_min=99.0,
        moisture_max=0.5,
        heavy_metals_max_ppm=10.0,
        microbial_limit_cfu_g=100.0,
        storage_conditions="Store below 25C",
    )


@pytest.fixture
def base_vendor():
    return Vendor(
        id=1,
        name="Reliable Pharma Chem",
        code="VEND-01",
        certification_status="GMP_CERTIFIED",
    )


@pytest.fixture
def base_batch():
    return Batch(
        id=10,
        batch_number="BATCH-2026-AAA",
        vendor_id=1,
        raw_material_id=1,
        purity_reported=99.3,
        manufacturing_date=datetime.datetime(2026, 1, 1),
        expiry_date=datetime.datetime(2028, 1, 1),
    )


def test_validation_pass_full_compliance(validation_service, base_batch, base_material, base_vendor):
    docs = [
        DocumentProcessResult(
            filename="coa.pdf",
            document_type=DocumentType.COA,
            status=DocumentExtractionStatus.PROCESSED,
            extracted_data={
                "batch_number": "BATCH-2026-AAA",
                "purity": 99.3,  # >= 99.0% -> PASS
                "moisture": 0.35,  # <= 0.5% -> PASS
                "heavy_metals": 4.0,  # <= 10.0 ppm -> PASS
                "microbial_parameters": {"TAMC_cfu_g": 20.0},
                "expiry_date": "2028-01-01",
            }
        ),
        DocumentProcessResult(
            filename="sds.pdf",
            document_type=DocumentType.SDS,
            status=DocumentExtractionStatus.PROCESSED,
            extracted_data={"storage_requirements": "Store in dry place under 25C"}
        ),
        DocumentProcessResult(
            filename="gmp.pdf",
            document_type=DocumentType.GMP,
            status=DocumentExtractionStatus.PROCESSED,
            extracted_data={"certificate_number": "GMP-999", "valid_until": "2027-12-31"}
        ),
    ]

    fixed_today = datetime.date(2026, 3, 1)
    res = validation_service.validate_batch(
        batch=base_batch,
        material=base_material,
        vendor=base_vendor,
        processed_docs=docs,
        current_date=fixed_today
    )

    assert res.overall_status == OverallValidationStatus.PASS
    assert len(res.missing_information) == 0
    # Verify purity check was evaluated correctly
    purity_check = next(c for c in res.checks if c.name == "purity")
    assert purity_check.status == CheckStatus.PASS
    assert purity_check.actual == 99.3


def test_validation_fail_purity_substandard(validation_service, base_batch, base_material, base_vendor):
    # Purity 98.2% < 99.0% min required
    docs = [
        DocumentProcessResult(
            filename="coa.pdf",
            document_type=DocumentType.COA,
            status=DocumentExtractionStatus.PROCESSED,
            extracted_data={
                "batch_number": "BATCH-2026-AAA",
                "purity": 98.2,  # Substandard!
                "moisture": 0.4,
                "heavy_metals": 2.0,
                "expiry_date": "2028-01-01",
            }
        ),
        DocumentProcessResult(
            filename="sds.pdf",
            document_type=DocumentType.SDS,
            status=DocumentExtractionStatus.PROCESSED,
            extracted_data={"storage_requirements": "Store cold"}
        ),
        DocumentProcessResult(
            filename="gmp.pdf",
            document_type=DocumentType.GMP,
            status=DocumentExtractionStatus.PROCESSED,
            extracted_data={"certificate_number": "GMP-1", "valid_until": "2027-01-01"}
        )
    ]

    res = validation_service.validate_batch(base_batch, base_material, base_vendor, docs)
    assert res.overall_status == OverallValidationStatus.FAIL

    purity_check = next(c for c in res.checks if c.name == "purity")
    assert purity_check.status == CheckStatus.FAIL
    assert purity_check.actual == 98.2


def test_validation_fail_expired_gmp_certificate(validation_service, base_batch, base_material, base_vendor):
    # GMP expired in 2025, current date is 2026-03-01
    docs = [
        DocumentProcessResult(
            filename="coa.pdf",
            document_type=DocumentType.COA,
            status=DocumentExtractionStatus.PROCESSED,
            extracted_data={"batch_number": "BATCH-2026-AAA", "purity": 99.5, "moisture": 0.3}
        ),
        DocumentProcessResult(
            filename="sds.pdf",
            document_type=DocumentType.SDS,
            status=DocumentExtractionStatus.PROCESSED,
            extracted_data={"storage_requirements": "Room temp"}
        ),
        DocumentProcessResult(
            filename="gmp.pdf",
            document_type=DocumentType.GMP,
            status=DocumentExtractionStatus.PROCESSED,
            extracted_data={"certificate_number": "GMP-OLD", "valid_until": "2025-05-15"}  # EXPIRED!
        )
    ]

    fixed_today = datetime.date(2026, 3, 1)
    res = validation_service.validate_batch(
        batch=base_batch,
        material=base_material,
        vendor=base_vendor,
        processed_docs=docs,
        current_date=fixed_today
    )

    assert res.overall_status == OverallValidationStatus.FAIL
    gmp_check = next(c for c in res.checks if c.name == "gmp_certificate_validity")
    assert gmp_check.status == CheckStatus.FAIL
    assert "expired on 2025-05-15" in gmp_check.reason


def test_validation_fail_missing_required_document(validation_service, base_batch, base_material, base_vendor):
    # Only COA provided, SDS and GMP missing
    docs = [
        DocumentProcessResult(
            filename="coa.pdf",
            document_type=DocumentType.COA,
            status=DocumentExtractionStatus.PROCESSED,
            extracted_data={"batch_number": "BATCH-2026-AAA", "purity": 99.5}
        )
    ]

    res = validation_service.validate_batch(base_batch, base_material, base_vendor, docs)
    assert res.overall_status == OverallValidationStatus.FAIL
    assert any("SDS" in m for m in res.missing_information)
    assert any("GMP" in m for m in res.missing_information)


def test_validation_fail_batch_number_mismatch(validation_service, base_batch, base_material, base_vendor):
    # Batch record says BATCH-2026-AAA, but COA says BATCH-DIFFERENT-999
    docs = [
        DocumentProcessResult(
            filename="coa.pdf",
            document_type=DocumentType.COA,
            status=DocumentExtractionStatus.PROCESSED,
            extracted_data={"batch_number": "BATCH-DIFFERENT-999", "purity": 99.5}
        ),
        DocumentProcessResult(
            filename="sds.pdf",
            document_type=DocumentType.SDS,
            status=DocumentExtractionStatus.PROCESSED,
            extracted_data={"storage_requirements": "Standard"}
        ),
        DocumentProcessResult(
            filename="gmp.pdf",
            document_type=DocumentType.GMP,
            status=DocumentExtractionStatus.PROCESSED,
            extracted_data={"valid_until": "2027-10-10"}
        )
    ]

    res = validation_service.validate_batch(base_batch, base_material, base_vendor, docs)
    assert res.overall_status == OverallValidationStatus.FAIL
    match_check = next(c for c in res.checks if c.name == "batch_number_traceability")
    assert match_check.status == CheckStatus.FAIL


def test_validation_needs_review_missing_purity_value(validation_service, base_batch, base_material, base_vendor):
    # COA present, but purity is None
    docs = [
        DocumentProcessResult(
            filename="coa.pdf",
            document_type=DocumentType.COA,
            status=DocumentExtractionStatus.PROCESSED,
            extracted_data={"batch_number": "BATCH-2026-AAA", "moisture": 0.4}  # NO purity!
        ),
        DocumentProcessResult(
            filename="sds.pdf",
            document_type=DocumentType.SDS,
            status=DocumentExtractionStatus.PROCESSED,
            extracted_data={"storage_requirements": "Standard"}
        ),
        DocumentProcessResult(
            filename="gmp.pdf",
            document_type=DocumentType.GMP,
            status=DocumentExtractionStatus.PROCESSED,
            extracted_data={"valid_until": "2027-10-10"}
        )
    ]

    res = validation_service.validate_batch(base_batch, base_material, base_vendor, docs)
    assert res.overall_status == OverallValidationStatus.NEEDS_REVIEW
    assert "COA purity value" in res.missing_information
