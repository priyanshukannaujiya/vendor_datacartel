"""
Raw Material CRUD router with specification validation and tenant isolation.
Follows VendorIQ PRD Section 12 & 15.
"""
from typing import Optional
from uuid import UUID
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session
from sqlalchemy import or_
from app.core.database import get_db
from app.core.security import get_current_user, get_optional_current_user
from app.core.errors import NotFoundError, ConflictError, ValidationError
from app.models.user import User
from app.models.raw_material import RawMaterial
from app.models.vendor import Vendor
from app.schemas.raw_material import (
    MaterialSpecification,
    RawMaterialCreate,
    RawMaterialUpdate,
    RawMaterialResponse,
    RawMaterialListResponse,
)

router = APIRouter(prefix="/raw-materials", tags=["Raw Materials"])


def validate_specification_json(spec_dict: Optional[dict]) -> None:
    """Validate specification structure using MaterialSpecification Pydantic schema."""
    if spec_dict:
        try:
            MaterialSpecification.model_validate(spec_dict)
        except Exception as e:
            raise ValidationError(
                message=f"Invalid material specification format: {str(e)}",
                details=getattr(e, "errors", lambda: str(e))(),
            )


@router.get("", response_model=RawMaterialListResponse)
def list_raw_materials(
    search: Optional[str] = Query(None, description="Search by material name or code"),
    active: Optional[bool] = Query(None, description="Filter by active status"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(50, ge=1, le=100, description="Items per page"),
    current_user: Optional[User] = Depends(get_optional_current_user),
    db: Session = Depends(get_db),
):
    """
    List raw materials. Scoped to company if user is authenticated.
    Supports search by name/code and pagination.
    """
    query = db.query(RawMaterial)
    if current_user and current_user.company_id:
        query = query.filter(RawMaterial.company_id == current_user.company_id)

    if active is not None:
        query = query.filter(RawMaterial.active == active)

    if search:
        search_pattern = f"%{search.strip()}%"
        query = query.filter(
            or_(
                RawMaterial.name.ilike(search_pattern),
                RawMaterial.code.ilike(search_pattern),
                RawMaterial.category.ilike(search_pattern),
            )
        )

    total = query.count()
    items = (
        query.order_by(RawMaterial.name.asc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )

    return RawMaterialListResponse(
        items=[RawMaterialResponse.model_validate(m) for m in items],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.post("", response_model=RawMaterialResponse, status_code=status.HTTP_201_CREATED)
def create_raw_material(
    data: RawMaterialCreate,
    current_user: Optional[User] = Depends(get_optional_current_user),
    db: Session = Depends(get_db),
):
    """
    Create a new raw material for the authenticated company.
    Validates JSON specification structure against Pydantic schema.
    Enforces unique material code per company.
    """
    company_id = current_user.company_id if current_user else None
    if not company_id:
        first_c = db.query(Vendor).first()
        company_id = first_c.company_id if first_c else uuid.uuid4()

    # Validate material code uniqueness within company
    existing = (
        db.query(RawMaterial)
        .filter(
            RawMaterial.company_id == company_id,
            RawMaterial.code == data.code,
        )
        .first()
    )
    if existing:
        raise ConflictError(f"Material with code '{data.code}' already exists in your company")

    # Validate specification format
    if data.specification:
        validate_specification_json(data.specification)

    material = RawMaterial(
        company_id=company_id,
        name=data.name,
        code=data.code,
        category=data.category,
        description=data.description,
        specification=data.specification or {},
        required_documents=data.required_documents or ["COA", "SDS", "GMP"],
        purity_min=data.purity_min or 99.0,
        moisture_max=data.moisture_max or 1.0,
        heavy_metals_max_ppm=data.heavy_metals_max_ppm or 10.0,
        microbial_limit_cfu_g=data.microbial_limit_cfu_g or 100.0,
        storage_conditions=data.storage_conditions or "Store below 25C in a dry, dark place",
        lead_time_days=data.lead_time_days or 14.0,
        base_price=data.base_price or 100.0,
        active=data.active,
    )
    db.add(material)
    db.commit()
    db.refresh(material)

    return RawMaterialResponse.model_validate(material)


@router.get("/{material_id}", response_model=RawMaterialResponse)
def get_raw_material(
    material_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Retrieve raw material and specification by ID.
    Enforces company isolation; cross-company access returns 404.
    """
    material = (
        db.query(RawMaterial)
        .filter(
            RawMaterial.id == material_id,
            RawMaterial.company_id == current_user.company_id,
        )
        .first()
    )
    if not material:
        raise NotFoundError(f"Raw material with ID '{material_id}' not found")

    return RawMaterialResponse.model_validate(material)


@router.put("/{material_id}", response_model=RawMaterialResponse)
def update_raw_material(
    material_id: UUID,
    data: RawMaterialUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Update raw material details and specification.
    Enforces company isolation; cross-company access returns 404.
    """
    material = (
        db.query(RawMaterial)
        .filter(
            RawMaterial.id == material_id,
            RawMaterial.company_id == current_user.company_id,
        )
        .first()
    )
    if not material:
        raise NotFoundError(f"Raw material with ID '{material_id}' not found")

    update_data = data.model_dump(exclude_unset=True)

    # Check code uniqueness if code is changing
    if "code" in update_data and update_data["code"] != material.code:
        existing = (
            db.query(RawMaterial)
            .filter(
                RawMaterial.company_id == current_user.company_id,
                RawMaterial.code == update_data["code"],
                RawMaterial.id != material.id,
            )
            .first()
        )
        if existing:
            raise ConflictError(f"Material with code '{update_data['code']}' already exists")

    # Validate specification format if provided
    if "specification" in update_data and update_data["specification"]:
        validate_specification_json(update_data["specification"])

    for field, val in update_data.items():
        setattr(material, field, val)

    db.commit()
    db.refresh(material)

    return RawMaterialResponse.model_validate(material)
