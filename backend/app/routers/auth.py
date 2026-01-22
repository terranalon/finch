"""Authentication router."""

import logging
import secrets
from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.dependencies.auth import get_current_user
from app.models.email_verification_token import EmailVerificationToken
from app.models.portfolio import Portfolio
from app.models.session import Session as UserSession
from app.models.user import User
from app.rate_limiter import limiter
from app.schemas.auth import (
    MessageResponse,
    ResendVerificationRequest,
    TokenRefresh,
    TokenResponse,
    UserInfo,
    UserLogin,
    UserPreferencesUpdate,
    UserRegister,
    VerifyEmailRequest,
)
from app.services.auth_service import AuthService
from app.services.email_service import EmailService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["authentication"])


def _find_valid_session(
    db: Session, user_id: str, refresh_token: str
) -> UserSession | None:
    """Find a valid (non-revoked, non-expired) session matching the refresh token."""
    sessions = (
        db.query(UserSession)
        .filter(
            UserSession.user_id == user_id,
            UserSession.is_revoked == False,  # noqa: E712
            UserSession.expires_at > datetime.now(UTC),
        )
        .all()
    )
    for session in sessions:
        if AuthService.verify_token_hash(refresh_token, session.refresh_token_hash):
            return session
    return None


def _create_verification_token(db: Session, user_id: str) -> str:
    """Create a new email verification token for a user."""
    token = secrets.token_urlsafe(32)
    verification = EmailVerificationToken(
        user_id=user_id,
        token_hash=AuthService.hash_token(token),
        expires_at=datetime.now(UTC) + timedelta(hours=24),
    )
    db.add(verification)
    return token


@router.post("/register", response_model=MessageResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit("5/minute")
def register(request: Request, data: UserRegister, db: Session = Depends(get_db)) -> dict:
    """Register a new user and send verification email."""
    # Check if email already exists
    existing = db.query(User).filter(User.email == data.email).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered",
        )

    # Create user with email_verified=False
    user = User(
        email=data.email,
        password_hash=AuthService.hash_password(data.password),
        email_verified=False,
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

    # Generate verification token
    token = _create_verification_token(db, user.id)
    db.commit()

    # Send verification email
    EmailService.send_verification_email(user.email, token)

    logger.info(f"User registered (pending verification): {user.email}")
    return {"message": "Registration successful. Please check your email to verify your account."}


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

    # Check if email is verified
    if not user.email_verified:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="email_not_verified",
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
    valid_session = _find_valid_session(db, user_id, data.refresh_token)
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
        session = _find_valid_session(db, user_id, data.refresh_token)
        if session:
            session.is_revoked = True
            db.commit()

    return {"message": "Successfully logged out"}


@router.post("/verify-email", response_model=MessageResponse)
def verify_email(data: VerifyEmailRequest, db: Session = Depends(get_db)) -> dict:
    """Verify email with token from email link."""
    token_hash = AuthService.hash_token(data.token)
    verification = (
        db.query(EmailVerificationToken)
        .filter(
            EmailVerificationToken.token_hash == token_hash,
            EmailVerificationToken.used_at.is_(None),
            EmailVerificationToken.expires_at > datetime.now(UTC),
        )
        .first()
    )
    if not verification:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired verification token",
        )

    # Mark token as used and verify user
    verification.used_at = datetime.now(UTC)
    verification.user.email_verified = True
    db.commit()

    # Send welcome email
    EmailService.send_welcome_email(verification.user.email)

    logger.info(f"Email verified for user: {verification.user.email}")
    return {"message": "Email verified successfully. You can now log in."}


@router.post("/resend-verification", response_model=MessageResponse)
@limiter.limit("1/minute")
def resend_verification(
    request: Request, data: ResendVerificationRequest, db: Session = Depends(get_db)
) -> dict:
    """Resend verification email."""
    user = db.query(User).filter(User.email == data.email).first()

    if user and not user.email_verified:
        # Invalidate existing tokens and create new one
        db.query(EmailVerificationToken).filter(EmailVerificationToken.user_id == user.id).delete()
        token = _create_verification_token(db, user.id)
        db.commit()

        EmailService.send_verification_email(user.email, token)
        logger.info(f"Verification email resent to: {user.email}")

    # Always return success (don't reveal if email exists)
    return {"message": "If that email exists and is unverified, we sent a new verification link."}


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
