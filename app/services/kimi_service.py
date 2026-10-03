import json
import logging
import re
from typing import Dict, Any, List, Optional
import httpx

from app.core.config import settings
from app.schemas.kimi import KimiAnalysisResult, KimiStatus
from app.schemas.validation import ValidationResult
from app.schemas.vendor_history import VendorHistoryMetrics
from app.schemas.prediction import RiskPredictionResult
from app.models.batch import Batch
from app.models.raw_material import RawMaterial
from app.models.vendor import Vendor

logger = logging.getLogger(__name__)


SYSTEM_PROMPT = """You are VendorIQ's Quality Auditor Reasoning Engine.
Your purpose is ONLY to analyze supplier qualification data, batch test results, validation outputs, and deterministic ML predictions to provide clear, actionable explanations.

STRICT CONSTRAINTS:
1. You MUST NOT modify, recalculate, or override the ML risk score or risk level.
2. You MUST NOT override deterministic validation check failures.
3. You MUST NOT invent, assume, or hallucinate missing chemical, batch, or supplier data.
4. You MUST NOT make unsupported regulatory claims.
5. The final business approval decision belongs to the human QA Lead / Decision Engine; your role is explanatory synthesis only.

Output format MUST be valid raw JSON with the following exact keys:
{
    "summary": "Concise 1-2 sentence executive overview of the batch qualification status.",
    "key_findings": ["Bullet point 1", "Bullet point 2"],
    "risk_factors": ["Detected risk factor 1", "Detected risk factor 2"],
    "business_impact": ["Operational or supply chain impact 1", "Financial/regulatory exposure 2"],
    "recommended_actions": ["Specific step 1 for QA team", "Specific step 2"],
    "decision_explanation": "Comprehensive reasoning synthesizing why the ML model scored this batch at its assigned risk level and highlighting any validation anomalies."
}
"""


