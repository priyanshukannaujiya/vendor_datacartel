"""
Authentication routes for registration, login, and profile.
Follows VendorIQ PRD Section 12 & 13.
"""
from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.security import (
    get_password_hash,
    verify_password,
    create_access_token,
    get_current_user,
)
from app.core.errors import ConflictError, UnauthorizedError, NotFoundError
from app.models.company import Company
from app.models.user import User
from app.schemas.auth import (
    RegisterRequest,
    LoginRequest,
    TokenResponse,
    UserResponse,
    MeResponse,
)
from app.schemas.company import CompanyResponse

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def register(data: RegisterRequest, db: Session = Depends(get_db)):
    """
    Register a new company and its initial administrator user in one atomic transaction.
    """
    # Check for existing email
    existing_user = db.query(User).filter(User.email == data.email).first()
    if existing_user:
        raise ConflictError(f"A user with email '{data.email}' already exists")

    # Check for existing company name
    existing_company = db.query(Company).filter(Company.name == data.company_name).first()
    if existing_company:
        raise ConflictError(f"A company named '{data.company_name}' already exists")

    # Atomic creation of company and user
    company = Company(name=data.company_name)
    db.add(company)
    db.flush()

    user = User(
        company_id=company.id,
        email=data.email,
        password_hash=get_password_hash(data.password),
        full_name=data.full_name,
        role="admin",
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    return user


@router.post("/login", response_model=TokenResponse)
def login(data: LoginRequest, db: Session = Depends(get_db)):
    """
    Authenticate user credentials and return a signed JWT access token.
    Rejects inactive users with 401 Unauthorized.
    """
    user = db.query(User).filter(User.email == data.email).first()
    if not user or not verify_password(data.password, user.password_hash):
        raise UnauthorizedError("Invalid email or password")

    if not user.is_active:
        raise UnauthorizedError("User account is inactive. Please contact your company administrator.")

    access_token = create_access_token(
        user_id=str(user.id),
        company_id=str(user.company_id),
    )
    return TokenResponse(access_token=access_token, token_type="bearer")


@router.get("/me", response_model=MeResponse)
def get_me(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """
    Retrieve current authenticated user information and their company tenant context.
    """
    company = db.query(Company).filter(Company.id == current_user.company_id).first()
    if not company:
        raise NotFoundError("Company context not found for current user")

    return MeResponse(
        user=UserResponse.model_validate(current_user),
        company=CompanyResponse.model_validate(company),
    )
