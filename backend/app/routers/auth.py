import secrets
from datetime import datetime, timezone, timedelta
from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.config import settings
from app.core.security import (
    get_password_hash,
    verify_password,
    create_access_token,
    get_current_user,
)
from app.core.errors import ConflictError, UnauthorizedError, NotFoundError, BadRequestError
from app.models.company import Company
from app.models.user import User
from app.schemas.auth import (
    RegisterRequest,
    LoginRequest,
    TokenResponse,
    UserResponse,
    MeResponse,
    ForgotPasswordRequest,
    ResetPasswordRequest,
    UpdateProfileRequest,
    UpdateCompanyRequest,
)
from app.schemas.company import CompanyResponse
from app.services.email_service import send_email

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def register(data: RegisterRequest, db: Session = Depends(get_db)):
    """
    Register a new company and its initial administrator user in one atomic transaction.
    """
    # Check for existing email
    existing_user = db.query(User).filter(User.email == data.email.lower().strip()).first()
    if existing_user:
        raise ConflictError(f"A user with email '{data.email}' already exists")

    # Check for existing company name
    existing_company = db.query(Company).filter(Company.name == data.company_name.strip()).first()
    if existing_company:
        raise ConflictError(f"A company named '{data.company_name}' already exists")

    # Atomic creation of company and user
    company = Company(name=data.company_name.strip())
    db.add(company)
    db.flush()

    user = User(
        company_id=company.id,
        email=data.email.lower().strip(),
        password_hash=get_password_hash(data.password),
        full_name=data.full_name.strip(),
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
    login_identifier = data.login_email
    user = db.query(User).filter(User.email == login_identifier).first()
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


@router.post("/forgot-password")
def forgot_password(data: ForgotPasswordRequest, db: Session = Depends(get_db)):
    """
    Generate password reset token and send reset link to the user's email via SMTP.
    """
    user = db.query(User).filter(User.email == data.email.lower().strip()).first()
    if not user:
        # Don't leak user existence; return generic success message
        return {"message": "If this email is registered, password reset instructions have been sent."}

    token = secrets.token_urlsafe(32)
    user.reset_password_token = token
    user.reset_password_expires_at = datetime.now(timezone.utc) + timedelta(hours=2)
    db.commit()

    # Build reset link
    reset_url = f"{settings.FRONTEND_URL}/reset-password?token={token}"
    html = f"""
    <div style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; max-width: 560px; margin: 0 auto; padding: 24px; color: #1e293b;">
        <h2 style="color: #0f172a; margin-bottom: 12px;">VendorIQ Password Reset Request</h2>
        <p>Hello {user.full_name},</p>
        <p>We received a request to reset your password for your VendorIQ account.</p>
        <div style="margin: 28px 0;">
            <a href="{reset_url}" style="background-color: #2563eb; color: #ffffff; padding: 12px 24px; border-radius: 6px; text-decoration: none; font-weight: 600; display: inline-block;">
                Reset My Password
            </a>
        </div>
        <p style="font-size: 13px; color: #64748b;">This link will expire in 2 hours. If you did not make this request, you can safely ignore this email.</p>
        <hr style="border: 0; border-top: 1px solid #e2e8f0; margin: 24px 0;" />
        <p style="font-size: 11px; color: #94a3b8;">VendorIQ Enterprise Platform &bull; Automated Security Delivery</p>
    </div>
    """
    try:
        send_email(
            recipient=user.email,
            subject="VendorIQ - Password Reset Request",
            html_content=html,
            text_content=f"Reset your password at: {reset_url}",
        )
    except Exception as exc:
        pass

    return {"message": "If this email is registered, password reset instructions have been sent."}


@router.post("/reset-password")
def reset_password(data: ResetPasswordRequest, db: Session = Depends(get_db)):
    """
    Validate reset token and update user password.
    """
    user = (
        db.query(User)
        .filter(User.reset_password_token == data.token)
        .first()
    )
    if not user or not user.reset_password_expires_at:
        raise BadRequestError("Invalid or expired password reset link")

    if user.reset_password_expires_at < datetime.now(timezone.utc):
        raise BadRequestError("Password reset link has expired. Please request a new one.")

    user.password_hash = get_password_hash(data.new_password)
    user.reset_password_token = None
    user.reset_password_expires_at = None
    db.commit()

    return {"message": "Password updated successfully. You can now log in with your new password."}


@router.put("/profile", response_model=UserResponse)
def update_profile(
    data: UpdateProfileRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Update profile details for the currently logged-in user.
    """
    if data.full_name:
        current_user.full_name = data.full_name.strip()

    if data.email:
        new_email = data.email.lower().strip()
        if new_email != current_user.email:
            existing = db.query(User).filter(User.email == new_email).first()
            if existing:
                raise ConflictError(f"Email '{new_email}' is already taken.")
            current_user.email = new_email

    if data.new_password:
        if not data.current_password or not verify_password(data.current_password, current_user.password_hash):
            raise BadRequestError("Current password is required and must be correct to set a new password.")
        current_user.password_hash = get_password_hash(data.new_password)

    db.commit()
    db.refresh(current_user)
    return current_user


@router.put("/company", response_model=CompanyResponse)
def update_company(
    data: UpdateCompanyRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Update organization/company information for the current user's company.
    """
    company = db.query(Company).filter(Company.id == current_user.company_id).first()
    if not company:
        raise NotFoundError("Company not found")

    if data.name:
        company.name = data.name.strip()
    if data.industry is not None:
        company.industry = data.industry.strip()
    if data.settings is not None:
        company.settings = data.settings

    db.commit()
    db.refresh(company)
    return company

