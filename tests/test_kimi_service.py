import json
import pytest
import httpx
from unittest.mock import patch, MagicMock

from app.services.kimi_service import KimiReasoningService
from app.schemas.kimi import KimiStatus
from app.schemas.prediction import RiskPredictionResult, RiskLevel
from app.schemas.validation import ValidationResult, OverallValidationStatus
from app.schemas.vendor_history import VendorHistoryMetrics
from app.models.batch import Batch
from app.models.raw_material import RawMaterial
from app.models.vendor import Vendor


@pytest.fixture
def dummy_prediction():
    return RiskPredictionResult(
        risk_score=18.0,
        risk_probability=0.18,
        risk_level=RiskLevel.LOW,
        risk_factors=["Slight purity variance"]
    )


@pytest.fixture
def dummy_validation():
    return ValidationResult(
        overall_status=OverallValidationStatus.PASS,
        checks=[],
        missing_information=[],
        warnings=[]
    )


@pytest.fixture
def dummy_history():
    return VendorHistoryMetrics(
        vendor_id=1,
        previous_batches=10,
        approval_rate=0.95,
        rejection_rate=0.05,
    )


def test_kimi_success_response(dummy_prediction, dummy_validation, dummy_history):
    service = KimiReasoningService(api_key="sk-test-valid-key")

    mock_llm_payload = {
        "summary": "Batch B-001 meets all quality and analytical purity requirements.",
        "key_findings": [
            "Assay purity measured at 99.4%, exceeding 99.0% specification.",
            "All mandatory GMP and SDS documentation verified."
        ],
        "risk_factors": ["Slight purity variance"],
        "business_impact": ["Standard quality clearance.", "Low supply chain disruption risk."],
        "recommended_actions": ["Approve batch for production release."],
        "decision_explanation": "Low risk rating assigned due to high supplier approval rate and valid GMP certificate."
    }

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "choices": [
            {"message": {"content": json.dumps(mock_llm_payload)}}
        ]
    }

    vendor = Vendor(id=1, name="Acme Chem")
    material = RawMaterial(id=1, name="Paracetamol")
    batch = Batch(id=1, batch_number="B-001")

    with patch("httpx.Client.post", return_value=mock_response):
        result = service.generate_explanation(
            vendor=vendor,
            material=material,
            batch=batch,
            validation_result=dummy_validation,
            vendor_history=dummy_history,
            prediction=dummy_prediction,
        )

    assert result.kimi_status == KimiStatus.SUCCESS
    assert result.summary == mock_llm_payload["summary"]
    assert len(result.key_findings) == 2
    assert "Low risk rating" in result.decision_explanation


def test_kimi_timeout_failure_graceful_fallback(dummy_prediction, dummy_validation, dummy_history):
    service = KimiReasoningService(api_key="sk-test-key", timeout_seconds=1.0)

    vendor = Vendor(id=1, name="Acme Chem")
    material = RawMaterial(id=1, name="Paracetamol")
    batch = Batch(id=1, batch_number="B-001")

    with patch("httpx.Client.post", side_effect=httpx.TimeoutException("Connection timed out")):
        result = service.generate_explanation(
            vendor=vendor,
            material=material,
            batch=batch,
            validation_result=dummy_validation,
            vendor_history=dummy_history,
            prediction=dummy_prediction,
        )

    # Pipeline does NOT crash; returns status FAILED with structured fallback
    assert result.kimi_status == KimiStatus.FAILED
    assert "timed out" in result.error_message
    assert result.summary is not None
    assert len(result.recommended_actions) > 0


def test_kimi_http_500_error_handling(dummy_prediction, dummy_validation, dummy_history):
    service = KimiReasoningService(api_key="sk-test-key")

    vendor = Vendor(id=1, name="Acme Chem")
    material = RawMaterial(id=1, name="Paracetamol")
    batch = Batch(id=1, batch_number="B-001")

    mock_response = MagicMock()
    mock_response.status_code = 500
    mock_response.text = "Internal Server Error"
    http_error = httpx.HTTPStatusError("500 Server Error", request=MagicMock(), response=mock_response)

    with patch("httpx.Client.post", side_effect=http_error):
        result = service.generate_explanation(
            vendor=vendor,
            material=material,
            batch=batch,
            validation_result=dummy_validation,
            vendor_history=dummy_history,
            prediction=dummy_prediction,
        )

    assert result.kimi_status == KimiStatus.FAILED
    assert "HTTP 500" in result.error_message


def test_kimi_invalid_malformed_response_handling(dummy_prediction, dummy_validation, dummy_history):
    service = KimiReasoningService(api_key="sk-test-key")

    vendor = Vendor(id=1, name="Acme Chem")
    material = RawMaterial(id=1, name="Paracetamol")
    batch = Batch(id=1, batch_number="B-001")

    mock_response = MagicMock()
    mock_response.status_code = 200
    # Malformed non-JSON string returned by LLM
    mock_response.json.return_value = {
        "choices": [
            {"message": {"content": "This is plain text with no valid JSON {} brackets."}}
        ]
    }

    with patch("httpx.Client.post", return_value=mock_response):
        result = service.generate_explanation(
            vendor=vendor,
            material=material,
            batch=batch,
            validation_result=dummy_validation,
            vendor_history=dummy_history,
            prediction=dummy_prediction,
        )

    # Handled gracefully
    assert result.kimi_status == KimiStatus.FAILED


def test_kimi_missing_api_key_returns_fallback_without_network_call(dummy_prediction, dummy_validation, dummy_history):
    # Empty API key
    service = KimiReasoningService(api_key="")

    vendor = Vendor(id=1, name="Acme Chem")
    material = RawMaterial(id=1, name="Paracetamol")
    batch = Batch(id=1, batch_number="B-001")

    with patch("httpx.Client.post") as mock_post:
        result = service.generate_explanation(
            vendor=vendor,
            material=material,
            batch=batch,
            validation_result=dummy_validation,
            vendor_history=dummy_history,
            prediction=dummy_prediction,
        )
        # Ensure post was NOT called
        mock_post.assert_not_called()

    assert result.kimi_status == KimiStatus.FAILED
    assert "KIMI_API_KEY is not configured" in result.error_message
    assert result.summary is not None
