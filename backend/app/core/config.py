import json
import os
from pathlib import Path
from typing import List, Union, Optional
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

_BACKEND_DIR = Path(__file__).resolve().parent.parent.parent
_ENV_FILES = (
    str(_BACKEND_DIR / ".env"),
    str(Path.cwd() / ".env"),
    str(Path.cwd() / "backend" / ".env"),
    ".env",
    "backend/.env",
)


class Settings(BaseSettings):
    """
    Application configuration settings loaded from environment variables or .env file.
    Follows VendorIQ PRD requirements.
    """
    model_config = SettingsConfigDict(
        env_file=_ENV_FILES,
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=True,
    )

    PROJECT_NAME: str = "VendorIQ API"
    PROJECT_DESCRIPTION: str = "AI-Powered Supplier Qualification & Batch Intelligence Platform"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api"
    ENVIRONMENT: str = "development"
    DEBUG: bool = True

    # Core required environment variables
    DATABASE_URL: str = ""
    JWT_SECRET: str = "vendoriq-default-secret-key-change-in-production-2026"
    FRONTEND_URL: str = "http://localhost:5173"
    CORS_ORIGINS: Union[List[str], str] = []

    # Optional configuration values from VendorIQ PRD
    JWT_EXPIRE_MINUTES: int = 1440  # 24 hours
    MAX_UPLOAD_MB: int = 10
    UPLOAD_DIR: str = "./uploads"

    # Developer 2: Kimi K3 External Reasoning Layer
    KIMI_API_KEY: Optional[str] = None
    KIMI_API_BASE: str = "https://api.moonshot.cn/v1"
    KIMI_MODEL: str = "moonshot-v1-8k"
    KIMI_TIMEOUT_SECONDS: float = 30.0

    # Developer 3: Google SMTP Settings
    SMTP_HOST: str = "smtp.gmail.com"
    SMTP_PORT: int = 587
    SMTP_USERNAME: Optional[str] = None
    SMTP_PASSWORD: Optional[str] = None
    SMTP_FROM: Optional[str] = None
    SMTP_FROM_NAME: str = "VendorIQ"

    # Optional Gmail inbox polling for supplier PDF replies.
    IMAP_ENABLED: bool = False
    IMAP_HOST: str = "imap.gmail.com"
    IMAP_PORT: int = 993
    IMAP_USERNAME: Optional[str] = None
    IMAP_PASSWORD: Optional[str] = None
    IMAP_FOLDER: str = "INBOX"
    IMAP_POLL_INTERVAL_SECONDS: int = 120
    IMAP_LOOKBACK_DAYS: int = 30

    @field_validator("JWT_EXPIRE_MINUTES", mode="before")
    @classmethod
    def parse_jwt_expire_minutes(cls, v: Union[str, int, None]) -> int:
        if v == "" or v is None:
            return 1440
        return int(v)

    @field_validator("MAX_UPLOAD_MB", mode="before")
    @classmethod
    def parse_max_upload_mb(cls, v: Union[str, int, None]) -> int:
        if v == "" or v is None:
            return 10
        return int(v)

    @field_validator("SMTP_PORT", mode="before")
    @classmethod
    def parse_smtp_port(cls, v: Union[str, int, None]) -> int:
        if v == "" or v is None:
            return 587
        return int(v)

    @field_validator("IMAP_PORT", mode="before")
    @classmethod
    def parse_imap_port(cls, v: Union[str, int, None]) -> int:
        if v == "" or v is None:
            return 993
        return int(v)

    @field_validator("IMAP_POLL_INTERVAL_SECONDS", mode="before")
    @classmethod
    def parse_imap_poll_interval(cls, v: Union[str, int, None]) -> int:
        if v == "" or v is None:
            return 120
        return max(30, int(v))

    @field_validator("IMAP_LOOKBACK_DAYS", mode="before")
    @classmethod
    def parse_imap_lookback_days(cls, v: Union[str, int, None]) -> int:
        if v == "" or v is None:
            return 30
        return max(1, int(v))

    @field_validator("FRONTEND_URL", mode="before")
    @classmethod
    def parse_frontend_url(cls, v: Union[str, None]) -> str:
        if v == "" or v is None:
            return "http://localhost:5173"
        return str(v)

    @field_validator("UPLOAD_DIR", mode="before")
    @classmethod
    def parse_upload_dir(cls, v: Union[str, None]) -> str:
        if v == "" or v is None:
            return "./uploads"
        return str(v)

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v: Union[str, List[str], None]) -> List[str]:
        if v is None or v == "":
            return []
        if isinstance(v, str):
            stripped = v.strip()
            if not stripped:
                return []
            if stripped.startswith("[") and stripped.endswith("]"):
                try:
                    return json.loads(stripped)
                except Exception:
                    pass
            return [origin.strip() for origin in stripped.split(",") if origin.strip()]
        elif isinstance(v, list):
            return v
        return []

    @property
    def all_cors_origins(self) -> List[str]:
        """Combine CORS_ORIGINS list and FRONTEND_URL with local development defaults."""
        defaults = [
            "http://localhost:5173",
            "http://localhost:3000",
            "http://localhost:4173",
            "http://localhost:5174",
            "http://127.0.0.1:5173",
            "http://127.0.0.1:3000",
            "http://127.0.0.1:4173",
            "http://127.0.0.1:5174",
        ]
        origins: List[str] = list(defaults)
        if isinstance(self.CORS_ORIGINS, list):
            for o in self.CORS_ORIGINS:
                if o and o not in origins:
                    origins.append(o)
        if self.FRONTEND_URL and self.FRONTEND_URL not in origins:
            origins.append(self.FRONTEND_URL)
        return origins

    @property
    def sync_database_url(self) -> str:
        """
        Normalize DATABASE_URL for SQLAlchemy psycopg2 driver.
        Ensures postgres:// or postgresql:// scheme uses psycopg2 driver (postgresql+psycopg2://).
        Falls back to local sqlite when DATABASE_URL is not set.
        """
        url = self.DATABASE_URL
        if not url:
            return "sqlite:///./vendoriq.db"
        if url.startswith("postgres://"):
            url = url.replace("postgres://", "postgresql+psycopg2://", 1)
        elif url.startswith("postgresql://") and not url.startswith("postgresql+psycopg2://"):
            url = url.replace("postgresql://", "postgresql+psycopg2://", 1)
        return url


settings = Settings()
