import os
from pathlib import Path
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.core.config import settings

# Fixed absolute path for SQLite fallback so all processes (FastAPI + Celery) share the exact same DB
SQLITE_DB_PATH = Path("D:/CodeSheriff/codesheriff_local.db").resolve()
FALLBACK_SQLITE_URL = f"sqlite:///{SQLITE_DB_PATH.as_posix()}"

# Engine — with SQLite fallback for local dev without Postgres
try:
    engine = create_engine(settings.DATABASE_URL)
    with engine.connect() as conn:
        pass
    print("[DATABASE] Connected to PostgreSQL successfully.")
except Exception as e:
    if "postgresql" in settings.DATABASE_URL:
        print(f"[DATABASE WARNING] PostgreSQL failed: {e}. Falling back to SQLite at: {FALLBACK_SQLITE_URL}")
        engine = create_engine(FALLBACK_SQLITE_URL, connect_args={"check_same_thread": False})
    else:
        print(f"[DATABASE ERROR] {e}")
        raise e

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
