"""
Documents router for listing, retrieving, and managing supplier/batch documents in VendorIQ.
"""
import os
import uuid
from typing import Optional, List
from uuid import UUID
from fastapi import APIRouter, Depends, Query, status, HTTPException, UploadFile, File
from sqlalchemy.orm import Session
from sqlalchemy import desc

from app.core.database import get_db
from app.core.config import settings
from app.core.errors import NotFoundError
from app.models.document import Document
from app.models.batch import Batch
from app.models.vendor import Vendor

router = APIRouter(prefix="/documents", tags=["Documents"])


@router.get("")
def list_documents(
    batch_id: Optional[UUID] = Query(None, description="Filter by batch ID"),
    vendor_id: Optional[UUID] = Query(None, description="Filter by vendor ID"),
    document_type: Optional[str] = Query(None, description="Filter by document type (COA, SDS, GMP, etc.)"),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db),
):
    query = db.query(Document)
    if batch_id:
        query = query.filter(Document.batch_id == batch_id)
    if vendor_id:
        query = query.filter(Document.vendor_id == vendor_id)
    if document_type:
        query = query.filter(Document.document_type.ilike(f"%{document_type}%"))

    total = query.count()
    docs = (
        query.order_by(desc(Document.created_at))
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
            "document_type": d.document_type,
            "status": d.status,
            "file_size": d.file_size,
            "file_path": d.file_path,
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


@router.post("", status_code=status.HTTP_201_CREATED)
async def upload_document(
    file: UploadFile = File(...),
    document_type: str = Query("OTHER"),
    batch_id: Optional[UUID] = Query(None),
    vendor_id: Optional[UUID] = Query(None),
    db: Session = Depends(get_db),
):
    upload_dir = settings.UPLOAD_DIR
    os.makedirs(upload_dir, exist_ok=True)
    clean_filename = f"{uuid.uuid4()[:8]}_{file.filename}"
    file_path = os.path.join(upload_dir, clean_filename)

    contents = await file.read()
    with open(file_path, "wb") as f:
        f.write(contents)

    doc = Document(
        batch_id=batch_id,
        vendor_id=vendor_id,
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

    return {
        "id": str(doc.id),
        "filename": doc.filename,
        "document_type": doc.document_type,
        "file_size": doc.file_size,
        "status": doc.status,
        "message": "Document uploaded successfully."
    }


@router.get("/{document_id}")
def get_document(
    document_id: UUID,
    db: Session = Depends(get_db),
):
    doc = db.query(Document).filter(Document.id == document_id).first()
    if not doc:
        raise NotFoundError(f"Document with ID '{document_id}' not found")

    return {
        "id": str(doc.id),
        "filename": doc.filename,
        "document_type": doc.document_type,
        "status": doc.status,
        "file_size": doc.file_size,
        "file_path": doc.file_path,
        "batch_id": str(doc.batch_id) if doc.batch_id else None,
        "vendor_id": str(doc.vendor_id) if doc.vendor_id else None,
        "created_at": doc.created_at.isoformat() if doc.created_at else None,
        "processed_at": doc.processed_at.isoformat() if doc.processed_at else None,
        "extracted_data": doc.extracted_data,
        "extraction_error": doc.extraction_error,
    }
