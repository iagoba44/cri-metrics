"""Configuracion de base de datos multi-engine (SQLite + PostgreSQL)."""
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from app.config import get_settings
import logging

logger = logging.getLogger(__name__)
settings = get_settings()

def _build_url() -> str:
    if settings.DB_ENGINE == "postgres":
        pw = settings.POSTGRES_PASSWORD
        return f"postgresql://{settings.POSTGRES_USER}:{pw}@{settings.POSTGRES_HOST}:{settings.POSTGRES_PORT}/{settings.POSTGRES_DB}"
    return settings.DATABASE_URL

def _get_connect_args() -> dict:
    if "sqlite" in _build_url():
        return {"check_same_thread": False}
    return {}

DATABASE_URL = _build_url()
logger.info(f"[DB] Engine: {settings.DB_ENGINE.upper()} -> {DATABASE_URL.split('@')[-1] if '@' in DATABASE_URL else DATABASE_URL}")

engine = create_engine(
    DATABASE_URL,
    connect_args=_get_connect_args(),
    echo=False,
    pool_pre_ping=True if settings.DB_ENGINE == "postgres" else False,
    pool_size=5 if settings.DB_ENGINE == "postgres" else 0,
    max_overflow=10 if settings.DB_ENGINE == "postgres" else 0,
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def check_db_connection() -> dict:
    """Verifica conectividad con la base de datos."""
    try:
        with engine.connect() as conn:
            result = conn.exec_driver_sql("SELECT 1")
            result.fetchone()
        tables = Base.metadata.tables.keys()
        return {"status": "connected", "engine": settings.DB_ENGINE, "tables": list(tables)}
    except Exception as e:
        return {"status": "error", "engine": settings.DB_ENGINE, "error": str(e)}
