import logging
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.batch import Batch
from app.models.vendor import Vendor
from app.models.raw_material import RawMaterial
from app.models.document import Document
from app.models.intelligence import BatchIntelligence
from app.schemas.batch_intelligence import BatchProcessResponse, BatchPredictRiskResponse
from app.schemas.document import DocumentProcessResult, DocumentType
from app.schemas.validation import ValidationResult
from app.schemas.vendor_history import VendorHistoryMetrics
from app.services.document_service import document_service
from app.services.validation_service import validation_service
from app.services.vendor_history_service import vendor_history_service
from app.services.prediction_service import prediction_service
from app.services.kimi_service import kimi_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/batches", tags=["Batches - Intelligence & Validation"])


@router.post("/{batch_id}/process", response_model=BatchProcessResponse)
def process_batch(
    batch_id: int,
    db: Session = Depends(get_db)
):
    """
    Developer 2 Document Processing and Batch Validation Pipeline.
    1. Extracts technical parameters from all attached documents (COA, SDS, GMP, etc.)
    2. Executes deterministic validation against material specifications
    3. Analyzes historical supplier track record from Neon database
    4. Persists intermediate intelligence record
    """
    batch = db.query(Batch).filter(Batch.id == batch_id).first()
    if not batch:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Batch with id {batch_id} not found."
        )

    material = db.query(RawMaterial).filter(RawMaterial.id == batch.raw_material_id).first()
    if not material:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Raw material with id {batch.raw_material_id} not found for this batch."
        )

    vendor = db.query(Vendor).filter(Vendor.id == batch.vendor_id).first()

    # 1. Process all documents attached to this batch or vendor
    docs: List[Document] = db.query(Document).filter(Document.batch_id == batch.id).all()
    # Also include vendor-level documents (such as general GMP certificates)
    if vendor:
        vendor_docs = db.query(Document).filter(
            Document.vendor_id == vendor.id,
            Document.batch_id == None
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

        # Update document record in database
        doc.extracted_data = result.extracted_data
        doc.status = result.status.value
        doc.extraction_error = result.error
        db.add(doc)

        processed_results.append(result)

        if doc_type_enum == DocumentType.COA and result.extracted_data.get("purity") is not None:
            extracted_purity = result.extracted_data.get("purity")
            if batch.purity_reported is None:
                batch.purity_reported = extracted_purity

    # 2. Validation Service
    validation_res = validation_service.validate_batch(
        batch=batch,
        material=material,
        vendor=vendor,
        processed_docs=processed_results,
    )

    # 3. Vendor History Analysis
    vendor_hist = vendor_history_service.analyze_vendor_history(
        db=db,
        vendor_id=batch.vendor_id,
        current_batch=batch,
    )

    # 4. Save/Update BatchIntelligence
    intel = db.query(BatchIntelligence).filter(BatchIntelligence.batch_id == batch.id).first()
    if not intel:
        intel = BatchIntelligence(batch_id=batch.id)
        db.add(intel)

    intel.validation_result = validation_res.model_dump()
    intel.vendor_history = vendor_hist.model_dump()
    db.commit()

    return BatchProcessResponse(
        batch_id=batch.id,
        batch_number=batch.batch_number,
        validation_result=validation_res,
        vendor_history=vendor_hist,
        extracted_documents=processed_results,
        message="Batch documents processed and validated successfully."
    )


@router.post("/{batch_id}/predict-risk", response_model=BatchPredictRiskResponse)
def predict_batch_risk(
    batch_id: int,
    db: Session = Depends(get_db)
):
    """
    Developer 2 ML Risk Prediction and Kimi K3 Technical Synthesis.
    1. Assembles feature vector from validation and vendor history
    2. Runs trained RandomForestClassifier ML model (risk_score, risk_level, risk_factors)
    3. Calls Kimi K3 external API for reasoning/explanation (with graceful failure fallback)
    4. Persists predictions and AI audit findings
    """
    batch = db.query(Batch).filter(Batch.id == batch_id).first()
    if not batch:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Batch with id {batch_id} not found."
        )

    material = db.query(RawMaterial).filter(RawMaterial.id == batch.raw_material_id).first()
    if not material:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Raw material {batch.raw_material_id} not found."
        )

    vendor = db.query(Vendor).filter(Vendor.id == batch.vendor_id).first()
    if not vendor:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Vendor {batch.vendor_id} not found."
        )

    # Retrieve existing intelligence record or generate on the fly
    intel = db.query(BatchIntelligence).filter(BatchIntelligence.batch_id == batch.id).first()
    
    validation_res = None
    vendor_hist = None

    if intel and intel.validation_result:
        validation_res = ValidationResult(**intel.validation_result)
    else:
        # Run on the fly validation
        validation_res = validation_service.validate_batch(
            batch=batch,
            material=material,
            vendor=vendor,
            processed_docs=[]
        )

    if intel and intel.vendor_history:
        vendor_hist = VendorHistoryMetrics(**intel.vendor_history)
    else:
        # Run on the fly vendor history
        vendor_hist = vendor_history_service.analyze_vendor_history(
            db=db,
            vendor_id=vendor.id,
            current_batch=batch
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
    intel.ml_prediction = prediction_result.model_dump()
    intel.kimi_analysis = kimi_analysis.model_dump()
    intel.kimi_status = kimi_analysis.kimi_status.value
    db.commit()

    return BatchPredictRiskResponse(
        batch_id=batch.id,
        batch_number=batch.batch_number,
        risk_prediction=prediction_result,
        kimi_analysis=kimi_analysis,
        features_used=features_used,
        message="Risk prediction and AI reasoning generated successfully."
    )
