"""Admin router for administrative operations."""

import logging

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies.admin import get_admin_user
from app.models.email_otp_code import EmailOtpCode
from app.models.user import User
from app.models.user_mfa import UserMfa
from app.models.user_recovery_code import UserRecoveryCode
from app.rate_limiter import limiter
from app.schemas.admin import AdminDisableMfaRequest
from app.schemas.auth import MessageResponse
from app.services.email_service import EmailService
from app.services.security_audit_service import SecurityAuditService, SecurityEventType

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin", tags=["admin"])


@router.post("/users/{user_id}/disable-mfa", response_model=MessageResponse)
@limiter.limit("10/minute")
def admin_disable_mfa(
    request: Request,
    user_id: str,
    data: AdminDisableMfaRequest,
    db: Session = Depends(get_db),
    admin: User = Depends(get_admin_user),
) -> MessageResponse:
    """Admin endpoint to disable MFA for a user.

    This should only be used for account recovery when user has lost
    access to their MFA methods and recovery codes.
    """
    # Find target user
    target_user = db.query(User).filter(User.id == user_id).first()
    if not target_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    # Check if user has MFA
    mfa = db.query(UserMfa).filter(UserMfa.user_id == user_id).first()
    if not mfa:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User does not have MFA enabled",
        )

    # Delete MFA record and related data
    db.delete(mfa)
    db.query(UserRecoveryCode).filter(UserRecoveryCode.user_id == user_id).delete()
    db.query(EmailOtpCode).filter(EmailOtpCode.user_id == user_id).delete()

    # Log security event
    SecurityAuditService.log_event(
        db,
        SecurityEventType.ADMIN_MFA_DISABLED,
        user_id=user_id,
        details={"admin_id": admin.id, "reason": data.reason},
    )

    db.commit()

    # Send notification to user
    EmailService.send_mfa_disabled_notification(target_user.email)

    logger.info(
        "Admin %s disabled MFA for user %s", admin.email, target_user.email
    )
    return {"message": "MFA has been disabled for the user"}
