import pytest

from app.services.decision_service import APPROVED, NEEDS_REVIEW, REJECTED, evaluate_decision


def evaluate(**overrides):
    values = {
        "validation_results": {"coa": True},
        "risk_score": 18,
        "risk_level": "LOW",
        "document_completeness": 1.0,
        "material_specification": True,
        "company_thresholds": {
            "mandatory_validation_checks": ["coa"],
            "critical_document_types": ["COA"],
            "max_approval_risk_score": 25,
            "approval_risk_levels": ["LOW"],
        },
    }
    values.update(overrides)
    return evaluate_decision(**values)


def test_approves_when_checks_and_company_thresholds_pass():
    result = evaluate()

    assert result.decision == APPROVED
    assert result.recommended_actions == []


def test_rejects_failed_material_specification():
    assert evaluate(material_specification=False).decision == REJECTED


def test_rejects_failed_configured_mandatory_check():
    result = evaluate(validation_results={"coa": False})

    assert result.decision == REJECTED
    assert "coa" in result.reason


def test_requires_review_for_missing_critical_document():
    result = evaluate(
        document_completeness={
            "completeness": 0.8,
            "missing_documents": ["COA"],
        }
    )

    assert result.decision == NEEDS_REVIEW
    assert "COA" in result.reason


def test_requires_review_for_risk_above_company_threshold():
    assert evaluate(risk_score=26).decision == NEEDS_REVIEW


def test_requires_review_when_specification_result_is_unknown():
    assert evaluate(material_specification=None).decision == NEEDS_REVIEW


def test_rejects_invalid_risk_score():
    with pytest.raises(ValueError, match="risk_score"):
        evaluate(risk_score=101)
