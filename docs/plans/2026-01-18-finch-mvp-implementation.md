# Finch MVP Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Transform the single-user portfolio tracker into a multi-tenant SaaS with authentication, Hebrew localization, and full Israeli broker support.

**Architecture:** Add User model with JWT authentication, introduce Portfolio as grouping layer, migrate existing Entity→Account to User→Portfolio→Account. All existing data becomes the "seed user" for migration. Row-level isolation via user_id.

**Tech Stack:** FastAPI, SQLAlchemy 2.0, PostgreSQL 15, React 18, bcrypt, PyJWT, Google OAuth (authlib)

---

## Implementation Phases

| Phase | Focus | Status |
|-------|-------|--------|
| **Phase 1** | Auth & Multi-tenancy | Detailed below |
| **Phase 2** | Data Model Migration | ✅ Complete (Task 16 frontend toggle pending) |
| **Phase 3** | Broker Integrations | Outlined |
| **Phase 4** | i18n & UI Polish | Outlined |
| **Phase 5** | Deployment & Infrastructure | Outlined |

---

# Phase 1: Authentication & Multi-Tenancy
## Overview

Add user authentication (email/password + Google OAuth), create User and Portfolio models, and migrate existing Entity-based data to the new User→Portfolio→Account hierarchy.

**Estimated Tasks:** 25 bite-sized steps
**Dependencies:** None (this is the foundation)

---

## Task 1: Add Authentication Dependencies

**Files:**
- Modify: `backend/pyproject.toml`
- Modify: `backend/app/config.py`

**Step 1.1: Add auth dependencies to pyproject.toml**

Add to `[project.dependencies]`:
```toml
"bcrypt>=4.1.0",
"PyJWT>=2.8.0",
"authlib>=1.3.0",
"httpx>=0.27.0",
```

**Step 1.2: Install dependencies**

Run: `cd backend && uv sync`
Expected: Dependencies installed successfully

**Step 1.3: Add auth config to config.py**

Add new fields to `Settings` class:
```python
# Authentication
jwt_secret_key: str = "change-me-in-production"  # Generate with: openssl rand -hex 32
jwt_algorithm: str = "HS256"
access_token_expire_minutes: int = 30
refresh_token_expire_days: int = 7

# Google OAuth
google_client_id: str = ""
google_client_secret: str = ""
google_redirect_uri: str = "http://localhost:8000/api/auth/google/callback"
```

**Step 1.4: Commit**

```bash
git add backend/pyproject.toml backend/app/config.py
git commit -m "feat(auth): add authentication dependencies and config"
```

---

## Task 2: Create User Model

**Files:**
- Create: `backend/app/models/user.py`
- Modify: `backend/app/models/__init__.py`
- Test: `backend/tests/test_user_model.py`

**Step 2.1: Write the failing test**

Create `backend/tests/test_user_model.py`:
```python
"""Tests for User model."""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.database import Base
from app.models.user import User


@pytest.fixture
def db_session():
    """Create in-memory SQLite database for testing."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()
    yield session
    session.close()


def test_create_user_with_password(db_session: Session):
    """Test creating a user with email and password."""
    user = User(
        email="test@example.com",
        password_hash="hashed_password_here",
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)

    assert user.id is not None
    assert user.email == "test@example.com"
    assert user.password_hash == "hashed_password_here"
    assert user.google_id is None
    assert user.is_active is True


def test_create_user_with_google(db_session: Session):
    """Test creating a user with Google OAuth."""
    user = User(
        email="google@example.com",
        google_id="google_123456",
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)

    assert user.id is not None
    assert user.email == "google@example.com"
    assert user.password_hash is None
    assert user.google_id == "google_123456"


def test_user_email_unique(db_session: Session):
    """Test that user emails are unique."""
    user1 = User(email="same@example.com", password_hash="hash1")
    db_session.add(user1)
    db_session.commit()

    user2 = User(email="same@example.com", password_hash="hash2")
    db_session.add(user2)

    with pytest.raises(Exception):  # IntegrityError
        db_session.commit()
```

**Step 2.2: Run test to verify it fails**

Run: `cd backend && pytest tests/test_user_model.py -v`
Expected: FAIL with "ModuleNotFoundError: No module named 'app.models.user'"

**Step 2.3: Create User model**

Create `backend/app/models/user.py`:
```python
"""User model for authentication."""

from datetime import datetime
from uuid import uuid4

from sqlalchemy import Boolean, String
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.database import Base


class User(Base):
    """User model representing authenticated users."""

    __tablename__ = "users"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid4())
    )
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    password_hash: Mapped[str | None] = mapped_column(String(255))
    google_id: Mapped[str | None] = mapped_column(String(255), unique=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        server_default=func.now(), onupdate=func.now()
    )

    # Relationships (to be added when Portfolio model is created)
    # portfolios: Mapped[list["Portfolio"]] = relationship(back_populates="user")

    def __repr__(self) -> str:
        return f"<User(id={self.id}, email='{self.email}')>"
```

**Step 2.4: Export User from models/__init__.py**

Add to `backend/app/models/__init__.py`:
```python
from app.models.user import User

# Add "User" to __all__ list
```

**Step 2.5: Run test to verify it passes**

Run: `cd backend && pytest tests/test_user_model.py -v`
Expected: PASS (3 tests)

**Step 2.6: Commit**

```bash
git add backend/app/models/user.py backend/app/models/__init__.py backend/tests/test_user_model.py
git commit -m "feat(auth): add User model with email/password and Google OAuth support"
```

---

## Task 3: Create Session Model (for JWT Revocation)

**Files:**
- Create: `backend/app/models/session.py`
- Modify: `backend/app/models/__init__.py`
- Test: `backend/tests/test_session_model.py`

**Step 3.1: Write the failing test**

Create `backend/tests/test_session_model.py`:
```python
"""Tests for Session model."""

import pytest
from datetime import datetime, timedelta, timezone
from sqlalchemy import create_engine
from sqlalchemy.orm import Session as DBSession, sessionmaker

from app.database import Base
from app.models.user import User
from app.models.session import Session


@pytest.fixture
def db_session():
    """Create in-memory SQLite database for testing."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()
    yield session
    session.close()


def test_create_session(db_session: DBSession):
    """Test creating a session for a user."""
    user = User(email="test@example.com", password_hash="hash")
    db_session.add(user)
    db_session.commit()

    session = Session(
        user_id=user.id,
        refresh_token_hash="hashed_refresh_token",
        expires_at=datetime.now(timezone.utc) + timedelta(days=7),
    )
    db_session.add(session)
    db_session.commit()
    db_session.refresh(session)

    assert session.id is not None
    assert session.user_id == user.id
    assert session.refresh_token_hash == "hashed_refresh_token"
    assert session.is_revoked is False


def test_session_cascade_delete(db_session: DBSession):
    """Test that sessions are deleted when user is deleted."""
    user = User(email="test@example.com", password_hash="hash")
    db_session.add(user)
    db_session.commit()

    session = Session(
        user_id=user.id,
        refresh_token_hash="token",
        expires_at=datetime.now(timezone.utc) + timedelta(days=7),
    )
    db_session.add(session)
    db_session.commit()

    db_session.delete(user)
    db_session.commit()

    remaining = db_session.query(Session).filter_by(user_id=user.id).all()
    assert len(remaining) == 0
```

**Step 3.2: Run test to verify it fails**

Run: `cd backend && pytest tests/test_session_model.py -v`
Expected: FAIL with "ModuleNotFoundError: No module named 'app.models.session'"

**Step 3.3: Create Session model**

Create `backend/app/models/session.py`:
```python
"""Session model for JWT refresh token management."""

from datetime import datetime
from uuid import uuid4

from sqlalchemy import Boolean, DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.database import Base


class Session(Base):
    """Session model for managing refresh tokens."""

    __tablename__ = "sessions"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid4())
    )
    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    refresh_token_hash: Mapped[str] = mapped_column(String(255))
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    is_revoked: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())

    # Relationships
    user: Mapped["User"] = relationship(back_populates="sessions")

    def __repr__(self) -> str:
        return f"<Session(id={self.id}, user_id='{self.user_id}')>"
```

**Step 3.4: Update User model with sessions relationship**

Add to `backend/app/models/user.py` in User class:
```python
# Add import at top
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from app.models.session import Session

# Add relationship in class
sessions: Mapped[list["Session"]] = relationship(
    back_populates="user", cascade="all, delete-orphan"
)
```

**Step 3.5: Export Session from models/__init__.py**

Add to `backend/app/models/__init__.py`:
```python
from app.models.session import Session

# Add "Session" to __all__ list
```

**Step 3.6: Run test to verify it passes**

Run: `cd backend && pytest tests/test_session_model.py -v`
Expected: PASS (2 tests)

**Step 3.7: Commit**

```bash
git add backend/app/models/session.py backend/app/models/user.py backend/app/models/__init__.py backend/tests/test_session_model.py
git commit -m "feat(auth): add Session model for JWT refresh token management"
```

---

## Task 4: Create Portfolio Model

**Files:**
- Create: `backend/app/models/portfolio.py`
- Modify: `backend/app/models/__init__.py`
- Test: `backend/tests/test_portfolio_model.py`

**Step 4.1: Write the failing test**

Create `backend/tests/test_portfolio_model.py`:
```python
"""Tests for Portfolio model."""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.database import Base
from app.models.user import User
from app.models.portfolio import Portfolio


@pytest.fixture
def db_session():
    """Create in-memory SQLite database for testing."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()
    yield session
    session.close()


def test_create_portfolio(db_session: Session):
    """Test creating a portfolio for a user."""
    user = User(email="test@example.com", password_hash="hash")
    db_session.add(user)
    db_session.commit()

    portfolio = Portfolio(
        user_id=user.id,
        name="My Investments",
        description="Personal portfolio",
    )
    db_session.add(portfolio)
    db_session.commit()
    db_session.refresh(portfolio)

    assert portfolio.id is not None
    assert portfolio.user_id == user.id
    assert portfolio.name == "My Investments"


def test_user_has_multiple_portfolios(db_session: Session):
    """Test that a user can have multiple portfolios."""
    user = User(email="test@example.com", password_hash="hash")
    db_session.add(user)
    db_session.commit()

    portfolio1 = Portfolio(user_id=user.id, name="Personal")
    portfolio2 = Portfolio(user_id=user.id, name="Retirement")
    db_session.add_all([portfolio1, portfolio2])
    db_session.commit()

    db_session.refresh(user)
    assert len(user.portfolios) == 2
```

**Step 4.2: Run test to verify it fails**

Run: `cd backend && pytest tests/test_portfolio_model.py -v`
Expected: FAIL with "ModuleNotFoundError: No module named 'app.models.portfolio'"

**Step 4.3: Create Portfolio model**

Create `backend/app/models/portfolio.py`:
```python
"""Portfolio model - groups accounts for a user."""

from datetime import datetime
from uuid import uuid4

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.database import Base


class Portfolio(Base):
    """Portfolio model representing a grouping of accounts."""

    __tablename__ = "portfolios"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid4())
    )
    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    name: Mapped[str] = mapped_column(String(100))
    description: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        server_default=func.now(), onupdate=func.now()
    )

    # Relationships
    user: Mapped["User"] = relationship(back_populates="portfolios")
    # accounts: Mapped[list["Account"]] = relationship(back_populates="portfolio")

    def __repr__(self) -> str:
        return f"<Portfolio(id={self.id}, name='{self.name}')>"
```

**Step 4.4: Update User model with portfolios relationship**

Add to `backend/app/models/user.py` in User class:
```python
# Add to TYPE_CHECKING imports
from app.models.portfolio import Portfolio

# Add relationship
portfolios: Mapped[list["Portfolio"]] = relationship(
    back_populates="user", cascade="all, delete-orphan"
)
```

**Step 4.5: Export Portfolio from models/__init__.py**

Add to `backend/app/models/__init__.py`:
```python
from app.models.portfolio import Portfolio

# Add "Portfolio" to __all__ list
```

**Step 4.6: Run test to verify it passes**

Run: `cd backend && pytest tests/test_portfolio_model.py -v`
Expected: PASS (2 tests)

**Step 4.7: Commit**

```bash
git add backend/app/models/portfolio.py backend/app/models/user.py backend/app/models/__init__.py backend/tests/test_portfolio_model.py
git commit -m "feat(auth): add Portfolio model for grouping accounts per user"
```

---

## Task 5: Create Auth Service

**Files:**
- Create: `backend/app/services/auth_service.py`
- Test: `backend/tests/test_auth_service.py`

**Step 5.1: Write the failing test**

Create `backend/tests/test_auth_service.py`:
```python
"""Tests for auth service."""

import pytest
from datetime import datetime, timedelta, timezone

from app.services.auth_service import AuthService


def test_hash_password():
    """Test password hashing."""
    password = "secure_password_123"
    hashed = AuthService.hash_password(password)

    assert hashed != password
    assert hashed.startswith("$2b$")  # bcrypt prefix


def test_verify_password_correct():
    """Test verifying correct password."""
    password = "secure_password_123"
    hashed = AuthService.hash_password(password)

    assert AuthService.verify_password(password, hashed) is True


def test_verify_password_incorrect():
    """Test verifying incorrect password."""
    password = "secure_password_123"
    hashed = AuthService.hash_password(password)

    assert AuthService.verify_password("wrong_password", hashed) is False


def test_create_access_token():
    """Test creating access token."""
    user_id = "user-123"
    token = AuthService.create_access_token(user_id)

    assert token is not None
    assert isinstance(token, str)
    assert len(token) > 50  # JWT tokens are long


def test_decode_access_token():
    """Test decoding access token."""
    user_id = "user-123"
    token = AuthService.create_access_token(user_id)
    decoded = AuthService.decode_access_token(token)

    assert decoded is not None
    assert decoded["sub"] == user_id
    assert decoded["type"] == "access"


def test_decode_expired_token():
    """Test that expired tokens fail."""
    user_id = "user-123"
    # Create token that expired 1 hour ago
    token = AuthService.create_access_token(
        user_id, expires_delta=timedelta(hours=-1)
    )
    decoded = AuthService.decode_access_token(token)

    assert decoded is None


def test_create_refresh_token():
    """Test creating refresh token."""
    user_id = "user-123"
    token = AuthService.create_refresh_token(user_id)

    assert token is not None
    decoded = AuthService.decode_access_token(token)
    assert decoded["type"] == "refresh"
```

**Step 5.2: Run test to verify it fails**

Run: `cd backend && pytest tests/test_auth_service.py -v`
Expected: FAIL with "ModuleNotFoundError: No module named 'app.services.auth_service'"

**Step 5.3: Create AuthService**

Create `backend/app/services/auth_service.py`:
```python
"""Authentication service for password hashing and JWT management."""

import logging
from datetime import datetime, timedelta, timezone

import bcrypt
import jwt

from app.config import settings

logger = logging.getLogger(__name__)


class AuthService:
    """Service for authentication operations."""

    @staticmethod
    def hash_password(password: str) -> str:
        """Hash a password using bcrypt."""
        salt = bcrypt.gensalt()
        hashed = bcrypt.hashpw(password.encode("utf-8"), salt)
        return hashed.decode("utf-8")

    @staticmethod
    def verify_password(password: str, hashed: str) -> bool:
        """Verify a password against its hash."""
        try:
            return bcrypt.checkpw(password.encode("utf-8"), hashed.encode("utf-8"))
        except Exception as e:
            logger.error(f"Password verification error: {e}")
            return False

    @staticmethod
    def create_access_token(
        user_id: str,
        expires_delta: timedelta | None = None,
    ) -> str:
        """Create a JWT access token."""
        if expires_delta is None:
            expires_delta = timedelta(minutes=settings.access_token_expire_minutes)

        expire = datetime.now(timezone.utc) + expires_delta
        payload = {
            "sub": user_id,
            "exp": expire,
            "iat": datetime.now(timezone.utc),
            "type": "access",
        }
        return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)

    @staticmethod
    def create_refresh_token(
        user_id: str,
        expires_delta: timedelta | None = None,
    ) -> str:
        """Create a JWT refresh token."""
        if expires_delta is None:
            expires_delta = timedelta(days=settings.refresh_token_expire_days)

        expire = datetime.now(timezone.utc) + expires_delta
        payload = {
            "sub": user_id,
            "exp": expire,
            "iat": datetime.now(timezone.utc),
            "type": "refresh",
        }
        return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)

    @staticmethod
    def decode_access_token(token: str) -> dict | None:
        """Decode and validate a JWT token."""
        try:
            payload = jwt.decode(
                token,
                settings.jwt_secret_key,
                algorithms=[settings.jwt_algorithm],
            )
            return payload
        except jwt.ExpiredSignatureError:
            logger.debug("Token expired")
            return None
        except jwt.InvalidTokenError as e:
            logger.debug(f"Invalid token: {e}")
            return None
```

**Step 5.4: Run test to verify it passes**

Run: `cd backend && pytest tests/test_auth_service.py -v`
Expected: PASS (7 tests)

**Step 5.5: Commit**

```bash
git add backend/app/services/auth_service.py backend/tests/test_auth_service.py
git commit -m "feat(auth): add AuthService with password hashing and JWT tokens"
```

---

## Task 6: Create Auth Router (Registration & Login)

