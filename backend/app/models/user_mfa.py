"""User MFA settings model."""

from datetime import datetime
from typing import TYPE_CHECKING
from uuid import uuid4

from sqlalchemy import Boolean, DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.user import User


class UserMfa(Base):
    """MFA configuration for a user."""

    __tablename__ = "user_mfa"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid4())
    )
    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), unique=True, index=True
    )
    totp_secret_encrypted: Mapped[str | None] = mapped_column(String(255))
    totp_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    email_otp_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    primary_method: Mapped[str | None] = mapped_column(String(10))  # 'totp' or 'email'
    enabled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    user: Mapped["User"] = relationship(back_populates="mfa")

    def __repr__(self) -> str:
        return f"<UserMfa(user_id={self.user_id}, totp={self.totp_enabled}, email={self.email_otp_enabled})>"
