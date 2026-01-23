"""MFA router for TOTP, Email OTP, and recovery code operations."""

import logging
import secrets
from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.dependencies.auth import get_current_user
from app.models.email_otp_code import EmailOtpCode
from app.models.mfa_temp_session import MfaTempSession
from app.models.session import Session as UserSession
from app.models.user import User
from app.models.user_mfa import UserMfa
from app.models.user_recovery_code import UserRecoveryCode
from app.schemas.auth import MessageResponse, TokenResponse, UserInfo
from app.schemas.mfa import (
    MfaDisableRequest,
    MfaEnabledResponse,
    MfaVerifyRequest,
    RecoveryCodesRequest,
    RecoveryCodesResponse,
    SendEmailOtpRequest,
    TotpConfirmRequest,
    TotpSetupResponse,
)
from app.services.auth_service import AuthService
from app.services.email_service import EmailService
from app.services.mfa_service import MfaService
from app.services.security_audit_service import SecurityAuditService, SecurityEventType

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth/mfa", tags=["mfa"])


def _generate_and_store_recovery_codes(db: Session, user_id: str) -> list[str]:
    """Generate recovery codes and store hashed versions in database."""
    # Delete existing recovery codes
    db.query(UserRecoveryCode).filter(UserRecoveryCode.user_id == user_id).delete()

    # Generate new codes
    codes = MfaService.generate_recovery_codes()

    # Store hashed codes
    for code in codes:
        recovery_code = UserRecoveryCode(
            user_id=user_id,
            code_hash=AuthService.hash_password(code),  # bcrypt for recovery codes
        )
        db.add(recovery_code)

    return codes


def _verify_recovery_code(db: Session, user_id: str, code: str) -> bool:
    """Verify and consume a recovery code. Returns True if valid."""
    recovery_codes = db.query(UserRecoveryCode).filter(UserRecoveryCode.user_id == user_id).all()

    for stored_code in recovery_codes:
        if AuthService.verify_password(code, stored_code.code_hash):
            # Consume the code by deleting it
            db.delete(stored_code)
            return True
    return False


def _get_or_create_mfa(db: Session, user_id: str) -> UserMfa:
    """Get existing MFA record or create new one."""
    mfa = db.query(UserMfa).filter(UserMfa.user_id == user_id).first()
    if not mfa:
        mfa = UserMfa(user_id=user_id)
        db.add(mfa)
    return mfa


