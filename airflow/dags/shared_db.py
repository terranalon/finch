"""Shared database connection pool for Airflow DAGs.

Provides a centralized connection pool to prevent connection exhaustion
when multiple DAGs run simultaneously.

Settings:
- pool_size=5: Conservative pool size per worker
- max_overflow=10: Limited overflow to prevent connection storms
- pool_recycle=1800: Recycle connections every 30 min
- isolation_level=READ COMMITTED: Allows reads during writes
"""

import logging
import os

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

logger = logging.getLogger(__name__)

# Load environment variables from backend .env
load_dotenv("/opt/airflow/backend/.env")

# Get database URL from environment and modify for Docker networking
DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise ValueError("DATABASE_URL not found in environment variables")

# Replace 'postgres' hostname with 'host.docker.internal' for cross-network access
# Airflow containers can't access backend's 'postgres' service directly
DATABASE_URL = DATABASE_URL.replace("postgres:5432", "host.docker.internal:5432")

# Single shared engine with conservative pooling and PostgreSQL optimizations
engine = create_engine(
    DATABASE_URL,
    pool_size=5,  # Conservative pool size per worker
    max_overflow=10,  # Limited overflow to prevent connection storms
    pool_recycle=1800,  # Recycle connections every 30 min
    pool_pre_ping=True,  # Enable connection health checks
    isolation_level="READ COMMITTED",  # Allow reads during writes
    connect_args={
        "options": "-c lock_timeout=10000"  # 10s lock timeout
    },
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_session() -> Session:
    """Get a database session with proper cleanup.

    Usage:
        session = get_session()
        try:
            result = session.execute(text(QUERY))
            session.commit()
        finally:
            session.close()

    Returns:
        SQLAlchemy database session
    """
    return SessionLocal()


def get_engine() -> Engine:
    """Get the shared database engine.

    Returns:
        SQLAlchemy database engine
    """
    return engine
