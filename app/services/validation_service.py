import datetime
import logging
import re
from typing import Dict, Any, List, Optional

from app.schemas.validation import (
    CheckStatus,
    OverallValidationStatus,
    ValidationCheckItem,
    ValidationResult,
)
from app.models.batch import Batch
from app.models.raw_material import RawMaterial
from app.models.vendor import Vendor
from app.schemas.document import DocumentProcessResult, DocumentType

logger = logging.getLogger(__name__)


class BatchValidationService:
    """
    Developer 2 Validation Service.
    Validates batch parameters, documentation completeness, COA lab tests,
    GMP certificate validity, SDS storage specs, and traceability.

    NOTE: Thresholds and requirements are configurable per company and material
    specifications in the database, not universal statutory values.
    """

    def validate_batch(
        self,
        batch: Batch,
        material: RawMaterial,
        vendor: Optional[Vendor],
        processed_docs: List[DocumentProcessResult],
        current_date: Optional[datetime.date] = None,
    ) -> ValidationResult:
        if current_date is None:
            current_date = datetime.date.today()

        checks: List[ValidationCheckItem] = []
        missing_info: List[str] = []
        warnings: List[str] = []

        # Map processed documents by type
        docs_by_type: Dict[str, List[DocumentProcessResult]] = {}
        for doc in processed_docs:
            dtype = doc.document_type.value if hasattr(doc.document_type, "value") else str(doc.document_type)
            docs_by_type.setdefault(dtype, []).append(doc)

        coa_docs = docs_by_type.get(DocumentType.COA.value, [])
        sds_docs = docs_by_type.get(DocumentType.SDS.value, [])
        gmp_docs = docs_by_type.get(DocumentType.GMP.value, [])

        # ---------------------------------------------------------
        # 1. Documentation Completeness
        # ---------------------------------------------------------
        req_types = [
            (DocumentType.COA.value, "Certificate of Analysis (COA)"),
            (DocumentType.SDS.value, "Safety Data Sheet (SDS)"),
            (DocumentType.GMP.value, "GMP Certificate"),
        ]
        for dtype, dname in req_types:
            if dtype in docs_by_type and len(docs_by_type[dtype]) > 0:
                checks.append(
                    ValidationCheckItem(
                        name=f"document_present_{dtype.lower()}",
                        status=CheckStatus.PASS,
                        expected=f"{dname} uploaded",
                        actual="Present",
                        reason=f"Mandatory document {dname} is present."
                    )
                )
            else:
                checks.append(
                    ValidationCheckItem(
                        name=f"document_present_{dtype.lower()}",
                        status=CheckStatus.FAIL,
                        expected=f"{dname} uploaded",
                        actual="Missing",
                        reason=f"Mandatory document {dname} was not provided."
                    )
                )
                missing_info.append(f"Missing {dname}")

        # ---------------------------------------------------------
        # 2. COA Parameter Validation against Material Specifications
        # ---------------------------------------------------------
        if coa_docs:
            primary_coa = coa_docs[0]
            coa_data = primary_coa.extracted_data

            # 2.1 Batch Number Match
            coa_batch_no = coa_data.get("batch_number")
            if coa_batch_no:
                if str(coa_batch_no).strip().lower() == str(batch.batch_number).strip().lower():
                    checks.append(
                        ValidationCheckItem(
                            name="batch_number_traceability",
                            status=CheckStatus.PASS,
                            expected=f"Batch {batch.batch_number}",
                            actual=str(coa_batch_no),
                            reason="COA batch number matches the system batch record."
                        )
                    )
                else:
                    checks.append(
                        ValidationCheckItem(
                            name="batch_number_traceability",
                            status=CheckStatus.FAIL,
                            expected=f"Batch {batch.batch_number}",
                            actual=str(coa_batch_no),
                            reason="COA batch number does NOT match the system batch record."
                        )
                    )
            else:
                checks.append(
                    ValidationCheckItem(
                        name="batch_number_traceability",
                        status=CheckStatus.NEEDS_REVIEW,
                        expected=f"Batch {batch.batch_number}",
                        actual="MISSING in COA",
                        reason="Batch number could not be extracted from COA."
                    )
                )
                missing_info.append("COA batch number")

            # 2.2 Purity (Assay)
            actual_purity = coa_data.get("purity")
            expected_purity = material.purity_min if material else 99.0
            if actual_purity is not None:
                if actual_purity >= expected_purity:
                    checks.append(
                        ValidationCheckItem(
                            name="purity",
                            status=CheckStatus.PASS,
                            expected=f">={expected_purity}%",
                            actual=actual_purity,
                            reason=f"Actual purity {actual_purity}% satisfies specification requirement of >={expected_purity}%."
                        )
                    )
                else:
                    checks.append(
                        ValidationCheckItem(
                            name="purity",
                            status=CheckStatus.FAIL,
                            expected=f">={expected_purity}%",
                            actual=actual_purity,
                            reason=f"Actual purity {actual_purity}% is below specification threshold of >={expected_purity}%."
                        )
                    )
            else:
                checks.append(
                    ValidationCheckItem(
                        name="purity",
                        status=CheckStatus.NEEDS_REVIEW,
                        expected=f">={expected_purity}%",
                        actual="MISSING",
                        reason="Assay/purity figure missing from COA."
                    )
                )
                missing_info.append("COA purity value")

            # 2.3 Moisture (Water Content)
            actual_moisture = coa_data.get("moisture")
            expected_moisture = material.moisture_max if material else 1.0
            if actual_moisture is not None:
                if actual_moisture <= expected_moisture:
                    checks.append(
                        ValidationCheckItem(
                            name="moisture",
                            status=CheckStatus.PASS,
                            expected=f"<={expected_moisture}%",
                            actual=actual_moisture,
                            reason=f"Actual moisture {actual_moisture}% meets limit of <={expected_moisture}%."
                        )
                    )
                else:
                    checks.append(
                        ValidationCheckItem(
                            name="moisture",
                            status=CheckStatus.FAIL,
                            expected=f"<={expected_moisture}%",
                            actual=actual_moisture,
                            reason=f"Actual moisture {actual_moisture}% exceeds maximum limit of <={expected_moisture}%."
                        )
                    )
            else:
                checks.append(
                    ValidationCheckItem(
                        name="moisture",
                        status=CheckStatus.NEEDS_REVIEW,
                        expected=f"<={expected_moisture}%",
                        actual="MISSING",
                        reason="Moisture content missing from COA."
                    )
                )
                missing_info.append("COA moisture value")

            # 2.4 Heavy Metals Contaminant Limit
            actual_hm = coa_data.get("heavy_metals")
            expected_hm = material.heavy_metals_max_ppm if material else 10.0
            if actual_hm is not None:
                if actual_hm <= expected_hm:
                    checks.append(
                        ValidationCheckItem(
                            name="heavy_metals",
                            status=CheckStatus.PASS,
                            expected=f"<={expected_hm} ppm",
                            actual=actual_hm,
                            reason=f"Heavy metals content {actual_hm} ppm is within safety limit of <={expected_hm} ppm."
                        )
                    )
                else:
                    checks.append(
                        ValidationCheckItem(
                            name="heavy_metals",
                            status=CheckStatus.FAIL,
                            expected=f"<={expected_hm} ppm",
                            actual=actual_hm,
                            reason=f"Heavy metals {actual_hm} ppm exceeds configured threshold of <={expected_hm} ppm."
                        )
                    )
            else:
                checks.append(
                    ValidationCheckItem(
                        name="heavy_metals",
                        status=CheckStatus.NEEDS_REVIEW,
                        expected=f"<={expected_hm} ppm",
                        actual="MISSING",
                        reason="Heavy metals analysis missing from COA."
                    )
                )
                missing_info.append("Heavy metals data")

            # 2.5 Microbial Parameters
            microbial = coa_data.get("microbial_parameters") or {}
            expected_microbial = material.microbial_limit_cfu_g if material else 100.0
            tamc = microbial.get("TAMC_cfu_g")
            if tamc is not None:
                if tamc <= expected_microbial:
                    checks.append(
                        ValidationCheckItem(
                            name="microbial_tamc",
                            status=CheckStatus.PASS,
                            expected=f"<={expected_microbial} CFU/g",
                            actual=tamc,
                            reason=f"Total Aerobic Microbial Count {tamc} CFU/g is within limit of <={expected_microbial} CFU/g."
                        )
                    )
                else:
                    checks.append(
                        ValidationCheckItem(
                            name="microbial_tamc",
                            status=CheckStatus.FAIL,
                            expected=f"<={expected_microbial} CFU/g",
                            actual=tamc,
                            reason=f"Total Aerobic Microbial Count {tamc} CFU/g exceeds limit of <={expected_microbial} CFU/g."
                        )
                    )

            # 2.6 Shelf Life / Expiry Traceability
            exp_str = coa_data.get("expiry_date")
            mfg_str = coa_data.get("manufacturing_date")
            if exp_str:
                try:
                    exp_parsed = self._parse_date(exp_str)
                    if exp_parsed:
                        if exp_parsed >= current_date:
                            checks.append(
                                ValidationCheckItem(
                                    name="material_shelf_life",
                                    status=CheckStatus.PASS,
                                    expected=f"Expiry >= {current_date.isoformat()}",
                                    actual=exp_parsed.isoformat(),
                                    reason=f"Batch material remains unexpired through {exp_parsed.isoformat()}."
                                )
                            )
                        else:
                            checks.append(
                                ValidationCheckItem(
                                    name="material_shelf_life",
                                    status=CheckStatus.FAIL,
                                    expected=f"Expiry >= {current_date.isoformat()}",
                                    actual=exp_parsed.isoformat(),
                                    reason=f"Batch material expired on {exp_parsed.isoformat()}."
                                )
                            )
                except Exception as e:
                    warnings.append(f"Could not parse COA expiry date '{exp_str}': {str(e)}")

        # ---------------------------------------------------------
        # 3. GMP Certificate Validation & Expiry
        # ---------------------------------------------------------
        if gmp_docs:
            primary_gmp = gmp_docs[0]
            gmp_data = primary_gmp.extracted_data
            valid_until_str = gmp_data.get("valid_until")

            if valid_until_str:
                valid_until = self._parse_date(valid_until_str)
                if valid_until:
                    if valid_until >= current_date:
                        checks.append(
                            ValidationCheckItem(
                                name="gmp_certificate_validity",
                                status=CheckStatus.PASS,
                                expected=f"Valid until >= {current_date.isoformat()}",
                                actual=valid_until.isoformat(),
                                reason=f"Vendor GMP certification is valid until {valid_until.isoformat()}."
                            )
                        )
                    else:
                        checks.append(
                            ValidationCheckItem(
                                name="gmp_certificate_validity",
                                status=CheckStatus.FAIL,
                                expected=f"Valid until >= {current_date.isoformat()}",
                                actual=valid_until.isoformat(),
                                reason=f"Vendor GMP certificate expired on {valid_until.isoformat()}."
                            )
                        )
                else:
                    checks.append(
                        ValidationCheckItem(
                            name="gmp_certificate_validity",
                            status=CheckStatus.NEEDS_REVIEW,
                            expected="Valid unexpired certificate date",
                            actual=valid_until_str,
                            reason="Could not reliably parse GMP validity date."
                        )
                    )
            else:
                checks.append(
                    ValidationCheckItem(
                        name="gmp_certificate_validity",
                        status=CheckStatus.NEEDS_REVIEW,
                        expected="Unexpired valid date",
                        actual="MISSING",
                        reason="GMP certificate is missing expiry date specification."
                    )
                )

        # ---------------------------------------------------------
        # 4. SDS & Storage Requirements Validation
        # ---------------------------------------------------------
        if sds_docs:
            sds_data = sds_docs[0].extracted_data
            storage_req = sds_data.get("storage_requirements")
            if storage_req:
                checks.append(
                    ValidationCheckItem(
                        name="storage_requirements_defined",
                        status=CheckStatus.PASS,
                        expected="Storage requirements specified in SDS",
                        actual=storage_req[:80] + ("..." if len(storage_req) > 80 else ""),
                        reason="SDS explicitly defines storage and handling conditions."
                    )
                )
            else:
                checks.append(
                    ValidationCheckItem(
                        name="storage_requirements_defined",
                        status=CheckStatus.NEEDS_REVIEW,
                        expected="Storage conditions specified",
                        actual="MISSING",
                        reason="Storage section not identified in SDS."
                    )
                )

        # ---------------------------------------------------------
        # 5. Overall Status Aggregation
        # ---------------------------------------------------------
        has_fail = any(c.status == CheckStatus.FAIL for c in checks)
        has_needs_review = any(c.status in (CheckStatus.NEEDS_REVIEW, CheckStatus.MISSING) for c in checks)

        if has_fail:
            overall_status = OverallValidationStatus.FAIL
        elif has_needs_review or len(missing_info) > 0:
            overall_status = OverallValidationStatus.NEEDS_REVIEW
        else:
            overall_status = OverallValidationStatus.PASS

        return ValidationResult(
            overall_status=overall_status,
            checks=checks,
            missing_information=missing_info,
            warnings=warnings,
        )

    def _parse_date(self, date_str: str) -> Optional[datetime.date]:
        """Safely parses dates in various common formats."""
        cleaned = re.sub(r"[^\d/\-]", "", date_str.strip())
        formats = [
            "%Y-%m-%d", "%Y/%m/%d",
            "%d-%m-%Y", "%d/%m/%Y",
            "%m-%d-%Y", "%m/%d/%Y",
            "%Y-%m", "%m/%Y"
        ]
        for fmt in formats:
            try:
                dt = datetime.datetime.strptime(cleaned, fmt)
                return dt.date()
            except ValueError:
                continue
        return None


# Singleton instance
validation_service = BatchValidationService()
