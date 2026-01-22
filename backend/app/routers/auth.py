"""Authentication router."""

import logging
from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.dependencies.auth import get_current_user
from app.models.portfolio import Portfolio
from app.models.session import Session as UserSession
from app.models.user import User
from app.rate_limiter import limiter
from app.schemas.auth import (
    MessageResponse,
    TokenRefresh,
    TokenResponse,
    UserInfo,
    UserLogin,
    UserPreferencesUpdate,
    UserRegister,
)
from app.services.auth_service import AuthService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["authentication"])


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit("5/minute")
def register(request: Request, data: UserRegister, db: Session = Depends(get_db)) -> dict:
    """Register a new user and return tokens."""
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

    # Create default portfolio for new user
    default_portfolio = Portfolio(
        user_id=user.id,
        name="My Portfolio",
        description="Default portfolio",
        is_default=True,
    )
    db.add(default_portfolio)
    db.commit()

    # Create tokens
    access_token = AuthService.create_access_token(user.id)
    refresh_token = AuthService.create_refresh_token(user.id)

    # Store refresh token hash in session
    session = UserSession(
        user_id=user.id,
        refresh_token_hash=AuthService.hash_token(refresh_token),
        expires_at=datetime.now(UTC) + timedelta(days=settings.refresh_token_expire_days),
    )
    db.add(session)
    db.commit()

    logger.info(f"User registered: {user.email}")
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "user": UserInfo.model_validate(user),
    }


@router.post("/login", response_model=TokenResponse)
@limiter.limit("5/minute")
def login(request: Request, data: UserLogin, db: Session = Depends(get_db)) -> dict:
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

    # Store refresh token hash in session (use SHA-256, not bcrypt, for long tokens)
    session = UserSession(
        user_id=user.id,
        refresh_token_hash=AuthService.hash_token(refresh_token),
        expires_at=datetime.now(UTC) + timedelta(days=settings.refresh_token_expire_days),
    )
    db.add(session)
    db.commit()

    logger.info(f"User logged in: {user.email}")
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "user": UserInfo.model_validate(user),
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
    sessions = (
        db.query(UserSession)
        .filter(
            UserSession.user_id == user_id,
            UserSession.is_revoked == False,  # noqa: E712
            UserSession.expires_at > datetime.now(UTC),
        )
        .all()
    )

    valid_session = None
    for session in sessions:
        if AuthService.verify_token_hash(data.refresh_token, session.refresh_token_hash):
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

    # Store new refresh token (use SHA-256, not bcrypt, for long tokens)
    new_session = UserSession(
        user_id=user.id,
        refresh_token_hash=AuthService.hash_token(refresh_token),
        expires_at=datetime.now(UTC) + timedelta(days=settings.refresh_token_expire_days),
    )
    db.add(new_session)
    db.commit()

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "user": UserInfo.model_validate(user),
    }


@router.post("/logout", response_model=MessageResponse)
def logout(data: TokenRefresh, db: Session = Depends(get_db)) -> dict:
    """Logout and revoke refresh token."""
    payload = AuthService.decode_access_token(data.refresh_token)
    if payload and payload.get("type") == "refresh":
        user_id = payload["sub"]
        # Revoke all sessions for this user (or just the matching one)
        sessions = (
            db.query(UserSession)
            .filter(
                UserSession.user_id == user_id,
                UserSession.is_revoked == False,  # noqa: E712
            )
            .all()
        )

        for session in sessions:
            if AuthService.verify_token_hash(data.refresh_token, session.refresh_token_hash):
                session.is_revoked = True
                break

        db.commit()

    return {"message": "Successfully logged out"}


@router.get("/me", response_model=UserInfo)
def get_me(current_user: User = Depends(get_current_user)) -> User:
    """Get the current authenticated user's information."""
    return current_user


@router.put("/me", response_model=UserInfo)
def update_me(
    preferences: UserPreferencesUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> User:
    """Update the current user's preferences."""
    update_data = preferences.model_dump(exclude_unset=True)

    for field, value in update_data.items():
        setattr(current_user, field, value)

    db.commit()
    db.refresh(current_user)
    return current_user