class KimiReasoningService:
    """
    Developer 2 Kimi K3 Reasoning Integration.
    Calls Kimi K3 (Moonshot API) to generate human-readable technical synthesis
    for batch qualification.

    FAILURE RESILIENCE:
    - If Kimi is unreachable, times out, returns HTTP errors, or returns malformed JSON:
      It NEVER crashes the pipeline.
      Returns a structured KimiAnalysisResult with kimi_status = FAILED.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        api_base: Optional[str] = None,
        model: Optional[str] = None,
        timeout_seconds: Optional[float] = None,
    ):
        self.api_key = api_key or settings.KIMI_API_KEY
        self.api_base = (api_base or settings.KIMI_API_BASE).rstrip("/")
        self.model = model or settings.KIMI_MODEL
        self.timeout = timeout_seconds or settings.KIMI_TIMEOUT_SECONDS

    def build_payload(
        self,
        vendor: Vendor,
        material: RawMaterial,
        batch: Batch,
        validation_result: Optional[ValidationResult],
        vendor_history: Optional[VendorHistoryMetrics],
        prediction: RiskPredictionResult,
    ) -> Dict[str, Any]:
        """Assembles structured technical context for Kimi K3."""
        return {
            "vendor_information": {
                "id": vendor.id if vendor else None,
                "name": vendor.name if vendor else "Unknown",
                "tier": vendor.tier if vendor else None,
                "certification_status": vendor.certification_status if vendor else None,
                "delivery_reliability": vendor.delivery_reliability if vendor else None,
            },
            "material_information": {
                "id": material.id if material else None,
                "name": material.name if material else "Unknown",
                "code": material.code if material else None,
                "purity_min": material.purity_min if material else None,
                "moisture_max": material.moisture_max if material else None,
                "heavy_metals_max_ppm": material.heavy_metals_max_ppm if material else None,
                "storage_conditions": material.storage_conditions if material else None,
            },
            "batch_information": {
                "id": batch.id if batch else None,
                "batch_number": batch.batch_number if batch else None,
                "quantity": batch.quantity if batch else None,
                "unit": batch.unit if batch else None,
                "manufacturing_date": str(batch.manufacturing_date) if batch and batch.manufacturing_date else None,
                "expiry_date": str(batch.expiry_date) if batch and batch.expiry_date else None,
            },
            "validation_results": validation_result.model_dump() if validation_result else None,
            "vendor_history": vendor_history.model_dump() if vendor_history else None,
            "ml_prediction": {
                "risk_score": prediction.risk_score,
                "risk_probability": prediction.risk_probability,
                "risk_level": prediction.risk_level.value if hasattr(prediction.risk_level, "value") else str(prediction.risk_level),
                "risk_factors": prediction.risk_factors,
            },
        }

    def generate_explanation(
        self,
        vendor: Vendor,
        material: RawMaterial,
        batch: Batch,
        validation_result: Optional[ValidationResult],
        vendor_history: Optional[VendorHistoryMetrics],
        prediction: RiskPredictionResult,
    ) -> KimiAnalysisResult:
        """
        Invokes Kimi K3 API to synthesize risk analysis and explanations.
        Guaranteed to never raise an unhandled exception to protect the batch pipeline.
        """
        # Check if API key is configured
        if not self.api_key or self.api_key.strip() in ("", "YOUR_KIMI_API_KEY", "dummy"):
            logger.warning("KIMI_API_KEY is not set or empty. Returning graceful degradation fallback.")
            return self._build_offline_fallback(
                validation_result=validation_result,
                vendor_history=vendor_history,
                prediction=prediction,
                status=KimiStatus.FAILED,
                error_message="KIMI_API_KEY is not configured. Reasoning layer defaulted to deterministic rules."
            )

        context_payload = self.build_payload(
            vendor=vendor,
            material=material,
            batch=batch,
            validation_result=validation_result,
            vendor_history=vendor_history,
            prediction=prediction,
        )

        user_content = (
            "Analyze the following VendorIQ supplier qualification batch dossier and provide structured audit findings:\n\n"
            + json.dumps(context_payload, indent=2)
        )

        url = f"{self.api_base}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        body = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_content}
            ],
            "temperature": 0.2,
        }

        try:
            with httpx.Client(timeout=self.timeout) as client:
                response = client.post(url, headers=headers, json=body)
                response.raise_for_status()
                data = response.json()

            raw_text = data["choices"][0]["message"]["content"]
            parsed_result = self._parse_json_response(raw_text)
            
            return KimiAnalysisResult(
                summary=parsed_result.get("summary", "Analysis completed."),
                key_findings=parsed_result.get("key_findings", []),
                risk_factors=parsed_result.get("risk_factors", prediction.risk_factors),
                business_impact=parsed_result.get("business_impact", []),
                recommended_actions=parsed_result.get("recommended_actions", []),
                decision_explanation=parsed_result.get("decision_explanation", "Deterministic rules evaluated."),
                kimi_status=KimiStatus.SUCCESS,
            )

        except httpx.TimeoutException as e:
            logger.error(f"Kimi API request timed out after {self.timeout}s: {e}")
            return self._build_offline_fallback(
                validation_result, vendor_history, prediction,
                status=KimiStatus.FAILED,
                error_message=f"Kimi API timed out after {self.timeout}s."
            )
        except httpx.HTTPStatusError as e:
            logger.error(f"Kimi API HTTP error {e.response.status_code}: {e.response.text}")
            return self._build_offline_fallback(
                validation_result, vendor_history, prediction,
                status=KimiStatus.FAILED,
                error_message=f"Kimi API returned HTTP {e.response.status_code}."
            )
        except Exception as e:
            logger.exception(f"Unexpected error in Kimi reasoning service: {e}")
            return self._build_offline_fallback(
                validation_result, vendor_history, prediction,
                status=KimiStatus.FAILED,
                error_message=f"Kimi invocation error: {str(e)}"
            )

    def _parse_json_response(self, text: str) -> Dict[str, Any]:
        """Safely parses JSON from LLM output, extracting from markdown fence if needed."""
        cleaned = text.strip()
        if "```" in cleaned:
            match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", cleaned, re.DOTALL)
            if match:
                cleaned = match.group(1)
        
        parsed = None
        try:
            parsed = json.loads(cleaned)
        except json.JSONDecodeError:
            # Fallback regex search for outer braces
            match = re.search(r"(\{.*\})", cleaned, re.DOTALL)
            if match:
                parsed = json.loads(match.group(1))

        if not isinstance(parsed, dict) or not any(k in parsed for k in ("summary", "decision_explanation", "key_findings")):
            raise ValueError(f"Unable to parse structured JSON from response or missing required keys: {text[:200]}")

        return parsed

    def _build_offline_fallback(
        self,
        validation_result: Optional[ValidationResult],
        vendor_history: Optional[VendorHistoryMetrics],
        prediction: RiskPredictionResult,
        status: KimiStatus = KimiStatus.FAILED,
        error_message: Optional[str] = None
    ) -> KimiAnalysisResult:
        """
        Deterministic, rule-based reasoning fallback when Kimi is unavailable.
        Ensures the decision engine receives a complete, coherent explanation package.
        """
        val_status = validation_result.overall_status if validation_result else "UNKNOWN"
        summary = (
            f"Batch evaluated with ML Risk Score {prediction.risk_score}/100 "
            f"({prediction.risk_level.value}) and validation status '{val_status}'."
        )

        key_findings = []
        if validation_result:
            key_findings.append(f"Validation completed with overall status: {val_status}.")
            for c in validation_result.checks:
                if c.status != "PASS":
                    key_findings.append(f"Check '{c.name}': {c.status} ({c.reason})")

        if vendor_history:
            key_findings.append(
                f"Historical vendor performance: {vendor_history.previous_batches} prior batches, "
                f"approval rate {vendor_history.approval_rate * 100:.1f}%."
            )

        recommended_actions = []
        if prediction.risk_level.value in ("HIGH", "CRITICAL"):
            recommended_actions.append("Escalate batch dossier to Senior QA Lead for secondary physical inspection.")
        if validation_result and validation_result.missing_information:
            recommended_actions.append(f"Request missing documentation from supplier: {', '.join(validation_result.missing_information)}.")
        if not recommended_actions:
            recommended_actions.append("Proceed with standard quality gate workflow.")

        return KimiAnalysisResult(
            summary=summary,
            key_findings=key_findings,
            risk_factors=prediction.risk_factors,
            business_impact=[
                f"Risk rating: {prediction.risk_level.value}.",
                "Supply chain continuity preserved without pipeline interruption."
            ],
            recommended_actions=recommended_actions,
            decision_explanation=(
                f"The ML model assigned a risk score of {prediction.risk_score} based on the supplier's "
                f"reliability metrics, documentation integrity, and analytical test results. "
                + (f"Note: {error_message}" if error_message else "")
            ),
            kimi_status=status,
            error_message=error_message
        )


kimi_service = KimiReasoningService()
