"""Configurable supplier-batch decision rules."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping


APPROVED = "APPROVED"
REJECTED = "REJECTED"
NEEDS_REVIEW = "NEEDS_REVIEW"


@dataclass(frozen=True)
class DecisionResult:
    decision: str
    reason: str
    recommended_actions: list[str]


def _passed(value: Any) -> bool | None:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        normalized = value.upper()
        if normalized in {"PASS", "PASSED", "SUCCESS"}:
            return True
        if normalized in {"FAIL", "FAILED"}:
            return False
    if isinstance(value, Mapping):
        result = value.get("passed")
        if isinstance(result, bool):
            return result
        status = value.get("status")
        return _passed(status) if status is not None else None
    return None


def evaluate_decision(
    *,
    validation_results: Mapping[str, Any],
    risk_score: float,
    risk_level: str,
    document_completeness: float | Mapping[str, Any],
    material_specification: bool | Mapping[str, Any] | None,
    company_thresholds: Mapping[str, Any],
) -> DecisionResult:
    """Evaluate a batch using thresholds supplied by the owning company.

    Threshold defaults are operational examples only; callers should load the
    company's approved configuration and pass it in explicitly.
    """
    if not 0 <= risk_score <= 100:
        raise ValueError("risk_score must be between 0 and 100")

    actions: list[str] = []
    review_reasons: list[str] = []

    specification_passed = _passed(material_specification)
    if specification_passed is False:
        return DecisionResult(
            REJECTED,
            "The material specification did not pass the configured mandatory check.",
            ["Resolve the specification mismatch and submit the batch for reassessment."],
        )
    if specification_passed is None:
        review_reasons.append("The material specification result is missing or uncertain.")
        actions.append("Complete and verify the material specification check.")

    mandatory_checks = company_thresholds.get("mandatory_validation_checks", [])
    if not isinstance(mandatory_checks, (list, tuple)):
        raise ValueError("mandatory_validation_checks must be a list")
    for check_name in mandatory_checks:
        check_result = _passed(validation_results.get(check_name))
        if check_result is False:
            return DecisionResult(
                REJECTED,
                f"Mandatory validation check '{check_name}' failed.",
                [f"Resolve the '{check_name}' validation failure and resubmit the batch."],
            )
        if check_result is None:
            review_reasons.append(f"Mandatory validation check '{check_name}' is incomplete.")
            actions.append(f"Complete the '{check_name}' validation check.")

    if isinstance(document_completeness, Mapping):
        completeness = document_completeness.get("completeness", 1.0)
        missing_documents = document_completeness.get("missing_documents", [])
        critical_missing = document_completeness.get("critical_missing", [])
    else:
        completeness = document_completeness
        missing_documents = []
        critical_missing = []
    if not isinstance(completeness, (int, float)) or not 0 <= completeness <= 1:
        raise ValueError("document completeness must be a number between 0 and 1")
    if not isinstance(missing_documents, (list, tuple)) or not isinstance(
        critical_missing, (list, tuple)
    ):
        raise ValueError("missing document fields must be lists")

    configured_critical = company_thresholds.get("critical_document_types", [])
    if not isinstance(configured_critical, (list, tuple)):
        raise ValueError("critical_document_types must be a list")
    critical_missing = set(critical_missing) | (
        set(missing_documents) & set(configured_critical)
    )
    if critical_missing:
        missing = ", ".join(sorted(str(item) for item in critical_missing))
        return DecisionResult(
            NEEDS_REVIEW,
            f"Critical documentation is missing: {missing}.",
            ["Request the missing critical documents and complete manual review."],
        )

    minimum_completeness = company_thresholds.get("minimum_document_completeness", 1.0)
    if not isinstance(minimum_completeness, (int, float)) or not 0 <= minimum_completeness <= 1:
        raise ValueError("minimum_document_completeness must be between 0 and 1")
    if completeness < minimum_completeness or missing_documents:
        review_reasons.append("Required documentation is incomplete.")
        actions.append("Request outstanding documentation and verify completeness.")

    for check_name, result in validation_results.items():
        if _passed(result) is False and check_name not in mandatory_checks:
            review_reasons.append(f"Validation check '{check_name}' did not pass.")
            actions.append(f"Review the '{check_name}' validation result.")

    max_approval_risk = company_thresholds.get("max_approval_risk_score", 25)
    if not isinstance(max_approval_risk, (int, float)) or not 0 <= max_approval_risk <= 100:
        raise ValueError("max_approval_risk_score must be between 0 and 100")
    allowed_levels = company_thresholds.get("approval_risk_levels", ["LOW"])
    if not isinstance(allowed_levels, (list, tuple)):
        raise ValueError("approval_risk_levels must be a list")
    if risk_score > max_approval_risk or risk_level.upper() not in {
        str(level).upper() for level in allowed_levels
    }:
        review_reasons.append("Risk is outside the company's automatic-approval threshold.")
        actions.append("Review the risk assessment against the company's configured threshold.")

    if review_reasons:
        return DecisionResult(NEEDS_REVIEW, " ".join(review_reasons), list(dict.fromkeys(actions)))

    return DecisionResult(
        APPROVED,
        "Configured mandatory checks passed and the batch is within the company's approval thresholds.",
        [],
    )
