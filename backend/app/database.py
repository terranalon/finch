"""Database configuration and session management."""

from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.config import settings


# Base class for ORM models
class Base(DeclarativeBase):
    """Base class for all SQLAlchemy ORM models."""

    pass


# Create database engine with connection pooling and PostgreSQL optimizations
# Key settings to prevent UI blocking during DAG execution:
# - isolation_level="READ COMMITTED": Allows reads during writes (MVCC)
# - lock_timeout: Prevents queries from waiting indefinitely on locks
engine = create_engine(
    settings.database_url,
    pool_pre_ping=True,  # Enable connection health checks
    pool_size=10,  # Number of connections to maintain
    max_overflow=20,  # Maximum number of connections beyond pool_size
    pool_recycle=3600,  # Recycle connections after 1 hour
    echo=False,  # Set to True for SQL query logging in development
    isolation_level="READ COMMITTED",  # Allow reads during writes to prevent UI blocking
    connect_args={
        "options": "-c lock_timeout=5000"  # 5s lock timeout to prevent indefinite waits
    },
)

# Create session factory
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
    expire_on_commit=False,  # Prevent lazy loading errors after commit
)


# Dependency for FastAPI routes
def get_db() -> Generator[Session, None, None]:
    """
    Database session dependency for FastAPI routes.

    Yields:
        Session: SQLAlchemy database session

    Example:
        @app.get("/items")
        def get_items(db: Session = Depends(get_db)):
            return db.query(Item).all()
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