**Files:**
- Create: `backend/app/routers/auth.py`
- Create: `backend/app/schemas/auth.py`
- Modify: `backend/app/main.py`
- Test: `backend/tests/test_auth_router.py`

**Step 6.1: Create auth schemas**

Create `backend/app/schemas/auth.py`:
```python
"""Schemas for authentication endpoints."""

from pydantic import BaseModel, EmailStr, Field


class UserRegister(BaseModel):
    """Schema for user registration."""

    email: EmailStr
    password: str = Field(min_length=8, max_length=100)


class UserLogin(BaseModel):
    """Schema for user login."""

    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    """Schema for token response."""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class TokenRefresh(BaseModel):
    """Schema for token refresh."""

    refresh_token: str


class UserResponse(BaseModel):
    """Schema for user response."""

    id: str
    email: str
    is_active: bool

    model_config = {"from_attributes": True}


class MessageResponse(BaseModel):
    """Schema for simple message response."""

    message: str
```

**Step 6.2: Create auth router**

Create `backend/app/routers/auth.py`:
```python
"""Authentication router."""

import logging
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User
from app.models.session import Session as UserSession
from app.schemas.auth import (
    MessageResponse,
    TokenRefresh,
    TokenResponse,
    UserLogin,
    UserRegister,
    UserResponse,
)
from app.services.auth_service import AuthService
from app.config import settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["authentication"])


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def register(data: UserRegister, db: Session = Depends(get_db)) -> User:
    """Register a new user."""
    # Check if email already exists
    existing = db.query(User).filter(User.email == data.email).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered",
        )

    # Create user
    user = User(
        email=data.email,
        password_hash=AuthService.hash_password(data.password),
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    logger.info(f"User registered: {user.email}")
    return user


@router.post("/login", response_model=TokenResponse)
def login(data: UserLogin, db: Session = Depends(get_db)) -> dict:
    """Login and get access/refresh tokens."""
    # Find user
    user = db.query(User).filter(User.email == data.email).first()
    if not user or not user.password_hash:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    # Verify password
    if not AuthService.verify_password(data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    # Check if user is active
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is disabled",
        )

    # Create tokens
    access_token = AuthService.create_access_token(user.id)
    refresh_token = AuthService.create_refresh_token(user.id)

    # Store refresh token hash in session
    session = UserSession(
        user_id=user.id,
        refresh_token_hash=AuthService.hash_password(refresh_token),
        expires_at=datetime.now(timezone.utc) + timedelta(days=settings.refresh_token_expire_days),
    )
    db.add(session)
    db.commit()

    logger.info(f"User logged in: {user.email}")
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
    }


@router.post("/refresh", response_model=TokenResponse)
def refresh_tokens(data: TokenRefresh, db: Session = Depends(get_db)) -> dict:
    """Refresh access token using refresh token."""
    # Decode refresh token
    payload = AuthService.decode_access_token(data.refresh_token)
    if not payload or payload.get("type") != "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token",
        )

    user_id = payload["sub"]

    # Find user
    user = db.query(User).filter(User.id == user_id).first()
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive",
        )

    # Verify refresh token exists in sessions (not revoked)
    sessions = db.query(UserSession).filter(
        UserSession.user_id == user_id,
        UserSession.is_revoked == False,
        UserSession.expires_at > datetime.now(timezone.utc),
    ).all()

    valid_session = None
    for session in sessions:
        if AuthService.verify_password(data.refresh_token, session.refresh_token_hash):
            valid_session = session
            break

    if not valid_session:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token not found or revoked",
        )

    # Revoke old session
    valid_session.is_revoked = True

    # Create new tokens
    access_token = AuthService.create_access_token(user.id)
    refresh_token = AuthService.create_refresh_token(user.id)

    # Store new refresh token
    new_session = UserSession(
        user_id=user.id,
        refresh_token_hash=AuthService.hash_password(refresh_token),
        expires_at=datetime.now(timezone.utc) + timedelta(days=settings.refresh_token_expire_days),
    )
    db.add(new_session)
    db.commit()

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
    }


@router.post("/logout", response_model=MessageResponse)
def logout(data: TokenRefresh, db: Session = Depends(get_db)) -> dict:
    """Logout and revoke refresh token."""
    payload = AuthService.decode_access_token(data.refresh_token)
    if payload and payload.get("type") == "refresh":
        user_id = payload["sub"]
        # Revoke all sessions for this user (or just the matching one)
        sessions = db.query(UserSession).filter(
            UserSession.user_id == user_id,
            UserSession.is_revoked == False,
        ).all()

        for session in sessions:
            if AuthService.verify_password(data.refresh_token, session.refresh_token_hash):
                session.is_revoked = True
                break

        db.commit()

    return {"message": "Successfully logged out"}
```

**Step 6.3: Register auth router in main.py**

Add to `backend/app/main.py`:
```python
from app.routers import auth

# In router registration section
app.include_router(auth.router, prefix="/api")
```

**Step 6.4: Write integration test**

Create `backend/tests/test_auth_router.py`:
```python
"""Integration tests for auth router."""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.main import app
from app.database import Base, get_db


@pytest.fixture
def client():
    """Create test client with in-memory database."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    TestingSessionLocal = sessionmaker(bind=engine)

    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    yield TestClient(app)
    app.dependency_overrides.clear()


def test_register_success(client):
    """Test successful registration."""
    response = client.post(
        "/api/auth/register",
        json={"email": "test@example.com", "password": "secure123"},
    )
    assert response.status_code == 201
    data = response.json()
    assert data["email"] == "test@example.com"
    assert "id" in data


def test_register_duplicate_email(client):
    """Test registration with duplicate email."""
    client.post(
        "/api/auth/register",
        json={"email": "test@example.com", "password": "secure123"},
    )
    response = client.post(
        "/api/auth/register",
        json={"email": "test@example.com", "password": "different"},
    )
    assert response.status_code == 400


def test_login_success(client):
    """Test successful login."""
    client.post(
        "/api/auth/register",
        json={"email": "test@example.com", "password": "secure123"},
    )
    response = client.post(
        "/api/auth/login",
        json={"email": "test@example.com", "password": "secure123"},
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data


def test_login_wrong_password(client):
    """Test login with wrong password."""
    client.post(
        "/api/auth/register",
        json={"email": "test@example.com", "password": "secure123"},
    )
    response = client.post(
        "/api/auth/login",
        json={"email": "test@example.com", "password": "wrong"},
    )
    assert response.status_code == 401
```

**Step 6.5: Run tests**

Run: `cd backend && pytest tests/test_auth_router.py -v`
Expected: PASS (4 tests)

**Step 6.6: Commit**

```bash
git add backend/app/routers/auth.py backend/app/schemas/auth.py backend/app/main.py backend/tests/test_auth_router.py
git commit -m "feat(auth): add auth router with register, login, refresh, logout endpoints"
```

---

## Task 7: Create Auth Dependency (Protected Routes)

**Files:**
- Create: `backend/app/dependencies/auth.py`
- Test: `backend/tests/test_auth_dependency.py`

**Step 7.1: Create auth dependency**

Create `backend/app/dependencies/__init__.py`:
```python
"""FastAPI dependencies."""
```

Create `backend/app/dependencies/auth.py`:
```python
"""Authentication dependencies for protected routes."""

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User
from app.services.auth_service import AuthService

security = HTTPBearer()


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db),
) -> User:
    """
    Get current authenticated user from JWT token.

    Usage:
        @router.get("/protected")
        def protected_route(user: User = Depends(get_current_user)):
            return {"user_id": user.id}
    """
    token = credentials.credentials
    payload = AuthService.decode_access_token(token)

    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if payload.get("type") != "access":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token type",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_id = payload.get("sub")
    user = db.query(User).filter(User.id == user_id).first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is disabled",
        )

    return user


def get_current_user_optional(
    credentials: HTTPAuthorizationCredentials | None = Depends(
        HTTPBearer(auto_error=False)
    ),
    db: Session = Depends(get_db),
) -> User | None:
    """
    Get current user if authenticated, None otherwise.
    Useful for routes that work with or without authentication.
    """
    if not credentials:
        return None

    try:
        return get_current_user(credentials, db)
    except HTTPException:
        return None
```

**Step 7.2: Write test**

Create `backend/tests/test_auth_dependency.py`:
```python
"""Tests for auth dependency."""

import pytest
from fastapi import FastAPI, Depends
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base, get_db
from app.models.user import User
from app.dependencies.auth import get_current_user
from app.services.auth_service import AuthService


@pytest.fixture
def test_app():
    """Create test app with protected route."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    TestingSessionLocal = sessionmaker(bind=engine)

    app = FastAPI()

    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db

    @app.get("/protected")
    def protected_route(user: User = Depends(get_current_user)):
        return {"user_id": user.id, "email": user.email}

    # Create test user
    db = TestingSessionLocal()
    user = User(email="test@example.com", password_hash="hash")
    db.add(user)
    db.commit()
    user_id = user.id
    db.close()

    return TestClient(app), user_id


def test_protected_route_with_valid_token(test_app):
    """Test accessing protected route with valid token."""
    client, user_id = test_app
    token = AuthService.create_access_token(user_id)

    response = client.get(
        "/protected",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    assert response.json()["user_id"] == user_id


def test_protected_route_without_token(test_app):
    """Test accessing protected route without token."""
    client, _ = test_app
    response = client.get("/protected")
    assert response.status_code == 403  # HTTPBearer returns 403 when missing


def test_protected_route_with_invalid_token(test_app):
    """Test accessing protected route with invalid token."""
    client, _ = test_app
    response = client.get(
        "/protected",
        headers={"Authorization": "Bearer invalid_token"},
    )
    assert response.status_code == 401
```

**Step 7.3: Run tests**

Run: `cd backend && pytest tests/test_auth_dependency.py -v`
Expected: PASS (3 tests)

**Step 7.4: Commit**

```bash
git add backend/app/dependencies/ backend/tests/test_auth_dependency.py
git commit -m "feat(auth): add get_current_user dependency for protected routes"
```

---

## Task 8: Create Database Migration

**Files:**
- Create: `backend/alembic/versions/xxxx_add_auth_tables.py`

**Step 8.1: Generate migration**

Run: `cd backend && alembic revision -m "add auth tables (users, sessions, portfolios)"`

**Step 8.2: Edit migration file**

Edit the generated file to include:
```python
"""add auth tables (users, sessions, portfolios)

Revision ID: <generated>
Revises: <previous>
Create Date: <generated>
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers
revision = '<generated>'
down_revision = '<previous>'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create users table
    op.create_table(
        'users',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('email', sa.String(255), unique=True, nullable=False, index=True),
        sa.Column('password_hash', sa.String(255), nullable=True),
        sa.Column('google_id', sa.String(255), unique=True, nullable=True),
        sa.Column('is_active', sa.Boolean(), default=True, nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now(), onupdate=sa.func.now()),
    )

    # Create sessions table
    op.create_table(
        'sessions',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('user_id', sa.String(36), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('refresh_token_hash', sa.String(255), nullable=False),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('is_revoked', sa.Boolean(), default=False, nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
    )

    # Create portfolios table
    op.create_table(
        'portfolios',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('user_id', sa.String(36), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now(), onupdate=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table('portfolios')
    op.drop_table('sessions')
    op.drop_table('users')
```

**Step 8.3: Run migration**

Run: `cd backend && alembic upgrade head`
Expected: Migration applied successfully

**Step 8.4: Commit**

```bash
git add backend/alembic/versions/
git commit -m "feat(auth): add migration for users, sessions, portfolios tables"
```

---

## Task 9: Add Google OAuth Endpoints (DEFERRED)

**Status:** Deferred - will implement after data migration is complete.

---

## Task 10: Create Demo User Seeding Script

**Files:**
- Create: `backend/scripts/seed_demo_user.py`
- Test: `backend/tests/test_seed_demo_user.py`

**Step 10.1: Write the failing test**

Create `backend/tests/test_seed_demo_user.py`:
```python
"""Tests for demo user seeding script."""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.models.user import User
from app.models.session import Session
from app.models.portfolio import Portfolio


@pytest.fixture
def db_session():
    """Create in-memory SQLite database for testing."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    User.__table__.create(engine, checkfirst=True)
    Session.__table__.create(engine, checkfirst=True)
    Portfolio.__table__.create(engine, checkfirst=True)
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()
    yield session
    session.close()


def test_create_demo_user(db_session):
    """Test creating demo user with portfolio."""
    from scripts.seed_demo_user import create_demo_user

    user, portfolio = create_demo_user(db_session)

    assert user.email == "demo@finch.com"
    assert user.is_active is True
    assert portfolio.name == "Demo Portfolio"
    assert portfolio.user_id == user.id


def test_create_demo_user_idempotent(db_session):
    """Test that running seed twice doesn't create duplicates."""
    from scripts.seed_demo_user import create_demo_user

    user1, _ = create_demo_user(db_session)
    user2, _ = create_demo_user(db_session)

    assert user1.id == user2.id
    users = db_session.query(User).filter(User.email == "demo@finch.com").all()
    assert len(users) == 1
```

**Step 10.2: Run test to verify it fails**

Run: `cd backend && pytest tests/test_seed_demo_user.py -v`
Expected: FAIL with "ModuleNotFoundError: No module named 'scripts'"

**Step 10.3: Create seed script**

Create `backend/scripts/__init__.py`:
```python
"""Scripts for database seeding and management."""
```

Create `backend/scripts/seed_demo_user.py`:
```python
"""Seed demo user for 'Demo Portfolio' feature."""

import logging
from sqlalchemy.orm import Session as DBSession

from app.models.user import User
from app.models.portfolio import Portfolio
from app.services.auth_service import AuthService

logger = logging.getLogger(__name__)

DEMO_EMAIL = "demo@finch.com"
DEMO_PASSWORD = "demo1234"  # Simple password for demo account


def create_demo_user(db: DBSession) -> tuple[User, Portfolio]:
    """
    Create demo user with a sample portfolio.

    Returns existing user if already created (idempotent).

    Returns:
        Tuple of (User, Portfolio)
    """
    # Check if demo user already exists
    user = db.query(User).filter(User.email == DEMO_EMAIL).first()

    if user:
        logger.info(f"Demo user already exists: {user.id}")
        portfolio = db.query(Portfolio).filter(Portfolio.user_id == user.id).first()
        return user, portfolio

    # Create demo user
    user = User(
        email=DEMO_EMAIL,
        password_hash=AuthService.hash_password(DEMO_PASSWORD),
        is_active=True,
    )
    db.add(user)
    db.flush()  # Get user.id before creating portfolio

    # Create demo portfolio
    portfolio = Portfolio(
        user_id=user.id,
        name="Demo Portfolio",
        description="Sample portfolio demonstrating Finch features",
    )
    db.add(portfolio)
    db.commit()
    db.refresh(user)
    db.refresh(portfolio)

    logger.info(f"Created demo user: {user.email} with portfolio: {portfolio.name}")
    return user, portfolio


if __name__ == "__main__":
    """Run as standalone script."""
    import sys
    logging.basicConfig(level=logging.INFO)

    from app.database import SessionLocal

    db = SessionLocal()
    try:
        user, portfolio = create_demo_user(db)
        print(f"Demo user created: {user.email}")
        print(f"Demo portfolio: {portfolio.name}")
    finally:
        db.close()
```

**Step 10.4: Run test to verify it passes**

Run: `cd backend && pytest tests/test_seed_demo_user.py -v`
Expected: PASS (2 tests)

**Step 10.5: Commit (when git available)**

```bash
git add backend/scripts/ backend/tests/test_seed_demo_user.py
git commit -m "feat(auth): add demo user seeding script"
```

---

## Task 11: Migrate Account Model to Portfolio

**Files:**
- Modify: `backend/app/models/account.py`
- Modify: `backend/app/models/portfolio.py`
- Create: `backend/alembic/versions/add_portfolio_to_account.py`
- Test: `backend/tests/test_account_portfolio.py`

**Step 11.1: Write the failing test**

Create `backend/tests/test_account_portfolio.py`:
```python
"""Tests for Account-Portfolio relationship."""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.models.user import User
from app.models.session import Session as UserSession
from app.models.portfolio import Portfolio
from app.models.account import Account


@pytest.fixture
def db_session():
    """Create in-memory SQLite database for testing."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    # Create tables in dependency order
    User.__table__.create(engine, checkfirst=True)
    UserSession.__table__.create(engine, checkfirst=True)
    Portfolio.__table__.create(engine, checkfirst=True)
    # For Account, we need to create without the entity FK for this test
    # We'll test the portfolio_id relationship specifically
    yield engine


def test_account_has_portfolio_id():
    """Test that Account model has portfolio_id field."""
    # This tests the model definition
    assert hasattr(Account, "portfolio_id")


def test_portfolio_has_accounts_relationship():
    """Test that Portfolio has accounts relationship."""
    assert hasattr(Portfolio, "accounts")
```

**Step 11.2: Run test to verify it fails**

Run: `cd backend && pytest tests/test_account_portfolio.py::test_account_has_portfolio_id -v`
Expected: FAIL with "AssertionError" (portfolio_id not defined yet)

**Step 11.3: Update Account model**

