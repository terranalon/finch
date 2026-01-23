"""User model for authentication."""

from datetime import datetime
from typing import TYPE_CHECKING
from uuid import uuid4

from sqlalchemy import Boolean, DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.database import Base

if TYPE_CHECKING:
    from app.models.email_otp_code import EmailOtpCode
    from app.models.email_verification_token import EmailVerificationToken
    from app.models.mfa_temp_session import MfaTempSession
    from app.models.password_reset_token import PasswordResetToken
    from app.models.portfolio import Portfolio
    from app.models.session import Session
    from app.models.user_mfa import UserMfa
    from app.models.user_recovery_code import UserRecoveryCode


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
    is_service_account: Mapped[bool] = mapped_column(Boolean, default=False)
    email_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    is_admin: Mapped[bool] = mapped_column(Boolean, default=False)
    show_combined_view: Mapped[bool] = mapped_column(Boolean, default=True)
    failed_login_attempts: Mapped[int] = mapped_column(Integer, default=0)
    locked_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        server_default=func.now(), onupdate=func.now()
    )

    # Relationships
    portfolios: Mapped[list["Portfolio"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    sessions: Mapped[list["Session"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    email_verification_tokens: Mapped[list["EmailVerificationToken"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    password_reset_tokens: Mapped[list["PasswordResetToken"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    mfa: Mapped["UserMfa | None"] = relationship(
        back_populates="user", cascade="all, delete-orphan", uselist=False
    )
    email_otp_codes: Mapped[list["EmailOtpCode"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    recovery_codes: Mapped[list["UserRecoveryCode"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    mfa_temp_sessions: Mapped[list["MfaTempSession"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<User(id={self.id}, email='{self.email}')>"
