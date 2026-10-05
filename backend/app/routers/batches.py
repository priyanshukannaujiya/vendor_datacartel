"""
Unified Batch management router for VendorIQ.
Combines Developer 1 (CRUD), Developer 2 (Doc Processing, Validation, ML Risk, Kimi K3),
and Developer 3 (Decision Engine, Google SMTP Email Delivery, Audit Trail).
"""
import os
import uuid
import logging
from typing import Optional, List, Dict, Any, Union
from uuid import UUID
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Query, status, HTTPException, UploadFile, File, Body
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import or_, desc

from app.core.database import get_db
from app.core.security import get_current_user, get_optional_current_user
from app.core.errors import NotFoundError, ConflictError, BadRequestError
from app.core.config import settings

from app.models.user import User
from app.models.vendor import Vendor
from app.models.raw_material import RawMaterial
from app.models.vendor_material import VendorMaterial
from app.models.batch import Batch
from app.models.document import Document
from app.models.intelligence import BatchIntelligence
from app.models.decision import BatchDecision, EmailEvent, AuditEvent

from app.schemas.batch import (
    BatchCreate,
    BatchUpdate,
    BatchResponse,
    BatchDetailResponse,
    BatchListResponse,
    BatchDecisionRequest,
    BatchDecisionResponse,
)
from app.schemas.batch_intelligence import BatchProcessResponse, BatchPredictRiskResponse
from app.schemas.document import DocumentProcessResult, DocumentType
from app.schemas.validation import ValidationResult
from app.schemas.vendor_history import VendorHistoryMetrics

from app.services.document_service import DocumentProcessingService
from app.services.validation_service import BatchValidationService
from app.services.vendor_history_service import VendorHistoryService
from app.services.prediction_service import BatchRiskPredictionService
from app.services.kimi_service import KimiReasoningService
from app.services.decision_service import evaluate_decision
from app.services.email_service import EmailDeliveryError, send_email
from app.services.email_templates import render_decision_email, render_document_request_email
from app.services.audit_service import record_audit_event

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/batches", tags=["Batches"])

document_service = DocumentProcessingService()
validation_service = BatchValidationService()
vendor_history_service = VendorHistoryService()
prediction_service = BatchRiskPredictionService()
kimi_service = KimiReasoningService()


def _get_batch_by_id(db: Session, batch_id: Union[UUID, str]) -> Optional[Batch]:
    """Helper to query batch by UUID or str."""
    try:
        if isinstance(batch_id, str):
            b_uuid = UUID(batch_id)
        else:
            b_uuid = batch_id
        return db.query(Batch).filter(Batch.id == b_uuid).first()
    except Exception:
        return db.query(Batch).filter(Batch.batch_number == str(batch_id)).first()


def _enrich_batch_response(
    batch: Batch,
    db: Session,
    intel: Optional[BatchIntelligence] = None,
    latest_email: Optional[EmailEvent] = None,
    preloaded: bool = False,
) -> BatchResponse:
    """Enrich basic batch response with joined vendor, material, and pipeline info."""
    resp = BatchResponse.model_validate(batch)
    if batch.vendor:
        resp.vendor_name = batch.vendor.vendor_name
        resp.vendor_email = batch.vendor.email
        resp.vendor_code = batch.vendor.code
    if batch.raw_material:
        resp.raw_material_name = batch.raw_material.name
        resp.material_required_purity = batch.raw_material.purity_min

    # Check intelligence and decisions
    if not preloaded:
        intel = db.query(BatchIntelligence).filter(BatchIntelligence.batch_id == batch.id).first()
    if intel and intel.ml_prediction:
        resp.risk_score = intel.ml_prediction.get("risk_score")
        resp.risk_level = intel.ml_prediction.get("risk_level")
        resp.processed = True
    elif intel and intel.validation_result:
        resp.processed = True

    # Check email status
    if not preloaded:
        latest_email = (
            db.query(EmailEvent)
            .filter(EmailEvent.batch_id == batch.id)
            .order_by(desc(EmailEvent.created_at))
            .first()
        )
    if latest_email:
        resp.email_status = latest_email.status

    return resp


