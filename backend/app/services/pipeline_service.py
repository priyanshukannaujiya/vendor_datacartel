"""
Batch Pipeline Service.
Executes the end-to-end qualification and assessment pipeline for a batch:
1. Extracts purity, dates, specs from uploaded PDFs (COA, SDS, GMP)
2. Validates batch against raw material specifications
3. Analyzes historical supplier performance
4. Predicts risk score with ML Random Forest model
5. Generates Kimi AI contextual reasoning summary
6. Automatically evaluates the qualification decision (APPROVED / REJECTED / NEEDS_REVIEW)
7. Updates the supplier's aggregate metrics (approval rate, quality score, risk score)
8. Invalidates the analytics cache so Dashboard immediately reflects genuine data
"""
import logging
from typing import Optional
from sqlalchemy.orm import Session

from app.models.batch import Batch
from app.models.vendor import Vendor
from app.models.raw_material import RawMaterial
from app.models.document import Document
from app.models.intelligence import BatchIntelligence
from app.models.decision import BatchDecision
from app.schemas.document import DocumentType, DocumentProcessResult
from app.services.document_service import DocumentProcessingService
from app.services.validation_service import BatchValidationService
from app.services.vendor_history_service import VendorHistoryService
from app.services.prediction_service import BatchRiskPredictionService
from app.services.kimi_service import KimiReasoningService
from app.services.decision_service import evaluate_decision
from app.services.audit_service import record_audit_event
from app.routers.analytics import invalidate_analytics_cache

logger = logging.getLogger("vendoriq.pipeline")