@router.post("/setup/totp", response_model=TotpSetupResponse)
def setup_totp(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    """Initiate TOTP setup. Returns secret and QR code (don't save yet)."""
    secret = MfaService.generate_totp_secret()
    uri = MfaService.get_totp_uri(secret, current_user.email)
    qr_code = MfaService.generate_qr_code_base64(uri)

    return {
        "secret": secret,
        "qr_code_base64": qr_code,
        "manual_entry_key": secret,
    }


@router.post("/confirm/totp", response_model=MfaEnabledResponse)
def confirm_totp(
    data: TotpConfirmRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    """Confirm TOTP setup with valid code. Enables TOTP and returns recovery codes."""
    # Verify the code against the provided secret
    if not MfaService.verify_totp(data.secret, data.code):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid TOTP code",
        )

    # Get or create MFA record
    mfa = _get_or_create_mfa(db, current_user.id)

    # Store encrypted secret and enable TOTP
    mfa.totp_secret_encrypted = MfaService.encrypt_secret(data.secret)
    mfa.totp_enabled = True
    mfa.primary_method = mfa.primary_method or "totp"
    mfa.enabled_at = mfa.enabled_at or datetime.now(UTC)

    # Generate recovery codes
    recovery_codes = _generate_and_store_recovery_codes(db, current_user.id)

    # Log MFA enabled
    SecurityAuditService.log_event(
        db, SecurityEventType.MFA_ENABLED, user_id=current_user.id,
        details={"method": "totp"}
    )
    db.commit()
    logger.info(f"TOTP MFA enabled for user: {current_user.email}")

    return {
        "message": "TOTP MFA enabled successfully",
        "recovery_codes": recovery_codes,
    }


@router.post("/setup/email", response_model=MfaEnabledResponse)
def setup_email_otp(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    """Enable Email OTP MFA. Returns recovery codes."""
    # Get or create MFA record
    mfa = _get_or_create_mfa(db, current_user.id)

    # Enable email OTP
    mfa.email_otp_enabled = True
    mfa.primary_method = mfa.primary_method or "email"
    mfa.enabled_at = mfa.enabled_at or datetime.now(UTC)

    # Generate recovery codes
    recovery_codes = _generate_and_store_recovery_codes(db, current_user.id)

    # Log MFA enabled
    SecurityAuditService.log_event(
        db, SecurityEventType.MFA_ENABLED, user_id=current_user.id,
        details={"method": "email"}
    )
    db.commit()
    logger.info(f"Email OTP MFA enabled for user: {current_user.email}")

    return {
        "message": "Email OTP MFA enabled successfully",
        "recovery_codes": recovery_codes,
    }


@router.delete("", response_model=MessageResponse)
def disable_mfa(
    data: MfaDisableRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    """Disable all MFA methods. Requires MFA code or recovery code."""
    mfa = db.query(UserMfa).filter(UserMfa.user_id == current_user.id).first()
    if not mfa:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="MFA is not enabled",
        )

    # Verify using either TOTP code or recovery code
    verified = (data.mfa_code and _verify_totp_code(mfa, data.mfa_code)) or (
        data.recovery_code and _verify_recovery_code(db, current_user.id, data.recovery_code)
    )

    if not verified:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid MFA code or recovery code",
        )

    # Delete MFA record and recovery codes
    db.delete(mfa)
    db.query(UserRecoveryCode).filter(UserRecoveryCode.user_id == current_user.id).delete()
    db.query(EmailOtpCode).filter(EmailOtpCode.user_id == current_user.id).delete()

    # Log MFA disabled
    SecurityAuditService.log_event(
        db, SecurityEventType.MFA_DISABLED, user_id=current_user.id
    )
    db.commit()

    # Send notification
    EmailService.send_mfa_disabled_notification(current_user.email)

    logger.info(f"MFA disabled for user: {current_user.email}")
    return {"message": "MFA has been disabled"}


@router.post("/recovery-codes", response_model=RecoveryCodesResponse)
def regenerate_recovery_codes(
    data: RecoveryCodesRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    """Regenerate recovery codes. Requires TOTP verification."""
    mfa = db.query(UserMfa).filter(UserMfa.user_id == current_user.id).first()
    if not mfa or not (mfa.totp_enabled or mfa.email_otp_enabled):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="MFA is not enabled",
        )

    if not _verify_totp_code(mfa, data.mfa_code):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid MFA code",
        )

    recovery_codes = _generate_and_store_recovery_codes(db, current_user.id)
    db.commit()

    logger.info(f"Recovery codes regenerated for user: {current_user.email}")
    return {"recovery_codes": recovery_codes}


@router.post("/send-email-code", response_model=MessageResponse)
def send_email_otp_code(
    data: SendEmailOtpRequest,
    db: Session = Depends(get_db),
) -> dict:
    """Send email OTP code for MFA verification during login."""
    # Verify temp session
    temp_session = _validate_temp_session(db, data.temp_token)

    user = temp_session.user
    mfa = db.query(UserMfa).filter(UserMfa.user_id == user.id).first()

    if not mfa or not mfa.email_otp_enabled:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email OTP is not enabled for this user",
        )

    # Invalidate existing email OTP codes
    db.query(EmailOtpCode).filter(
        EmailOtpCode.user_id == user.id,
        EmailOtpCode.used_at.is_(None),
    ).delete()

    # Generate and store new code
    code = MfaService.generate_email_otp()
    email_otp = EmailOtpCode(
        user_id=user.id,
        code_hash=AuthService.hash_token(code),  # SHA-256 for OTP
        expires_at=datetime.now(UTC) + timedelta(minutes=5),
    )
    db.add(email_otp)
    db.commit()

    # Send email
    EmailService.send_mfa_otp_email(user.email, code)

    logger.info(f"Email OTP sent to: {user.email}")
    return {"message": "Verification code sent to your email"}