@router.get("", response_model=BatchListResponse)
def list_batches(
    status_filter: Optional[str] = Query(None, alias="status", description="Filter by batch status"),
    vendor_id: Optional[UUID] = Query(None, description="Filter by vendor ID"),
    raw_material_id: Optional[UUID] = Query(None, description="Filter by raw material ID"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(50, ge=1, le=100, description="Items per page"),
    current_user: Optional[User] = Depends(get_optional_current_user),
    db: Session = Depends(get_db),
):
    """
    List batches. Scoped to company if user is authenticated.
    Supports filtering by status, vendor, and raw material.
    """
    query = db.query(Batch)
    if current_user and current_user.company_id:
        query = query.filter(Batch.company_id == current_user.company_id)

    if status_filter:
        query = query.filter(Batch.status.ilike(f"%{status_filter}%"))
    if vendor_id:
        query = query.filter(Batch.vendor_id == vendor_id)
    if raw_material_id:
        query = query.filter(Batch.raw_material_id == raw_material_id)

    total = query.count()
    items = (
        query.options(joinedload(Batch.vendor), joinedload(Batch.raw_material))
        .order_by(desc(Batch.created_at))
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )

    batch_ids = [b.id for b in items if b.id]
    intel_map = {}
    email_map = {}
    if batch_ids:
        intels = db.query(BatchIntelligence).filter(BatchIntelligence.batch_id.in_(batch_ids)).all()
        intel_map = {bi.batch_id: bi for bi in intels}

        emails = (
            db.query(EmailEvent)
            .filter(EmailEvent.batch_id.in_(batch_ids))
            .order_by(desc(EmailEvent.created_at))
            .all()
        )
        for em in emails:
            if em.batch_id not in email_map:
                email_map[em.batch_id] = em

    enriched_items = [
        _enrich_batch_response(
            b,
            db,
            intel=intel_map.get(b.id),
            latest_email=email_map.get(b.id),
            preloaded=True,
        )
        for b in items
    ]

    return BatchListResponse(
        items=enriched_items,
        total=total,
        page=page,
        page_size=page_size,
    )


@router.post("", response_model=BatchResponse, status_code=status.HTTP_201_CREATED)
def create_batch(
    data: BatchCreate,
    current_user: Optional[User] = Depends(get_optional_current_user),
    db: Session = Depends(get_db),
):
    """
    Create an incoming raw material batch with initial status 'RECEIVED'.
    """
    v_uuid = uuid.UUID(str(data.vendor_id)) if data.vendor_id else None
    m_uuid = uuid.UUID(str(data.raw_material_id)) if data.raw_material_id else None

    vendor = db.query(Vendor).filter(Vendor.id == v_uuid).first()
    if not vendor or (current_user and vendor.company_id != current_user.company_id):
        raise NotFoundError(f"Vendor with ID '{data.vendor_id}' not found in your company")

    if not m_uuid:
        # Auto-resolve or create default raw material for the company
        material = db.query(RawMaterial).filter(RawMaterial.company_id == vendor.company_id).first()
        if not material:
            material = RawMaterial(
                company_id=vendor.company_id,
                name="Cosmetic & Formulation Grade Ingredient",
                code="RM-DEFAULT",
                purity_min=95.0,
                category="Standard Ingredient",
            )
            db.add(material)
            db.flush()
        m_uuid = material.id
    else:
        material = db.query(RawMaterial).filter(RawMaterial.id == m_uuid).first()
        if not material or (current_user and material.company_id != current_user.company_id):
            raise NotFoundError(f"Raw material with ID '{data.raw_material_id}' not found in your company")

    company_id = vendor.company_id

    # Check for duplicate batch number for same vendor in company
    existing = (
        db.query(Batch)
        .filter(
            Batch.company_id == company_id,
            Batch.vendor_id == v_uuid,
            Batch.batch_number == data.batch_number,
        )
        .first()
    )
    if existing:
        raise ConflictError(f"Batch with number '{data.batch_number}' already exists for this vendor")

    try:
        batch = Batch(
            company_id=company_id,
            vendor_id=v_uuid,
            raw_material_id=m_uuid,
            batch_number=data.batch_number,
            manufacturing_date=data.manufacturing_date,
            expiry_date=data.expiry_date,
            quantity=data.quantity or 1000.0,
            unit=data.unit or "kg",
            price=data.price or 100.0,
            expected_delivery_date=data.expected_delivery_date,
            actual_delivery_date=data.actual_delivery_date,
            purity_reported=data.purity_reported,
            status="RECEIVED",
            created_by=current_user.id if current_user else None,
        )
        db.add(batch)
        db.commit()
        db.refresh(batch)
    except Exception as exc:
        db.rollback()
        raise ConflictError(f"Batch with number '{data.batch_number}' already exists for this vendor")

    record_audit_event(
        db,
        "Batch Received",
        company_id=batch.company_id,
        vendor_id=batch.vendor_id,
        batch_id=batch.id,
        details={"batch_number": batch.batch_number},
    )

    return _enrich_batch_response(batch, db)


@router.get("/{batch_id}", response_model=BatchDetailResponse)
def get_batch_detail(
    batch_id: UUID,
    current_user: Optional[User] = Depends(get_optional_current_user),
    db: Session = Depends(get_db),
):
    """
    MAIN DEMO PAGE ENDPOINT.
    Returns complete batch intelligence: batch metadata, quality checks (spec, COA, SDS, GMP, testing, contaminants),
    historical comparison, ML risk prediction, Kimi K3 reasoning, decision, email status, and audit timeline.
    """
    batch = _get_batch_by_id(db, batch_id)
    if not batch:
        raise NotFoundError(f"Batch with ID '{batch_id}' not found")
    if current_user and current_user.company_id and batch.company_id != current_user.company_id:
        raise NotFoundError(f"Batch with ID '{batch_id}' not found")

    vendor = batch.vendor
    material = batch.raw_material
    intelligence = db.query(BatchIntelligence).filter(BatchIntelligence.batch_id == batch.id).first()
    docs = db.query(Document).filter(Document.batch_id == batch.id).all()
    decisions = (
        db.query(BatchDecision)
        .filter(BatchDecision.batch_id == batch.id)
        .order_by(desc(BatchDecision.created_at))
        .all()
    )
    emails = (
        db.query(EmailEvent)
        .filter(EmailEvent.batch_id == batch.id)
        .order_by(desc(EmailEvent.created_at))
        .all()
    )
    audit_events = (
        db.query(AuditEvent)
        .filter(AuditEvent.batch_id == batch.id)
        .order_by(AuditEvent.created_at.asc())
        .all()
    )

    # Base enrichment
    base_resp = _enrich_batch_response(batch, db)

    # Assemble Quality Checks
    val_data = intelligence.validation_result if intelligence and intelligence.validation_result else {}
    checks_list = val_data.get("checks", [])

    quality_checks = {
        "specification": {
            "name": material.name if material else None,
            "purity_min": material.purity_min if material else None,
            "moisture_max": material.moisture_max if material else None,
            "heavy_metals_max_ppm": material.heavy_metals_max_ppm if material else None,
            "microbial_limit_cfu_g": material.microbial_limit_cfu_g if material else None,
            "storage_conditions": material.storage_conditions if material else None,
        },
        "all_checks": checks_list,
    }

    # Historical Comparison
    v_hist = intelligence.vendor_history if intelligence and intelligence.vendor_history else {}
    prior_batches = (
        db.query(Batch)
        .filter(Batch.vendor_id == batch.vendor_id, Batch.id != batch.id)
        .all()
    )
    prior_purities = [float(item.purity_reported) for item in prior_batches if item.purity_reported is not None]
    approved_prior = sum(1 for item in prior_batches if item.status == "APPROVED")
    rejected_prior = sum(1 for item in prior_batches if item.status == "REJECTED")
    historical_comparison = {
        "previous_batches": len(prior_batches),
        "approved_count": approved_prior,
        "rejected_count": rejected_prior,
        "approval_rate": approved_prior / len(prior_batches) if prior_batches else None,
        "delivery_reliability": v_hist.get("delivery_reliability"),
        "average_purity": sum(prior_purities) / len(prior_purities) if prior_purities else None,
        "purity_variance": (
            batch.purity_reported - (sum(prior_purities) / len(prior_purities))
            if batch.purity_reported is not None and prior_purities
            else None
        ),
    }

    # ML Risk Prediction
    risk_prediction = intelligence.ml_prediction if intelligence and intelligence.ml_prediction else None

    # Kimi K3 Analysis
    kimi_analysis = intelligence.kimi_analysis if intelligence and intelligence.kimi_analysis else None

    # Final Decision
    final_decision = None
    if decisions:
        d = decisions[0]
        final_decision = {
            "id": str(d.id),
            "decision": d.decision,
            "risk_score": d.risk_score,
            "risk_level": d.risk_level,
            "reason": d.reason,
            "recommended_actions": d.recommended_actions,
            "created_at": d.created_at.isoformat() if d.created_at else None,
        }
    # Email Event
    email_event = None
    if emails:
        e = emails[0]
        email_event = {
            "id": str(e.id),
            "recipient_email": e.recipient_email,
            "subject": e.subject,
            "email_type": e.email_type,
            "status": e.status,
            "provider": e.provider,
            "sent_at": e.sent_at.isoformat() if e.sent_at else None,
            "error_message": e.error_message,
        }

    # Audit Timeline
    # Format: Email Received -> Documents Processed -> Validation Completed -> Risk Predicted -> Kimi Assessment -> Decision -> Email Sent
    audit_timeline = []
    if audit_events:
        for ev in audit_events:
            audit_timeline.append({
                "id": str(ev.id),
                "event_type": ev.event_type,
                "timestamp": ev.created_at.isoformat() if ev.created_at else None,
                "details": ev.details,
            })
    # Documents List
    documents_list = [
        {
            "id": str(d.id),
            "filename": d.filename,
            "document_type": d.document_type,
            "status": d.status,
            "file_size": d.file_size,
            "created_at": d.created_at.isoformat() if d.created_at else None,
            "extracted_data": d.extracted_data,
        }
        for d in docs
    ]

    detail = BatchDetailResponse.model_validate(base_resp)
    detail.quality_checks = quality_checks
    detail.historical_comparison = historical_comparison
    detail.risk_prediction = risk_prediction
    detail.kimi_analysis = kimi_analysis
    detail.final_decision = final_decision
    detail.email_event = email_event
    detail.audit_timeline = audit_timeline
    detail.documents = documents_list

    return detail


@router.post("/{batch_id}/process", response_model=BatchProcessResponse)
def process_batch(
    batch_id: UUID,
    db: Session = Depends(get_db),
):
    """
    Developer 2 Document Processing and Batch Validation Pipeline.
    1. Extracts technical parameters from all attached documents (COA, SDS, GMP, etc.)
    2. Executes deterministic validation against material specifications
    3. Analyzes historical supplier track record
    4. Persists intermediate intelligence record
    """
    batch = _get_batch_by_id(db, batch_id)
    if not batch:
        raise HTTPException(status_code=404, detail=f"Batch {batch_id} not found.")

    material = db.query(RawMaterial).filter(RawMaterial.id == batch.raw_material_id).first()
    if not material:
        raise HTTPException(status_code=400, detail=f"Raw material {batch.raw_material_id} not found.")

    vendor = db.query(Vendor).filter(Vendor.id == batch.vendor_id).first()

    # Process all attached documents
    docs: List[Document] = db.query(Document).filter(Document.batch_id == batch.id).all()
    if vendor:
        vendor_docs = db.query(Document).filter(
            Document.vendor_id == vendor.id,
            Document.batch_id.is_(None)
        ).all()
        docs.extend(vendor_docs)

    processed_results: List[DocumentProcessResult] = []
    extracted_purity = None

    for doc in docs:
        try:
            doc_type_enum = DocumentType(doc.document_type)
        except ValueError:
            doc_type_enum = DocumentType.OTHER

        result = document_service.process_document(
            file_source=doc.file_path,
            filename=doc.filename,
            document_type=doc_type_enum,
            document_id=doc.id
        )

        doc.extracted_data = result.extracted_data
        doc.status = result.status.value
        doc.extraction_error = result.error
        doc.processed_at = datetime.now(timezone.utc)
        db.add(doc)

        processed_results.append(result)

        if doc_type_enum == DocumentType.COA and result.extracted_data.get("purity") is not None:
            extracted_purity = result.extracted_data.get("purity")
            if batch.purity_reported is None:
                batch.purity_reported = extracted_purity

    # Run deterministic validation
    validation_res = validation_service.validate_batch(
        batch=batch,
        material=material,
        vendor=vendor,
        processed_docs=processed_results,
    )

    # Analyze historical track record
    vendor_hist = vendor_history_service.analyze_vendor_history(
        db=db,
        vendor_id=batch.vendor_id,
        current_batch=batch,
    )

    # Persist in BatchIntelligence
    intel = db.query(BatchIntelligence).filter(BatchIntelligence.batch_id == batch.id).first()
    if not intel:
        intel = BatchIntelligence(batch_id=batch.id)
        db.add(intel)

    intel.validation_result = validation_res.model_dump(mode="json")
    intel.vendor_history = vendor_hist.model_dump(mode="json")

    batch.status = "PROCESSING"

    record_audit_event(
        db,
        "Documents Processed",
        company_id=batch.company_id,
        vendor_id=batch.vendor_id,
        batch_id=batch.id,
        details={"documents_count": len(processed_results)},
        commit=False,
    )
    record_audit_event(
        db,
        "Validation Completed",
        company_id=batch.company_id,
        vendor_id=batch.vendor_id,
        batch_id=batch.id,
        details={"status": validation_res.overall_status.value},
        commit=False,
    )
    db.commit()

    return BatchProcessResponse(
        batch_id=str(batch.id),
        batch_number=batch.batch_number,
        validation_result=validation_res,
        vendor_history=vendor_hist,
        extracted_documents=processed_results,
        message="Batch documents processed and validated successfully."
    )


@router.post("/{batch_id}/predict-risk", response_model=BatchPredictRiskResponse)
def predict_batch_risk(
    batch_id: UUID,
    db: Session = Depends(get_db),
):
    """
    Developer 2 ML Risk Prediction and Kimi K3 Technical Synthesis.
    1. Assembles feature vector from validation and vendor history
    2. Runs trained RandomForestClassifier ML model
    3. Calls Kimi K3 external API for reasoning/explanation (with graceful failure fallback)
    4. Persists predictions and AI audit findings
    """
    batch = _get_batch_by_id(db, batch_id)
    if not batch:
        raise HTTPException(status_code=404, detail=f"Batch {batch_id} not found.")

    material = db.query(RawMaterial).filter(RawMaterial.id == batch.raw_material_id).first()
    if not material:
        raise HTTPException(status_code=400, detail=f"Raw material {batch.raw_material_id} not found.")

    vendor = db.query(Vendor).filter(Vendor.id == batch.vendor_id).first()

    # Load or generate on the fly validation and vendor history
    intel = db.query(BatchIntelligence).filter(BatchIntelligence.batch_id == batch.id).first()

    validation_res = None
    vendor_hist = None

    if intel and intel.validation_result:
        validation_res = ValidationResult(**intel.validation_result)
    else:
        validation_res = validation_service.validate_batch(
            batch=batch,
            material=material,
            vendor=vendor,
            processed_docs=[]
        )

    if intel and intel.vendor_history:
        vendor_hist = VendorHistoryMetrics(**intel.vendor_history)
    else:
        vendor_hist = vendor_history_service.analyze_vendor_history(
            db=db,
            vendor_id=vendor.id if vendor else None,
            current_batch=batch,
        )

    # 1. Execute ML Risk Prediction
    prediction_result, features_used = prediction_service.predict_risk(
        batch=batch,
        material=material,
        vendor=vendor,
        validation_result=validation_res,
        vendor_history=vendor_hist,
        extracted_coa_purity=batch.purity_reported,
    )

    # 2. Call Kimi K3 Reasoning Engine (Guaranteed not to crash ML prediction)
    kimi_analysis = kimi_service.generate_explanation(
        vendor=vendor,
        material=material,
        batch=batch,
        validation_result=validation_res,
        vendor_history=vendor_hist,
        prediction=prediction_result,
    )

    # 3. Persist intelligence results
    if not intel:
        intel = BatchIntelligence(batch_id=batch.id)
        db.add(intel)

    intel.ml_features = features_used
    intel.ml_prediction = prediction_result.model_dump(mode="json")
    intel.kimi_analysis = kimi_analysis.model_dump(mode="json")
    intel.kimi_status = kimi_analysis.kimi_status.value

    # Update vendor's current risk score
    if vendor:
        vendor.risk_score = prediction_result.risk_score

    record_audit_event(
        db,
        "Risk Predicted",
        company_id=batch.company_id,
        vendor_id=batch.vendor_id,
        batch_id=batch.id,
        details={
            "risk_score": prediction_result.risk_score,
            "risk_level": prediction_result.risk_level.value,
        },
        commit=False,
    )
    if kimi_analysis.kimi_status.value == "SUCCESS":
        record_audit_event(
            db,
            "Kimi Assessment Generated",
            company_id=batch.company_id,
            vendor_id=batch.vendor_id,
            batch_id=batch.id,
            details={"assessment_available": bool(kimi_analysis.summary)},
            commit=False,
        )
    db.commit()

    return BatchPredictRiskResponse(
        batch_id=str(batch.id),
        batch_number=batch.batch_number,
        risk_prediction=prediction_result,
        kimi_analysis=kimi_analysis,
        features_used=features_used,
        message="Risk prediction and AI reasoning generated successfully."
    )


@router.post("/{batch_id}/decision", response_model=BatchDecisionResponse)
def create_batch_decision(
    batch_id: UUID,
    request: BatchDecisionRequest = Body(default=BatchDecisionRequest()),
    db: Session = Depends(get_db),
):
    """
    Developer 3 Decision Engine & Google SMTP Workflow.
    1. Consumes validation, ML prediction, and Kimi assessment
    2. Determines final qualification decision: APPROVED, REJECTED, or NEEDS_REVIEW
    3. Persists BatchDecision and updates Batch status
    4. Renders responsive HTML decision email
    5. Dispatches via Google SMTP (with STARTTLS) and creates EmailEvent
    """
    batch = _get_batch_by_id(db, batch_id)
    if not batch:
        raise HTTPException(status_code=404, detail=f"Batch with ID '{batch_id}' not found.")

    vendor = batch.vendor
    material = batch.raw_material
    intelligence = db.query(BatchIntelligence).filter(BatchIntelligence.batch_id == batch.id).first()

    # If intelligence is not yet run, generate it automatically so decision can proceed seamlessly
    if not intelligence or not intelligence.validation_result or not intelligence.ml_prediction:
        # Run process & predict automatically
        validation_res = validation_service.validate_batch(
            batch=batch,
            material=material,
            vendor=vendor,
            processed_docs=[]
        )
        vendor_hist = vendor_history_service.analyze_vendor_history(
            db=db,
            vendor_id=vendor.id if vendor else None,
            current_batch=batch,
        )
        pred_res, feat = prediction_service.predict_risk(
            batch=batch,
            material=material,
            vendor=vendor,
            validation_result=validation_res,
            vendor_history=vendor_hist,
            extracted_coa_purity=batch.purity_reported,
        )
        kimi_res = kimi_service.generate_explanation(
            vendor=vendor,
            material=material,
            batch=batch,
            validation_result=validation_res,
            vendor_history=vendor_hist,
            prediction=pred_res,
        )
        if not intelligence:
            intelligence = BatchIntelligence(batch_id=batch.id)
            db.add(intelligence)
        intelligence.validation_result = validation_res.model_dump(mode="json")
        intelligence.vendor_history = vendor_hist.model_dump(mode="json")
        intelligence.ml_features = feat
        intelligence.ml_prediction = pred_res.model_dump(mode="json")
        intelligence.kimi_analysis = kimi_res.model_dump(mode="json")
        intelligence.kimi_status = kimi_res.kimi_status.value
        db.commit()
        db.refresh(intelligence)

    validation = intelligence.validation_result
    prediction = intelligence.ml_prediction
    risk_score = prediction.get("risk_score", 15.0)
    risk_level = prediction.get("risk_level", "LOW")

    # Helper extraction for decision service
    checks = validation.get("checks", [])
    validation_results = {}
    spec_outcomes = []
    doc_checks = []

    for c in checks:
        name = c.get("name", "")
        status_val = c.get("status")
        outcome = True if status_val == "PASS" else (False if status_val == "FAIL" else None)
        validation_results[name] = {"passed": outcome, "status": status_val, "reason": c.get("reason", "")}
        if name in ["purity", "moisture", "heavy_metals", "microbial_tamc", "material_shelf_life"]:
            spec_outcomes.append(outcome)
        if name.startswith("document_present_"):
            doc_checks.append(outcome)

    if any(o is False for o in spec_outcomes):
        material_specification = False
    elif spec_outcomes and all(o is True for o in spec_outcomes):
        material_specification = True
    else:
        material_specification = None

    completeness = (sum(1 for o in doc_checks if o is True) / len(doc_checks)) if doc_checks else 1.0
    document_completeness = {
        "completeness": completeness,
        "missing_documents": [c.get("name", "") for c in checks if c.get("status") in ["FAIL", "MISSING"] and "document_present" in c.get("name", "")],
    }

    thresholds = request.company_thresholds
    if "mandatory_validation_checks" not in thresholds:
        thresholds["mandatory_validation_checks"] = []

    decision_res = evaluate_decision(
        validation_results=validation_results,
        risk_score=float(risk_score),
        risk_level=risk_level,
        document_completeness=document_completeness,
        material_specification=material_specification,
        company_thresholds=thresholds,
    )

    decision_value = request.decision if request.manual_override else decision_res.decision
    reason_value = (
        f"Manual override: {request.notes.strip()}"
        if request.manual_override and request.notes
        else decision_res.reason
    )
    recommended_actions = [] if request.manual_override else decision_res.recommended_actions

    # Persist BatchDecision
    decision = BatchDecision(
        batch_id=batch.id,
        company_id=batch.company_id,
        decision=decision_value,
        risk_score=float(risk_score),
        risk_level=risk_level,
        reason=reason_value,
        recommended_actions=recommended_actions,
    )
    db.add(decision)
    batch.status = decision_value

    record_audit_event(
        db,
        "Decision Made",
        company_id=batch.company_id,
        vendor_id=batch.vendor_id,
        batch_id=batch.id,
        details={
            "decision": decision_value,
            "manual_override": request.manual_override,
            "override_notes": request.notes.strip() if request.manual_override and request.notes else None,
        },
        commit=False,
    )
    db.commit()
    db.refresh(decision)

    # Render decision email template
    kimi_analysis = intelligence.kimi_analysis or {}
    subject, html_content = render_decision_email(
        decision_value,
        batch_number=batch.batch_number,
        vendor_name=vendor.vendor_name if vendor else "Valued Vendor",
        material=material.name if material else "Raw Material",
        risk_score=risk_score,
        risk_level=risk_level,
        validation_summary=[f"{c.get('name', 'Check').replace('_', ' ').title()}: {c.get('status', 'UNKNOWN')}" for c in checks],
        validation_results=validation_results,
        kimi_summary=kimi_analysis.get("summary", ""),
        primary_issues=validation.get("missing_information", []),
        uncertain_checks=[c.get("name") for c in checks if c.get("status") in ["MISSING", "NEEDS_REVIEW"]],
        missing_information=document_completeness["missing_documents"],
        reason=reason_value,
        recommended_actions=recommended_actions,
        reference_id=str(decision.id),
        timestamp=datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
    )

    recipient = (vendor.contact_email or vendor.email) if vendor else None
    if not recipient:
        last_req = (
            db.query(EmailEvent)
            .filter(EmailEvent.batch_id == batch.id)
            .order_by(desc(EmailEvent.created_at))
            .first()
        )
        if last_req and last_req.recipient_email:
            recipient = last_req.recipient_email
    if not recipient:
        received_audit = (
            db.query(AuditEvent)
            .filter(AuditEvent.batch_id == batch.id, AuditEvent.event_type == "Email Received")
            .order_by(desc(AuditEvent.created_at))
            .first()
        )
        if received_audit and received_audit.details and received_audit.details.get("sender"):
            recipient = received_audit.details.get("sender")

    if recipient and vendor and not vendor.email:
        vendor.email = recipient
        db.add(vendor)

    email_status = "NOT_APPLICABLE"
    if recipient:
        email_event = EmailEvent(
            company_id=batch.company_id,
            vendor_id=batch.vendor_id,
            batch_id=batch.id,
            decision_id=decision.id,
            recipient_email=recipient,
            subject=subject,
            email_type=decision_value,
            status="PENDING",
            provider="GOOGLE_SMTP",
            html_content=html_content,
            text_content=f"VendorIQ batch {batch.batch_number}: {decision_value}\n{reason_value}",
        )
        db.add(email_event)
        db.commit()
        db.refresh(email_event)

        try:
            send_email(
                recipient=recipient,
                subject=subject,
                html_content=html_content,
                text_content=email_event.text_content,
            )
            email_event.status = "SENT"
            email_event.sent_at = datetime.now(timezone.utc)
            record_audit_event(
                db,
                "Email Sent",
                company_id=batch.company_id,
                vendor_id=batch.vendor_id,
                batch_id=batch.id,
                details={"email_id": str(email_event.id), "status": "SENT"},
            )
        except EmailDeliveryError as exc:
            email_event.status = "FAILED"
            email_event.error_message = str(exc)
            logger.warning("SMTP delivery failed for batch %s: %s", batch.batch_number, exc)

        db.commit()
        email_status = email_event.status

    return BatchDecisionResponse(
        decision=decision_value,
        risk_score=float(risk_score),
        reason=reason_value,
        recommended_actions=recommended_actions,
        reference_id=str(decision.id),
        email_status=email_status,
    )


@router.get("/{batch_id}/intelligence")
def get_batch_intelligence(
    batch_id: UUID,
    db: Session = Depends(get_db),
):
    """Retrieve raw stored intelligence record for a batch."""
    intel = db.query(BatchIntelligence).filter(BatchIntelligence.batch_id == batch_id).first()
    if not intel:
        raise NotFoundError(f"No intelligence record found for batch {batch_id}")
    return {
        "batch_id": str(intel.batch_id),
        "validation_result": intel.validation_result,
        "vendor_history": intel.vendor_history,
        "ml_features": intel.ml_features,
        "ml_prediction": intel.ml_prediction,
        "kimi_analysis": intel.kimi_analysis,
        "kimi_status": intel.kimi_status,
        "created_at": intel.created_at.isoformat() if intel.created_at else None,
    }


@router.post("/{batch_id}/upload-document")
async def upload_batch_document(
    batch_id: UUID,
    file: UploadFile = File(...),
    document_type: str = Query("OTHER", description="COA, SDS, GMP, SPECIFICATION, TEST_REPORT, OTHER"),
    db: Session = Depends(get_db),
):
    """Upload a document associated with a specific batch."""
    batch = _get_batch_by_id(db, batch_id)
    if not batch:
        raise NotFoundError(f"Batch with ID '{batch_id}' not found")

    upload_dir = settings.UPLOAD_DIR
    os.makedirs(upload_dir, exist_ok=True)
    file_path = os.path.join(upload_dir, f"{batch.id}_{file.filename}")

    contents = await file.read()
    with open(file_path, "wb") as f:
        f.write(contents)

    doc = Document(
        company_id=batch.company_id,
        batch_id=batch.id,
        vendor_id=batch.vendor_id,
        file_name=file.filename,
        file_path=file_path,
        document_type=document_type.upper(),
        mime_type=file.content_type or "application/octet-stream",
        file_size=len(contents),
        processing_status="UPLOADED",
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)

    # Process document details (PDF parsing & extraction)
    try:
        doc_type_enum = DocumentType(doc.document_type)
    except ValueError:
        doc_type_enum = DocumentType.OTHER

    proc_result = document_service.process_document(
        file_source=file_path,
        filename=file.filename,
        document_type=doc_type_enum,
        document_id=doc.id,
    )
    doc.extracted_data = proc_result.extracted_data
    doc.status = proc_result.status.value
    doc.extraction_error = proc_result.error
    doc.processed_at = datetime.now(timezone.utc)

    if doc_type_enum == DocumentType.COA and proc_result.extracted_data.get("purity") is not None:
        if batch.purity_reported is None:
            batch.purity_reported = proc_result.extracted_data.get("purity")

    db.add(doc)
    db.commit()

    # Trigger complete automated qualification pipeline and update genuine analytics
    try:
        from app.services.pipeline_service import run_full_batch_pipeline
        run_full_batch_pipeline(db, batch)
    except Exception as exc:
        logger.warning("Could not run full batch pipeline after batch doc upload: %s", exc)

    return {
        "id": str(doc.id),
        "filename": doc.filename,
        "document_type": doc.document_type,
        "file_size": doc.file_size,
        "status": doc.status,
        "extracted_data": doc.extracted_data,
        "message": "Batch document uploaded, extracted, and analyzed successfully."
    }


@router.put("/{batch_id}", response_model=BatchResponse)
def update_batch(
    batch_id: UUID,
    data: BatchUpdate,
    current_user: Optional[User] = Depends(get_optional_current_user),
    db: Session = Depends(get_db),
):
    """Update batch details."""
    batch = _get_batch_by_id(db, batch_id)
    if not batch:
        raise NotFoundError(f"Batch with ID '{batch_id}' not found")
    if current_user and current_user.company_id and batch.company_id != current_user.company_id:
        raise NotFoundError(f"Batch with ID '{batch_id}' not found")

    update_dict = data.model_dump(exclude_unset=True)
    for field, value in update_dict.items():
        setattr(batch, field, value)

    batch.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(batch)
    return _enrich_batch_response(batch, db)


@router.delete("/{batch_id}")
def delete_batch(
    batch_id: UUID,
    current_user: Optional[User] = Depends(get_optional_current_user),
    db: Session = Depends(get_db),
):
    """Delete a batch."""
    batch = _get_batch_by_id(db, batch_id)
    if not batch:
        raise NotFoundError(f"Batch with ID '{batch_id}' not found")
    if current_user and current_user.company_id and batch.company_id != current_user.company_id:
        raise NotFoundError(f"Batch with ID '{batch_id}' not found")

    db.delete(batch)
    db.commit()
    return {"message": "Batch deleted successfully"}


@router.post("/{batch_id}/request-documents")
def request_batch_documents(
    batch_id: Union[UUID, str],
    custom_email: Optional[str] = Body(None, embed=True),
    current_user: Optional[User] = Depends(get_optional_current_user),
    db: Session = Depends(get_db),
):
    """
    Send an official documentation request email to the supplier/vendor.
    Requests PDF attachments for COA, SDS, and GMP release certificates.
    Dispatched via Google SMTP (Gmail).
    """
    batch = _get_batch_by_id(db, batch_id)
    if not batch:
        raise NotFoundError(f"Batch '{batch_id}' not found")

    vendor = batch.vendor
    recipient = custom_email or (vendor.contact_email if vendor else None) or (vendor.email if vendor else None)
    if not recipient:
        raise BadRequestError("No recipient email found for this vendor. Please provide an email address.")

    vendor_name = vendor.name if vendor else "Supplier QA"
    material_name = batch.raw_material.name if batch.raw_material else "Raw Material"
    required_purity = getattr(batch.raw_material, "required_purity", 99.0) if batch.raw_material else 99.0

    subject, html_content = render_document_request_email(
        reference_id=str(batch.id),
        vendor_name=vendor_name,
        batch_number=batch.batch_number,
        material_name=material_name,
        required_purity=required_purity,
        quantity=batch.quantity,
        unit=batch.unit or "kg",
    )

    email_status = "PENDING"
    error_message = None

    try:
        send_email(
            recipient=recipient,
            subject=subject,
            html_content=html_content,
            text_content=f"Please submit PDF documentation (COA, SDS, GMP) for Batch {batch.batch_number}.",
        )
        email_status = "SENT"
        logger.info("Documentation request email successfully sent to %s for batch %s", recipient, batch.batch_number)
    except Exception as exc:
        email_status = "FAILED"
        error_message = str(exc)
        logger.warning("Could not dispatch email via SMTP (will record event): %s", exc)

    # Record email event
    email_event = EmailEvent(
        company_id=batch.company_id,
        vendor_id=batch.vendor_id,
        batch_id=batch.id,
        recipient_email=recipient,
        subject=subject,
        email_type="DOCUMENT_REQUEST",
        status=email_status,
        provider="GOOGLE_SMTP",
        sent_at=datetime.now(timezone.utc) if email_status == "SENT" else None,
        error_message=error_message,
        html_content=html_content,
        text_content=f"Please submit PDF documentation (COA, SDS, GMP) for Batch {batch.batch_number}.",
    )
    db.add(email_event)

    # Record audit log
    record_audit_event(
        db=db,
        event_type="DOC_REQUEST_SENT",
        company_id=batch.company_id,
        vendor_id=batch.vendor_id,
        batch_id=batch.id,
        details={
            "recipient": recipient,
            "subject": subject,
            "status": email_status,
            "error": error_message,
        },
        commit=False,
    )

    batch.status = "PENDING"
    batch.updated_at = datetime.now(timezone.utc)
    db.commit()

    return {
        "success": email_status == "SENT",
        "batch_id": str(batch.id),
        "batch_number": batch.batch_number,
        "recipient": recipient,
        "subject": subject,
        "email_status": email_status,
        "message": (
            f"Documentation request email successfully delivered to {recipient} via Google SMTP."
            if email_status == "SENT"
            else (
                f"Email delivery failed for {recipient}; the failed event is saved for retry. "
                f"Google SMTP error: {error_message or 'Check SMTP credentials in Settings'}"
            )
        ),
    }
