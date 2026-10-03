"""
Batch management router for incoming ingredient batches.
Follows VendorIQ PRD Section 12 & 16.
"""
from typing import Optional
from uuid import UUID
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.security import get_current_user
from app.core.errors import NotFoundError, ConflictError, BadRequestError
from app.models.user import User
from app.models.vendor import Vendor
from app.models.raw_material import RawMaterial
from app.models.vendor_material import VendorMaterial
from app.models.batch import Batch
from app.schemas.batch import (
    BatchCreate,
    BatchResponse,
    BatchListResponse,
)

router = APIRouter(prefix="/batches", tags=["Batches"])


@router.get("", response_model=BatchListResponse)
def list_batches(
    status_filter: Optional[str] = Query(None, alias="status", description="Filter by batch status"),
    vendor_id: Optional[UUID] = Query(None, description="Filter by vendor ID"),
    raw_material_id: Optional[UUID] = Query(None, description="Filter by raw material ID"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    List batches scoped strictly to current user's company.
    Supports filtering by status, vendor, and raw material.
    """
    query = db.query(Batch).filter(Batch.company_id == current_user.company_id)

    if status_filter:
        query = query.filter(Batch.status == status_filter)
    if vendor_id:
        query = query.filter(Batch.vendor_id == vendor_id)
    if raw_material_id:
        query = query.filter(Batch.raw_material_id == raw_material_id)

    total = query.count()
    items = (
        query.order_by(Batch.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )

    return BatchListResponse(
        items=[BatchResponse.model_validate(b) for b in items],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.post("", response_model=BatchResponse, status_code=status.HTTP_201_CREATED)
def create_batch(
    data: BatchCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Create an incoming raw material batch with initial status 'RECEIVED'.
    Validates vendor and material tenant ownership and active status.
    Flags warning if vendor is not approved for the material.
    Enforces uniqueness on (company_id, vendor_id, batch_number).
    """
    # 1. Verify vendor belongs to company and is active
    vendor = (
        db.query(Vendor)
        .filter(
            Vendor.id == data.vendor_id,
            Vendor.company_id == current_user.company_id,
            Vendor.deleted_at.is_(None),
        )
        .first()
    )
    if not vendor:
        raise NotFoundError(f"Vendor with ID '{data.vendor_id}' not found in your company")
    if not vendor.is_active:
        raise BadRequestError(f"Vendor '{vendor.vendor_name}' is inactive")

    # 2. Verify raw material belongs to company and is active
    material = (
        db.query(RawMaterial)
        .filter(
            RawMaterial.id == data.raw_material_id,
            RawMaterial.company_id == current_user.company_id,
        )
        .first()
    )
    if not material:
        raise NotFoundError(f"Raw material with ID '{data.raw_material_id}' not found in your company")
    if not material.active:
        raise BadRequestError(f"Raw material '{material.name}' is inactive")

    # 3. Check for duplicate batch number per vendor within company
    existing = (
        db.query(Batch)
        .filter(
            Batch.company_id == current_user.company_id,
            Batch.vendor_id == data.vendor_id,
            Batch.batch_number == data.batch_number,
        )
        .first()
    )
    if existing:
        raise ConflictError(
            f"Batch '{data.batch_number}' already exists for vendor '{vendor.vendor_name}' in your company"
        )

    # 4. Check vendor-material approval status (PRD configurable warning)
    warning_message = None
    vm_link = (
        db.query(VendorMaterial)
        .filter(
            VendorMaterial.vendor_id == data.vendor_id,
            VendorMaterial.raw_material_id == data.raw_material_id,
        )
        .first()
    )
    if not vm_link:
        warning_message = f"Warning: No vendor-material relationship found for vendor '{vendor.vendor_name}' and material '{material.name}'."
    elif not vm_link.is_approved:
        warning_message = f"Warning: Vendor '{vendor.vendor_name}' is not currently approved for raw material '{material.name}'."

    # 5. Create batch with initial status RECEIVED
    batch = Batch(
        company_id=current_user.company_id,
        vendor_id=data.vendor_id,
        raw_material_id=data.raw_material_id,
        batch_number=data.batch_number,
        manufacturing_date=data.manufacturing_date,
        expiry_date=data.expiry_date,
        quantity=data.quantity,
        unit=data.unit,
        price=data.price,
        expected_delivery_date=data.expected_delivery_date,
        actual_delivery_date=data.actual_delivery_date,
        status="RECEIVED",
        created_by=current_user.id,
    )
    db.add(batch)
    db.commit()
    db.refresh(batch)

    res = BatchResponse.model_validate(batch)
    if warning_message:
        res.warning = warning_message
    return res


@router.get("/{batch_id}", response_model=BatchResponse)
def get_batch(
    batch_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Retrieve batch details by ID.
    Enforces company isolation; cross-company access returns 404.
    """
    batch = (
        db.query(Batch)
        .filter(
            Batch.id == batch_id,
            Batch.company_id == current_user.company_id,
        )
        .first()
    )
    if not batch:
        raise NotFoundError(f"Batch with ID '{batch_id}' not found")

    return BatchResponse.model_validate(batch)