Modify `backend/app/models/account.py`:
```python
"""Account model - represents financial accounts."""

from datetime import datetime

from sqlalchemy import Boolean, ForeignKey, Index, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.database import Base


class Account(Base):
    """Account model representing financial accounts belonging to portfolios."""

    __tablename__ = "accounts"
    __table_args__ = (
        Index("idx_accounts_entity", "entity_id"),
        Index("idx_accounts_portfolio", "portfolio_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    # Legacy: keep entity_id temporarily for migration
    entity_id: Mapped[int | None] = mapped_column(
        ForeignKey("entities.id", ondelete="CASCADE"), nullable=True
    )
    # New: portfolio_id for multi-tenant auth
    portfolio_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("portfolios.id", ondelete="CASCADE"), nullable=True
    )
    name: Mapped[str] = mapped_column(String(100))
    institution: Mapped[str | None] = mapped_column(String(100))
    account_type: Mapped[str] = mapped_column(String(50))
    currency: Mapped[str] = mapped_column(String(3))
    account_number: Mapped[str | None] = mapped_column(String(100))
    external_id: Mapped[str | None] = mapped_column(String(100))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    broker_type: Mapped[str | None] = mapped_column(String(50))
    meta_data: Mapped[dict | None] = mapped_column("metadata", JSONB)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(server_default=func.now(), onupdate=func.now())

    # Relationships
    entity: Mapped["Entity"] = relationship(back_populates="accounts")
    portfolio: Mapped["Portfolio"] = relationship(back_populates="accounts")
    holdings: Mapped[list["Holding"]] = relationship(
        back_populates="account", cascade="all, delete-orphan"
    )
    historical_snapshots: Mapped[list["HistoricalSnapshot"]] = relationship(
        back_populates="account", cascade="all, delete-orphan"
    )
    broker_data_sources: Mapped[list["BrokerDataSource"]] = relationship(
        back_populates="account", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Account(id={self.id}, name='{self.name}', type='{self.account_type}')>"
```

**Step 11.4: Update Portfolio model with accounts relationship**

Modify `backend/app/models/portfolio.py` - add accounts relationship:
```python
# Add to TYPE_CHECKING section
from app.models.account import Account

# Add relationship in class body
accounts: Mapped[list["Account"]] = relationship(
    back_populates="portfolio", cascade="all, delete-orphan"
)
```

**Step 11.5: Run test to verify it passes**

Run: `cd backend && pytest tests/test_account_portfolio.py -v`
Expected: PASS (2 tests)

**Step 11.6: Create database migration**

Create `backend/alembic/versions/add_portfolio_to_account.py`:
```python
"""Add portfolio_id to accounts table

Revision ID: add_portfolio_to_account
Revises: add_auth_tables
Create Date: 2026-01-18
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "add_portfolio_to_account"
down_revision: str | None = "add_auth_tables"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Add portfolio_id column (nullable for existing data)
    op.add_column(
        "accounts",
        sa.Column("portfolio_id", sa.String(36), nullable=True),
    )
    # Add foreign key constraint
    op.create_foreign_key(
        "fk_accounts_portfolio_id",
        "accounts",
        "portfolios",
        ["portfolio_id"],
        ["id"],
        ondelete="CASCADE",
    )
    # Add index for performance
    op.create_index("idx_accounts_portfolio", "accounts", ["portfolio_id"])
    # Make entity_id nullable (was required before)
    op.alter_column("accounts", "entity_id", nullable=True)


def downgrade() -> None:
    op.drop_index("idx_accounts_portfolio", table_name="accounts")
    op.drop_constraint("fk_accounts_portfolio_id", "accounts", type_="foreignkey")
    op.drop_column("accounts", "portfolio_id")
    op.alter_column("accounts", "entity_id", nullable=False)
```

**Step 11.7: Run migration**

Run: `cd backend && alembic upgrade head`
Expected: Migration applied successfully

**Step 11.8: Commit (when git available)**

```bash
git add backend/app/models/account.py backend/app/models/portfolio.py backend/alembic/versions/add_portfolio_to_account.py backend/tests/test_account_portfolio.py
git commit -m "feat(auth): add portfolio_id to Account model"
```

---

## Task 12: Create Data Migration Script

**Files:**
- Create: `backend/scripts/migrate_entities_to_portfolios.py`
- Test: `backend/tests/test_entity_migration.py`

**Step 12.1: Write the failing test**

Create `backend/tests/test_entity_migration.py`:
```python
"""Tests for entity to portfolio migration script."""

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.models.user import User
from app.models.session import Session as UserSession
from app.models.portfolio import Portfolio


@pytest.fixture
def db_session():
    """Create in-memory SQLite database with mock entity/account data."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    # Create auth tables
    User.__table__.create(engine, checkfirst=True)
    UserSession.__table__.create(engine, checkfirst=True)
    Portfolio.__table__.create(engine, checkfirst=True)

    # Create mock entities table (simulating existing data)
    with engine.connect() as conn:
        conn.execute(text("""
            CREATE TABLE entities (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                type TEXT NOT NULL
            )
        """))
        conn.execute(text("""
            CREATE TABLE accounts (
                id INTEGER PRIMARY KEY,
                entity_id INTEGER,
                portfolio_id TEXT,
                name TEXT NOT NULL,
                account_type TEXT NOT NULL,
                currency TEXT NOT NULL
            )
        """))
        # Insert test data
        conn.execute(text("INSERT INTO entities (id, name, type) VALUES (1, 'John Doe', 'Individual')"))
        conn.execute(text("INSERT INTO entities (id, name, type) VALUES (2, 'Jane Corp', 'Corporation')"))
        conn.execute(text("INSERT INTO accounts (id, entity_id, name, account_type, currency) VALUES (1, 1, 'IBI Account', 'brokerage', 'ILS')"))
        conn.execute(text("INSERT INTO accounts (id, entity_id, name, account_type, currency) VALUES (2, 1, 'Binance', 'crypto', 'USD')"))
        conn.execute(text("INSERT INTO accounts (id, entity_id, name, account_type, currency) VALUES (3, 2, 'Corp Account', 'brokerage', 'USD')"))
        conn.commit()

    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()
    yield session
    session.close()


def test_migrate_creates_default_user(db_session):
    """Test migration creates a default user."""
    from scripts.migrate_entities_to_portfolios import migrate_entities

    result = migrate_entities(db_session)

    assert result["user_created"] is True
    user = db_session.query(User).filter(User.email == "migrated@finch.local").first()
    assert user is not None


def test_migrate_creates_portfolios_from_entities(db_session):
    """Test migration creates portfolio per entity."""
    from scripts.migrate_entities_to_portfolios import migrate_entities

    result = migrate_entities(db_session)

    assert result["portfolios_created"] == 2
    portfolios = db_session.query(Portfolio).all()
    assert len(portfolios) == 2
    names = {p.name for p in portfolios}
    assert "John Doe" in names
    assert "Jane Corp" in names


def test_migrate_links_accounts_to_portfolios(db_session):
    """Test migration links accounts to their new portfolios."""
    from scripts.migrate_entities_to_portfolios import migrate_entities

    migrate_entities(db_session)

    # Check accounts have portfolio_id set
    from sqlalchemy import text
    result = db_session.execute(text("SELECT id, portfolio_id FROM accounts WHERE portfolio_id IS NOT NULL"))
    rows = result.fetchall()
    assert len(rows) == 3  # All 3 accounts should have portfolio_id


def test_migrate_is_idempotent(db_session):
    """Test running migration twice doesn't create duplicates."""
    from scripts.migrate_entities_to_portfolios import migrate_entities

    migrate_entities(db_session)
    result = migrate_entities(db_session)

    assert result["portfolios_created"] == 0  # No new portfolios
    users = db_session.query(User).filter(User.email == "migrated@finch.local").all()
    assert len(users) == 1
```

**Step 12.2: Run test to verify it fails**

Run: `cd backend && pytest tests/test_entity_migration.py -v`
Expected: FAIL with "ModuleNotFoundError" or "ImportError"

**Step 12.3: Create migration script**

Create `backend/scripts/migrate_entities_to_portfolios.py`:
```python
"""Migrate Entity→Account to User→Portfolio→Account hierarchy."""

import logging
from sqlalchemy import text
from sqlalchemy.orm import Session as DBSession

from app.models.user import User
from app.models.portfolio import Portfolio
from app.services.auth_service import AuthService

logger = logging.getLogger(__name__)

MIGRATION_USER_EMAIL = "migrated@finch.local"
MIGRATION_USER_PASSWORD = "migrated-user-change-me"


def migrate_entities(db: DBSession) -> dict:
    """
    Migrate existing Entity→Account data to User→Portfolio→Account.

    Strategy:
    1. Create a default "migration user" for existing data
    2. For each Entity, create a Portfolio with same name
    3. Link all entity's accounts to the new portfolio

    Returns:
        Dict with migration statistics
    """
    stats = {
        "user_created": False,
        "portfolios_created": 0,
        "accounts_updated": 0,
    }

    # Step 1: Create or get migration user
    user = db.query(User).filter(User.email == MIGRATION_USER_EMAIL).first()
    if not user:
        user = User(
            email=MIGRATION_USER_EMAIL,
            password_hash=AuthService.hash_password(MIGRATION_USER_PASSWORD),
            is_active=True,
        )
        db.add(user)
        db.flush()
        stats["user_created"] = True
        logger.info(f"Created migration user: {user.email}")

    # Step 2: Get all entities
    entities_result = db.execute(text("SELECT id, name, type FROM entities"))
    entities = entities_result.fetchall()

    # Track entity_id -> portfolio_id mapping
    entity_to_portfolio = {}

    for entity_id, entity_name, entity_type in entities:
        # Check if portfolio already exists for this entity
        # (using description to track source entity_id)
        existing = (
            db.query(Portfolio)
            .filter(
                Portfolio.user_id == user.id,
                Portfolio.description.like(f"%entity_id:{entity_id}%"),
            )
            .first()
        )

        if existing:
            entity_to_portfolio[entity_id] = existing.id
            logger.debug(f"Portfolio already exists for entity {entity_id}")
            continue

        # Create new portfolio
        portfolio = Portfolio(
            user_id=user.id,
            name=entity_name,
            description=f"Migrated from {entity_type}. Original entity_id:{entity_id}",
        )
        db.add(portfolio)
        db.flush()
        entity_to_portfolio[entity_id] = portfolio.id
        stats["portfolios_created"] += 1
        logger.info(f"Created portfolio '{entity_name}' for entity {entity_id}")

    # Step 3: Update accounts to link to portfolios
    for entity_id, portfolio_id in entity_to_portfolio.items():
        result = db.execute(
            text(
                "UPDATE accounts SET portfolio_id = :portfolio_id "
                "WHERE entity_id = :entity_id AND portfolio_id IS NULL"
            ),
            {"portfolio_id": portfolio_id, "entity_id": entity_id},
        )
        stats["accounts_updated"] += result.rowcount

    db.commit()
    logger.info(f"Migration complete: {stats}")
    return stats


if __name__ == "__main__":
    """Run as standalone script."""
    import sys
    logging.basicConfig(level=logging.INFO)

    from app.database import SessionLocal

    db = SessionLocal()
    try:
        stats = migrate_entities(db)
        print(f"Migration complete: {stats}")
    finally:
        db.close()
```

**Step 12.4: Run test to verify it passes**

Run: `cd backend && pytest tests/test_entity_migration.py -v`
Expected: PASS (4 tests)

**Step 12.5: Commit (when git available)**

```bash
git add backend/scripts/migrate_entities_to_portfolios.py backend/tests/test_entity_migration.py
git commit -m "feat(auth): add Entity to Portfolio data migration script"
```

---

## Task 13: Update Routers with Auth

**Files:**
- Modify: `backend/app/routers/accounts.py`
- Modify: `backend/app/routers/holdings.py`
- Modify: `backend/app/routers/transactions.py`
- Modify: `backend/app/routers/positions.py`
- Modify: `backend/app/routers/dashboard.py`
- Modify: `backend/app/routers/snapshots.py`
- Modify: `backend/app/routers/assets.py`
- Modify: `backend/app/routers/prices.py`
- Modify: `backend/app/routers/broker_data.py`
- Test: `backend/tests/test_protected_routes.py`

**Step 13.1: Write the failing test**

Create `backend/tests/test_protected_routes.py`:
```python
"""Tests for auth-protected routes."""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import get_db
from app.main import app
from app.models.user import User
from app.models.session import Session as UserSession
from app.models.portfolio import Portfolio
from app.services.auth_service import AuthService


@pytest.fixture
def client_with_user():
    """Create test client with a user and their portfolio."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    # Create only auth tables for this test
    User.__table__.create(engine, checkfirst=True)
    UserSession.__table__.create(engine, checkfirst=True)
    Portfolio.__table__.create(engine, checkfirst=True)

    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    # Create test user and portfolio
    db = TestingSessionLocal()
    user = User(email="test@example.com", password_hash=AuthService.hash_password("test123"))
    db.add(user)
    db.commit()
    db.refresh(user)

    portfolio = Portfolio(user_id=user.id, name="Test Portfolio")
    db.add(portfolio)
    db.commit()
    db.refresh(portfolio)

    user_id = user.id
    portfolio_id = portfolio.id
    db.close()

    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db

    with TestClient(app) as test_client:
        yield test_client, user_id, portfolio_id

    app.dependency_overrides.clear()


def test_accounts_requires_auth(client_with_user):
    """Test that /api/accounts requires authentication."""
    client, _, _ = client_with_user
    response = client.get("/api/accounts")
    assert response.status_code == 403  # HTTPBearer returns 403 when missing


def test_accounts_with_auth(client_with_user):
    """Test that /api/accounts works with valid token."""
    client, user_id, _ = client_with_user
    token = AuthService.create_access_token(user_id)

    response = client.get(
        "/api/accounts",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200


def test_holdings_requires_auth(client_with_user):
    """Test that /api/holdings requires authentication."""
    client, _, _ = client_with_user
    response = client.get("/api/holdings")
    assert response.status_code == 403


def test_dashboard_requires_auth(client_with_user):
    """Test that /api/dashboard requires authentication."""
    client, _, _ = client_with_user
    response = client.get("/api/dashboard/summary")
    assert response.status_code == 403
```

**Step 13.2: Run test to verify it fails**

Run: `cd backend && pytest tests/test_protected_routes.py::test_accounts_requires_auth -v`
Expected: FAIL (returns 200 instead of 403 - no auth required yet)

**Step 13.3: Update accounts router**

Modify `backend/app/routers/accounts.py`:
```python
"""Accounts API router."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies.auth import get_current_user
from app.models import Account
from app.models.user import User
from app.schemas.account import Account as AccountSchema
from app.schemas.account import AccountCreate, AccountUpdate

router = APIRouter(prefix="/api/accounts", tags=["accounts"])


def get_user_account_ids(user: User, db: Session) -> list[int]:
    """Get all account IDs belonging to user's portfolios."""
    portfolio_ids = [p.id for p in user.portfolios]
    if not portfolio_ids:
        return []
    accounts = db.query(Account).filter(Account.portfolio_id.in_(portfolio_ids)).all()
    return [a.id for a in accounts]


@router.get("", response_model=list[AccountSchema])
async def list_accounts(
    skip: int = 0,
    limit: int = 100,
    is_active: bool = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get list of accounts for the current user."""
    # Get user's portfolio IDs
    portfolio_ids = [p.id for p in current_user.portfolios]
    if not portfolio_ids:
        return []

    query = db.query(Account).filter(Account.portfolio_id.in_(portfolio_ids))

    if is_active is not None:
        query = query.filter(Account.is_active == is_active)

    accounts = query.offset(skip).limit(limit).all()
    return accounts


@router.get("/{account_id}", response_model=AccountSchema)
async def get_account(
    account_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get a specific account by ID (must belong to user)."""
    allowed_ids = get_user_account_ids(current_user, db)
    if account_id not in allowed_ids:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Account with id {account_id} not found",
        )

    account = db.query(Account).filter(Account.id == account_id).first()
    return account


@router.post("", response_model=AccountSchema, status_code=status.HTTP_201_CREATED)
async def create_account(
    account: AccountCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create a new account (must specify user's portfolio_id)."""
    # Verify portfolio belongs to user
    portfolio_ids = [p.id for p in current_user.portfolios]
    if account.portfolio_id not in portfolio_ids:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot create account in a portfolio you don't own",
        )

    db_account = Account(**account.model_dump())
    db.add(db_account)
    db.commit()
    db.refresh(db_account)
    return db_account


@router.put("/{account_id}", response_model=AccountSchema)
async def update_account(
    account_id: int,
    account_update: AccountUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update an existing account (must belong to user)."""
    allowed_ids = get_user_account_ids(current_user, db)
    if account_id not in allowed_ids:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Account with id {account_id} not found",
        )

    db_account = db.query(Account).filter(Account.id == account_id).first()

    update_data = account_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_account, field, value)

    db.commit()
    db.refresh(db_account)
    return db_account


@router.delete("/{account_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_account(
    account_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Delete an account (must belong to user)."""
    allowed_ids = get_user_account_ids(current_user, db)
    if account_id not in allowed_ids:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Account with id {account_id} not found",
        )

    db_account = db.query(Account).filter(Account.id == account_id).first()
    db.delete(db_account)
    db.commit()
    return None
```

