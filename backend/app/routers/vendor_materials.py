"""
Vendor-Material link router managing qualified supplier/material mappings.
Follows VendorIQ PRD Section 12 & 16.
"""
from typing import Optional
from uuid import UUID
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.security import get_current_user
from app.core.errors import NotFoundError, ConflictError
from app.models.user import User
from app.models.vendor import Vendor
from app.models.raw_material import RawMaterial
from app.models.vendor_material import VendorMaterial
from app.schemas.vendor_material import (
    VendorMaterialCreate,
    VendorMaterialUpdate,
    VendorMaterialResponse,
    VendorMaterialListResponse,
)

router = APIRouter(prefix="/vendor-materials", tags=["Vendor Materials"])


@router.get("", response_model=VendorMaterialListResponse)
def list_vendor_materials(
    vendor_id: Optional[UUID] = Query(None, description="Filter by vendor ID"),
    raw_material_id: Optional[UUID] = Query(None, description="Filter by raw material ID"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    List vendor-material mappings scoped to current user's company.
    Supports filtering by vendor or raw material ID.
    """
    query = db.query(VendorMaterial).filter(VendorMaterial.company_id == current_user.company_id)

    if vendor_id:
        query = query.filter(VendorMaterial.vendor_id == vendor_id)
    if raw_material_id:
        query = query.filter(VendorMaterial.raw_material_id == raw_material_id)

    total = query.count()
    items = (
        query.order_by(VendorMaterial.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )

    return VendorMaterialListResponse(
        items=[VendorMaterialResponse.model_validate(vm) for vm in items],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.post("", response_model=VendorMaterialResponse, status_code=status.HTTP_201_CREATED)
def create_vendor_material(
    data: VendorMaterialCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Link a vendor to a raw material within the authenticated company.
    Verifies that both vendor and raw material exist and belong to the user's company.
    Prevents duplicate pairings.
    """
    # Verify vendor belongs to company
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

    # Verify raw material belongs to company
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

    # Prevent duplicate relationship
    existing = (
        db.query(VendorMaterial)
        .filter(
            VendorMaterial.vendor_id == data.vendor_id,
            VendorMaterial.raw_material_id == data.raw_material_id,
        )
        .first()
    )
    if existing:
        raise ConflictError("A relationship between this vendor and raw material already exists")

    approved_at = datetime.now(timezone.utc) if data.is_approved else None
    approved_by = current_user.id if data.is_approved else None

    vm = VendorMaterial(
        company_id=current_user.company_id,
        vendor_id=data.vendor_id,
        raw_material_id=data.raw_material_id,
        is_approved=data.is_approved,
        approved_at=approved_at,
        approved_by=approved_by,
        notes=data.notes,
    )
    db.add(vm)
    db.commit()
    db.refresh(vm)

    return VendorMaterialResponse.model_validate(vm)


@router.put("/{vm_id}", response_model=VendorMaterialResponse)
def update_vendor_material(
    vm_id: UUID,
    data: VendorMaterialUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Update vendor-material approval status and notes.
    Enforces company isolation; cross-company access returns 404.
    """
    vm = (
        db.query(VendorMaterial)
        .filter(
            VendorMaterial.id == vm_id,
            VendorMaterial.company_id == current_user.company_id,
        )
        .first()
    )
    if not vm:
        raise NotFoundError(f"Vendor-material mapping with ID '{vm_id}' not found")

    if data.is_approved is not None:
        if data.is_approved and not vm.is_approved:
            vm.is_approved = True
            vm.approved_at = datetime.now(timezone.utc)
            vm.approved_by = current_user.id
        elif not data.is_approved and vm.is_approved:
            vm.is_approved = False
            vm.approved_at = None
            vm.approved_by = None

    if data.notes is not None:
        vm.notes = data.notes

    db.commit()
    db.refresh(vm)

    return VendorMaterialResponse.model_validate(vm)
