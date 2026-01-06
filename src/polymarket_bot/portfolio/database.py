"""Database configuration and session management."""

from contextlib import contextmanager
from typing import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from polymarket_bot.config import settings
from polymarket_bot.portfolio.models import Base

# Create engine (lazy initialization)
_engine = None
_SessionLocal = None


def get_engine():
    """Get or create the database engine."""
    global _engine
    if _engine is None:
        # Use SQLite by default, stored in data/ directory
        # Can be overridden with DATABASE_URL environment variable
        db_url = getattr(settings, 'database_url', 'sqlite:///./data/portfolio.db')

        _engine = create_engine(
            db_url,
            echo=False,  # Set to True for SQL debugging
            pool_pre_ping=True,  # Verify connections before using
        )
    return _engine


def get_session_factory():
    """Get or create the session factory."""
    global _SessionLocal
    if _SessionLocal is None:
        engine = get_engine()
        _SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    return _SessionLocal


def init_db():
    """Initialize database tables."""
    engine = get_engine()
    Base.metadata.create_all(bind=engine)


def drop_db():
    """Drop all database tables. Use with caution!"""
    engine = get_engine()
    Base.metadata.drop_all(bind=engine)


@contextmanager
def get_db() -> Generator[Session, None, None]:
    """
    Get a database session as a context manager.

    Usage:
        with get_db() as db:
            portfolio = db.query(Portfolio).first()
    """
    SessionLocal = get_session_factory()
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def get_db_session() -> Session:
    """
    Get a database session (must be closed manually).

    Prefer using get_db() context manager when possible.
    """
    SessionLocal = get_session_factory()
    return SessionLocal()
