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
from app.models.password_reset_token import PasswordResetToken
from app.models.portfolio import Portfolio
from app.models.session import Session as UserSession
from app.models.user import User
from app.models.user_mfa import UserMfa
from app.rate_limiter import limiter
from app.schemas.auth import (
    ChangePasswordRequest,
    ForgotPasswordRequest,
    MessageResponse,
    ResendVerificationRequest,
    ResetPasswordRequest,
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
from app.services.security_audit_service import SecurityAuditService, SecurityEventType

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["authentication"])


def _find_valid_session(db: Session, user_id: str, refresh_token: str) -> UserSession | None:
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


def _create_token(db: Session, user_id: str, model_class: type, expires_hours: int) -> str:
    """Create a new token for a user (verification or password reset)."""
    token = secrets.token_urlsafe(32)
    token_record = model_class(
        user_id=user_id,
        token_hash=AuthService.hash_token(token),
        expires_at=datetime.now(UTC) + timedelta(hours=expires_hours),
    )
    db.add(token_record)
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

    # Generate verification token (24 hours)
    token = _create_token(db, user.id, EmailVerificationToken, expires_hours=24)
    db.commit()

    # Send verification email
    EmailService.send_verification_email(user.email, token)

    logger.info(f"User registered (pending verification): {user.email}")
    return {"message": "Registration successful. Please check your email to verify your account."}


MAX_LOGIN_ATTEMPTS = 5
LOCKOUT_DURATION_MINUTES = 15


def _check_account_lockout(user: User, db: Session, ip_address: str | None, user_agent: str | None):
    """Check if account is locked and raise exception if so.

    Returns same error as invalid credentials to prevent email enumeration.
    """
    if user.locked_until:
        # Handle both timezone-aware and naive datetimes (SQLite stores naive)
        locked_until = user.locked_until
        if locked_until.tzinfo is None:
            locked_until = locked_until.replace(tzinfo=UTC)
        if locked_until > datetime.now(UTC):
            SecurityAuditService.log_event(
                db, SecurityEventType.LOGIN_BLOCKED_LOCKOUT, user_id=user.id,
                ip_address=ip_address, user_agent=user_agent,
                details={"locked_until": user.locked_until.isoformat()}
            )
            db.commit()
            # Return same error as invalid credentials to prevent email enumeration
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password",
            )


def _record_failed_login(user: User, db: Session, ip_address: str | None, user_agent: str | None, reason: str):
    """Record a failed login attempt and lock account if threshold reached."""
    user.failed_login_attempts += 1

    if user.failed_login_attempts >= MAX_LOGIN_ATTEMPTS:
        user.locked_until = datetime.now(UTC) + timedelta(minutes=LOCKOUT_DURATION_MINUTES)
        SecurityAuditService.log_event(
            db, SecurityEventType.LOGIN_FAILED, user_id=user.id, ip_address=ip_address,
            user_agent=user_agent, details={"reason": reason, "account_locked": True}
        )
    else:
        SecurityAuditService.log_event(
            db, SecurityEventType.LOGIN_FAILED, user_id=user.id, ip_address=ip_address,
            user_agent=user_agent, details={"reason": reason, "attempts": user.failed_login_attempts}
        )
    db.commit()


def _clear_failed_attempts(user: User):
    """Clear failed login attempts on successful login."""
    user.failed_login_attempts = 0
    user.locked_until = None


@router.post("/login")
@limiter.limit("5/minute")
def login(request: Request, data: UserLogin, db: Session = Depends(get_db)) -> dict:
    """Login and get access/refresh tokens."""
    ip_address, user_agent = SecurityAuditService.get_request_info(request)

    # Find user
    user = db.query(User).filter(User.email == data.email).first()
    if not user or not user.password_hash:
        # Perform dummy password verification to prevent timing-based email enumeration
        AuthService.verify_password(data.password, AuthService.get_dummy_hash())
        SecurityAuditService.log_event(
            db, SecurityEventType.LOGIN_FAILED, ip_address=ip_address,
            user_agent=user_agent, details={"email": data.email, "reason": "user_not_found"}
        )
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    # Check if account is locked
    _check_account_lockout(user, db, ip_address, user_agent)

    # Verify password
    if not AuthService.verify_password(data.password, user.password_hash):
        _record_failed_login(user, db, ip_address, user_agent, "invalid_password")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    # Password correct - clear any failed login attempts
    _clear_failed_attempts(user)

    # Check if user is active
    if not user.is_active:
        SecurityAuditService.log_event(
            db, SecurityEventType.LOGIN_BLOCKED_DISABLED, user_id=user.id,
            ip_address=ip_address, user_agent=user_agent
        )
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is disabled",
        )

    # Check if email is verified (service accounts bypass this check)
    if not user.email_verified and not user.is_service_account:
        SecurityAuditService.log_event(
            db, SecurityEventType.LOGIN_BLOCKED_UNVERIFIED, user_id=user.id,
            ip_address=ip_address, user_agent=user_agent
        )
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="email_not_verified",
        )

    # Check if MFA is enabled
    mfa = db.query(UserMfa).filter(UserMfa.user_id == user.id).first()
    if mfa and (mfa.totp_enabled or mfa.email_otp_enabled):
        # MFA is enabled - return temp token instead of full tokens
        from app.routers.mfa import create_mfa_temp_session, get_mfa_methods

        temp_token = create_mfa_temp_session(db, user.id)
        methods = get_mfa_methods(mfa)
        db.commit()

        logger.info(f"MFA required for user: {user.email}")
        return {
            "mfa_required": True,
            "temp_token": temp_token,
            "methods": methods,
            "primary_method": mfa.primary_method,
        }

    # No MFA - create full tokens
    access_token = AuthService.create_access_token(user.id)
    refresh_token = AuthService.create_refresh_token(user.id)

    # Store refresh token hash in session (use SHA-256, not bcrypt, for long tokens)
    session = UserSession(
        user_id=user.id,
        refresh_token_hash=AuthService.hash_token(refresh_token),
        expires_at=datetime.now(UTC) + timedelta(days=settings.refresh_token_expire_days),
    )
    db.add(session)

    # Log successful login
    SecurityAuditService.log_event(
        db, SecurityEventType.LOGIN_SUCCESS, user_id=user.id,
        ip_address=ip_address, user_agent=user_agent
    )
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

    # Log email verification
    SecurityAuditService.log_event(
        db, SecurityEventType.EMAIL_VERIFIED, user_id=verification.user_id
    )
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
        token = _create_token(db, user.id, EmailVerificationToken, expires_hours=24)
        db.commit()

        EmailService.send_verification_email(user.email, token)
        logger.info(f"Verification email resent to: {user.email}")

    # Always return success (don't reveal if email exists)
    return {"message": "If that email exists and is unverified, we sent a new verification link."}


