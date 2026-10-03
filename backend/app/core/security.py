"""
Authentication and security foundations for VendorIQ.
Follows VendorIQ PRD Section 13 & 26:
- Passwords hashed with bcrypt
- JWT (HS256) signed with JWT_SECRET; claims: sub (user_id), company_id, exp
- get_current_user dependency foundation returning token claims (user_id, company_id)
"""
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional
import bcrypt
from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from app.core.config import settings
from app.core.database import get_db
from app.core.errors import UnauthorizedError

ALGORITHM = "HS256"

# HTTPBearer authorization header (Authorization: Bearer <token>)
bearer_scheme = HTTPBearer(auto_error=False)


def get_password_hash(password: str) -> str:
    """Hash a password using bcrypt."""
    password_bytes = password.encode("utf-8")
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password_bytes, salt).decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plain password against a bcrypt hash."""
    try:
        return bcrypt.checkpw(
            plain_password.encode("utf-8"),
            hashed_password.encode("utf-8"),
        )
    except Exception:
        return False


def get_jwt_secret() -> str:
    """Retrieve JWT secret from settings or environment."""
    import os
    return settings.JWT_SECRET or os.environ.get("JWT_SECRET", "")


def create_access_token(
    user_id: str,
    company_id: str,
    expires_delta: Optional[timedelta] = None,
    extra_claims: Optional[Dict[str, Any]] = None,
) -> str:
    """
    Create a JWT access token with HS256 algorithm.
    Required claims:
      - sub: user ID
      - company_id: tenant ID
      - exp: expiration timestamp
      - iat: issued-at timestamp
    """
    secret = get_jwt_secret()
    if not secret:
        raise RuntimeError("JWT_SECRET is not configured in environment or .env file.")

    now = datetime.now(timezone.utc)
    if expires_delta is not None:
        expire = now + expires_delta
    else:
        expire = now + timedelta(minutes=settings.JWT_EXPIRE_MINUTES)

    to_encode: Dict[str, Any] = {
        "sub": str(user_id),
        "company_id": str(company_id),
        "exp": expire,
        "iat": now,
    }
    if extra_claims:
        to_encode.update(extra_claims)

    return jwt.encode(to_encode, secret, algorithm=ALGORITHM)


def decode_access_token(token: str) -> Dict[str, Any]:
    """
    Decode and validate a JWT access token.
    Raises UnauthorizedError if token is invalid, expired, or missing claims.
    """
    secret = get_jwt_secret()
    if not secret:
        raise UnauthorizedError("JWT_SECRET is not configured on the server")

    try:
        payload = jwt.decode(token, secret, algorithms=[ALGORITHM])
        user_id = payload.get("sub")
        company_id = payload.get("company_id")
        if not user_id or not company_id:
            raise UnauthorizedError("Invalid token: missing required user or company claim")
        return payload
    except JWTError:
        raise UnauthorizedError("Invalid or expired access token")


def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme),
    db: Any = Depends(get_db),
) -> Any:
    """
    Validates the Bearer JWT token, loads the user from the database,
    rejects inactive users (401), and returns the User object.
    Provides tenant isolation by verifying company_id.
    """
    from app.models.user import User

    if not credentials or not credentials.credentials:
        raise UnauthorizedError("Authentication credentials were not provided")

    payload = decode_access_token(credentials.credentials)
    user_id = payload.get("sub")
    company_id = payload.get("company_id")

    try:
        user = db.query(User).filter(User.id == user_id, User.company_id == company_id).first()
    except Exception:
        raise UnauthorizedError("Invalid user credentials or database error")

    if not user:
        raise UnauthorizedError("User not found or does not belong to specified company")
    if not user.is_active:
        raise UnauthorizedError("User account is inactive")

    return user