def _validate_temp_session(db: Session, temp_token: str) -> MfaTempSession:
    """Validate MFA temp session token and return the session."""
    token_hash = AuthService.hash_token(temp_token)
    temp_session = (
        db.query(MfaTempSession)
        .filter(
            MfaTempSession.session_token_hash == token_hash,
            MfaTempSession.used_at.is_(None),
            MfaTempSession.expires_at > datetime.now(UTC),
        )
        .first()
    )

    if not temp_session:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired temporary session",
        )

    return temp_session


def _verify_totp_code(mfa: UserMfa | None, code: str) -> bool:
    """Verify TOTP code against user's MFA settings."""
    if not mfa or not mfa.totp_enabled or not mfa.totp_secret_encrypted:
        return False
    secret = MfaService.decrypt_secret(mfa.totp_secret_encrypted)
    return MfaService.verify_totp(secret, code)


def _verify_email_otp_code(db: Session, user_id: str, mfa: UserMfa | None, code: str) -> bool:
    """Verify email OTP code and mark as used if valid."""
    if not mfa or not mfa.email_otp_enabled:
        return False

    code_hash = AuthService.hash_token(code)
    email_otp = (
        db.query(EmailOtpCode)
        .filter(
            EmailOtpCode.user_id == user_id,
            EmailOtpCode.code_hash == code_hash,
            EmailOtpCode.used_at.is_(None),
            EmailOtpCode.expires_at > datetime.now(UTC),
        )
        .first()
    )
    if email_otp:
        email_otp.used_at = datetime.now(UTC)
        return True
    return False


@router.post("/verify", response_model=TokenResponse)
def verify_mfa(
    data: MfaVerifyRequest,
    db: Session = Depends(get_db),
) -> dict:
    """Verify MFA code and return full access/refresh tokens."""
    temp_session = _validate_temp_session(db, data.temp_token)
    user = temp_session.user
    mfa = db.query(UserMfa).filter(UserMfa.user_id == user.id).first()

    # Verify based on method
    if data.method == "totp":
        verified = _verify_totp_code(mfa, data.code)
    elif data.method == "email":
        verified = _verify_email_otp_code(db, user.id, mfa, data.code)
    else:  # recovery
        verified = _verify_recovery_code(db, user.id, data.code)

    if not verified:
        SecurityAuditService.log_event(
            db, SecurityEventType.MFA_FAILED, user_id=user.id,
            details={"method": data.method}
        )
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid MFA code",
        )

    # Mark temp session as used
    temp_session.used_at = datetime.now(UTC)

    # Create full session tokens
    access_token = AuthService.create_access_token(user.id)
    refresh_token = AuthService.create_refresh_token(user.id)

    # Store refresh token hash in session
    session = UserSession(
        user_id=user.id,
        refresh_token_hash=AuthService.hash_token(refresh_token),
        expires_at=datetime.now(UTC) + timedelta(days=settings.refresh_token_expire_days),
    )
    db.add(session)

    # Log successful MFA verification
    event_type = SecurityEventType.RECOVERY_CODE_USED if data.method == "recovery" else SecurityEventType.MFA_VERIFIED
    SecurityAuditService.log_event(
        db, event_type, user_id=user.id,
        details={"method": data.method}
    )
    db.commit()

    logger.info(f"MFA verified for user: {user.email} using {data.method}")
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "user": UserInfo.model_validate(user),
    }


def create_mfa_temp_session(db: Session, user_id: str) -> str:
    """Create a temporary session for MFA verification. Returns the temp token."""
    temp_token = secrets.token_urlsafe(32)

    temp_session = MfaTempSession(
        user_id=user_id,
        session_token_hash=AuthService.hash_token(temp_token),
        expires_at=datetime.now(UTC) + timedelta(minutes=5),
    )
    db.add(temp_session)

    return temp_token


def get_mfa_methods(mfa: UserMfa | None) -> list[str]:
    """Get list of enabled MFA methods for a user."""
    if not mfa:
        return []
    return [
        method
        for method, enabled in [("totp", mfa.totp_enabled), ("email", mfa.email_otp_enabled)]
        if enabled
    ]
