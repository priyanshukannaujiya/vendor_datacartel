import os
import json
import pytest
from unittest.mock import patch, MagicMock

from app.models.document import Document
from app.models.intelligence import BatchIntelligence


def test_health_check_endpoint(client):
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "VendorIQ" in data["app"]


def test_process_batch_endpoint_success(client, db_session, sample_batch, sample_vendor, tmp_path):
    # Create mock COA file on disk
    coa_file = tmp_path / "coa_sample.txt"
    coa_file.write_text("""
    CERTIFICATE OF ANALYSIS
    Batch Number: BATCH-2026-X01
    Product: Paracetamol API
    Purity: 99.4%
    Moisture: 0.28%
    Heavy Metals: < 5.0 ppm
    Test Date: 2026-01-20
    Expiry Date: 2028-01-14
    Laboratory: Central QC Lab
    """)

    # Attach document in DB
    doc = Document(
        batch_id=sample_batch.id,
        vendor_id=sample_vendor.id,
        filename="coa_sample.txt",
        file_path=str(coa_file),
        document_type="COA",
        status="UPLOADED"
    )
    db_session.add(doc)
    db_session.commit()

    response = client.post(f"/api/batches/{sample_batch.id}/process")
    assert response.status_code == 200
    data = response.json()

    assert data["batch_id"] == sample_batch.id
    assert data["batch_number"] == sample_batch.batch_number
    assert "validation_result" in data
    assert "vendor_history" in data
    assert len(data["extracted_documents"]) == 1

    # Verify database persistence in batch_intelligence table
    intel = db_session.query(BatchIntelligence).filter(BatchIntelligence.batch_id == sample_batch.id).first()
    assert intel is not None
    assert intel.validation_result is not None
    assert intel.vendor_history is not None


def test_predict_risk_endpoint_success_with_kimi_mock(client, db_session, sample_batch):
    from app.schemas.kimi import KimiAnalysisResult, KimiStatus
    mock_analysis = KimiAnalysisResult(
        summary="Synthetic risk assessment complete for batch BATCH-2026-X01.",
        key_findings=["Purity conforms to USP monograph."],
        risk_factors=[],
        business_impact=["Safe for immediate formulation."],
        recommended_actions=["Authorize batch intake."],
        decision_explanation="Deterministic score reflects strong supplier reliability.",
        kimi_status=KimiStatus.SUCCESS
    )

    with patch("app.api.routes.batches.kimi_service.generate_explanation", return_value=mock_analysis):
        response = client.post(f"/api/batches/{sample_batch.id}/predict-risk")

    assert response.status_code == 200
    data = response.json()

    assert data["batch_id"] == sample_batch.id
    assert "risk_prediction" in data
    assert "kimi_analysis" in data
    assert data["risk_prediction"]["risk_score"] >= 0.0
    assert data["risk_prediction"]["risk_level"] in ["LOW", "MEDIUM", "HIGH", "CRITICAL"]
    assert data["kimi_analysis"]["summary"] == mock_analysis.summary

    # Verify intelligence table updated
    intel = db_session.query(BatchIntelligence).filter(BatchIntelligence.batch_id == sample_batch.id).first()
    assert intel is not None
    assert intel.ml_prediction is not None
    assert intel.kimi_analysis is not None


def test_predict_risk_endpoint_graceful_when_kimi_fails(client, db_session, sample_batch):
    from app.schemas.kimi import KimiAnalysisResult, KimiStatus
    mock_failed_analysis = KimiAnalysisResult(
        summary="Fallback summary when Kimi is unreachable.",
        key_findings=[],
        risk_factors=[],
        business_impact=[],
        recommended_actions=["Manual QA review."],
        decision_explanation="Deterministic rules evaluated because external API failed.",
        kimi_status=KimiStatus.FAILED,
        error_message="External Kimi service unreachable"
    )

    with patch("app.api.routes.batches.kimi_service.generate_explanation", return_value=mock_failed_analysis):
        response = client.post(f"/api/batches/{sample_batch.id}/predict-risk")

    # MUST NOT fail or return 500!
    assert response.status_code == 200
    data = response.json()

    # ML prediction succeeds
    assert "risk_prediction" in data
    assert data["risk_prediction"]["risk_score"] >= 0.0
    # Kimi status is marked as FAILED
    assert data["kimi_analysis"]["kimi_status"] == "FAILED"


def test_process_batch_not_found(client):
    response = client.post("/api/batches/999999/process")
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


def test_predict_risk_not_found(client):
    response = client.post("/api/batches/999999/predict-risk")
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()
