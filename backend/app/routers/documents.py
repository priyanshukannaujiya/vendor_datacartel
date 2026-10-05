"""
Documents router for listing, retrieving, downloading, and managing supplier/batch documents in VendorIQ.
"""
import logging
import os
import uuid
from datetime import datetime, timezone
from typing import Optional, List
from uuid import UUID
from fastapi import APIRouter, Depends, Query, status, HTTPException, UploadFile, File
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import desc, or_

from app.core.database import get_db
from app.core.config import settings
from app.core.security import get_optional_current_user
from app.core.errors import NotFoundError
from app.models.document import Document
from app.models.batch import Batch
from app.models.vendor import Vendor
from app.models.company import Company
from app.models.user import User

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/documents", tags=["Documents"])


@router.get("")
def list_documents(
    batch_id: Optional[UUID] = Query(None, description="Filter by batch ID"),
    vendor_id: Optional[UUID] = Query(None, description="Filter by vendor ID"),
    document_type: Optional[str] = Query(None, description="Filter by document type (COA, SDS, GMP, etc.)"),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    current_user: Optional[User] = Depends(get_optional_current_user),
    db: Session = Depends(get_db),
):
    query = (
        db.query(Document)
        .outerjoin(Batch, Document.batch_id == Batch.id)
        .outerjoin(Vendor, Document.vendor_id == Vendor.id)
    )
    if current_user and current_user.company_id:
        query = query.filter(
            or_(
                Document.company_id == current_user.company_id,
                Document.company_id.is_(None),
                Batch.company_id == current_user.company_id,
                Vendor.company_id == current_user.company_id,
            )
        )
    if batch_id:
        query = query.filter(Document.batch_id == batch_id)
    if vendor_id:
        query = query.filter(Document.vendor_id == vendor_id)
    if document_type:
        query = query.filter(Document.document_type.ilike(f"%{document_type}%"))

    total = query.count()
    docs = (
        query.options(joinedload(Document.vendor), joinedload(Document.batch))
        .order_by(desc(Document.created_at))
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )

    items = []
    for d in docs:
        vendor_name = d.vendor.vendor_name if d.vendor else None
        batch_number = d.batch.batch_number if d.batch else None
        items.append({
            "id": str(d.id),
            "filename": d.filename,
            "original_filename": d.file_name,
            "document_type": d.document_type,
            "status": d.status,
            "extraction_status": d.processing_status,
            "file_size": d.file_size,
            "file_path": d.file_path,
            "mime_type": d.mime_type,
            "batch_id": str(d.batch_id) if d.batch_id else None,
            "batch_number": batch_number,
            "vendor_id": str(d.vendor_id) if d.vendor_id else None,
            "vendor_name": vendor_name,
            "created_at": d.created_at.isoformat() if d.created_at else None,
            "processed_at": d.processed_at.isoformat() if d.processed_at else None,
            "extracted_data": d.extracted_data,
            "extraction_error": d.extraction_error,
        })

    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
    }


@router.post("/sync-inbox")
def sync_documents_inbox(
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_current_user),
):
    """
    Poll the configured Gmail mailbox over IMAP for vendor PDF replies
    and ingest them immediately into the database and document processing pipeline.
    """
    try:
        from app.services.inbound_email_service import poll_inbox_once
        count = poll_inbox_once(force_rescan=True)
        return {
            "success": True,
            "new_documents_count": count,
            "message": f"Inbox sync completed. Imported {count} new document(s) from vendor emails.",
        }
    except Exception as exc:
        logger.exception("Inbox sync error: %s", exc)
        return {
            "success": False,
            "new_documents_count": 0,
            "message": f"Inbox sync error: {str(exc)}",
        }


