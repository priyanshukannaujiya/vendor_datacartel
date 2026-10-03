import argparse
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import settings
from app.core.security import get_password_hash
from app.models.company import Company
from app.models.user import User


def seed_dummy_account(
    email: str = "admin@vendoriq.com",
    password: str = "Password123!",
    full_name: str = "DR. Priyanshu",
    company_name: str = "APEX PHARMA",
    role: str = "admin",
    use_sqlite: bool = False,
):
    if use_sqlite:
        db_url = "sqlite:///./vendoriq.db"
        engine = create_engine(db_url, connect_args={"check_same_thread": False})
        Session = sessionmaker(autocommit=False, autoflush=False, bind=engine)
        db = Session()
        target_db = "SQLite (vendoriq.db)"
    else:
        from app.core.database import SessionLocal, get_engine
        get_engine()
        db = SessionLocal()
        target_db = settings.sync_database_url.split("@")[-1] if "@" in settings.sync_database_url else settings.sync_database_url

    try:
        # 1. Find or create company
        company = db.query(Company).filter(Company.name == company_name).first()
        if not company:
            company = Company(name=company_name, industry="Pharmaceuticals")
            db.add(company)
            db.flush()
            print(f"[+] Created company: {company_name} (ID: {company.id})")
        else:
            print(f"[*] Reusing existing company: {company_name} (ID: {company.id})")

        # 2. Find or create/update user
        user = db.query(User).filter(User.email == email).first()
        if user:
            user.company_id = company.id
            user.password_hash = get_password_hash(password)
            user.full_name = full_name
            user.role = role
            user.is_active = True
            print(f"[*] Updated existing user: {email} with new credentials")
        else:
            user = User(
                company_id=company.id,
                email=email,
                password_hash=get_password_hash(password),
                full_name=full_name,
                role=role,
                is_active=True,
            )
            db.add(user)
            print(f"[+] Created user: {email}")

        db.commit()
        db.refresh(user)

        print("\n" + "=" * 52)
        print(" SUCCESS  Dummy account ready in database!")
        print("=" * 52)
        print(f"  Target DB : {target_db}")
        print(f"  Email     : {user.email}")
        print(f"  Password  : {password}")
        print(f"  Name      : {user.full_name}")
        print(f"  Role      : {user.role}")
        print(f"  Company   : {company.name} ({company.id})")
        print("=" * 52 + "\n")
        return user

    except Exception as e:
        db.rollback()
        print(f"[!] Error seeding account: {e}", file=sys.stderr)
        raise
    finally:
        db.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Create dummy account directly in the database.")
    parser.add_argument("--email", default="admin@vendoriq.com", help="User email (default: admin@vendoriq.com)")
    parser.add_argument("--password", default="Password123!", help="User password (default: Password123!)")
    parser.add_argument("--name", default="DR. Priyanshu", help="Full name (default: DR. Priyanshu)")
    parser.add_argument("--company", default="APEX PHARMA", help="Company name (default: APEX PHARMA)")
    parser.add_argument("--role", default="admin", help="User role (default: admin)")
    parser.add_argument("--sqlite", action="store_true", help="Force using local vendoriq.db SQLite file")

    args = parser.parse_args()

    seed_dummy_account(
        email=args.email,
        password=args.password,
        full_name=args.name,
        company_name=args.company,
        role=args.role,
        use_sqlite=args.sqlite,
    )

