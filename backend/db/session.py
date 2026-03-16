from __future__ import annotations

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.core.config import get_settings

settings = get_settings()

connect_args = {"check_same_thread": False} if settings.normalized_database_url.startswith("sqlite") else {}
engine = create_engine(settings.normalized_database_url, future=True, pool_pre_ping=True, connect_args=connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine, future=True)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