@router.post("", status_code=status.HTTP_201_CREATED)
async def upload_document(
    file: UploadFile = File(...),
    document_type: str = Query("OTHER"),
    batch_id: Optional[UUID] = Query(None),
    vendor_id: Optional[UUID] = Query(None),
    current_user: Optional[User] = Depends(get_optional_current_user),
    db: Session = Depends(get_db),
):
    upload_dir = os.path.join(settings.UPLOAD_DIR, "documents")
    os.makedirs(upload_dir, exist_ok=True)
    clean_filename = f"{uuid.uuid4().hex[:8]}_{file.filename}"
    file_path = os.path.join(upload_dir, clean_filename)

    contents = await file.read()
    with open(file_path, "wb") as f:
        f.write(contents)

    target_company_id = current_user.company_id if current_user else None
    assigned_vendor_id = vendor_id
    if batch_id:
        b = db.query(Batch).filter(Batch.id == batch_id).first()
        if b:
            if not target_company_id:
                target_company_id = b.company_id
            if not assigned_vendor_id:
                assigned_vendor_id = b.vendor_id

    if not target_company_id and assigned_vendor_id:
        v = db.query(Vendor).filter(Vendor.id == assigned_vendor_id).first()
        if v:
            target_company_id = v.company_id

    if not target_company_id:
        default_company = db.query(Company).first()
        if default_company:
            target_company_id = default_company.id

    doc = Document(
        company_id=target_company_id,
        batch_id=batch_id,
        vendor_id=assigned_vendor_id,
        file_name=file.filename,
        file_path=file_path,
        document_type=document_type.upper(),
        mime_type=file.content_type or "application/pdf",
        file_size=len(contents),
        uploaded_by=current_user.id if current_user else None,
        processing_status="UPLOADED",
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)

    # Process document details (PDF parsing & extraction)
    from app.services.document_service import DocumentProcessingService
    from app.schemas.document import DocumentType as DocTypeEnum
    
    doc_svc = DocumentProcessingService()
    try:
        dt_enum = DocTypeEnum(doc.document_type)
    except Exception:
        dt_enum = DocTypeEnum.OTHER

    proc_result = doc_svc.process_document(
        file_source=file_path,
        filename=file.filename,
        document_type=dt_enum,
        document_id=doc.id,
    )
    doc.extracted_data = proc_result.extracted_data
    doc.processing_status = proc_result.status.value
    doc.extraction_error = proc_result.error
    doc.processed_at = datetime.now(timezone.utc)
    db.add(doc)
    db.commit()

    # If associated with a batch, auto-run complete qualification pipeline & update genuine analytics
    if batch_id:
        try:
            batch = db.query(Batch).filter(Batch.id == batch_id).first()
            if batch:
                if dt_enum == DocTypeEnum.COA and proc_result.extracted_data.get("purity") is not None:
                    if batch.purity_reported is None:
                        batch.purity_reported = proc_result.extracted_data.get("purity")
                        db.add(batch)
                        db.commit()
                from app.services.pipeline_service import run_full_batch_pipeline
                run_full_batch_pipeline(db, batch)
        except Exception:
            pass

    return {
        "id": str(doc.id),
        "filename": doc.filename,
        "original_filename": doc.file_name,
        "document_type": doc.document_type,
        "file_size": doc.file_size,
        "status": doc.status,
        "extraction_status": doc.processing_status,
        "batch_id": str(doc.batch_id) if doc.batch_id else None,
        "vendor_id": str(doc.vendor_id) if doc.vendor_id else None,
        "extracted_data": doc.extracted_data,
        "message": "Document uploaded, parsed, and analyzed successfully."
    }


@router.get("/{document_id}")
def get_document(
    document_id: UUID,
    db: Session = Depends(get_db),
):
    doc = (
        db.query(Document)
        .options(joinedload(Document.vendor), joinedload(Document.batch))
        .filter(Document.id == document_id)
        .first()
    )
    if not doc:
        raise NotFoundError(f"Document with ID '{document_id}' not found")

    vendor_name = doc.vendor.vendor_name if doc.vendor else None
    batch_number = doc.batch.batch_number if doc.batch else None

    return {
        "id": str(doc.id),
        "filename": doc.filename,
        "original_filename": doc.file_name,
        "document_type": doc.document_type,
        "status": doc.status,
        "extraction_status": doc.processing_status,
        "file_size": doc.file_size,
        "file_path": doc.file_path,
        "mime_type": doc.mime_type,
        "batch_id": str(doc.batch_id) if doc.batch_id else None,
        "batch_number": batch_number,
        "vendor_id": str(doc.vendor_id) if doc.vendor_id else None,
        "vendor_name": vendor_name,
        "created_at": doc.created_at.isoformat() if doc.created_at else None,
        "processed_at": doc.processed_at.isoformat() if doc.processed_at else None,
        "extracted_data": doc.extracted_data,
        "extraction_error": doc.extraction_error,
    }


@router.get("/{document_id}/download")
def download_document(
    document_id: UUID,
    db: Session = Depends(get_db),
):
    doc = db.query(Document).filter(Document.id == document_id).first()
    if not doc:
        raise NotFoundError(f"Document with ID '{document_id}' not found")
    
    target_path = doc.file_path
    if not os.path.exists(target_path):
        normalized = target_path.replace("\\", "/")
        if os.path.exists(normalized):
            target_path = normalized
        else:
            base_filename = os.path.basename(doc.file_path)
            cand1 = os.path.join(settings.UPLOAD_DIR, base_filename)
            cand2 = os.path.join(settings.UPLOAD_DIR, "documents", base_filename)
            if os.path.exists(cand1):
                target_path = cand1
            elif os.path.exists(cand2):
                target_path = cand2
            else:
                raise NotFoundError(f"Document file '{doc.file_name}' not found on storage")

    return FileResponse(
        path=target_path,
        filename=doc.file_name,
        media_type=doc.mime_type or "application/pdf",
    )


@router.delete("/{document_id}")
def delete_document(
    document_id: UUID,
    db: Session = Depends(get_db),
):
    doc = db.query(Document).filter(Document.id == document_id).first()
    if not doc:
        raise NotFoundError(f"Document with ID '{document_id}' not found")
    try:
        if os.path.exists(doc.file_path):
            os.remove(doc.file_path)
    except Exception:
        pass
    db.delete(doc)
    db.commit()
    return {"message": "Document deleted successfully"}