**Step 13.4: Create helper module for user scoping**

Create `backend/app/dependencies/user_scope.py`:
```python
"""Helper functions for user-scoped queries."""

from sqlalchemy.orm import Session

from app.models.account import Account
from app.models.user import User


def get_user_portfolio_ids(user: User) -> list[str]:
    """Get all portfolio IDs for a user."""
    return [p.id for p in user.portfolios]


def get_user_account_ids(user: User, db: Session) -> list[int]:
    """Get all account IDs belonging to user's portfolios."""
    portfolio_ids = get_user_portfolio_ids(user)
    if not portfolio_ids:
        return []
    accounts = db.query(Account.id).filter(Account.portfolio_id.in_(portfolio_ids)).all()
    return [a[0] for a in accounts]


def filter_by_user_accounts(query, user: User, db: Session):
    """Add filter to query to only include user's accounts."""
    account_ids = get_user_account_ids(user, db)
    if not account_ids:
        # Return empty result
        return query.filter(False)
    return query.filter(Account.id.in_(account_ids))
```

**Step 13.5: Update remaining routers (pattern)**

For each router (holdings, transactions, positions, dashboard, snapshots, assets, prices, broker_data):

1. Add import: `from app.dependencies.auth import get_current_user`
2. Add import: `from app.models.user import User`
3. Add `current_user: User = Depends(get_current_user)` to each endpoint
4. Filter queries by user's portfolios/accounts

Example pattern for holdings.py:
```python
@router.get("", response_model=list[HoldingSchema])
async def list_holdings(
    account_id: int = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),  # ADD THIS
):
    """Get holdings for current user only."""
    from app.dependencies.user_scope import get_user_account_ids

    allowed_account_ids = get_user_account_ids(current_user, db)
    query = db.query(Holding).filter(Holding.account_id.in_(allowed_account_ids))

    if account_id:
        if account_id not in allowed_account_ids:
            raise HTTPException(status_code=404, detail="Account not found")
        query = query.filter(Holding.account_id == account_id)

    return query.all()
```

**Step 13.6: Run tests to verify**

Run: `cd backend && pytest tests/test_protected_routes.py -v`
Expected: PASS (4 tests)

**Step 13.7: Run all tests**

Run: `cd backend && pytest -v`
Expected: All tests pass (existing tests may need updates for auth)

**Step 13.8: Commit (when git available)**

```bash
git add backend/app/routers/ backend/app/dependencies/user_scope.py backend/tests/test_protected_routes.py
git commit -m "feat(auth): add authentication to all data routers"
```

---

## Frontend Authentication Tasks (14-21)

These tasks implement the frontend authentication flow to work with the backend auth system.

### Task 14: Create API Client

**Files:**
- Create: `frontend/src/lib/api.js`

**Step 14.1: Create the API client module**

Create a centralized API client that handles auth headers automatically:

```javascript
// frontend/src/lib/api.js
const API_BASE = 'http://localhost:8000/api';

/**
 * Get stored auth token
 */
function getToken() {
  return localStorage.getItem('access_token');
}

/**
 * Set auth token
 */
export function setToken(token) {
  if (token) {
    localStorage.setItem('access_token', token);
  } else {
    localStorage.removeItem('access_token');
  }
}

/**
 * Set refresh token
 */
export function setRefreshToken(token) {
  if (token) {
    localStorage.setItem('refresh_token', token);
  } else {
    localStorage.removeItem('refresh_token');
  }
}

/**
 * Get refresh token
 */
export function getRefreshToken() {
  return localStorage.getItem('refresh_token');
}

/**
 * Clear all auth tokens
 */
export function clearTokens() {
  localStorage.removeItem('access_token');
  localStorage.removeItem('refresh_token');
}

/**
 * Check if user is authenticated
 */
export function isAuthenticated() {
  return !!getToken();
}

/**
 * Make an authenticated API request
 */
export async function api(endpoint, options = {}) {
  const token = getToken();

  const headers = {
    'Content-Type': 'application/json',
    ...options.headers,
  };

  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }

  const response = await fetch(`${API_BASE}${endpoint}`, {
    ...options,
    headers,
  });

  // Handle 401 - try to refresh token
  if (response.status === 401 && getRefreshToken()) {
    const refreshed = await refreshAccessToken();
    if (refreshed) {
      // Retry the original request with new token
      headers['Authorization'] = `Bearer ${getToken()}`;
      return fetch(`${API_BASE}${endpoint}`, {
        ...options,
        headers,
      });
    }
  }

  return response;
}

/**
 * Refresh the access token using refresh token
 */
async function refreshAccessToken() {
  const refreshToken = getRefreshToken();
  if (!refreshToken) return false;

  try {
    const response = await fetch(`${API_BASE}/auth/refresh`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ refresh_token: refreshToken }),
    });

    if (response.ok) {
      const data = await response.json();
      setToken(data.access_token);
      if (data.refresh_token) {
        setRefreshToken(data.refresh_token);
      }
      return true;
    }
  } catch (error) {
    console.error('Token refresh failed:', error);
  }

  // Refresh failed - clear tokens
  clearTokens();
  return false;
}

/**
 * Login with email and password
 */
export async function login(email, password) {
  const response = await fetch(`${API_BASE}/auth/login`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email, password }),
  });

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || 'Login failed');
  }

  const data = await response.json();
  setToken(data.access_token);
  setRefreshToken(data.refresh_token);
  return data;
}

/**
 * Register a new user
 */
export async function register(email, password, name) {
  const response = await fetch(`${API_BASE}/auth/register`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email, password, name }),
  });

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || 'Registration failed');
  }

  const data = await response.json();
  setToken(data.access_token);
  setRefreshToken(data.refresh_token);
  return data;
}

/**
 * Logout
 */
export async function logout() {
  const token = getToken();
  const refreshToken = getRefreshToken();

  if (token && refreshToken) {
    try {
      await fetch(`${API_BASE}/auth/logout`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`,
        },
        body: JSON.stringify({ refresh_token: refreshToken }),
      });
    } catch (error) {
      console.error('Logout request failed:', error);
    }
  }

  clearTokens();
}

export default api;
```

**Step 14.2: Verify file was created**

Run: `ls frontend/src/lib/api.js`
Expected: File exists

**Step 14.3: Commit**

```bash
git add frontend/src/lib/api.js
git commit -m "feat(frontend): add centralized API client with auth"
```

---

### Task 15: Create AuthContext

**Files:**
- Create: `frontend/src/contexts/AuthContext.jsx`
- Modify: `frontend/src/contexts/index.js`

**Step 15.1: Create AuthContext**

```jsx
// frontend/src/contexts/AuthContext.jsx
import { createContext, useContext, useState, useEffect, useCallback } from 'react';
import {
  login as apiLogin,
  logout as apiLogout,
  register as apiRegister,
  isAuthenticated,
  clearTokens,
  api
} from '../lib/api';

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  // Check authentication status on mount
  useEffect(() => {
    async function checkAuth() {
      if (isAuthenticated()) {
        try {
          // Fetch current user profile
          const response = await api('/auth/me');
          if (response.ok) {
            const userData = await response.json();
            setUser(userData);
          } else {
            // Token invalid, clear it
            clearTokens();
          }
        } catch (error) {
          console.error('Auth check failed:', error);
          clearTokens();
        }
      }
      setLoading(false);
    }
    checkAuth();
  }, []);

  const login = useCallback(async (email, password) => {
    const data = await apiLogin(email, password);
    setUser(data.user);
    return data;
  }, []);

  const register = useCallback(async (email, password, name) => {
    const data = await apiRegister(email, password, name);
    setUser(data.user);
    return data;
  }, []);

  const logout = useCallback(async () => {
    await apiLogout();
    setUser(null);
  }, []);

  const value = {
    user,
    loading,
    isAuthenticated: !!user,
    login,
    register,
    logout,
  };

  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
}
```

**Step 15.2: Update contexts index to export AuthContext**

Add to `frontend/src/contexts/index.js`:

```javascript
export { ThemeProvider, useTheme } from './ThemeContext';
export { CurrencyProvider, useCurrency, CURRENCIES } from './CurrencyContext';
export { AuthProvider, useAuth } from './AuthContext';
```

**Step 15.3: Commit**

```bash
git add frontend/src/contexts/AuthContext.jsx frontend/src/contexts/index.js
git commit -m "feat(frontend): add AuthContext for authentication state"
```

---

### Task 16: Create Login Page

**Files:**
- Create: `frontend/src/pages/Login.jsx`

**Step 16.1: Create Login page component**

```jsx
// frontend/src/pages/Login.jsx
import { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { useAuth } from '../contexts';

export default function Login() {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const { login } = useAuth();
  const navigate = useNavigate();

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setLoading(true);

    try {
      await login(email, password);
      navigate('/');
    } catch (err) {
      setError(err.message || 'Login failed');
    } finally {
      setLoading(false);
    }
  };

  const handleDemoLogin = async () => {
    setError('');
    setLoading(true);

    try {
      await login('demo@finch.com', 'demo123');
      navigate('/');
    } catch (err) {
      setError('Demo login failed. Make sure the demo user is seeded.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50 dark:bg-gray-900 py-12 px-4 sm:px-6 lg:px-8">
      <div className="max-w-md w-full space-y-8">
        <div>
          <h2 className="mt-6 text-center text-3xl font-extrabold text-gray-900 dark:text-white">
            Sign in to Finch
          </h2>
          <p className="mt-2 text-center text-sm text-gray-600 dark:text-gray-400">
            Or{' '}
            <Link to="/register" className="font-medium text-blue-600 hover:text-blue-500">
              create a new account
            </Link>
          </p>
        </div>

        <form className="mt-8 space-y-6" onSubmit={handleSubmit}>
          {error && (
            <div className="rounded-md bg-red-50 dark:bg-red-900/50 p-4">
              <p className="text-sm text-red-700 dark:text-red-200">{error}</p>
            </div>
          )}

          <div className="rounded-md shadow-sm -space-y-px">
            <div>
              <label htmlFor="email" className="sr-only">Email address</label>
              <input
                id="email"
                name="email"
                type="email"
                autoComplete="email"
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="appearance-none rounded-none relative block w-full px-3 py-2 border border-gray-300 dark:border-gray-600 placeholder-gray-500 dark:placeholder-gray-400 text-gray-900 dark:text-white dark:bg-gray-800 rounded-t-md focus:outline-none focus:ring-blue-500 focus:border-blue-500 focus:z-10 sm:text-sm"
                placeholder="Email address"
              />
            </div>
            <div>
              <label htmlFor="password" className="sr-only">Password</label>
              <input
                id="password"
                name="password"
                type="password"
                autoComplete="current-password"
                required
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="appearance-none rounded-none relative block w-full px-3 py-2 border border-gray-300 dark:border-gray-600 placeholder-gray-500 dark:placeholder-gray-400 text-gray-900 dark:text-white dark:bg-gray-800 rounded-b-md focus:outline-none focus:ring-blue-500 focus:border-blue-500 focus:z-10 sm:text-sm"
                placeholder="Password"
              />
            </div>
          </div>

          <div>
            <button
              type="submit"
              disabled={loading}
              className="group relative w-full flex justify-center py-2 px-4 border border-transparent text-sm font-medium rounded-md text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {loading ? 'Signing in...' : 'Sign in'}
            </button>
          </div>

          <div className="relative">
            <div className="absolute inset-0 flex items-center">
              <div className="w-full border-t border-gray-300 dark:border-gray-600"></div>
            </div>
            <div className="relative flex justify-center text-sm">
              <span className="px-2 bg-gray-50 dark:bg-gray-900 text-gray-500">Or</span>
            </div>
          </div>

          <div>
            <button
              type="button"
              onClick={handleDemoLogin}
              disabled={loading}
              className="group relative w-full flex justify-center py-2 px-4 border border-gray-300 dark:border-gray-600 text-sm font-medium rounded-md text-gray-700 dark:text-gray-200 bg-white dark:bg-gray-800 hover:bg-gray-50 dark:hover:bg-gray-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              Try Demo Account
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
```

**Step 16.2: Commit**

```bash
git add frontend/src/pages/Login.jsx
git commit -m "feat(frontend): add Login page with demo account option"
```

---

### Task 17: Create Register Page

**Files:**
- Create: `frontend/src/pages/Register.jsx`

**Step 17.1: Create Register page component**

```jsx
// frontend/src/pages/Register.jsx
import { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { useAuth } from '../contexts';

export default function Register() {
  const [name, setName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const { register } = useAuth();
  const navigate = useNavigate();

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');

    if (password !== confirmPassword) {
      setError('Passwords do not match');
      return;
    }

    if (password.length < 8) {
      setError('Password must be at least 8 characters');
      return;
    }

    setLoading(true);

    try {
      await register(email, password, name);
      navigate('/');
    } catch (err) {
      setError(err.message || 'Registration failed');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50 dark:bg-gray-900 py-12 px-4 sm:px-6 lg:px-8">
      <div className="max-w-md w-full space-y-8">
        <div>
          <h2 className="mt-6 text-center text-3xl font-extrabold text-gray-900 dark:text-white">
            Create your account
          </h2>
          <p className="mt-2 text-center text-sm text-gray-600 dark:text-gray-400">
            Already have an account?{' '}
            <Link to="/login" className="font-medium text-blue-600 hover:text-blue-500">
              Sign in
            </Link>
          </p>
        </div>

        <form className="mt-8 space-y-6" onSubmit={handleSubmit}>
          {error && (
            <div className="rounded-md bg-red-50 dark:bg-red-900/50 p-4">
              <p className="text-sm text-red-700 dark:text-red-200">{error}</p>
            </div>
          )}

          <div className="space-y-4">
            <div>
              <label htmlFor="name" className="block text-sm font-medium text-gray-700 dark:text-gray-300">
                Name
              </label>
              <input
                id="name"
                name="name"
                type="text"
                autoComplete="name"
                required
                value={name}
                onChange={(e) => setName(e.target.value)}
                className="mt-1 appearance-none relative block w-full px-3 py-2 border border-gray-300 dark:border-gray-600 placeholder-gray-500 dark:placeholder-gray-400 text-gray-900 dark:text-white dark:bg-gray-800 rounded-md focus:outline-none focus:ring-blue-500 focus:border-blue-500 sm:text-sm"
                placeholder="Your name"
              />
            </div>

            <div>
              <label htmlFor="email" className="block text-sm font-medium text-gray-700 dark:text-gray-300">
                Email address
              </label>
              <input
                id="email"
                name="email"
                type="email"
                autoComplete="email"
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="mt-1 appearance-none relative block w-full px-3 py-2 border border-gray-300 dark:border-gray-600 placeholder-gray-500 dark:placeholder-gray-400 text-gray-900 dark:text-white dark:bg-gray-800 rounded-md focus:outline-none focus:ring-blue-500 focus:border-blue-500 sm:text-sm"
                placeholder="you@example.com"
              />
            </div>

            <div>
              <label htmlFor="password" className="block text-sm font-medium text-gray-700 dark:text-gray-300">
                Password
              </label>
              <input
                id="password"
                name="password"
                type="password"
                autoComplete="new-password"
                required
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="mt-1 appearance-none relative block w-full px-3 py-2 border border-gray-300 dark:border-gray-600 placeholder-gray-500 dark:placeholder-gray-400 text-gray-900 dark:text-white dark:bg-gray-800 rounded-md focus:outline-none focus:ring-blue-500 focus:border-blue-500 sm:text-sm"
                placeholder="At least 8 characters"
              />
            </div>

            <div>
              <label htmlFor="confirmPassword" className="block text-sm font-medium text-gray-700 dark:text-gray-300">
                Confirm Password
              </label>
              <input
                id="confirmPassword"
                name="confirmPassword"
                type="password"
                autoComplete="new-password"
                required
                value={confirmPassword}
                onChange={(e) => setConfirmPassword(e.target.value)}
                className="mt-1 appearance-none relative block w-full px-3 py-2 border border-gray-300 dark:border-gray-600 placeholder-gray-500 dark:placeholder-gray-400 text-gray-900 dark:text-white dark:bg-gray-800 rounded-md focus:outline-none focus:ring-blue-500 focus:border-blue-500 sm:text-sm"
                placeholder="Confirm your password"
              />
            </div>
          </div>

          <div>
            <button
              type="submit"
              disabled={loading}
              className="group relative w-full flex justify-center py-2 px-4 border border-transparent text-sm font-medium rounded-md text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {loading ? 'Creating account...' : 'Create account'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
```

**Step 17.2: Commit**

```bash
git add frontend/src/pages/Register.jsx
git commit -m "feat(frontend): add Register page"
```

---

### Task 18: Create ProtectedRoute Component

**Files:**
- Create: `frontend/src/components/ProtectedRoute.jsx`

**Step 18.1: Create ProtectedRoute component**

```jsx
// frontend/src/components/ProtectedRoute.jsx
import { Navigate, useLocation } from 'react-router-dom';
import { useAuth } from '../contexts';

export default function ProtectedRoute({ children }) {
  const { isAuthenticated, loading } = useAuth();
  const location = useLocation();

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50 dark:bg-gray-900">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
      </div>
    );
  }

  if (!isAuthenticated) {
    // Redirect to login, but save the attempted URL
    return <Navigate to="/login" state={{ from: location }} replace />;
  }

  return children;
}
```

**Step 18.2: Commit**

```bash
git add frontend/src/components/ProtectedRoute.jsx
git commit -m "feat(frontend): add ProtectedRoute component for auth guards"
```

---

### Task 19: Update App.jsx with Auth

**Files:**
- Modify: `frontend/src/App.jsx`

**Step 19.1: Update App.jsx to include AuthProvider and auth routes**

Replace the current App.jsx with auth-aware version:

```jsx
// frontend/src/App.jsx
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'

import { ThemeProvider, CurrencyProvider, AuthProvider, useAuth } from './contexts'

import Layout from './components/Layout'
import ProtectedRoute from './components/ProtectedRoute'
import Login from './pages/Login'
import Register from './pages/Register'
import Overview from './pages/Overview'
import Holdings from './pages/Holdings'
import Accounts from './pages/Accounts'
import AccountDetail from './pages/AccountDetail'
import Import from './pages/Import'
import Transactions from './pages/Transactions'
import Settings from './pages/Settings'

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 5 * 60 * 1000,
      retry: 1,
    },
  },
})

// Redirect authenticated users away from auth pages
function PublicRoute({ children }) {
  const { isAuthenticated, loading } = useAuth();

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50 dark:bg-gray-900">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
      </div>
    );
  }

  if (isAuthenticated) {
    return <Navigate to="/" replace />;
  }

  return children;
}

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <ThemeProvider>
        <CurrencyProvider>
          <AuthProvider>
            <Router>
              <Routes>
                {/* Public routes (redirect to home if authenticated) */}
                <Route path="/login" element={
                  <PublicRoute><Login /></PublicRoute>
                } />
                <Route path="/register" element={
                  <PublicRoute><Register /></PublicRoute>
                } />

                {/* Protected routes */}
                <Route path="/" element={
                  <ProtectedRoute>
                    <Layout />
                  </ProtectedRoute>
                }>
                  <Route index element={<Overview />} />
                  <Route path="holdings" element={<Holdings />} />
                  <Route path="accounts" element={<Accounts />} />
                  <Route path="accounts/:id" element={<AccountDetail />} />
                  <Route path="import" element={<Import />} />
                  <Route path="transactions" element={<Transactions />} />
                  <Route path="settings" element={<Settings />} />
                </Route>

                {/* Catch-all redirect */}
                <Route path="*" element={<Navigate to="/" replace />} />
              </Routes>
            </Router>
          </AuthProvider>
        </CurrencyProvider>
      </ThemeProvider>
    </QueryClientProvider>
  )
}

