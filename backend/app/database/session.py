"""Database engine and request-scoped SQLAlchemy sessions."""

from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import get_settings


settings = get_settings()
engine = create_engine(settings.database_url, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)


def get_db() -> Generator[Session, None, None]:
    """Yield a transaction session and ensure it is closed after the request."""
    database = SessionLocal()
    try:
        yield database
    finally:
        database.close()