def _invalidate_user_sessions(db: Session, user_id: str) -> None:
    """Revoke all active sessions for a user."""
    db.query(UserSession).filter(
        UserSession.user_id == user_id,
        UserSession.is_revoked == False,  # noqa: E712
    ).update({UserSession.is_revoked: True})


@router.put("/change-password", response_model=MessageResponse)
def change_password(
    request: Request,
    data: ChangePasswordRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    """Change password while logged in."""
    ip_address, user_agent = SecurityAuditService.get_request_info(request)

    # Verify current password
    if not AuthService.verify_password(data.current_password, current_user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Current password is incorrect",
        )

    # Update password
    current_user.password_hash = AuthService.hash_password(data.new_password)

    # Invalidate all other sessions (keep current one active)
    # Note: We can't easily identify the current session from the access token,
    # so we invalidate all sessions - user will need to re-login
    _invalidate_user_sessions(db, current_user.id)

    # Log password change
    SecurityAuditService.log_event(
        db, SecurityEventType.PASSWORD_CHANGED, user_id=current_user.id,
        ip_address=ip_address, user_agent=user_agent
    )
    db.commit()

    # Send notification email
    EmailService.send_password_changed_notification(current_user.email)

    logger.info(f"Password changed for user: {current_user.email}")
    return {"message": "Password changed successfully. Please log in again."}


@router.post("/forgot-password", response_model=MessageResponse)
@limiter.limit("3/hour")
def forgot_password(
    request: Request, data: ForgotPasswordRequest, db: Session = Depends(get_db)
) -> dict:
    """Request password reset email."""
    ip_address, user_agent = SecurityAuditService.get_request_info(request)
    user = db.query(User).filter(User.email == data.email).first()

    if user and user.email_verified:
        # Invalidate existing reset tokens
        db.query(PasswordResetToken).filter(PasswordResetToken.user_id == user.id).delete()

        # Create new reset token (1 hour)
        token = _create_token(db, user.id, PasswordResetToken, expires_hours=1)

        # Log password reset request
        SecurityAuditService.log_event(
            db, SecurityEventType.PASSWORD_RESET_REQUESTED, user_id=user.id,
            ip_address=ip_address, user_agent=user_agent
        )
        db.commit()

        EmailService.send_password_reset_email(user.email, token)
        logger.info(f"Password reset email sent to: {user.email}")

    # Always return success (don't reveal if email exists)
    return {"message": "If that email exists, we sent a password reset link."}


@router.post("/reset-password", response_model=MessageResponse)
def reset_password(
    request: Request, data: ResetPasswordRequest, db: Session = Depends(get_db)
) -> dict:
    """Reset password with token from email."""
    ip_address, user_agent = SecurityAuditService.get_request_info(request)
    token_hash = AuthService.hash_token(data.token)
    reset_token = (
        db.query(PasswordResetToken)
        .filter(
            PasswordResetToken.token_hash == token_hash,
            PasswordResetToken.used_at.is_(None),
            PasswordResetToken.expires_at > datetime.now(UTC),
        )
        .first()
    )

    if not reset_token:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired reset token",
        )

    # Update password
    reset_token.user.password_hash = AuthService.hash_password(data.new_password)
    reset_token.used_at = datetime.now(UTC)

    # Invalidate all sessions
    _invalidate_user_sessions(db, reset_token.user_id)

    # Log password reset completion
    SecurityAuditService.log_event(
        db, SecurityEventType.PASSWORD_RESET_COMPLETED, user_id=reset_token.user_id,
        ip_address=ip_address, user_agent=user_agent
    )
    db.commit()

    # Send notification email
    EmailService.send_password_changed_notification(reset_token.user.email)

    logger.info(f"Password reset for user: {reset_token.user.email}")
    return {"message": "Password reset successfully. You can now log in with your new password."}


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