export default App
```

**Step 19.2: Update Layout to show user and logout**

The Layout component should show the logged-in user and a logout button. Modify `frontend/src/components/Layout.jsx` to add user info in the header/sidebar.

**Step 19.3: Commit**

```bash
git add frontend/src/App.jsx frontend/src/components/Layout.jsx
git commit -m "feat(frontend): integrate auth into App with protected routes"
```

---

### Task 20: Refactor Pages to Use API Client

**Files:**
- Modify: `frontend/src/pages/Overview.jsx`
- Modify: `frontend/src/pages/Holdings.jsx`
- Modify: `frontend/src/pages/Accounts.jsx`
- Modify: `frontend/src/pages/AccountDetail.jsx`
- Modify: `frontend/src/pages/Transactions.jsx`
- Modify: `frontend/src/pages/Import.jsx`

**Step 20.1: Update Overview.jsx**

Replace hardcoded fetch calls with the api client:

```jsx
// In frontend/src/pages/Overview.jsx
// Replace:
const API_BASE = 'http://localhost:8000/api';
// ...
fetch(`${API_BASE}/dashboard/summary?display_currency=${currency}`)

// With:
import api from '../lib/api';
// ...
api(`/dashboard/summary?display_currency=${currency}`)
```

**Step 20.2: Update all other pages similarly**

Each page that makes API calls should:
1. Remove `const API_BASE = ...` if present
2. Import `api` from `../lib/api`
3. Replace `fetch(API_BASE + ...)` with `api(...)`

Example pattern:

```jsx
// Before
const response = await fetch(`${API_BASE}/accounts`);

