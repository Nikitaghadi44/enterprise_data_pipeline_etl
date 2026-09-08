"""
Database engine + session factory.
Works against SQLite (default, zero-config) or MySQL (set DB_ENGINE=mysql).
"""
from contextlib import contextmanager
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from config.config import config
from database.models import Base

_connect_args = {"check_same_thread": False} if config.DB_ENGINE == "sqlite" else {}

engine = create_engine(
    config.SQLALCHEMY_DATABASE_URI,
    pool_pre_ping=True,
    connect_args=_connect_args,
)

SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


def init_db():
    """Create all tables if they don't already exist."""
    Base.metadata.create_all(bind=engine)


@contextmanager
def get_session():
    """Context-managed session: commits on success, rolls back on error."""
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
