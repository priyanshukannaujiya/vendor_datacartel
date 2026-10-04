"""
SQLAlchemy database setup and session management for VendorIQ.
Compatible with PostgreSQL (Neon Serverless PostgreSQL) and SQLite fallback for local testing.
"""
from typing import Generator
from sqlalchemy import create_engine, event
from sqlalchemy.orm import declarative_base, sessionmaker, Session
from app.core.config import settings

# Declarative Base for all SQLAlchemy models
Base = declarative_base()

# SQLAlchemy Engine & SessionLocal
engine = None
SessionLocal = None


def get_engine():
    """Lazily initialize and return the SQLAlchemy engine with optimized connection settings."""
    global engine, SessionLocal
    if engine is None:
        db_url = settings.sync_database_url
        engine_kwargs = {}
        if db_url.startswith("sqlite"):
            engine_kwargs["connect_args"] = {"check_same_thread": False}
        else:
            engine_kwargs["pool_pre_ping"] = True
            engine_kwargs["pool_recycle"] = 60
            engine_kwargs["pool_size"] = 15
            engine_kwargs["max_overflow"] = 25
            engine_kwargs["pool_timeout"] = 30
            engine_kwargs["connect_args"] = {
                "keepalives": 1,
                "keepalives_idle": 30,
                "keepalives_interval": 10,
                "keepalives_count": 5,
            }

        engine = create_engine(db_url, **engine_kwargs)

        # Performance tuning for SQLite: WAL mode, synchronous=NORMAL, 64MB cache
        if db_url.startswith("sqlite"):
            @event.listens_for(engine, "connect")
            def set_sqlite_pragma(dbapi_connection, connection_record):
                cursor = dbapi_connection.cursor()
                try:
                    cursor.execute("PRAGMA journal_mode=WAL")
                    cursor.execute("PRAGMA synchronous=NORMAL")
                    cursor.execute("PRAGMA cache_size=-64000")  # 64MB cache
                    cursor.execute("PRAGMA foreign_keys=ON")
                except Exception:
                    pass
                finally:
                    cursor.close()

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
