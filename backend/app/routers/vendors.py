"""
Vendor CRUD router with search, pagination, soft-delete, and tenant isolation.
Follows VendorIQ PRD Section 12 & 14.
"""
from typing import Optional
from uuid import UUID
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session
from sqlalchemy import or_, func
from app.core.database import get_db
from app.core.security import get_current_user
from app.core.errors import NotFoundError, ConflictError
from app.models.user import User
from app.models.vendor import Vendor
from app.schemas.vendor import (
    VendorCreate,
    VendorUpdate,
    VendorResponse,
    VendorListResponse,
)

router = APIRouter(prefix="/vendors", tags=["Vendors"])


@router.get("", response_model=VendorListResponse)
def list_vendors(
    search: Optional[str] = Query(None, description="Search by vendor name, country, or category"),
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    List vendors scoped strictly to current user's company.
    Soft-deleted vendors are excluded. Supports search and pagination.
    """
    query = db.query(Vendor).filter(
        Vendor.company_id == current_user.company_id,
        Vendor.deleted_at.is_(None),
    )

    if is_active is not None:
        query = query.filter(Vendor.is_active == is_active)

    if search:
        search_pattern = f"%{search.strip()}%"
        query = query.filter(
            or_(
                Vendor.vendor_name.ilike(search_pattern),
                Vendor.country.ilike(search_pattern),
                Vendor.supplier_category.ilike(search_pattern),
            )
        )

    total = query.count()
    items = (
        query.order_by(Vendor.vendor_name.asc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )

    return VendorListResponse(
        items=[VendorResponse.model_validate(v) for v in items],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.post("", response_model=VendorResponse, status_code=status.HTTP_201_CREATED)
def create_vendor(
    data: VendorCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Create a new vendor for the authenticated company.
    Prevents duplicate active vendors with identical names in the same company.
    """
    existing = (
        db.query(Vendor)
        .filter(
            Vendor.company_id == current_user.company_id,
            Vendor.vendor_name == data.vendor_name,
            Vendor.deleted_at.is_(None),
        )
        .first()
    )
    if existing:
        raise ConflictError(f"Vendor '{data.vendor_name}' already exists in your company")

    vendor = Vendor(
        company_id=current_user.company_id,
        vendor_name=data.vendor_name,
        company_registration_id=data.company_registration_id,
        country=data.country,
        contact_name=data.contact_name,
        email=data.email,
        phone=data.phone,
        address=data.address,
        industry=data.industry,
        supplier_category=data.supplier_category,
        is_active=data.is_active,
    )
    db.add(vendor)
    db.commit()
    db.refresh(vendor)

    return VendorResponse.model_validate(vendor)


@router.get("/{vendor_id}", response_model=VendorResponse)
def get_vendor(
    vendor_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Retrieve vendor details by ID.
    Enforces company isolation; cross-company access returns 404.
    """
    vendor = (
        db.query(Vendor)
        .filter(
            Vendor.id == vendor_id,
            Vendor.company_id == current_user.company_id,
            Vendor.deleted_at.is_(None),
        )
        .first()
    )
    if not vendor:
        raise NotFoundError(f"Vendor with ID '{vendor_id}' not found")

    return VendorResponse.model_validate(vendor)


@router.put("/{vendor_id}", response_model=VendorResponse)
def update_vendor(
    vendor_id: UUID,
    data: VendorUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Update vendor details.
    Enforces company isolation; cross-company access returns 404.
    """
    vendor = (
        db.query(Vendor)
        .filter(
            Vendor.id == vendor_id,
            Vendor.company_id == current_user.company_id,
            Vendor.deleted_at.is_(None),
        )
        .first()
    )
    if not vendor:
        raise NotFoundError(f"Vendor with ID '{vendor_id}' not found")

    update_data = data.model_dump(exclude_unset=True)
    if "vendor_name" in update_data and update_data["vendor_name"] != vendor.vendor_name:
        existing = (
            db.query(Vendor)
            .filter(
                Vendor.company_id == current_user.company_id,
                Vendor.vendor_name == update_data["vendor_name"],
                Vendor.id != vendor.id,
                Vendor.deleted_at.is_(None),
            )
            .first()
        )
        if existing:
            raise ConflictError(f"Vendor '{update_data['vendor_name']}' already exists")

    for field, val in update_data.items():
        setattr(vendor, field, val)

    db.commit()
    db.refresh(vendor)
    return VendorResponse.model_validate(vendor)


@router.delete("/{vendor_id}", status_code=status.HTTP_200_OK)
def delete_vendor(
    vendor_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Soft-delete a vendor (sets deleted_at timestamp and is_active=False).
    Enforces company isolation; cross-company access returns 404.
    """
    vendor = (
        db.query(Vendor)
        .filter(
            Vendor.id == vendor_id,
            Vendor.company_id == current_user.company_id,
            Vendor.deleted_at.is_(None),
        )
        .first()
    )
    if not vendor:
        raise NotFoundError(f"Vendor with ID '{vendor_id}' not found")

    vendor.deleted_at = datetime.now(timezone.utc)
    vendor.is_active = False
    db.commit()

    return {"message": f"Vendor '{vendor.vendor_name}' deleted successfully", "id": str(vendor.id)}