// After
import api from '../lib/api';
const response = await api('/accounts');
```

**Step 20.3: Commit**

```bash
git add frontend/src/pages/*.jsx
git commit -m "refactor(frontend): migrate all pages to use authenticated API client"
```

---

### Task 21: Add /auth/me Endpoint (Backend)

**Files:**
- Modify: `backend/app/routers/auth.py`
- Modify: `backend/app/schemas/auth.py`

The frontend AuthContext needs a `/auth/me` endpoint to check the current user.

**Step 21.1: Add UserResponse schema**

Add to `backend/app/schemas/auth.py`:

```python
class UserResponse(BaseModel):
    id: str
    email: str
    name: str | None = None

    model_config = ConfigDict(from_attributes=True)
```

**Step 21.2: Add /auth/me endpoint**

Add to `backend/app/routers/auth.py`:

```python
from app.schemas.auth import UserResponse

@router.get("/me", response_model=UserResponse)
async def get_current_user_info(
    current_user: User = Depends(get_current_user),
):
    """Get the current authenticated user's information."""
    return current_user
```

**Step 21.3: Update AuthResponse to include user**

Update `backend/app/schemas/auth.py`:

```python
class AuthResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user: UserResponse  # Add this field
```

**Step 21.4: Update login/register endpoints to return user**

Modify the login and register endpoints in `backend/app/routers/auth.py` to include the user in the response.

**Step 21.5: Create test for /auth/me**

Add to `backend/tests/test_auth_router.py`:

```python
def test_get_me_authenticated(client, db_session):
    """Test getting current user info when authenticated."""
    # Register and login
    client.post("/api/auth/register", json={
        "email": "me@test.com",
        "password": "testpassword123",
        "name": "Test User"
    })
    login_response = client.post("/api/auth/login", json={
        "email": "me@test.com",
        "password": "testpassword123"
    })
    token = login_response.json()["access_token"]

    # Get /me
    response = client.get("/api/auth/me", headers={
        "Authorization": f"Bearer {token}"
    })

    assert response.status_code == 200
    data = response.json()
    assert data["email"] == "me@test.com"
    assert data["name"] == "Test User"


def test_get_me_unauthenticated(client):
    """Test /auth/me without authentication returns 401."""
    response = client.get("/api/auth/me")
    assert response.status_code == 401
```

**Step 21.6: Run tests**

Run: `cd backend && pytest tests/test_auth_router.py -v`
Expected: All tests pass

**Step 21.7: Commit**

```bash
git add backend/app/routers/auth.py backend/app/schemas/auth.py backend/tests/test_auth_router.py
git commit -m "feat(auth): add /auth/me endpoint and include user in auth responses"
```

---

## Frontend Auth Testing Checklist

After implementing all tasks, verify the following manually:

1. **Login Flow:**
   - Navigate to `/login`
   - Enter invalid credentials → see error message
   - Enter valid credentials → redirect to `/`
   - Refresh page → stay logged in

2. **Register Flow:**
   - Navigate to `/register`
   - Enter mismatched passwords → see error
   - Enter valid details → redirect to `/`
   - User appears in database

3. **Demo Login:**
   - Click "Try Demo Account" on login page
   - Should log in as demo@finch.com
   - Should see demo user's portfolios and data

4. **Protected Routes:**
   - Log out
   - Try to access `/holdings` directly → redirect to `/login`
   - Login → can access `/holdings`

5. **Token Refresh:**
   - Wait for access token to expire (or manually expire it)
   - Make an API call → should auto-refresh token

6. **Logout:**
   - Click logout
   - Try to access protected route → redirect to login
   - Tokens cleared from localStorage

---

# Phase 2: Data Model Migration (Outline)

**Goal:** Complete transition from Entity→Account to User→Portfolio→Account, add full multi-portfolio support

**Tasks:**
1. ~~Update Account model (remove entity_id, require portfolio_id)~~ ✅
2. ~~Update all routers to filter by current user~~ ✅
3. ~~Update dashboard queries to scope by user~~ ✅
4. ~~Update snapshot service for multi-user~~ ✅
5. ~~Create data migration for existing data~~ ✅
6. ~~Remove Entity model and router~~ ✅

### Multi-Portfolio Support (Tasks 7-12) ✅

**Goal:** Allow users to create multiple portfolios and filter views by selected portfolio

**7. Backend: Portfolio CRUD Router** ✅
- Create `backend/app/schemas/portfolio.py` with PortfolioCreate, PortfolioUpdate, Portfolio schemas
- Create `backend/app/routers/portfolios.py` with endpoints:
  - `GET /api/portfolios` - List user's portfolios with account counts
  - `POST /api/portfolios` - Create new portfolio
  - `GET /api/portfolios/{id}` - Get single portfolio
  - `PUT /api/portfolios/{id}` - Update portfolio name/description
  - `DELETE /api/portfolios/{id}` - Delete (error if has accounts or is only portfolio)
- Register router in `main.py`, export schemas in `schemas/__init__.py`

**8. Backend: Auto-create Default Portfolio on Registration** ✅
- Modify `backend/app/routers/auth.py` register function
- After creating user, create default Portfolio with name "My Portfolio"
- This fixes bug where new users have no portfolio and can't add accounts

**9. Backend: Add portfolio_id Filter to Endpoints** ✅
- Modify `backend/app/dependencies/user_scope.py`:
  - Update `get_user_account_ids(user, db, portfolio_id=None)` to accept optional portfolio filter
- Add `portfolio_id: str | None = Query(None)` parameter to:
  - `GET /api/accounts` (accounts.py)
  - `GET /api/holdings` (holdings.py)
  - `GET /api/dashboard/summary` (dashboard.py)
  - `GET /api/positions` (positions.py)
  - `GET /api/transactions` (transactions.py)
  - `GET /api/snapshots/portfolio` (snapshots.py)
- Validate portfolio_id belongs to user, return 404 if not

**10. Frontend: PortfolioContext** ✅
- Create `frontend/src/contexts/PortfolioContext.jsx` following CurrencyContext pattern:
  - Fetch portfolios from `/api/portfolios` on mount
  - Store `selectedPortfolioId` (null = all portfolios)
  - Persist to localStorage key `finch-portfolio-id`
  - Provide hook: `usePortfolio()` with portfolios, selectedPortfolioId, selectPortfolio(), refetchPortfolios()
- Export from `contexts/index.js`
- Add PortfolioProvider to App.jsx inside AuthProvider

**11. Frontend: Portfolio Selector in Navbar** ✅
- Add PortfolioSelector component to `frontend/src/components/layout/Navbar.jsx`
- Dropdown with briefcase icon showing current selection
- Options: "All Portfolios" + list of user portfolios with account counts
- Checkmark on selected item
- Update all pages to include `portfolio_id` in API calls when selected

**12. Frontend: Portfolio Management in Settings** ✅
- Add "Portfolios" section to `frontend/src/pages/Settings.jsx`
- List portfolios with name + account count
- Rename button (inline edit)
- Delete button (disabled if only 1 portfolio or has accounts)
- "Create New Portfolio" button

### UI & UX Enhancements (Tasks 13-18) ✅

**Goal:** Polish multi-portfolio UX and add portfolio-level preferences

**13. UI Consistency & Polish** ✅
- Use consistent icon for portfolios (BriefcaseIcon in navbar vs FolderIcon in settings - pick one)
- Add background/border styling to portfolio selector in navbar for better visibility
- Files: `Navbar.jsx`, `Settings.jsx`

**14. Add default_currency to Portfolio Model** ✅
- Add `default_currency` field to Portfolio model (String(3), default "USD")
- Create Alembic migration for new column
- Update portfolio schemas and CRUD endpoints
- Add currency selector in portfolio creation/edit forms
- Use portfolio's default_currency when displaying that portfolio's data
- Files: `models/portfolio.py`, `schemas/portfolio.py`, `routers/portfolios.py`, migration file, `Settings.jsx`

**15. Add Default Portfolio Preference** ✅
- Add `is_default` field to Portfolio model (Boolean, default False)
- Constraint: only one portfolio per user can be default
- Add "Set as default" option in portfolio management
- On login, select user's default portfolio instead of "All Portfolios"
- Files: `models/portfolio.py`, `routers/portfolios.py`, migration file, `PortfolioContext.jsx`, `Settings.jsx`

**16. Make "All Portfolios" Opt-in** ⏳ (Backend ✅, Frontend pending)
- Add `show_combined_view` field to User model (Boolean, default True)
- Add user preferences endpoint or extend /auth/me
- Add toggle in Settings: "Show combined portfolio view"
- Conditionally render "All Portfolios" option in selector based on preference
- Files: `models/user.py`, `schemas/auth.py`, migration file, `Settings.jsx`, `Navbar.jsx`

**17. Show Portfolio Values in Selector Dropdown** ✅
- Extend `/api/portfolios` endpoint to optionally include total_value
- Calculate sum of account values per portfolio
- Display formatted value next to each portfolio name in dropdown
- Files: `routers/portfolios.py`, `Navbar.jsx`, `PortfolioContext.jsx`

**18. Create Second Demo Portfolio with Data** ✅
- Data Model: User → Portfolio → Account → Holdings/Transactions
- Portfolio 1: "US Investments" (rename existing) - USD-based
  - Existing accounts: "Main Brokerage", "Retirement IRA"
- Portfolio 2: "Israeli Savings" (NEW) - ILS-based
  - New accounts: "Bank Leumi Brokerage", "Gemel Pension"
  - Sample transactions for Israeli stocks (TASE tickers)
- Files: `seed_demo_user.py`, potentially `seed_demo_transactions.py`

---

# Phase 3: Broker Integrations

**Goal:** Transform the portfolio tracker into a comprehensive multi-broker platform by adding crypto exchanges, Israeli brokers, and Israeli banks with both API and file upload support.

**Current State:**
- Base infrastructure exists: `BaseBrokerParser`, `BrokerParserRegistry`, `BrokerImportData`
- Two brokers implemented: IBKR (full API + file), Meitav (file upload)
- TASE integration for Israeli security resolution

**Key Principles:**
- For brokers with APIs: First research the API, then implement both API client AND file parser
- User can choose: API key, file upload, or both (hybrid approach)
- All brokers should support file upload as fallback

---

## Task Summary

| # | Task | Type | Status |
|---|------|------|--------|
| **Sprint 1: Crypto Exchanges** ||||
| 1 | Kraken - API Research | Research | ✅ Complete |
| 2 | Kraken - Implementation | API + File | ✅ Complete |
| 2a | Kraken - Code Simplification | Review | ✅ Complete |
| 3 | Kraken - Documentation | Docs | ✅ Complete |
| 4 | Bit2C - API Research | Research | ✅ Complete |
| 5 | Bit2C - Implementation | API + File | ✅ Complete |
| 5a | Bit2C - Code Simplification | Review | ✅ Complete |
| 6 | Bit2C - Documentation | Docs | ✅ Complete |
| 7 | Binance - API Research | Research | ✅ Complete |
| 8 | Binance - Implementation | API + File | ✅ Complete |
| 8a | Binance - Code Simplification | Review | ✅ Complete |
| 9 | Binance - Documentation | Docs | ✅ Complete |
| **Sprint 1a: Crypto Price Provider** ||||
| 9c | CoinGecko - API Research | Research | ✅ Complete |
| 9d | CoinGecko - Implementation | API Client | ✅ Complete |
| 9e | CoinGecko - Documentation | Docs | ✅ Complete |
| 9f | CryptoCompare - Research & Implementation | API Client | ✅ Complete |
| 9g | Historical Price Backfill DAG | Integration | ✅ Complete |
| **Sprint 1b: Airflow Integration** ||||
| 9a | Airflow DAG Updates for Crypto Exchanges | Integration | ✅ Complete |
| 9b | Backend API Endpoints for Crypto Import | API | ✅ Complete |
| 9h | Unified Broker Router Refactoring | API | ✅ Complete |
| **Sprint 2: Israeli Brokers** ||||
| 10 | IBI - Research & Implementation | File | Pending |
| 10a | IBI - Code Simplification | Review | Pending |
| 11 | IBI - Documentation | Docs | Pending |
| 12 | Excellence - Research & Implementation | File | Pending |
| 12a | Excellence - Code Simplification | Review | Pending |
| 13 | Excellence - Documentation | Docs | Pending |
| 14 | Altshuler Shaham - Research & Implementation | File | Pending |
| 14a | Altshuler Shaham - Code Simplification | Review | Pending |
| 15 | Altshuler Shaham - Documentation | Docs | Pending |
| **Sprint 3: Israeli Banks** ||||
| 16 | Bank Leumi - Research & Implementation | File | Pending |
| 16a | Bank Leumi - Code Simplification | Review | Pending |
| 17 | Bank Leumi - Documentation | Docs | Pending |
| 18 | Bank Hapoalim - Research & Implementation | File | Pending |
| 18a | Bank Hapoalim - Code Simplification | Review | Pending |
| 19 | Bank Hapoalim - Documentation | Docs | Pending |
| 20 | Discount Bank - Research & Implementation | File | Pending |
| 20a | Discount Bank - Code Simplification | Review | Pending |
| 21 | Discount Bank - Documentation | Docs | Pending |
| 22 | Mizrahi Tefahot - Research & Implementation | File | Pending |
| 22a | Mizrahi Tefahot - Code Simplification | Review | Pending |
| 23 | Mizrahi Tefahot - Documentation | Docs | Pending |
| **Sprint 4: Polish** ||||
| 24 | Stock Split Transaction Type | Feature | Pending |
| 25 | Broker Tutorial Content System | Feature | Pending |
| 26 | File Upload Progress Tracking | Feature | Pending |

**Progress Tracking:** `docs/progress/phase-3-broker-integrations.md`

---

## Documentation Standards

Each broker integration includes a documentation file at `docs/brokers/<broker-type>.md`:

### For API-based Brokers
```markdown
# <Broker Name> Integration

## Overview
Brief description of the broker and what data we can import.

## API Documentation
- Official docs: <link>
- Base URL: <url>

## Authentication
- Method: (e.g., HMAC-SHA256, nonce-based)
- Required credentials: api_key, api_secret

## Endpoints Used

### GET /endpoint1
**Purpose:** What data this provides
**Rate limit:** X requests per minute
**Response mapping:**
| API Field | Our Field | Notes |
|-----------|-----------|-------|
| `balance` | `quantity` | |

## File Export Format
How to export from the UI, CSV/JSON format, column mappings.

## Data Mapping to BrokerImportData
How API/file fields map to ParsedTransaction, ParsedPosition, etc.
```

### For File-based Brokers (Israeli)
```markdown
# <Broker Name> Integration

## Overview
Brief description, account types supported.

## Export Instructions
Step-by-step how to export from the broker's website/app.

## File Format
- Type: XLSX/CSV
- Encoding: UTF-8
- Language: Hebrew

## Column Schema

### Positions File (יתרות)
| Hebrew Column | English | Type | Description |
|---------------|---------|------|-------------|
| שם נייר | security_name | string | Security name |
| מס' נייר | security_number | string | TASE security number |

### Transactions File (פעולות)
| Hebrew Column | English | Type | Description |
|---------------|---------|------|-------------|

## Data Transformations
- Agorot → ILS conversion
- TASE security number → Symbol resolution
- Hebrew action types → English mapping

## Data Mapping to BrokerImportData
Field mappings to ParsedTransaction, ParsedPosition, etc.
```

---

# Sprint 1: Crypto Exchanges

## Task 1: Kraken API Research

**Goal:** Research Kraken API to understand endpoints, authentication, rate limits, and data formats.

### Deliverable
Create `docs/research/kraken-api-research.md` with:
1. API documentation links
2. Authentication method (API key + nonce-based signing)
3. Required endpoints for:
   - Account balances
   - Trade history
   - Deposit/withdrawal history
   - Staking rewards (if available)
4. Rate limits and throttling rules
5. Available export file formats (CSV, etc.)
6. Data fields mapping to our `BrokerImportData` model

### Research Questions
- What authentication method? (API key + secret + nonce)
- What are the rate limits?
- Can we get full trade history or is there pagination?
- What file export formats are available from the UI?
- Are there test/sandbox credentials available?

### Commit
```
docs(kraken): add API research documentation
```

---

## Task 2: Kraken Implementation

**Goal:** Implement Kraken support with both API client and file parser.

### Files
- Create: `backend/app/services/kraken_parser.py`
- Create: `backend/app/services/kraken_client.py`
- Create: `backend/tests/test_kraken_parser.py`
- Create: `backend/tests/test_kraken_client.py`
- Create: `backend/tests/fixtures/kraken_trades_sample.csv`
- Modify: `backend/app/services/broker_parser_registry.py`

---

### Step 2.1: Write failing metadata tests

```python
# backend/tests/test_kraken_parser.py
"""Tests for Kraken broker parser."""
import pytest
from app.services.kraken_parser import KrakenParser

class TestKrakenParserMetadata:
    def test_broker_type(self):
        assert KrakenParser.broker_type() == "kraken"

    def test_broker_name(self):
        assert KrakenParser.broker_name() == "Kraken"

    def test_supported_extensions(self):
        assert KrakenParser.supported_extensions() == [".csv"]

    def test_has_api(self):
        assert KrakenParser.has_api() is True
```

**Run:** `cd backend && pytest tests/test_kraken_parser.py -v`
**Expected:** FAIL (ModuleNotFoundError)

---

### Step 2.2: Implement KrakenParser skeleton

```python
# backend/app/services/kraken_parser.py
"""Kraken exchange parser for CSV file imports and API responses."""
import logging
from datetime import date
from decimal import Decimal

from app.services.base_broker_parser import BaseBrokerParser, BrokerImportData

logger = logging.getLogger(__name__)

ASSET_MAP = {
    "XXBT": "BTC", "XETH": "ETH", "XXRP": "XRP",
    "ZUSD": "USD", "ZEUR": "EUR", "ZGBP": "GBP",
}

class KrakenParser(BaseBrokerParser):
    @classmethod
    def broker_type(cls) -> str:
        return "kraken"

    @classmethod
    def broker_name(cls) -> str:
        return "Kraken"

    @classmethod
    def supported_extensions(cls) -> list[str]:
        return [".csv"]

    @classmethod
    def has_api(cls) -> bool:
        return True

    def extract_date_range(self, file_content: bytes) -> tuple[date, date]:
        raise NotImplementedError("CSV parsing not yet implemented")

    def parse(self, file_content: bytes) -> BrokerImportData:
        raise NotImplementedError("CSV parsing not yet implemented")
```

**Run:** `cd backend && pytest tests/test_kraken_parser.py::TestKrakenParserMetadata -v`
**Expected:** 4 passed

---

### Step 2.3: Commit metadata

```bash
git add backend/app/services/kraken_parser.py backend/tests/test_kraken_parser.py
git commit -m "feat(kraken): add KrakenParser skeleton with metadata

Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>"
```

---

### Step 2.4: Create CSV test fixture

```csv
# backend/tests/fixtures/kraken_trades_sample.csv
"txid","refid","time","type","subtype","aclass","asset","amount","fee","balance"
"LXXXX1","TXXXX1","2024-01-15 10:30:45","trade","","currency","XXBT","0.05000000","0.00000000","1.05000000"
"LXXXX2","TXXXX1","2024-01-15 10:30:45","trade","","currency","ZUSD","-1500.00000000","2.40000000","8500.00000000"
"LXXXX3","TXXXX2","2024-01-20 14:22:10","trade","","currency","XXBT","-0.02000000","0.00000000","1.03000000"
"LXXXX4","TXXXX2","2024-01-20 14:22:10","trade","","currency","ZUSD","620.00000000","0.99200000","9119.00800000"
"LXXXX5","DXXXX1","2024-01-10 09:00:00","deposit","","currency","ZUSD","10000.00000000","0.00000000","10000.00000000"
```

---

### Step 2.5: Write failing CSV parsing tests

```python
# Add to backend/tests/test_kraken_parser.py
from datetime import date
from decimal import Decimal
from pathlib import Path

class TestKrakenCSVParsing:
    @pytest.fixture
    def sample_csv(self) -> bytes:
        fixture_path = Path(__file__).parent / "fixtures" / "kraken_trades_sample.csv"
        return fixture_path.read_bytes()

    def test_extract_date_range(self, sample_csv):
        parser = KrakenParser()
        start_date, end_date = parser.extract_date_range(sample_csv)
        assert start_date == date(2024, 1, 10)
        assert end_date == date(2024, 1, 20)

    def test_parse_extracts_trades(self, sample_csv):
        parser = KrakenParser()
        result = parser.parse(sample_csv)
        assert len(result.transactions) == 2  # 2 trades (buy + sell)

    def test_parse_extracts_deposits(self, sample_csv):
        parser = KrakenParser()
        result = parser.parse(sample_csv)
        assert len(result.cash_transactions) == 1
        assert result.cash_transactions[0].amount == Decimal("10000")
```

**Run:** `cd backend && pytest tests/test_kraken_parser.py::TestKrakenCSVParsing -v`
**Expected:** FAIL (NotImplementedError)

---

### Step 2.6: Implement CSV parsing

```python
# Update backend/app/services/kraken_parser.py - add imports and methods
import csv
from datetime import datetime
from io import StringIO
from app.services.base_broker_parser import ParsedCashTransaction, ParsedTransaction

def normalize_asset(kraken_asset: str) -> str:
    return ASSET_MAP.get(kraken_asset, kraken_asset)

# Add to KrakenParser class:
def extract_date_range(self, file_content: bytes) -> tuple[date, date]:
    content = file_content.decode("utf-8")
    reader = csv.DictReader(StringIO(content))
    dates = []
    for row in reader:
        if time_str := row.get("time"):
            if parsed := self._parse_timestamp(time_str):
                dates.append(parsed)
    if not dates:
        raise ValueError("No valid dates found")
    return min(dates), max(dates)

def parse(self, file_content: bytes) -> BrokerImportData:
    content = file_content.decode("utf-8")
    reader = csv.DictReader(StringIO(content))
    transactions, cash_transactions, dates = [], [], []
    trades_by_ref: dict[str, list[dict]] = {}

    for row in reader:
        row_type, refid = row.get("type", ""), row.get("refid", "")
        if parsed := self._parse_timestamp(row.get("time", "")):
            dates.append(parsed)

        if row_type == "trade":
            trades_by_ref.setdefault(refid, []).append(row)
        elif row_type == "deposit":
            cash_transactions.append(ParsedCashTransaction(
                date=parsed or date.today(),
                transaction_type="Deposit",
                amount=abs(Decimal(row.get("amount", "0"))),
                currency=normalize_asset(row.get("asset", "")),
            ))

    for rows in trades_by_ref.values():
        if trade := self._process_trade_pair(rows):
            transactions.append(trade)

    return BrokerImportData(
        start_date=min(dates) if dates else date.today(),
        end_date=max(dates) if dates else date.today(),
        transactions=transactions,
        cash_transactions=cash_transactions,
    )

def _parse_timestamp(self, time_str: str) -> date | None:
    try:
        return datetime.strptime(time_str, "%Y-%m-%d %H:%M:%S").date()
    except ValueError:
        return None

def _process_trade_pair(self, rows: list[dict]) -> ParsedTransaction | None:
    if len(rows) != 2:
        return None
    crypto_row = next((r for r in rows if r.get("asset", "").startswith("X")), None)
    fiat_row = next((r for r in rows if r.get("asset", "").startswith("Z")), None)
    if not crypto_row or not fiat_row:
        return None

    crypto_amount = Decimal(crypto_row.get("amount", "0"))
    fiat_amount = Decimal(fiat_row.get("amount", "0"))

    return ParsedTransaction(
        trade_date=self._parse_timestamp(crypto_row.get("time", "")) or date.today(),
        symbol=normalize_asset(crypto_row.get("asset", "")),
        transaction_type="Buy" if crypto_amount > 0 else "Sell",
        quantity=abs(crypto_amount),
        amount=abs(fiat_amount),
        fees=abs(Decimal(fiat_row.get("fee", "0"))),
        currency=normalize_asset(fiat_row.get("asset", "")),
    )
```

**Run:** `cd backend && pytest tests/test_kraken_parser.py -v`
**Expected:** All tests pass

---

### Step 2.7: Commit CSV parsing

```bash
git add backend/app/services/kraken_parser.py backend/tests/test_kraken_parser.py backend/tests/fixtures/kraken_trades_sample.csv
git commit -m "feat(kraken): implement CSV parsing for trades and deposits

Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>"
```

---

### Step 2.8: Write failing API client tests

```python
# backend/tests/test_kraken_client.py
"""Tests for Kraken API client."""
import base64
import pytest
from app.services.kraken_client import KrakenClient

class TestKrakenClientSignature:
    def test_generate_signature(self):
        api_secret = base64.b64encode(b"test_secret_key").decode()
        client = KrakenClient(api_key="test_key", api_secret=api_secret)
        signature = client._generate_signature("/0/private/Balance", {}, 1616492376594)
        assert isinstance(signature, str)
        base64.b64decode(signature)  # Should be valid base64

    def test_signature_changes_with_nonce(self):
        api_secret = base64.b64encode(b"test_secret").decode()
        client = KrakenClient(api_key="key", api_secret=api_secret)
        sig1 = client._generate_signature("/0/private/Balance", {}, 1000)
        sig2 = client._generate_signature("/0/private/Balance", {}, 2000)
        assert sig1 != sig2
```

**Run:** `cd backend && pytest tests/test_kraken_client.py -v`
**Expected:** FAIL (ModuleNotFoundError)

---

### Step 2.9: Implement KrakenClient

```python
# backend/app/services/kraken_client.py
"""Kraken REST API client with HMAC-SHA512 authentication."""
import base64
import hashlib
import hmac
import logging
import time
from urllib.parse import urlencode
import httpx

logger = logging.getLogger(__name__)

class KrakenClient:
    BASE_URL = "https://api.kraken.com"

    def __init__(self, api_key: str, api_secret: str):
        self.api_key = api_key
        self.api_secret = api_secret
        self._client = httpx.Client(timeout=30.0)

    def _generate_nonce(self) -> int:
        return int(time.time() * 1000)

    def _generate_signature(self, path: str, data: dict, nonce: int) -> str:
        data_with_nonce = {**data, "nonce": nonce}
        post_data = urlencode(data_with_nonce)
        sha256_hash = hashlib.sha256((str(nonce) + post_data).encode()).digest()
        message = path.encode() + sha256_hash
        secret_decoded = base64.b64decode(self.api_secret)
        signature = hmac.new(secret_decoded, message, hashlib.sha512)
        return base64.b64encode(signature.digest()).decode()

    def _request(self, method: str, path: str, data: dict | None = None) -> dict:
        data = data or {}
        nonce = self._generate_nonce()
        signature = self._generate_signature(path, data, nonce)
        data["nonce"] = nonce
        headers = {"API-Key": self.api_key, "API-Sign": signature}
        response = self._client.request(method, f"{self.BASE_URL}{path}", data=data, headers=headers)
        response.raise_for_status()
        result = response.json()
        if result.get("error"):
            raise ValueError(f"Kraken API error: {result['error']}")
        return result.get("result", {})

    def get_balance(self) -> dict:
        return self._request("POST", "/0/private/Balance")

    def get_trades_history(self, start: int | None = None, ofs: int = 0) -> dict:
        data = {"ofs": ofs}
        if start:
            data["start"] = start
        return self._request("POST", "/0/private/TradesHistory", data)

    def get_ledgers(self, type_: str | None = None, start: int | None = None, ofs: int = 0) -> dict:
        data = {"ofs": ofs}
        if type_:
            data["type"] = type_
        if start:
            data["start"] = start
        return self._request("POST", "/0/private/Ledgers", data)
```

**Run:** `cd backend && pytest tests/test_kraken_client.py -v`
**Expected:** All tests pass

---

### Step 2.10: Commit API client

```bash
git add backend/app/services/kraken_client.py backend/tests/test_kraken_client.py
git commit -m "feat(kraken): add KrakenClient with HMAC-SHA512 authentication

Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>"
```

---

### Step 2.11: Register Kraken in parser registry

```python
# Update backend/app/services/broker_parser_registry.py _ensure_initialized()
from app.services.kraken_parser import KrakenParser

cls._parsers = {
    "ibkr": IBKRParserAdapter,
    "meitav": MeitavParser,
    "kraken": KrakenParser,  # Add this line
}
```

**Run:** `cd backend && pytest tests/ -k "kraken" -v`
**Expected:** All Kraken tests pass

---

### Step 2.12: Final commit for Task 2

```bash
git add backend/app/services/broker_parser_registry.py
git commit -m "feat(kraken): register KrakenParser in broker registry

Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>"
```

---

## Task 3: Kraken Documentation

**Goal:** Document Kraken integration for future reference and maintenance.

### Deliverable
Create `docs/brokers/kraken.md` with:
1. Overview of Kraken and supported features
2. API endpoints used and their purpose
3. Authentication details (nonce-based HMAC-SHA512)
4. Rate limits and throttling
5. CSV export format and column mappings
6. Data transformation logic (how Kraken fields map to our models)

### Commit
```
docs(kraken): add integration documentation
```

---

## Task 4: Bit2C API Research

**Goal:** Research Bit2C (Israeli crypto exchange) API.

### Deliverable
Create `docs/research/bit2c-api-research.md` with:
1. API documentation: https://bit2c.co.il/home/api
2. Authentication method
3. Required endpoints
4. ILS-denominated trading pairs (BTC/ILS, ETH/ILS, etc.)
5. Rate limits
6. Hebrew response handling (if any)
7. Available export formats

### Commit
```
docs(bit2c): add API research documentation
```

---

## Task 5: Bit2C Implementation ✅

**Status:** Complete (2026-01-20)

**Goal:** Implement Bit2C support with API and file parser.

### Files Created
- `backend/app/services/bit2c_client.py` - API client with HMAC authentication
- `backend/app/services/bit2c_parser.py` - XLSX parser (English + Hebrew)
- `backend/app/services/bit2c_constants.py` - Asset mappings and constants
- `backend/tests/test_bit2c_client.py` - 11 tests
- `backend/tests/test_bit2c_parser.py` - 26 tests

### Implementation
- ILS as base currency (NIS normalized to ILS)
- Support BTC/ILS, ETH/ILS, LTC/ILS, USDC/ILS pairs
- Full Hebrew column support with automatic language detection
- Dual-entry accounting (Trade Settlements for every trade)

### Commit
```
feat(bit2c): add Bit2C Israeli exchange client and parser
```

---

## Task 5a: Bit2C Integration Bugfixes ✅

**Status:** Complete (2026-01-21)

**Goal:** Apply lessons learned from Kraken integration to fix critical bugs before real API testing.

### Issues Fixed

| Issue | Solution |
|-------|----------|
| Missing dual-entry accounting | `_parse_trade()` now returns tuple `(crypto_txn, settlement_txn)` |
| Empty `cash_transactions` | `fetch_all_data()` and `parse()` now collect Trade Settlements |
| No constants file | Created `bit2c_constants.py` with `ASSET_NAME_MAP`, `TRADING_PAIRS`, `FIAT_CURRENCIES` |

### Dual-Entry Accounting Rules

| Trade Type | Crypto Transaction | Trade Settlement (ILS) |
|------------|-------------------|------------------------|
| **Buy** | `quantity = crypto_amount` | `amount = -(fiat + fee)` (negative, cash leaves) |
| **Sell** | `quantity = crypto_amount` | `amount = fiat - fee` (positive, cash received) |

### Files Modified
- `backend/app/services/bit2c_client.py` - Dual-entry in `_parse_trade()` and `fetch_all_data()`
- `backend/app/services/bit2c_parser.py` - Dual-entry in `_parse_trade()` and `parse()`
- `backend/app/services/bit2c_constants.py` - NEW: Centralized constants

### Code Simplification
Applied via `code-simplifier` agent:
- Removed redundant identity mappings from `ASSET_NAME_MAP`
- Added empty string handling to `to_decimal()`
- Simplified `_parse_row()` return type to `tuple[str, Any] | None`

### Test Results
- 37 tests passing (11 client + 26 parser)
- New dual-entry tests verify:
  - Buy creates negative settlement
  - Sell creates positive settlement
  - Fees included in settlement amounts

### Commit
```
fix(bit2c): add dual-entry accounting and Trade Settlements
```

---

## Task 5b: Bit2C FundsHistory Discovery ✅

**Status:** Complete (2026-01-22)

**Goal:** Fix deposit/withdrawal data retrieval from Bit2C API.

### Problem

The documented `/Order/AccountHistory` endpoint returns empty results even for accounts with known deposit/withdrawal activity. Testing confirmed this endpoint is broken or deprecated.

### Discovery

Found an **undocumented** endpoint `/AccountAPI/FundsHistory.json` in a third-party C# client:
- Source: https://github.com/macdasi/Bit2C.ApiClient/blob/master/Bit2C.API/Client.cs

This endpoint is NOT documented in the official Bit2C API docs but is essential for fetching deposit and withdrawal history.

### Testing Results

Successfully retrieved:
- 25 Deposits
- 20 Withdrawals
- 9 FeeWithdrawals
- Various refund types

### Action Types

| Value | Type | Description |
|-------|------|-------------|
| 2 | Deposit | NIS or crypto deposit |
| 3 | Withdrawal | NIS or crypto withdrawal |
| 4 | FeeWithdrawal | Withdrawal fee |
| 23 | RefundWithdrawal | Refunded withdrawal |
| 24 | RefundFeeWithdrawal | Refunded withdrawal fee |
| 26 | DepositFee | Deposit fee |
| 27 | RefundDepositFee | Refunded deposit fee |

### Files Modified

- `backend/app/services/bit2c_client.py`:
  - Added `get_funds_history()` method
  - Added `_parse_funds_record()` method
  - Updated `fetch_all_data()` to include FundsHistory
- `backend/tests/test_bit2c_client.py` - Added FundsHistory tests
- `docs/research/bit2c-api-research.md` - Documented undocumented endpoint

### Test Results
- 13 client tests passing (including new FundsHistory tests)

### Commit
```
fix(bit2c): add FundsHistory endpoint for deposits/withdrawals
```

---

## Task 6: Bit2C Documentation

**Goal:** Document Bit2C integration for future reference.

### Deliverable
Create `docs/brokers/bit2c.md` with:
1. Overview (Israeli crypto exchange, ILS-denominated)
2. API endpoints used and their purpose
3. Authentication method
4. Rate limits
5. File export format (if available)
6. Data transformation logic

### Commit
```
docs(bit2c): add integration documentation
```

---

## Task 7: Binance API Research ✅

**Status:** Complete (2026-01-20)

**Goal:** Research Binance API endpoints and file export formats.

### Deliverable
Create `docs/research/binance-api-research.md` with:
1. API documentation links
2. Authentication: HMAC SHA256 signing
3. Required endpoints:
   - `GET /api/v3/account` - Balances
   - `GET /api/v3/myTrades` - Trade history (per symbol)
   - `GET /sapi/v1/capital/deposit/hisrec` - Deposits
   - `GET /sapi/v1/capital/withdraw/history` - Withdrawals
4. Rate limits (1200 weight/minute)
5. File export formats from Binance UI
6. Pagination handling for large histories

### Commit
```
docs(binance): add API research documentation
```

---

## Task 8: Binance Implementation ✅

**Status:** Complete (2026-01-20)

**Goal:** Implement Binance support with API and file parser.

### Files to Create
- `backend/app/services/binance_client.py` - HMAC-authenticated client
- `backend/app/services/binance_parser.py` - CSV parser + API parser
- `backend/tests/test_binance_parser.py`

### Implementation
1. Create `BinanceClient` with HMAC SHA256 signing
2. Implement rate limiting (track request weights)
3. Create `BinanceParser` for both CSV and API responses
4. Map to `BrokerImportData`

### Commit
```
feat(binance): add Binance API client and CSV parser
```

---

## Task 9: Binance Documentation ✅

**Status:** Complete (2026-01-20)

**Goal:** Document Binance integration for future reference.

### Deliverable
Create `docs/brokers/binance.md` with:
1. Overview of Binance and supported features
2. API endpoints used and their purpose
3. Authentication details (HMAC SHA256)
4. Rate limits and weight system
5. CSV export format and column mappings
6. Data transformation logic

### Commit
```
docs(binance): add integration documentation
```

---

# Sprint 1a: Crypto Price Provider

This sprint implements a unified cryptocurrency price provider using CoinGecko, analogous to how yfinance is used for stock prices.

## Rationale

Just as we use yfinance as the single source of truth for stock prices, we need a centralized crypto price provider that:
- Fetches prices for all crypto assets regardless of which exchange they were traded on
- Provides historical price data for portfolio valuation
- Is independent of broker-specific APIs

**Design Decision:** Fetch prices in USD and convert to ILS using our existing `exchange_rates` table, rather than relying on CoinGecko's ILS support.

---

## Task 9c: CoinGecko API Research ✅

**Status:** Complete (2026-01-20)

**Goal:** Research CoinGecko API to understand endpoints, rate limits, and data formats.

### Deliverable
Create `docs/research/coingecko-api-research.md` with:
1. API documentation links
2. Authentication (API key optional for basic endpoints)
3. Required endpoints:
   - `/simple/price` - Current prices for multiple coins
   - `/coins/{id}/market_chart` - Historical OHLC data
   - `/coins/list` - Symbol to CoinGecko ID mapping
4. Rate limits (10-50 calls/min on free tier)
5. Response format examples
6. Symbol mapping strategy (BTC → bitcoin, ETH → ethereum)

### Research Questions
- How to map our symbols (BTC, ETH) to CoinGecko IDs?
- What's the best endpoint for batch price fetching?
- How far back does historical data go?
- Do we need an API key for our use case?

### Commit
```
docs(coingecko): add API research documentation
```

---

## Task 9d: CoinGecko Implementation ✅

**Status:** Complete (2026-01-20)

**Goal:** Implement CoinGecko client for crypto price fetching.

### Files to Create
- `backend/app/services/coingecko_client.py` - API client
- `backend/tests/test_coingecko_client.py` - Unit tests

### Implementation

```python
# backend/app/services/coingecko_client.py
"""CoinGecko API client for cryptocurrency prices.

Serves as the single source of truth for crypto prices,
analogous to yfinance for stocks.
"""
import logging
from decimal import Decimal
from datetime import date, datetime

import httpx

logger = logging.getLogger(__name__)

COINGECKO_BASE_URL = "https://api.coingecko.com/api/v3"

# Symbol to CoinGecko ID mapping
SYMBOL_TO_ID = {
    "BTC": "bitcoin",
    "ETH": "ethereum",
    "LTC": "litecoin",
    "XRP": "ripple",
    "USDC": "usd-coin",
    "USDT": "tether",
    "DOGE": "dogecoin",
    # Add more as needed
}


class CoinGeckoClient:
    """Client for fetching cryptocurrency prices from CoinGecko."""

    def __init__(self, api_key: str | None = None):
        """Initialize client with optional API key for higher rate limits."""
        self.api_key = api_key
        self.base_url = COINGECKO_BASE_URL

    def get_current_prices(
        self, symbols: list[str], vs_currency: str = "usd"
    ) -> dict[str, Decimal]:
        """Get current prices for multiple cryptocurrencies.

        Args:
            symbols: List of crypto symbols (e.g., ["BTC", "ETH"])
            vs_currency: Quote currency (default: "usd")

        Returns:
            Dict mapping symbol to current price
        """
        # Convert symbols to CoinGecko IDs
        ids = [SYMBOL_TO_ID.get(s.upper(), s.lower()) for s in symbols]
        ...

    def get_historical_price(
        self, symbol: str, target_date: date, vs_currency: str = "usd"
    ) -> Decimal | None:
        """Get historical price for a specific date.

        Args:
            symbol: Crypto symbol (e.g., "BTC")
            target_date: Date for historical price
            vs_currency: Quote currency (default: "usd")

        Returns:
            Price on that date, or None if unavailable
        """
        ...

    def get_price_history(
        self, symbol: str, start_date: date, end_date: date, vs_currency: str = "usd"
    ) -> list[tuple[date, Decimal]]:
        """Get price history for date range.

        Args:
            symbol: Crypto symbol
            start_date: Start of range
            end_date: End of range
            vs_currency: Quote currency

        Returns:
            List of (date, price) tuples
        """
        ...
```

### Key Design Decisions
1. **USD prices only** - Fetch in USD, convert to ILS via exchange_rates table
2. **Symbol mapping** - Maintain SYMBOL_TO_ID dict for common cryptos
3. **Caching** - Consider caching prices to reduce API calls
4. **Rate limiting** - Implement delays between requests if needed

### Commit
```
feat(coingecko): add CoinGecko client for crypto prices
```

---

## Task 9e: CoinGecko Documentation ✅

**Status:** Complete (2026-01-20)

**Goal:** Document CoinGecko integration for future reference.

### Deliverable
Create `docs/services/coingecko.md` with:
1. Overview and purpose (single source of truth for crypto prices)
2. API endpoints used
3. Symbol to CoinGecko ID mapping
4. Rate limits and caching strategy
5. Integration with exchange_rates table for ILS conversion
6. Comparison to yfinance for stocks

### Commit
```
docs(coingecko): add service documentation
```

---

## Task 9f: CryptoCompare - Research & Implementation ✅

**Status:** Complete (2026-01-20)

**Goal:** Implement CryptoCompare client to fetch historical crypto prices older than 365 days (CoinGecko free tier limitation).

### Problem
CoinGecko's free tier only provides 365 days of historical data, but users can upload transactions older than 1 year.

### Solution
CryptoCompare API provides full historical data back to coin inception:
- BTC: Data from December 2012
- ETH: Data from July 2015

### Files Created
- `docs/research/cryptocompare-api-research.md` - API research
- `backend/app/services/cryptocompare_client.py` - API client
- `backend/tests/test_cryptocompare_client.py` - 17 unit tests
- `docs/services/cryptocompare.md` - Service documentation

### Key Features
- `get_historical_price()` - Single date lookup
- `get_price_history()` - Date range with auto-pagination (up to 2000 days/request)
- Uses standard symbols directly (no ID mapping needed)
- Rate limiting (1 req/sec)

### Integration Strategy
| Data Type | API |
|-----------|-----|
| Current prices | CoinGecko |
| Historical < 365 days | CoinGecko |
| Historical > 365 days | CryptoCompare |

---

## Task 9g: Historical Price Backfill DAG ✅

**Status:** Complete (2026-01-20)

**Goal:** Update the backfill DAG to support crypto historical prices using CryptoCompare.

### Files Modified
- `airflow/dags/queries.py` - Added `GET_CRYPTO_ASSETS` and `GET_NON_CRYPTO_ASSETS` queries
- `airflow/dags/backfill_historical_data.py` - Added `backfill_crypto_prices` task

### How It Works
The `backfill_historical_data` DAG now has three parallel tasks:
1. `backfill_exchange_rates` - Yahoo Finance currency pairs
2. `backfill_asset_prices` - Yahoo Finance for stocks/ETFs
3. `backfill_crypto_prices` - CryptoCompare for crypto assets

### DAG Parameters
- `start_date`: Default "2017-01-01" (covers most crypto adoption)
- `end_date`: Default to yesterday

### Verification
Successfully tested:
- 72,825 stock/ETF prices backfilled
- 19,298 exchange rates backfilled
- Crypto infrastructure ready (will populate when crypto holdings exist)

---

# Sprint 1b: Airflow Integration

This sprint enables automated hourly imports for the newly implemented crypto exchanges.

## Current State Analysis

The existing `hourly_broker_import.py` DAG:
1. Queries accounts with broker API credentials from the database
2. Currently supports:
   - **IBKR**: Full implementation via `/api/ibkr/import-auto/{account_id}` endpoint
   - **Binance**: Placeholder only (logs "not yet implemented")
3. Uses dynamic task mapping for parallel imports
4. Checks `meta_data` JSONB field for broker credentials

### Required Changes

To support Kraken and Bit2C automated imports:

1. **DAG Updates (`airflow/dags/hourly_broker_import.py`):**
   - Add credential detection for Kraken (`meta_data.kraken.api_key`)
   - Add credential detection for Bit2C (`meta_data.bit2c.api_key`)
   - Add import handlers for each new broker type

2. **Backend API Endpoints:**
   - Create `/api/kraken/import-auto/{account_id}` - Kraken auto-import
   - Create `/api/bit2c/import-auto/{account_id}` - Bit2C auto-import
   - Create `/api/binance/import-auto/{account_id}` - Binance auto-import (when implemented)

3. **Database Schema:**
   - Document expected `meta_data` structure for each broker's credentials

---

## Task 9a: Airflow DAG Updates for Crypto Exchanges ✅

**Goal:** Update the hourly broker import DAG to support Kraken, Bit2C, and Binance automated imports.

**Status:** ✅ Complete

### Files to Modify
- `airflow/dags/hourly_broker_import.py`

### Implementation Steps

#### Step 1: Add Kraken credential detection

```python
# In get_active_accounts() task, add after Binance check:

# Check for Kraken credentials
kraken_config = meta_data.get("kraken", {})
if kraken_config.get("api_key") and kraken_config.get("api_secret"):
    accounts.append(
        {
            "account_id": account_id,
            "broker_type": "kraken",
            "has_credentials": True,
        }
    )
    logger.info("Found Kraken credentials for account %d", account_id)

# Check for Bit2C credentials
bit2c_config = meta_data.get("bit2c", {})
if bit2c_config.get("api_key") and bit2c_config.get("api_secret"):
    accounts.append(
        {
            "account_id": account_id,
            "broker_type": "bit2c",
            "has_credentials": True,
        }
    )
    logger.info("Found Bit2C credentials for account %d", account_id)
```

#### Step 2: Add import handlers

```python
# In import_broker_data() task, add broker handlers:

elif broker_type == "kraken":
    response = requests.post(
        f"{BACKEND_URL}/api/kraken/import-auto/{account_id}",
        timeout=300,
    )
    # ... standard success/error handling

elif broker_type == "bit2c":
    response = requests.post(
        f"{BACKEND_URL}/api/bit2c/import-auto/{account_id}",
        timeout=300,
    )
    # ... standard success/error handling
```

### Commit
```
feat(airflow): add Kraken and Bit2C support to hourly broker import DAG
```

---

## Task 9b: Backend API Endpoints for Crypto Import ✅

**Goal:** Create auto-import API endpoints for Kraken and Bit2C.

**Status:** ✅ Complete

### Files to Create
- `backend/app/api/kraken.py` - Kraken API routes
- `backend/app/api/bit2c.py` - Bit2C API routes

### Files to Modify
- `backend/app/api/__init__.py` - Register new routers

### Implementation Pattern

Follow the existing IBKR pattern in `backend/app/api/ibkr.py`:

```python
# backend/app/api/kraken.py
"""Kraken API routes for automated imports."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.services.kraken_client import KrakenClient, KrakenCredentials

router = APIRouter(prefix="/api/kraken", tags=["kraken"])

@router.post("/import-auto/{account_id}")
def import_kraken_auto(
    account_id: int,
    db: Session = Depends(get_db),
):
    """
    Auto-import Kraken data using stored API credentials.

    1. Fetch account and validate Kraken credentials in meta_data
    2. Create KrakenClient with credentials
    3. Call client.fetch_all_data()
    4. Save positions and transactions to database
    5. Return import statistics
    """
    # Implementation follows IBKR pattern
    ...
```

### Expected `meta_data` Structure

```json
{
  "kraken": {
    "api_key": "...",
    "api_secret": "..."
  },
  "bit2c": {
    "api_key": "...",
    "api_secret": "..."
  },
  "binance": {
    "api_key": "...",
    "api_secret": "..."
  }
}
```

### Commit
```
feat(api): add auto-import endpoints for Kraken and Bit2C
```

---

## Task 9h: Unified Broker Router Refactoring ✅

**Goal:** Consolidate all broker API endpoints into a single unified router with a data-driven registry pattern, and register Binance.

**Status:** ✅ Complete

### Changes Made

**1. Registered Binance in `BROKER_REGISTRY`:**
```python
BrokerType.BINANCE: BrokerConfig(
    key="binance",
    name="Binance",
    credential_type=CredentialType.API_KEY_SECRET,
    client_class=BinanceClient,
    credentials_class=BinanceCredentials,
    balance_method="get_account_balances",
),
```

**2. Removed `supports_test_credentials` field:**
- All brokers now support credential testing via `/api/brokers/{broker}/test-credentials/{account_id}`
- IBKR uses `IBKRFlexClient.request_flex_query()` to validate Flex Query credentials
- Crypto brokers (Kraken, Bit2C, Binance) fetch balances to validate API keys

**3. Data-driven client instantiation:**
- `BrokerConfig` now includes `client_class`, `credentials_class`, `balance_method`
- Eliminated if/elif chains in favor of `getattr(client, config.balance_method)()`
- Adding new brokers only requires registry entry, no endpoint code changes

**4. Added credential helper functions:**
- `get_credential_fields()` - returns field names for credential type
- `has_credentials()` - checks if credentials exist in metadata
- `remove_credential_fields()` - removes credential fields from metadata
- `build_credential_data()` - creates credential dict from Pydantic model with timestamp

**5. Added account validation helper:**
- `_get_validated_account()` - validates account ownership, returns Account or raises 404
- Replaced 5 repetitions of account validation logic

**6. Added crypto client factory:**
- `_create_crypto_client()` - creates broker client from registry config
- Uses `config.client_class` and `config.credentials_class`
- Eliminated if/elif chains for client instantiation

**7. Dynamic error messages:**
- Error messages in `_get_flex_query_credentials()` now use broker name/key from config
- Future brokers get correct error messages without code changes

### Available Endpoints (All Brokers)
- `GET /api/brokers/` - List all supported brokers
- `PUT /api/brokers/{broker}/credentials/{account_id}` - Store credentials
- `GET /api/brokers/{broker}/credentials/{account_id}` - Check credential status
- `POST /api/brokers/{broker}/test-credentials/{account_id}` - Test credentials
- `POST /api/brokers/{broker}/import/{account_id}` - Import data

### Code Simplification
- Reduced file from ~700 lines to ~580 lines (17% reduction)
- All linting checks pass
- All 23 tests passing
- New brokers require only registry entry (no endpoint changes)

### Commit
```
refactor(brokers): unify broker router with data-driven registry pattern
```

---

# Sprint 2: Israeli Brokers

## ⚠️ Broker Integration Guidelines (MANDATORY)

**CRITICAL:** Before implementing ANY broker, review `CLAUDE.md` → "Broker Integration Guidelines".

### Key Rules (learned from Kraken integration bugs)

1. **Dual-Entry Accounting**: Every trade MUST create TWO transactions:
   - Asset transaction (Buy/Sell on stock/crypto holding)
   - Trade Settlement (Cash impact on USD/ILS holding)

2. **Fee Handling**: ALL fee types must be handled correctly:
   | Transaction | Fee Rule |
   |-------------|----------|
   | Buy | Fee usually in fiat, included in Trade Settlement |
   | Sell | `quantity = abs(amount_sold) + fee` |
   | Withdrawal | `quantity = abs(amount) + fee` |
   | Staking/Dividend | `quantity = amount - fee` |

3. **Decimal Precision**:
   - Use `quantity` field (8 decimals) for shares/crypto
   - `amount` field only has 2 decimal places (for fiat values)

4. **Verification Checklist** (BEFORE marking complete):
   - [ ] Clear test account transactions
   - [ ] Import from broker
   - [ ] Compare each asset balance with broker's actual positions
   - [ ] Verify cash balance reflects all trade settlements
   - [ ] Re-sync should skip duplicates

### Reference Implementations
- IBKR (`ibkr_import_service.py`) - Best dual-entry example
- Meitav (`meitav_parser.py`) - Israeli broker reference
- Kraken (`kraken_client.py`) - Crypto with all fee types

---

## Task 10: IBI Parser

**Goal:** Support IBI Trade (52K accounts, fastest growing Israeli broker).

### Files to Create
- `backend/app/services/ibi_parser.py`
- `backend/tests/test_ibi_parser.py`
- `backend/tests/fixtures/ibi_sample.xlsx`

### Implementation
1. Research IBI "Spark" platform export format
2. Create Hebrew column mappings (similar to Meitav)
3. Implement `IBIParser` extending `BaseBrokerParser`
4. Reuse TASE security resolution
5. Handle Agorot → ILS conversion
6. **CRITICAL**: Implement dual-entry accounting (see guidelines above)
7. **CRITICAL**: Handle fees correctly for all transaction types

### Verification (REQUIRED before marking complete)
- [ ] Dual-entry: each trade creates asset transaction + Trade Settlement
- [ ] Fee handling: verify fees subtracted/added correctly
- [ ] Decimal precision: use `quantity` field for share counts
- [ ] Balance match: compare imported positions with broker's actual positions
- [ ] Cash balance: verify ILS balance reflects all settlements

### Pattern to Follow
Reference: `backend/app/services/meitav_parser.py`

### Commit
```
feat(ibi): add IBI broker parser for Excel imports
```

---

## Task 11: IBI Documentation

**Goal:** Document IBI integration for future reference.

### Deliverable
Create `docs/brokers/ibi.md` with:
1. Overview of IBI Trade and Spark platform
2. Export instructions (how to download from IBI website)
3. File format (XLSX) and column schema
4. Hebrew column mappings (שם נייר, מס' נייר, etc.)
5. Data transformations (Agorot → ILS, TASE resolution)

### Commit
```
docs(ibi): add integration documentation
```

---

## Task 12: Excellence (Phoenix) Parser

**Goal:** Support Excellence Investment House (Phoenix group).

### Files to Create
- `backend/app/services/excellence_parser.py`
- `backend/tests/test_excellence_parser.py`
- `backend/tests/fixtures/excellence_sample.xlsx`

### Implementation
1. Research Excellence export format (likely Excel)
2. Create Hebrew column mappings
3. Implement `ExcellenceParser`
4. Reuse TASE security resolution
5. **CRITICAL**: Implement dual-entry accounting (see Sprint 2 guidelines)
6. **CRITICAL**: Handle fees correctly for all transaction types

### Verification (REQUIRED before marking complete)
- [ ] Dual-entry: each trade creates asset transaction + Trade Settlement
- [ ] Fee handling: verify fees subtracted/added correctly
- [ ] Decimal precision: use `quantity` field for share counts
- [ ] Balance match: compare imported positions with broker's actual positions
- [ ] Cash balance: verify ILS balance reflects all settlements

### Commit
```
feat(excellence): add Excellence broker parser
```

---

## Task 13: Excellence Documentation

**Goal:** Document Excellence integration for future reference.

### Deliverable
Create `docs/brokers/excellence.md` with:
1. Overview of Excellence Investment House
2. Export instructions
3. File format and column schema
4. Hebrew column mappings
5. Data transformations

### Commit
```
docs(excellence): add integration documentation
```

---

## Task 14: Altshuler Shaham Parser

**Goal:** Support Altshuler Shaham broker.

### Files to Create
- `backend/app/services/altshuler_parser.py`
- `backend/tests/test_altshuler_parser.py`
- `backend/tests/fixtures/altshuler_sample.xlsx`

### Implementation
1. Research Altshuler Shaham export format
2. Create Hebrew column mappings
3. Implement `AltshulerParser`
4. Reuse TASE security resolution
5. **CRITICAL**: Implement dual-entry accounting (see Sprint 2 guidelines)
6. **CRITICAL**: Handle fees correctly for all transaction types

### Verification (REQUIRED before marking complete)
- [ ] Dual-entry: each trade creates asset transaction + Trade Settlement
- [ ] Fee handling: verify fees subtracted/added correctly
- [ ] Decimal precision: use `quantity` field for share counts
- [ ] Balance match: compare imported positions with broker's actual positions
- [ ] Cash balance: verify ILS balance reflects all settlements

### Commit
```
feat(altshuler): add Altshuler Shaham broker parser
```

---

## Task 15: Altshuler Shaham Documentation

**Goal:** Document Altshuler Shaham integration for future reference.

### Deliverable
Create `docs/brokers/altshuler.md` with:
1. Overview of Altshuler Shaham
2. Export instructions
3. File format and column schema
4. Hebrew column mappings
5. Data transformations

### Commit
```
docs(altshuler): add integration documentation
```

---

# Sprint 3: Israeli Banks

> **⚠️ IMPORTANT:** All brokers in this sprint MUST follow the Broker Integration Guidelines in Sprint 2. See `CLAUDE.md` → "Broker Integration Guidelines" for full details.

## Task 16: Bank Leumi Parser

**Goal:** Support Bank Leumi brokerage accounts.

### Files to Create
- `backend/app/services/leumi_parser.py`
- `backend/tests/test_leumi_parser.py`

### Implementation
1. Research Bank Leumi export format (likely PDF or Excel)
2. Create parser for positions and transactions
3. Handle pension/provident fund data if available
4. **CRITICAL**: Implement dual-entry accounting
5. **CRITICAL**: Handle fees correctly for all transaction types

### Verification (REQUIRED)
- [ ] Dual-entry accounting implemented
- [ ] Fee handling for all transaction types
- [ ] Balance match with broker positions
- [ ] Cash balance reflects all settlements

### Commit
```
feat(leumi): add Bank Leumi parser
```

---

## Task 17: Bank Leumi Documentation

**Goal:** Document Bank Leumi integration.

### Deliverable
Create `docs/brokers/leumi.md`

### Commit
```
docs(leumi): add integration documentation
```

---

## Task 18: Bank Hapoalim Parser

**Goal:** Support Bank Hapoalim brokerage accounts.

### Files to Create
- `backend/app/services/hapoalim_parser.py`
- `backend/tests/test_hapoalim_parser.py`

### Implementation
1. Research Bank Hapoalim export format
2. Create parser for positions and transactions
3. **CRITICAL**: Implement dual-entry accounting
4. **CRITICAL**: Handle fees correctly for all transaction types

### Verification (REQUIRED)
- [ ] Dual-entry accounting implemented
- [ ] Fee handling for all transaction types
- [ ] Balance match with broker positions
- [ ] Cash balance reflects all settlements

### Commit
```
feat(hapoalim): add Bank Hapoalim parser
```

---

## Task 19: Bank Hapoalim Documentation

**Goal:** Document Bank Hapoalim integration.

### Deliverable
Create `docs/brokers/hapoalim.md`

### Commit
```
docs(hapoalim): add integration documentation
```

---

## Task 20: Discount Bank Parser

**Goal:** Support Discount Bank brokerage accounts.

### Files to Create
- `backend/app/services/discount_parser.py`
- `backend/tests/test_discount_parser.py`

### Implementation
1. Research Discount Bank export format
2. Create parser for positions and transactions
3. **CRITICAL**: Implement dual-entry accounting
4. **CRITICAL**: Handle fees correctly for all transaction types

### Verification (REQUIRED)
- [ ] Dual-entry accounting implemented
- [ ] Fee handling for all transaction types
- [ ] Balance match with broker positions
- [ ] Cash balance reflects all settlements

### Commit
```
feat(discount): add Discount Bank parser
```

---

## Task 21: Discount Bank Documentation

**Goal:** Document Discount Bank integration.

### Deliverable
Create `docs/brokers/discount.md`

### Commit
```
docs(discount): add integration documentation
```

---

## Task 22: Mizrahi Tefahot Parser

**Goal:** Support Mizrahi Tefahot brokerage accounts.

### Files to Create
- `backend/app/services/mizrahi_parser.py`
- `backend/tests/test_mizrahi_parser.py`

### Implementation
1. Research Mizrahi Tefahot export format
2. Create parser for positions and transactions
3. **CRITICAL**: Implement dual-entry accounting
4. **CRITICAL**: Handle fees correctly for all transaction types

### Verification (REQUIRED)
- [ ] Dual-entry accounting implemented
- [ ] Fee handling for all transaction types
- [ ] Balance match with broker positions
- [ ] Cash balance reflects all settlements

### Commit
```
feat(mizrahi): add Mizrahi Tefahot parser
```

---

## Task 23: Mizrahi Tefahot Documentation

**Goal:** Document Mizrahi Tefahot integration.

### Deliverable
Create `docs/brokers/mizrahi.md`

### Commit
```
docs(mizrahi): add integration documentation
```

---

# Sprint 4: Polish

## Task 24: Stock Split Transaction Type

**Goal:** Handle corporate actions (stock splits) that adjust share quantities and cost basis.

### Files to Modify
- `backend/app/models/transaction.py`
- `backend/app/services/corporate_actions_service.py`
- `backend/app/services/ibkr_parser.py`
- `backend/app/services/portfolio_reconstruction_service.py`

### Implementation
1. Add `record_stock_split()` method
2. Add `apply_splits_to_quantity()` for historical adjustment
3. Parse splits from IBKR XML
4. Update portfolio reconstruction

### Commit
```
feat(splits): add stock split transaction type support
```

---

## Task 25: Broker Tutorial Content System

**Goal:** Guide users on how to export data from each supported broker.

### Files to Create
- `backend/app/services/broker_tutorials.py`
- `frontend/src/components/BrokerTutorial.jsx`

### Implementation
1. Create tutorial dataclasses
2. Define step-by-step tutorials for all supported brokers
3. Add API endpoint
4. Create React modal component

### Commit
```
feat(tutorials): add broker export tutorial system
```

---

## Task 26: File Upload Progress Tracking

**Goal:** Show real-time progress for large file uploads.

### Files to Create
- `backend/app/routers/broker_data_streaming.py` - SSE endpoint
- `frontend/src/hooks/useFileUploadProgress.js`

### Implementation
1. Create in-memory progress store
2. Add SSE endpoint for progress streaming
3. Create React hook using EventSource
4. Add progress bar UI

### Commit
```
feat(upload): add file upload progress tracking with SSE
```

---

## Verification Plan

### Unit Tests
```bash
cd backend && pytest tests/test_*_parser.py -v
pytest --cov=app.services --cov-report=html
```

### Integration Tests
1. Upload test fixtures through API
2. Test API fetch with sandbox credentials (where available)
3. Verify transactions and holdings

### Manual Testing Checklist
- [ ] Kraken: CSV upload + API fetch
- [ ] Bit2C: CSV upload + API fetch
- [ ] Binance: CSV upload + API fetch
- [ ] IBI: Excel upload
- [ ] Excellence: Excel upload
- [ ] Altshuler: Excel upload
- [ ] Leumi: File upload
- [ ] Hapoalim: File upload
- [ ] Discount: File upload
- [ ] Mizrahi: File upload

---

## Critical Files Reference

| File | Purpose |
|------|---------|
| `backend/app/services/base_broker_parser.py` | Interface for all parsers |
| `backend/app/services/broker_parser_registry.py` | Parser registration |
| `backend/app/services/meitav_parser.py` | Template for Israeli broker parsers |
| `backend/app/routers/broker_data.py` | Upload + API fetch endpoints |
| `frontend/src/pages/Accounts.jsx` | Upload UI integration |

---

# Phase 4: i18n & UI Polish (Outline)

**Goal:** Hebrew localization and UX improvements

**Tasks:**
1. Set up react-i18next
2. Extract all strings to translation files
3. Implement RTL support
4. Create Hebrew translations
5. Add language switcher
6. Implement Demo Portfolio feature
7. Create onboarding flow with broker tutorials
8. Add shareable performance chart

---

# Phase 5: Deployment & Infrastructure (Outline)

**Goal:** Deploy to Railway/Render with cron jobs

**Tasks:**
1. Create Railway/Render configuration
2. Set up PostgreSQL managed instance
3. Configure environment variables
4. Create CLI task scripts (migrate from Airflow DAGs)
5. Set up platform cron jobs
6. Configure SSL and domain
7. Set up error monitoring (Sentry)
8. Create CI/CD pipeline

---

# Phase 6: Security Hardening (Outline)

**Goal:** Production-ready security before public launch

**Tasks:**
1. **httpOnly Cookies for JWT tokens** - Replace localStorage token storage with httpOnly cookies
   - More secure against XSS attacks
   - Requires CORS configuration updates
   - Need CSRF token implementation
   - Update frontend API client to work with cookies
2. Implement Content Security Policy (CSP) headers
3. Add security headers (HSTS, X-Frame-Options, etc.)
4. Security audit of all endpoints
5. Penetration testing
6. Set up WAF rules if needed

**Note:** Rate limiting and password strength validation already implemented in Phase 1.