"""
SQLAlchemy database setup and session management for VendorIQ.
Compatible with PostgreSQL (Neon Serverless PostgreSQL) and SQLite fallback for local testing.
"""
from typing import Generator
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker, Session
from app.core.config import settings

# Declarative Base for all SQLAlchemy models
Base = declarative_base()

# SQLAlchemy Engine & SessionLocal
engine = None
SessionLocal = None


def get_engine():
    """Lazily initialize and return the SQLAlchemy engine."""
    global engine, SessionLocal
    if engine is None:
        db_url = settings.sync_database_url
        engine_kwargs = {}
        if db_url.startswith("sqlite"):
            engine_kwargs["connect_args"] = {"check_same_thread": False}
        else:
            engine_kwargs["pool_pre_ping"] = True
            if "neon.tech" in db_url or "sslmode=" in db_url:
                engine_kwargs["pool_recycle"] = 300

        engine = create_engine(db_url, **engine_kwargs)
        SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    return engine


# Initial engine setup
get_engine()


def get_db() -> Generator[Session, None, None]:
    """
    FastAPI dependency yielding a SQLAlchemy session.
    Ensures connection is closed after request lifecycle.
    """
    get_engine()
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
