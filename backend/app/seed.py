"""
Seed script for VendorIQ demonstrating:
- Demo Vendor 1: ABC Ingredients Pvt Ltd (VC-2026-104, >=99% req, 99.3% actual, 20 batches, 19 approved, Low risk, Approved, Email sent)
- Demo Vendor 2: XYZ Raw Materials (VC-2026-205, 98.2% actual, poor history, High risk, Rejected, Email sent)
- Default Admin: admin@vendoriq.com / Password123!
"""
import uuid
import datetime
from sqlalchemy.orm import Session
from app.core.database import get_engine, Base
from app.core.security import get_password_hash
from app.models.company import Company
from app.models.user import User
from app.models.vendor import Vendor
from app.models.raw_material import RawMaterial
from app.models.vendor_material import VendorMaterial
from app.models.batch import Batch
from app.models.document import Document
from app.models.intelligence import BatchIntelligence
from app.models.decision import BatchDecision, EmailEvent, AuditEvent


def seed_database():
    engine = get_engine()
    Base.metadata.create_all(bind=engine)
    session = Session(bind=engine)

    try:
        # 1. Company
        company = session.query(Company).filter(Company.name == "VendorIQ Skincare Technologies").first()
        if not company:
            company = Company(
                id=uuid.uuid4(),
                name="VendorIQ Skincare Technologies",
                industry="Cosmetics & Personal Care",
                settings={"auto_email": True, "strict_validation": True},
            )
            session.add(company)
            session.flush()

        # 2. Admin User
        admin = session.query(User).filter(User.email == "admin@vendoriq.com").first()
        if not admin:
            admin = User(
                id=uuid.uuid4(),
                company_id=company.id,
                email="admin@vendoriq.com",
                password_hash=get_password_hash("Password123!"),
                full_name="Alex Mercer (QA Director)",
                role="admin",
                is_active=True,
            )
            session.add(admin)
            session.flush()

        # 3. Raw Materials
        mat_ascorbic = session.query(RawMaterial).filter(RawMaterial.code == "RM-ASC-001").first()
        if not mat_ascorbic:
            mat_ascorbic = RawMaterial(
                id=uuid.uuid4(),
                company_id=company.id,
                name="L-Ascorbic Acid (USP Grade)",
                code="RM-ASC-001",
                category="Active Antioxidants",
                description="Ultra-pure active Vitamin C for anti-aging serums.",
                cas_number="50-81-7",
                purity_min=99.0,
                moisture_max=0.5,
                heavy_metals_max_ppm=5.0,
                microbial_limit_cfu_g=50.0,
                storage_conditions="Store below 25C in airtight, light-resistant container",
                lead_time_days=14.0,
                base_price=45.0,
                specification={
                    "purity_min": 99.0,
                    "moisture_max": 0.5,
                    "heavy_metals_max_ppm": 5.0,
                    "microbial_limit_cfu_g": 50.0,
                },
                required_documents=["COA", "SDS", "GMP"],
                active=True,
            )
            session.add(mat_ascorbic)
            session.flush()

        mat_hya = session.query(RawMaterial).filter(RawMaterial.code == "RM-HYA-002").first()
        if not mat_hya:
            mat_hya = RawMaterial(
                id=uuid.uuid4(),
                company_id=company.id,
                name="Sodium Hyaluronate (High MW)",
                code="RM-HYA-002",
                category="Humectants",
                description="Biotechnologically fermented hyaluronic acid sodium salt.",
                cas_number="9067-32-7",
                purity_min=95.0,
                moisture_max=8.0,
                heavy_metals_max_ppm=10.0,
                microbial_limit_cfu_g=100.0,
                storage_conditions="Keep sealed under 20C away from direct sunlight",
                lead_time_days=21.0,
                base_price=120.0,
                specification={"purity_min": 95.0, "moisture_max": 8.0},
                required_documents=["COA", "SDS", "GMP"],
                active=True,
            )
            session.add(mat_hya)
            session.flush()

        mat_nia = session.query(RawMaterial).filter(RawMaterial.code == "RM-NIA-003").first()
        if not mat_nia:
            mat_nia = RawMaterial(
                id=uuid.uuid4(),
                company_id=company.id,
                name="Niacinamide (Pure Grade B3)",
                code="RM-NIA-003",
                category="Vitamins",
                description="High tolerance vitamin B3 for skin barrier strengthening.",
                cas_number="98-92-0",
                purity_min=99.0,
                moisture_max=0.5,
                heavy_metals_max_ppm=10.0,
                microbial_limit_cfu_g=100.0,
                storage_conditions="Cool, dry storage",
                lead_time_days=10.0,
                base_price=38.0,
                specification={"purity_min": 99.0, "moisture_max": 0.5},
                required_documents=["COA", "SDS", "GMP"],
                active=True,
            )
            session.add(mat_nia)
            session.flush()

        # 4. DEMO VENDOR 1: ABC Ingredients Pvt Ltd
        vendor_abc = session.query(Vendor).filter(Vendor.vendor_name == "ABC Ingredients Pvt Ltd").first()
        if not vendor_abc:
            vendor_abc = Vendor(
                id=uuid.uuid4(),
                company_id=company.id,
                vendor_name="ABC Ingredients Pvt Ltd",
                company_registration_id="CIN-U24230MH2012PTC234",
                country="India",
                contact_name="Rajesh Sharma",
                email="compliance@abcingredients.com",
                phone="+91 22 4567 8900",
                address="Plot 42, Chemical Zone, MIDC Industrial Area, Navi Mumbai, India",
                industry="Fine Chemicals & APIs",
                supplier_category="Certified Primary Manufacturer",
                tier="TIER_1",
                status="ACTIVE",
                certification_status="GMP_CERTIFIED",
                delivery_reliability=0.97,
                capacity=200000.0,
                risk_score=12.5,
                approval_rate=0.95,
                quality_score=99.2,
                is_active=True,
            )
            session.add(vendor_abc)
            session.flush()

        # 5. DEMO VENDOR 2: XYZ Raw Materials
        vendor_xyz = session.query(Vendor).filter(Vendor.vendor_name == "XYZ Raw Materials").first()
        if not vendor_xyz:
            vendor_xyz = Vendor(
                id=uuid.uuid4(),
                company_id=company.id,
                vendor_name="XYZ Raw Materials",
                company_registration_id="REG-CN-9844211",
                country="China",
                contact_name="Li Wei",
                email="orders@xyzrawmaterials.com",
                phone="+86 21 6888 1234",
                address="Building 8, Industrial Export Park, Pudong, Shanghai, China",
                industry="Bulk Raw Chemicals",
                supplier_category="Secondary Trader / Distributor",
                tier="TIER_3",
                status="ON_PROBATION",
                certification_status="EXPIRED",
                delivery_reliability=0.81,
                capacity=60000.0,
                risk_score=78.4,
                approval_rate=0.65,
                quality_score=94.0,
                is_active=True,
            )
            session.add(vendor_xyz)
            session.flush()

        # Link Vendor Materials
        for v, m in [(vendor_abc, mat_ascorbic), (vendor_abc, mat_nia), (vendor_xyz, mat_ascorbic), (vendor_xyz, mat_hya)]:
            vm = session.query(VendorMaterial).filter(VendorMaterial.vendor_id == v.id, VendorMaterial.raw_material_id == m.id).first()
            if not vm:
                session.add(VendorMaterial(
                    company_id=company.id,
                    vendor_id=v.id,
                    raw_material_id=m.id,
                    is_approved=True if v == vendor_abc else False,
                    notes="Approved for high-purity production lines" if v == vendor_abc else "Under quality probationary review",
                ))

        # 6. Historical Batches for Vendor ABC (20 historical batches: 19 approved, 1 rejected)
        now = datetime.datetime.now(datetime.timezone.utc)
        for i in range(1, 21):
            b_num = f"ABC-2025-{100 + i}"
            existing_b = session.query(Batch).filter(Batch.batch_number == b_num).first()
            if not existing_b:
                is_app = (i != 7)  # 19 approved, 1 rejected
                b_date = now - datetime.timedelta(days=(22 - i) * 14)
                session.add(Batch(
                    id=uuid.uuid4(),
                    company_id=company.id,
                    vendor_id=vendor_abc.id,
                    raw_material_id=mat_ascorbic.id,
                    batch_number=b_num,
                    manufacturing_date=b_date.date(),
                    expiry_date=(b_date + datetime.timedelta(days=730)).date(),
                    quantity=2000.0,
                    unit="kg",
                    price=45.0,
                    status="APPROVED" if is_app else "REJECTED",
                    purity_reported=99.3 if is_app else 98.4,
                    lead_time_actual=13.5,
                    created_at=b_date,
                    updated_at=b_date + datetime.timedelta(hours=2),
                ))

        # Historical Batches for Vendor XYZ (10 historical batches: 6 approved, 4 rejected)
        for i in range(1, 11):
            b_num = f"XYZ-2025-{200 + i}"
            existing_b = session.query(Batch).filter(Batch.batch_number == b_num).first()
            if not existing_b:
                is_app = (i in [1, 2, 4, 6, 8, 10])
                b_date = now - datetime.timedelta(days=(12 - i) * 18)
                session.add(Batch(
                    id=uuid.uuid4(),
                    company_id=company.id,
                    vendor_id=vendor_xyz.id,
                    raw_material_id=mat_ascorbic.id,
                    batch_number=b_num,
                    manufacturing_date=b_date.date(),
                    expiry_date=(b_date + datetime.timedelta(days=730)).date(),
                    quantity=1200.0,
                    unit="kg",
                    price=40.0,
                    status="APPROVED" if is_app else "REJECTED",
                    purity_reported=99.0 if is_app else 97.9,
                    lead_time_actual=17.5,
                    created_at=b_date,
                    updated_at=b_date + datetime.timedelta(hours=4),
                ))

        session.flush()

        # 7. DEMO BATCH 1: VC-2026-104 (ABC Ingredients Pvt Ltd)
        batch_1 = session.query(Batch).filter(Batch.batch_number == "VC-2026-104").first()
        if not batch_1:
            batch_1 = Batch(
                id=uuid.uuid4(),
                company_id=company.id,
                vendor_id=vendor_abc.id,
                raw_material_id=mat_ascorbic.id,
                batch_number="VC-2026-104",
                manufacturing_date=(now - datetime.timedelta(days=10)).date(),
                expiry_date=(now + datetime.timedelta(days=720)).date(),
                quantity=2500.0,
                unit="kg",
                price=45.0,
                expected_delivery_date=(now - datetime.timedelta(days=2)).date(),
                actual_delivery_date=(now - datetime.timedelta(days=2)).date(),
                status="APPROVED",
                purity_reported=99.3,
                lead_time_actual=13.0,
                created_by=admin.id,
                created_at=now - datetime.timedelta(days=2),
                updated_at=now - datetime.timedelta(days=1),
            )
            session.add(batch_1)
            session.flush()

            # Attach Documents for Batch 1
            doc_coa_1 = Document(
                id=uuid.uuid4(),
                company_id=company.id,
                batch_id=batch_1.id,
                vendor_id=vendor_abc.id,
                document_type="COA",
                file_name="COA_VC-2026-104_AscorbicAcid.pdf",
                file_path="./uploads/COA_VC-2026-104_AscorbicAcid.pdf",
                mime_type="application/pdf",
                file_size=245000,
                processing_status="PROCESSED",
                extracted_data={
                    "batch_number": "VC-2026-104",
                    "material": "L-Ascorbic Acid USP",
                    "purity": 99.3,
                    "moisture": 0.28,
                    "heavy_metals": 2.1,
                    "tamc": 12.0,
                    "test_date": "2026-03-25",
                },
            )
            doc_sds_1 = Document(
                id=uuid.uuid4(),
                company_id=company.id,
                batch_id=batch_1.id,
                vendor_id=vendor_abc.id,
                document_type="SDS",
                file_name="SDS_AscorbicAcid_2026.pdf",
                file_path="./uploads/SDS_AscorbicAcid_2026.pdf",
                mime_type="application/pdf",
                file_size=412000,
                processing_status="PROCESSED",
                extracted_data={"storage_conditions": "Store below 25C", "hazard_class": "Non-hazardous"},
            )
            doc_gmp_1 = Document(
                id=uuid.uuid4(),
                company_id=company.id,
                batch_id=batch_1.id,
                vendor_id=vendor_abc.id,
                document_type="GMP",
                file_name="GMP_Certificate_ABC_2026.pdf",
                file_path="./uploads/GMP_Certificate_ABC_2026.pdf",
                mime_type="application/pdf",
                file_size=188000,
                processing_status="PROCESSED",
                extracted_data={"valid_until": "2027-12-31", "audit_body": "TUV Rheinland"},
            )
            session.add_all([doc_coa_1, doc_sds_1, doc_gmp_1])
            session.flush()

            # BatchIntelligence for Batch 1
            intel_1 = BatchIntelligence(
                id=uuid.uuid4(),
                batch_id=batch_1.id,
                validation_result={
                    "overall_status": "PASS",
                    "checks": [
                        {"name": "document_present_coa", "status": "PASS", "expected": "Present", "actual": "Present", "reason": "COA uploaded and verified."},
                        {"name": "document_present_sds", "status": "PASS", "expected": "Present", "actual": "Present", "reason": "SDS present."},
                        {"name": "document_present_gmp", "status": "PASS", "expected": "Present", "actual": "Present", "reason": "Valid GMP certificate."},
                        {"name": "purity", "status": "PASS", "expected": ">= 99.0%", "actual": 99.3, "reason": "Actual purity 99.3% meets specification limit of >= 99.0%."},
                        {"name": "moisture", "status": "PASS", "expected": "<= 0.5%", "actual": 0.28, "reason": "Moisture 0.28% is well below 0.5% boundary."},
                        {"name": "heavy_metals", "status": "PASS", "expected": "<= 5.0 ppm", "actual": 2.1, "reason": "Heavy metals within safety limit."},
                    ],
                    "passed_checks_count": 6,
                    "total_checks_count": 6,
                },
                vendor_history={
                    "vendor_id": str(vendor_abc.id),
                    "previous_batches": 20,
                    "approval_rate": 0.95,
                    "delivery_reliability": 0.97,
                    "average_purity": 99.25,
                    "purity_variance": 0.04,
                    "documentation_completeness": 1.0,
                    "incident_count": 0,
                },
                ml_features={
                    "actual_purity": 99.3,
                    "purity_margin": 0.3,
                    "approval_rate": 0.95,
                    "delivery_reliability": 0.97,
                    "purity_variance": 0.04,
                    "failed_checks_count": 0,
                },
                ml_prediction={
                    "risk_score": 12.5,
                    "risk_probability": 0.12,
                    "risk_level": "LOW",
                    "risk_factors": ["None - low risk profile across all indicators"],
                },
                kimi_analysis={
                    "summary": "Batch VC-2026-104 exhibits outstanding compliance with an assay purity of 99.3% (spec >= 99.0%) and complete documentation from TIER_1 supplier ABC Ingredients.",
                    "key_findings": [
                        "Actual purity exceeds minimum specification threshold by +0.3%.",
                        "Moisture content (0.28%) satisfies tight shelf-life criteria.",
                        "Supplier maintains 95% historical qualification rate over 20 batches.",
                    ],
                    "risk_factors": ["No significant operational or biochemical risk detected."],
                    "business_impact": ["Immediate clearance recommended for production formulation."],
                    "recommended_actions": ["Issue immediate batch qualification certificate and release to production."],
                    "kimi_status": "SUCCESS",
                },
                kimi_status="SUCCESS",
            )
            session.add(intel_1)

            # BatchDecision for Batch 1
            dec_1 = BatchDecision(
                id=uuid.uuid4(),
                batch_id=batch_1.id,
                company_id=company.id,
                decision="APPROVED",
                risk_score=12.5,
                risk_level="LOW",
                reason="All physical-chemical specification limits verified, documentation 100% complete, supplier historical approval rate 95%.",
                recommended_actions=["Authorize release for cosmetic line blending."],
            )
            session.add(dec_1)
            session.flush()

            # EmailEvent for Batch 1
            email_1 = EmailEvent(
                id=uuid.uuid4(),
                company_id=company.id,
                vendor_id=vendor_abc.id,
                batch_id=batch_1.id,
                decision_id=dec_1.id,
                recipient_email=vendor_abc.email,
                subject=f"VendorIQ — Batch VC-2026-104 Approved",
                email_type="APPROVED",
                status="SENT",
                provider="GOOGLE_SMTP",
                sent_at=now - datetime.timedelta(days=1),
                html_content="<p>Batch VC-2026-104 has been APPROVED.</p>",
                text_content="VendorIQ batch VC-2026-104: APPROVED",
            )
            session.add(email_1)

            # Audit Events for Batch 1
            events_1 = [
                ("Email Received", {"sender": vendor_abc.email, "tracking": "BL-9941"}),
                ("Documents Processed", {"count": 3, "formats": ["PDF", "PDF", "PDF"]}),
                ("Validation Completed", {"status": "PASS", "score": 100}),
                ("Risk Predicted", {"risk_score": 12.5, "risk_level": "LOW"}),
                ("Kimi Assessment Generated", {"status": "SUCCESS"}),
                ("Decision Made", {"decision": "APPROVED"}),
                ("Email Sent", {"recipient": vendor_abc.email, "status": "SENT"}),
            ]
            for ev_name, dt in events_1:
                session.add(AuditEvent(
                    id=uuid.uuid4(),
                    event_type=ev_name,
                    company_id=company.id,
                    vendor_id=vendor_abc.id,
                    batch_id=batch_1.id,
                    details=dt,
                    created_at=now - datetime.timedelta(hours=4),
                ))

        # 8. DEMO BATCH 2: VC-2026-205 (XYZ Raw Materials)
        batch_2 = session.query(Batch).filter(Batch.batch_number == "VC-2026-205").first()
        if not batch_2:
            batch_2 = Batch(
                id=uuid.uuid4(),
                company_id=company.id,
                vendor_id=vendor_xyz.id,
                raw_material_id=mat_ascorbic.id,
                batch_number="VC-2026-205",
                manufacturing_date=(now - datetime.timedelta(days=5)).date(),
                expiry_date=(now + datetime.timedelta(days=700)).date(),
                quantity=1000.0,
                unit="kg",
                price=40.0,
                expected_delivery_date=now.date(),
                actual_delivery_date=now.date(),
                status="REJECTED",
                purity_reported=98.2,
                failure_reason="Purity (98.2%) below specification threshold of >= 99.0%; GMP certificate expired.",
                lead_time_actual=19.0,
                created_by=admin.id,
                created_at=now - datetime.timedelta(days=1),
                updated_at=now,
            )
            session.add(batch_2)
            session.flush()

            # Attach Documents for Batch 2
            doc_coa_2 = Document(
                id=uuid.uuid4(),
                company_id=company.id,
                batch_id=batch_2.id,
                vendor_id=vendor_xyz.id,
                document_type="COA",
                file_name="COA_VC-2026-205_XYZ_Ascorbic.pdf",
                file_path="./uploads/COA_VC-2026-205_XYZ_Ascorbic.pdf",
                mime_type="application/pdf",
                file_size=210000,
                processing_status="PROCESSED",
                extracted_data={
                    "batch_number": "VC-2026-205",
                    "material": "L-Ascorbic Acid",
                    "purity": 98.2,
                    "moisture": 0.82,
                    "heavy_metals": 8.4,
                    "test_date": "2026-03-27",
                },
            )
            session.add(doc_coa_2)
            session.flush()

            # BatchIntelligence for Batch 2
            intel_2 = BatchIntelligence(
                id=uuid.uuid4(),
                batch_id=batch_2.id,
                validation_result={
                    "overall_status": "FAIL",
                    "checks": [
                        {"name": "document_present_coa", "status": "PASS", "expected": "Present", "actual": "Present", "reason": "COA uploaded."},
                        {"name": "document_present_gmp", "status": "FAIL", "expected": "Present", "actual": "Missing", "reason": "No valid GMP certificate on record."},
                        {"name": "purity", "status": "FAIL", "expected": ">= 99.0%", "actual": 98.2, "reason": "Actual purity 98.2% is below specification limit of >= 99.0%."},
                        {"name": "moisture", "status": "FAIL", "expected": "<= 0.5%", "actual": 0.82, "reason": "Moisture 0.82% exceeds max allowable limit of 0.5%."},
                    ],
                    "passed_checks_count": 1,
                    "total_checks_count": 4,
                },
                vendor_history={
                    "vendor_id": str(vendor_xyz.id),
                    "previous_batches": 10,
                    "approval_rate": 0.60,
                    "delivery_reliability": 0.81,
                    "average_purity": 98.4,
                    "purity_variance": 0.85,
                    "documentation_completeness": 0.5,
                    "incident_count": 4,
                },
                ml_features={
                    "actual_purity": 98.2,
                    "purity_margin": -0.8,
                    "approval_rate": 0.60,
                    "delivery_reliability": 0.81,
                    "purity_variance": 0.85,
                    "failed_checks_count": 3,
                },
                ml_prediction={
                    "risk_score": 78.4,
                    "risk_probability": 0.78,
                    "risk_level": "HIGH",
                    "risk_factors": [
                        "Purity below specification (98.2% vs >= 99.0%)",
                        "High moisture content (0.82% vs <= 0.5%)",
                        "Poor historical rejection rate (40% failures)",
                        "Unresolved documentation anomalies",
                    ],
                },
                kimi_analysis={
                    "summary": "CRITICAL QUALITY ALERT: Batch VC-2026-205 from XYZ Raw Materials fails fundamental chemical acceptance criteria (98.2% purity, 0.82% moisture) accompanied by elevated historical defect frequency.",
                    "key_findings": [
                        "Assay purity failed by -0.8% below formulation threshold.",
                        "Moisture content is 64% above allowable maximum.",
                        "Supplier is on probationary status with expired GMP credentials.",
                    ],
                    "risk_factors": ["High risk of product formulation degradation and regulatory batch quarantine."],
                    "business_impact": ["Significant financial loss if introduced to compounding stage."],
                    "recommended_actions": [
                        "Reject batch immediately and enforce physical quarantine.",
                        "Issue formal Supplier Non-Conformance Report (SNCR).",
                        "Withhold invoice payment pending supplier investigation.",
                    ],
                    "kimi_status": "SUCCESS",
                },
                kimi_status="SUCCESS",
            )
            session.add(intel_2)

            # BatchDecision for Batch 2
            dec_2 = BatchDecision(
                id=uuid.uuid4(),
                batch_id=batch_2.id,
                company_id=company.id,
                decision="REJECTED",
                risk_score=78.4,
                risk_level="HIGH",
                reason="Purity (98.2%) failed specification limit (>=99.0%), moisture (0.82%) failed limit (<=0.5%), supplier reliability unacceptable.",
                recommended_actions=["Reject shipment, initiate quarantine protocol, request vendor CAPA."],
            )
            session.add(dec_2)
            session.flush()

            # EmailEvent for Batch 2
            email_2 = EmailEvent(
                id=uuid.uuid4(),
                company_id=company.id,
                vendor_id=vendor_xyz.id,
                batch_id=batch_2.id,
                decision_id=dec_2.id,
                recipient_email=vendor_xyz.email,
                subject=f"VendorIQ — Batch VC-2026-205 Assessment Result",
                email_type="REJECTED",
                status="SENT",
                provider="GOOGLE_SMTP",
                sent_at=now,
                html_content="<p>Batch VC-2026-205 has been REJECTED.</p>",
                text_content="VendorIQ batch VC-2026-205: REJECTED",
            )
            session.add(email_2)

            # Audit Events for Batch 2
            events_2 = [
                ("Email Received", {"sender": vendor_xyz.email, "tracking": "BL-7712"}),
                ("Documents Processed", {"count": 1, "formats": ["PDF"]}),
                ("Validation Completed", {"status": "FAIL", "failed_checks": ["purity", "moisture", "gmp"]}),
                ("Risk Predicted", {"risk_score": 78.4, "risk_level": "HIGH"}),
                ("Kimi Assessment Generated", {"status": "SUCCESS"}),
                ("Decision Made", {"decision": "REJECTED"}),
                ("Email Sent", {"recipient": vendor_xyz.email, "status": "SENT"}),
            ]
            for ev_name, dt in events_2:
                session.add(AuditEvent(
                    id=uuid.uuid4(),
                    event_type=ev_name,
                    company_id=company.id,
                    vendor_id=vendor_xyz.id,
                    batch_id=batch_2.id,
                    details=dt,
                    created_at=now - datetime.timedelta(minutes=30),
                ))

        session.commit()
        print("VendorIQ Database Seeded Successfully with Demo Vendor 1 and Demo Vendor 2!")
    except Exception as e:
        session.rollback()
        print(f"Error seeding database: {e}")
        raise
    finally:
        session.close()


if __name__ == "__main__":
    seed_database()
