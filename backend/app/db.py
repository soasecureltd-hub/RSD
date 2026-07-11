"""
Database configuration and session management
"""
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from app.config import settings

DATABASE_URL = settings.DATABASE_URL
_is_sqlite = DATABASE_URL.startswith("sqlite")

# Create engine.
# For cloud Postgres (e.g. Supabase) pool_pre_ping validates a connection before
# use — Supabase drops idle connections, which would otherwise surface as random
# "server closed the connection unexpectedly" errors. pool_recycle proactively
# refreshes connections older than 30 minutes.
engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False} if _is_sqlite else {},
    pool_pre_ping=not _is_sqlite,
    pool_recycle=-1 if _is_sqlite else 1800,
    echo=False,
)

# Session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base for ORM models
Base = declarative_base()


def get_db():
    """Dependency to get database session"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """Initialize database tables"""
    Base.metadata.create_all(bind=engine)
