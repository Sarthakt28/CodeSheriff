import os
from pathlib import Path
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.core.config import settings

# Base directory for relative database fallback (cross-platform Linux & Windows)
BASE_DIR = Path(__file__).resolve().parent.parent.parent
FALLBACK_SQLITE_PATH = BASE_DIR / "codesheriff_local.db"
FALLBACK_SQLITE_URL = f"sqlite:///{FALLBACK_SQLITE_PATH.as_posix()}"

# Normalize PostgreSQL URL for SQLAlchemy compatibility
# (Render provides postgres:// or postgresql://; SQLAlchemy requires explicit driver)
db_url = settings.DATABASE_URL
if db_url.startswith("postgres://"):
    db_url = db_url.replace("postgres://", "postgresql+psycopg2://", 1)
elif db_url.startswith("postgresql://") and "+psycopg" not in db_url:
    db_url = db_url.replace("postgresql://", "postgresql+psycopg2://", 1)

# Engine initialization
try:
    engine = create_engine(db_url, pool_pre_ping=True)
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
