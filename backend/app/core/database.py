"""
SQLAlchemy database setup and session management for VendorIQ.
Compatible with PostgreSQL (Neon Serverless PostgreSQL).
"""
from typing import Generator
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker, Session
from app.core.config import settings

# Declarative Base for all future SQLAlchemy models
Base = declarative_base()

# SQLAlchemy Engine & SessionLocal
# Handled safely when DATABASE_URL is not yet provided in local .env
engine = None
SessionLocal = None


def get_engine():
    """Lazily initialize and return the SQLAlchemy engine."""
    global engine, SessionLocal
    if engine is None:
        import os
        raw_url = settings.DATABASE_URL or os.environ.get("DATABASE_URL", "")
        if raw_url:
            db_url = raw_url
            if db_url.startswith("postgres://"):
                db_url = db_url.replace("postgres://", "postgresql+psycopg2://", 1)
            elif db_url.startswith("postgresql://"):
                db_url = db_url.replace("postgresql://", "postgresql+psycopg2://", 1)
            engine_kwargs = {
                "pool_pre_ping": True,
            }
            if "neon.tech" in db_url or "sslmode=" in db_url:
                engine_kwargs["pool_recycle"] = 300
            engine = create_engine(db_url, **engine_kwargs)
            SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    return engine


# Initial attempt at module load
get_engine()


def get_db() -> Generator[Session, None, None]:
    """
    FastAPI dependency yielding a SQLAlchemy session.
    Ensures connection is closed after request lifecycle.
    """
    get_engine()
    if SessionLocal is None:
        raise RuntimeError(
            "DATABASE_URL is not configured. Please supply a valid DATABASE_URL in your backend/.env file."
        )
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