def run_full_batch_pipeline(db: Session, batch: Batch) -> Batch:
    """Run full automated assessment pipeline on a batch."""
    try:
        doc_svc = DocumentProcessingService()
        val_svc = BatchValidationService()
        hist_svc = VendorHistoryService()
        pred_svc = BatchRiskPredictionService()
        kimi_svc = KimiReasoningService()

        material = db.query(RawMaterial).filter(RawMaterial.id == batch.raw_material_id).first()
        vendor = db.query(Vendor).filter(Vendor.id == batch.vendor_id).first()

        # 1. Collect and process all documents attached to this batch
        batch_docs = db.query(Document).filter(Document.batch_id == batch.id).all()
        proc_docs = []
        for d in batch_docs:
            try:
                dt_e = DocumentType(d.document_type) if d.document_type in DocumentType.__members__ else DocumentType.OTHER
            except Exception:
                dt_e = DocumentType.OTHER

            # If document already has extracted data, construct DocumentProcessResult, otherwise process
            if d.extracted_data and d.processing_status in ["PROCESSED", "EXTRACTED", "COMPLETED"]:
                res = DocumentProcessResult(
                    document_id=d.id,
                    filename=d.file_name,
                    document_type=dt_e,
                    status=d.processing_status,
                    extracted_data=d.extracted_data,
                )
            else:
                res = doc_svc.process_document(d.file_path, d.file_name, dt_e, d.id)
                d.extracted_data = res.extracted_data
                d.processing_status = res.status.value
                db.add(d)

            # Update batch purity if found on COA
            if dt_e == DocumentType.COA and res.extracted_data.get("purity") is not None:
                if batch.purity_reported is None:
                    batch.purity_reported = float(res.extracted_data["purity"])

            proc_docs.append(res)

        # 2. Run deterministic validation against material specification
        val_res = val_svc.validate_batch(batch, material, vendor, proc_docs)

        # 3. Analyze vendor history
        v_hist = hist_svc.analyze_vendor_history(db, batch.vendor_id, batch)

        # 4. Predict ML risk score
        pred_res, feat = pred_svc.predict_risk(batch, material, vendor, val_res, v_hist, batch.purity_reported)

        # 5. Kimi explanation
        kimi_res = kimi_svc.generate_explanation(vendor, material, batch, val_res, v_hist, pred_res)

        # 6. Save BatchIntelligence record
        intel = db.query(BatchIntelligence).filter(BatchIntelligence.batch_id == batch.id).first()
        if not intel:
            intel = BatchIntelligence(batch_id=batch.id)
            db.add(intel)

        intel.validation_result = val_res.model_dump(mode="json")
        intel.vendor_history = v_hist.model_dump(mode="json")
        intel.ml_features = feat
        intel.ml_prediction = pred_res.model_dump(mode="json")
        intel.kimi_analysis = kimi_res.model_dump(mode="json")
        intel.kimi_status = kimi_res.kimi_status.value

        # 7. Evaluate automated qualification decision
        checks = [c.model_dump() if hasattr(c, "model_dump") else c for c in intel.validation_result.get("checks", [])]
        spec_check = next((c for c in checks if c.get("name") in ["specification_match", "material_specification", "purity_within_spec"]), None)
        material_spec_passed = spec_check.get("status") in ["PASS", "PASSED"] if spec_check else True

        doc_checks = [c for c in checks if "document_present" in c.get("name", "").lower()]
        if doc_checks:
            doc_passed = sum(1 for c in doc_checks if c.get("status") in ["PASS", "PASSED"])
            completeness = doc_passed / len(doc_checks)
        else:
            completeness = 1.0 if proc_docs else 0.5

        doc_completeness_map = {
            "completeness": completeness,
            "missing_documents": [c.get("name", "") for c in checks if c.get("status") in ["FAIL", "MISSING"] and "document" in c.get("name", "").lower()],
        }

        risk_sc = float(pred_res.risk_score)
        risk_lv = pred_res.risk_level.value if hasattr(pred_res.risk_level, "value") else str(pred_res.risk_level)

        decision_res = evaluate_decision(
            validation_results={c.get("name", f"check_{i}"): c.get("status") for i, c in enumerate(checks)},
            risk_score=risk_sc,
            risk_level=risk_lv,
            document_completeness=doc_completeness_map,
            material_specification=material_spec_passed,
            company_thresholds={},
        )

        batch.status = decision_res.decision

        # Persist BatchDecision
        dec = db.query(BatchDecision).filter(BatchDecision.batch_id == batch.id).first()
        if not dec:
            dec = BatchDecision(
                batch_id=batch.id,
                company_id=batch.company_id,
                decision=decision_res.decision,
                risk_score=risk_sc,
                risk_level=risk_lv,
                reason=decision_res.reason,
                recommended_actions=decision_res.recommended_actions,
            )
            db.add(dec)
        else:
            dec.decision = decision_res.decision
            dec.risk_score = risk_sc
            dec.risk_level = risk_lv
            dec.reason = decision_res.reason
            dec.recommended_actions = decision_res.recommended_actions

        # 8. Update vendor's real scores based on actual batch results
        if vendor:
            all_batches = db.query(Batch).filter(Batch.vendor_id == vendor.id).all()
            purities = [b.purity_reported for b in all_batches if b.purity_reported is not None]
            if purities:
                vendor.quality_score = round(sum(purities) / len(purities), 1)

            decided_batches = [b for b in all_batches if b.status in ["APPROVED", "REJECTED"]]
            if decided_batches:
                appr_count = sum(1 for b in decided_batches if b.status == "APPROVED")
                vendor.approval_rate = round((appr_count / len(decided_batches)) * 100, 1)

            vendor.risk_score = risk_sc
            db.add(vendor)

        # 9. Audit event
        record_audit_event(
            db,
            "Batch Evaluated",
            company_id=batch.company_id,
            vendor_id=batch.vendor_id,
            batch_id=batch.id,
            details={
                "batch_number": batch.batch_number,
                "decision": decision_res.decision,
                "risk_score": risk_sc,
                "risk_level": risk_lv,
                "purity_reported": batch.purity_reported,
            },
            commit=False,
        )

        db.commit()
        db.refresh(batch)

        # 10. Invalidate multi-tenant analytics cache so Dashboard shows genuine live data
        invalidate_analytics_cache(batch.company_id)
        logger.info(
            "Batch %s fully evaluated with decision %s and risk %.1f (genuine analytics invalidated).",
            batch.batch_number,
            decision_res.decision,
            risk_sc,
        )
    except Exception as exc:
        logger.exception("Error executing batch pipeline for batch %s: %s", getattr(batch, "batch_number", "unknown"), exc)

    return batch
