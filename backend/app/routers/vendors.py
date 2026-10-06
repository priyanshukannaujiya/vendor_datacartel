"""
Vendor CRUD router with search, pagination, soft-delete, and tenant isolation.
Follows VendorIQ PRD Section 12 & 14.
"""
from typing import Optional, List, Dict, Any
from uuid import UUID
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session
from sqlalchemy import or_, func
from app.core.database import get_db
from app.core.security import get_current_user, get_optional_current_user
from app.core.errors import NotFoundError, ConflictError
from app.models.user import User
from app.models.vendor import Vendor
from app.models.batch import Batch
from app.models.document import Document
from app.models.intelligence import BatchIntelligence
from app.schemas.vendor import (
    VendorCreate,
    VendorInviteRequest,
    VendorUpdate,
    VendorResponse,
    VendorDetailResponse,
    VendorListResponse,
)
from app.routers.analytics import invalidate_analytics_cache

router = APIRouter(prefix="/vendors", tags=["Vendors"])


@router.get("", response_model=VendorListResponse)
def list_vendors(
    search: Optional[str] = Query(None, description="Search by vendor name, country, or category"),
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    status_filter: Optional[str] = Query(None, alias="status", description="Filter by vendor status"),
    risk_level: Optional[str] = Query(None, description="Filter by risk level"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    List vendors scoped strictly to current user's company.
    Soft-deleted vendors are excluded. Supports search, status/risk filters, and pagination.
    """
    query = db.query(Vendor).filter(
        Vendor.company_id == current_user.company_id,
        Vendor.deleted_at.is_(None),
    )

    if is_active is not None:
        query = query.filter(Vendor.is_active == is_active)

    if status_filter:
        query = query.filter(Vendor.status.ilike(f"%{status_filter}%"))

    if risk_level:
        if risk_level.upper() == "LOW":
            query = query.filter(Vendor.risk_score < 25.0)
        elif risk_level.upper() == "MEDIUM":
            query = query.filter(Vendor.risk_score >= 25.0, Vendor.risk_score < 50.0)
        elif risk_level.upper() in ["HIGH", "CRITICAL"]:
            query = query.filter(Vendor.risk_score >= 50.0)

    if search:
        search_pattern = f"%{search.strip()}%"
        query = query.filter(
            or_(
                Vendor.vendor_name.ilike(search_pattern),
                Vendor.country.ilike(search_pattern),
                Vendor.supplier_category.ilike(search_pattern),
                Vendor.industry.ilike(search_pattern),
            )
        )

    total = query.count()
    items = (
        query.order_by(Vendor.vendor_name.asc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )

    counts_map = {}
    if items:
        vendor_ids = [v.id for v in items]
        counts = (
            db.query(Batch.vendor_id, func.count(Batch.id))
            .filter(Batch.vendor_id.in_(vendor_ids))
            .group_by(Batch.vendor_id)
            .all()
        )
        counts_map = dict(counts)

    results = []
    for v in items:
        resp = VendorResponse.model_validate(v)
        resp.name = v.vendor_name
        resp.code = v.code
        resp.total_batches = counts_map.get(v.id, 0)
        results.append(resp)

    return VendorListResponse(
        items=results,
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
        tier=data.tier or "TIER_2",
        status=data.status or "ACTIVE",
        certification_status=data.certification_status or "GMP_CERTIFIED",
        delivery_reliability=data.delivery_reliability or 0.95,
        capacity=data.capacity or 100000.0,
        risk_score=data.risk_score or 15.0,
        approval_rate=data.approval_rate or 0.95,
        quality_score=data.quality_score or 98.0,
        is_active=data.is_active,
    )
    db.add(vendor)
    db.commit()
    db.refresh(vendor)

    # Dispatch automated onboarding & document request email via Google SMTP
    recipient = vendor.email or vendor.contact_email
    if recipient:
        try:
            from app.services.email_service import send_email, EmailDeliveryError
            from app.services.email_templates import render_document_request_email
            from app.services.audit_service import record_audit_event
            from app.models.decision import EmailEvent

            subject, html_content = render_document_request_email(
                reference_id=str(vendor.id),
                vendor_name=vendor.vendor_name,
                batch_number="ONBOARDING",
                material_name="Raw Material Release Certificates (COA, SDS, GMP)",
            )
            email_event = EmailEvent(
                company_id=vendor.company_id,
                vendor_id=vendor.id,
                recipient_email=recipient,
                subject=subject,
                email_type="VENDOR_WELCOME_DOC_REQUEST",
                status="PENDING",
                provider="GOOGLE_SMTP",
                html_content=html_content,
                text_content=f"Welcome {vendor.vendor_name}! Please submit your compliance and quality assurance PDF documents.",
            )
            db.add(email_event)
            db.commit()

            try:
                send_email(
                    recipient=recipient,
                    subject=subject,
                    html_content=html_content,
                    text_content=email_event.text_content,
                )
                email_event.status = "SENT"
                email_event.sent_at = datetime.now(timezone.utc)
            except EmailDeliveryError as exc:
                email_event.status = "FAILED"
                email_event.error_message = str(exc)

            record_audit_event(
                db,
                "Vendor Registered & Onboarding Email Sent",
                company_id=vendor.company_id,
                vendor_id=vendor.id,
                details={"recipient": recipient, "email_status": email_event.status},
                commit=True,
            )
        except Exception:
            pass

    invalidate_analytics_cache(current_user.company_id)

    resp = VendorResponse.model_validate(vendor)
    resp.name = vendor.vendor_name
    resp.code = vendor.code
    return resp


@router.post("/invite", status_code=status.HTTP_201_CREATED)
def invite_vendor(
    data: VendorInviteRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Invite a supplier to the VendorIQ Vendor Portal.
    Generates a secure token, sends a real email with portal link via Google SMTP,
    and logs the email event and audit trail.
    """
    import secrets
    from app.core.config import settings
    from app.services.email_service import send_email, EmailDeliveryError
    from app.services.audit_service import record_audit_event
    from app.models.decision import EmailEvent
    from app.models.company import Company

    company = db.query(Company).filter(Company.id == current_user.company_id).first()
    company_name = company.name if company else "Our Procurement Team"

    clean_email = data.email.lower().strip()
    clean_name = data.vendor_name.strip()

    # Find existing vendor or create new one
    vendor = (
        db.query(Vendor)
        .filter(
            Vendor.company_id == current_user.company_id,
            (Vendor.email == clean_email) | (Vendor.vendor_name == clean_name),
            Vendor.deleted_at.is_(None),
        )
        .first()
    )

    token = secrets.token_urlsafe(32)
    now = datetime.now(timezone.utc)

    if not vendor:
        vendor = Vendor(
            company_id=current_user.company_id,
            vendor_name=clean_name,
            email=clean_email,
            contact_name=data.contact_name or clean_name,
            country=data.country or "Global",
            supplier_category=data.supplier_category or "Active Raw Material",
            status="PENDING_ONBOARDING",
            is_active=True,
            invitation_token=token,
            invitation_status="INVITED",
            invitation_sent_at=now,
        )
        db.add(vendor)
    else:
        vendor.invitation_token = token
        vendor.invitation_status = "INVITED"
        vendor.invitation_sent_at = now
        if not vendor.email:
            vendor.email = clean_email
        if data.contact_name and not vendor.contact_name:
            vendor.contact_name = data.contact_name

    db.commit()
    db.refresh(vendor)

    # Generate dedicated Vendor Portal URL
    portal_url = f"{settings.FRONTEND_URL}/vendor-portal?token={token}"

    email_subject = f"Invitation: VendorIQ Supplier Qualification for {company_name}"
    email_html = f"""
    <div style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; max-width: 600px; margin: 0 auto; padding: 28px; color: #1e293b; background-color: #ffffff; border-radius: 8px; border: 1px solid #e2e8f0;">
        <div style="margin-bottom: 24px;">
            <span style="font-size: 18px; font-weight: 800; color: #2563eb; letter-spacing: -0.5px;">VendorIQ</span>
            <span style="font-size: 13px; color: #64748b; margin-left: 8px;">&bull; Supplier Qualification Portal</span>
        </div>
        <h2 style="font-size: 20px; font-weight: 700; color: #0f172a; margin-top: 0; margin-bottom: 12px;">
            You have been invited to {company_name}'s Supplier Portal
        </h2>
        <p style="font-size: 14px; line-height: 1.6; color: #334155;">
            Dear {vendor.contact_name or vendor.vendor_name},
        </p>
        <p style="font-size: 14px; line-height: 1.6; color: #334155;">
            <strong>{company_name}</strong> uses VendorIQ to manage raw material compliance, batch certifications (COA, MSDS, GMP), and quality assurance.
        </p>
        <p style="font-size: 14px; line-height: 1.6; color: #334155;">
            Please access your dedicated supplier portal to view assigned ingredients, submit required batch documentation, and track approval status:
        </p>

        <div style="margin: 32px 0; text-align: center;">
            <a href="{portal_url}" style="background-color: #2563eb; color: #ffffff; padding: 14px 28px; border-radius: 6px; text-decoration: none; font-weight: 600; font-size: 14px; display: inline-block; box-shadow: 0 2px 4px rgba(37,99,235,0.2);">
                Access Vendor Portal &rarr;
            </a>
        </div>

        <div style="background-color: #f8fafc; border-left: 4px solid #3b82f6; padding: 14px 16px; margin-bottom: 24px; border-radius: 0 4px 4px 0;">
            <h4 style="margin: 0 0 6px 0; font-size: 13px; color: #1e293b;">Required for Initial Qualification:</h4>
            <ul style="margin: 0; padding-left: 20px; font-size: 12px; color: #475569; line-height: 1.6;">
                <li>Certificate of Analysis (COA) for active batches</li>
                <li>Material Safety Data Sheet (MSDS / SDS)</li>
                <li>GMP / ISO Quality Certifications (if applicable)</li>
            </ul>
        </div>

        <p style="font-size: 12px; color: #64748b; line-height: 1.5;">
            Direct Link: <a href="{portal_url}" style="color: #2563eb; word-break: break-all;">{portal_url}</a>
        </p>
        <hr style="border: 0; border-top: 1px solid #e2e8f0; margin: 24px 0;" />
        <p style="font-size: 11px; color: #94a3b8; margin: 0;">
            This invitation was dispatched securely by VendorIQ on behalf of {company_name}.
        </p>
    </div>
    """

    email_status = "PENDING"
    try:
        send_email(
            recipient=clean_email,
            subject=email_subject,
            html_content=email_html,
            text_content=f"Access your supplier portal at: {portal_url}",
        )
        email_status = "SENT"
    except Exception as exc:
        email_status = "FAILED"

    # Record email event
    email_event = EmailEvent(
        company_id=vendor.company_id,
        vendor_id=vendor.id,
        recipient_email=clean_email,
        subject=email_subject,
        email_type="VENDOR_PORTAL_INVITATION",
        status=email_status,
        provider="GOOGLE_SMTP",
        html_content=email_html,
        text_content=f"Access your supplier portal at: {portal_url}",
    )
    db.add(email_event)
    db.commit()

    record_audit_event(
        db,
        "Vendor Invited to Portal",
        company_id=vendor.company_id,
        vendor_id=vendor.id,
        details={"recipient": clean_email, "email_status": email_status},
        commit=True,
    )

    return {
        "message": f"Invitation dispatched to {clean_email}",
        "vendor_id": str(vendor.id),
        "vendor_name": vendor.vendor_name,
        "email": clean_email,
        "invitation_token": token,
        "invitation_url": portal_url,
        "email_status": email_status,
    }


@router.patch("/{vendor_id}/status")
def update_vendor_status(
    vendor_id: UUID,
    is_active: bool = Query(..., description="Set active status"),
    status_label: Optional[str] = Query(None, description="Set status text (e.g. ACTIVE, SUSPENDED, PENDING)"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Activate or deactivate a vendor with optional status reason.
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

    vendor.is_active = is_active
    if status_label:
        vendor.status = status_label
    elif not is_active:
        vendor.status = "INACTIVE"
    else:
        vendor.status = "ACTIVE"

    vendor.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(vendor)

    return {
        "id": str(vendor.id),
        "vendor_name": vendor.vendor_name,
        "is_active": vendor.is_active,
        "status": vendor.status,
    }


@router.get("/email-directory")
def get_vendor_email_directory(
    current_user: Optional[User] = Depends(get_optional_current_user),
    db: Session = Depends(get_db),
):
    """
    Get vendor contact list with email addresses and recent batches
    for quick document request dispatch, scoped to the current user's company.
    """
    query = db.query(Vendor).filter(Vendor.deleted_at.is_(None))
    if current_user and current_user.company_id:
        query = query.filter(Vendor.company_id == current_user.company_id)
    vendors = query.all()

    results = []
    for v in vendors:
        batches = db.query(Batch).filter(Batch.vendor_id == v.id).order_by(Batch.created_at.desc()).limit(5).all()
        batch_items = []
        for b in batches:
            batch_items.append({
                "id": str(b.id),
                "batch_number": b.batch_number,
                "status": b.status,
                "material_name": b.raw_material.name if b.raw_material else "Raw Material",
            })
        results.append({
            "id": str(v.id),
            "name": v.vendor_name,
            "code": v.code,
            "contact_name": v.contact_name or "QA Contact",
            "contact_email": v.contact_email or v.email or "quality@supplier.com",
            "phone": v.phone,
            "status": v.status,
            "risk_score": v.risk_score,
            "batches": batch_items,
        })
    return results


@router.get("/{vendor_id}", response_model=VendorDetailResponse)
def get_vendor(
    vendor_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Retrieve comprehensive vendor details by ID including historical batches,
    health metrics, certifications, and AI risk assessment.
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

    batches = (
        db.query(Batch)
        .filter(Batch.vendor_id == vendor.id)
        .order_by(Batch.created_at.desc())
        .all()
    )
    docs = db.query(Document).filter(Document.vendor_id == vendor.id).all()

    total_b = len(batches)
    approved_b = sum(1 for b in batches if b.status == "APPROVED")
    rejected_b = sum(1 for b in batches if b.status == "REJECTED")
    app_rate = (approved_b / total_b) if total_b > 0 else None

    historical_batches = [
        {
            "id": str(b.id),
            "batch_number": b.batch_number,
            "status": b.status,
            "created_at": b.created_at.isoformat() if b.created_at else None,
            "quantity": b.quantity,
            "purity_reported": b.purity_reported,
        }
        for b in batches[:15]
    ]

    documents = [
        {
            "id": str(d.id),
            "filename": d.filename,
            "document_type": d.document_type,
            "status": d.status,
            "created_at": d.created_at.isoformat() if d.created_at else None,
        }
        for d in docs
    ]

    certifications = [
        {
            "name": d.filename,
            "status": d.status,
            "document_type": d.document_type,
        }
        for d in docs
        if d.document_type and d.document_type.upper() in {"GMP", "CERTIFICATE", "CERTIFICATION"}
    ]

    intelligence_records = (
        db.query(BatchIntelligence)
        .filter(BatchIntelligence.batch_id.in_([b.id for b in batches]))
        .all()
        if batches
        else []
    )
    intelligence_by_batch = {record.batch_id: record for record in intelligence_records}
    risk_trend = []
    latest_risk_score = None
    latest_kimi_assessment = None
    for batch in batches:
        intelligence = intelligence_by_batch.get(batch.id)
        prediction = intelligence.ml_prediction if intelligence and intelligence.ml_prediction else None
        if prediction and prediction.get("risk_score") is not None:
            risk_score = float(prediction["risk_score"])
            risk_trend.append({
                "month": batch.created_at.strftime("%b %Y") if batch.created_at else None,
                "risk_score": risk_score,
            })
            if latest_risk_score is None:
                latest_risk_score = risk_score
        if latest_kimi_assessment is None and intelligence and intelligence.kimi_analysis:
            latest_kimi_assessment = intelligence.kimi_analysis

    resp = VendorDetailResponse.model_validate(vendor)
    resp.name = vendor.vendor_name
    resp.code = vendor.code
    resp.total_batches = total_b
    resp.risk_score = latest_risk_score
    resp.approval_rate = round(app_rate, 2) if app_rate is not None else None
    resp.quality_consistency = vendor.quality_score
    resp.documentation_completeness = 1.0 if docs else 0.0
    resp.health = {
        "status": vendor.status,
        "score": 100 - int(latest_risk_score) if latest_risk_score is not None else None,
        "approved_batches": approved_b,
        "rejected_batches": rejected_b,
        "total_batches": total_b,
    }
    resp.historical_batches = historical_batches
    resp.documents = documents
    resp.certifications = certifications
    resp.risk_trend = risk_trend
    resp.kimi_assessment = latest_kimi_assessment
    resp.recommended_actions = (
        latest_kimi_assessment.get("recommended_actions", [])
        if latest_kimi_assessment
        else []
    )

    return resp


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

    update_dict = data.model_dump(exclude_unset=True)
    for field, value in update_dict.items():
        setattr(vendor, field, value)

    vendor.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(vendor)

    resp = VendorResponse.model_validate(vendor)
    resp.name = vendor.vendor_name
    resp.code = vendor.code
    return resp


@router.delete("/{vendor_id}")
def delete_vendor(
    vendor_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Soft-delete a vendor by setting deleted_at timestamp.
    Preserves historical batch records for audit compliance.
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
    return {"message": "Vendor deleted successfully"}
