"""
Demo seed data for VendorIQ.
Follows VendorIQ PRD Section 13, 15, 33:
- One demo company: "Skincare Innovations Ltd"
- One demo QA user: demo@vendoriq.com / DemoUser123!
- ABC Chemicals vendor (Active Ingredients)
- L-Ascorbic Acid (LAA-001) with internal specification purity >= 99% mandatory
- Approved vendor-material relationship
"""
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from app.core.database import SessionLocal, get_engine
from app.core.security import get_password_hash
from app.models.company import Company
from app.models.user import User
from app.models.vendor import Vendor
from app.models.raw_material import RawMaterial
from app.models.vendor_material import VendorMaterial

DEMO_COMPANY_NAME = "Skincare Innovations Ltd"
DEMO_USER_EMAIL = "demo@vendoriq.com"
DEMO_USER_PASSWORD = "DemoUser123!"


def seed_demo_data(db: Session) -> dict:
    """
    Seeds initial company, user, vendor, raw material, and approval link if not already present.
    Idempotent: skips existing records.
    """
    # 1. Seed or retrieve demo company
    company = db.query(Company).filter(Company.name == DEMO_COMPANY_NAME).first()
    if not company:
        company = Company(
            name=DEMO_COMPANY_NAME,
            industry="Cosmetics & Skincare Manufacturing",
            settings={
                "auto_approval_max_risk": "LOW",
                "min_document_completeness": 1.0,
                "critical_document_types": ["COA", "GMP"],
            },
        )
        db.add(company)
        db.flush()

    # 2. Seed demo user
    user = db.query(User).filter(User.email == DEMO_USER_EMAIL).first()
    if not user:
        user = User(
            company_id=company.id,
            email=DEMO_USER_EMAIL,
            password_hash=get_password_hash(DEMO_USER_PASSWORD),
            full_name="Dr. Eleanor Vance",
            role="qa_manager",
            is_active=True,
        )
        db.add(user)
        db.flush()

    # 3. Seed ABC Chemicals vendor
    vendor = (
        db.query(Vendor)
        .filter(
            Vendor.company_id == company.id,
            Vendor.vendor_name == "ABC Chemicals",
            Vendor.deleted_at.is_(None),
        )
        .first()
    )
    if not vendor:
        vendor = Vendor(
            company_id=company.id,
            vendor_name="ABC Chemicals",
            company_registration_id="REG-ABC-8891",
            country="United States",
            contact_name="Marcus Vance",
            email="supplies@abcchemicals.com",
            phone="+1-555-0199",
            address="450 Innovation Parkway, Wilmington, DE",
            industry="Chemicals Manufacturing",
            supplier_category="Active Ingredients",
            is_active=True,
        )
        db.add(vendor)
        db.flush()

    # 4. Seed L-Ascorbic Acid raw material
    material = (
        db.query(RawMaterial)
        .filter(
            RawMaterial.company_id == company.id,
            RawMaterial.code == "LAA-001",
        )
        .first()
    )
    if not material:
        material = RawMaterial(
            company_id=company.id,
            name="L-Ascorbic Acid",
            code="LAA-001",
            category="Active Ingredients",
            description="Ultra-pure pharmaceutical/cosmetic grade Vitamin C powder used in topical antioxidant serums.",
            specification={
                "parameters": [
                    {
                        "name": "purity",
                        "operator": ">=",
                        "value": 99.0,
                        "unit": "%",
                        "mandatory": True,
                    }
                ],
                "moisture_max": 0.25,
                "heavy_metals_max": 10.0,
                "storage_requirements": "Store in tightly closed container at room temperature away from light and moisture.",
                "notes": "Company internal specification for Vitamin C serum grade (not a universal regulation).",
            },
            required_documents=["COA", "SDS", "GMP"],
            active=True,
        )
        db.add(material)
        db.flush()

    # 5. Seed approved vendor-material link
    vm_link = (
        db.query(VendorMaterial)
        .filter(
            VendorMaterial.vendor_id == vendor.id,
            VendorMaterial.raw_material_id == material.id,
        )
        .first()
    )
    if not vm_link:
        vm_link = VendorMaterial(
            company_id=company.id,
            vendor_id=vendor.id,
            raw_material_id=material.id,
            is_approved=True,
            approved_at=datetime.now(timezone.utc),
            approved_by=user.id,
            notes="Primary verified manufacturer for Vitamin C raw material.",
        )
        db.add(vm_link)
        db.flush()

    db.commit()

    return {
        "company_id": str(company.id),
        "user_email": user.email,
        "vendor_id": str(vendor.id),
        "material_id": str(material.id),
        "vendor_material_id": str(vm_link.id),
    }


if __name__ == "__main__":
    get_engine()
    with SessionLocal() as session:
        result = seed_demo_data(session)
        print("Seed completed successfully:", result)
