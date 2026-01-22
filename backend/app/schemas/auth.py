"""Schemas for authentication endpoints."""

import re

from pydantic import BaseModel, EmailStr, Field, field_validator


def _validate_password_strength(v: str) -> str:
    """Shared password validation logic."""
    errors = []
    if not re.search(r"[a-z]", v):
        errors.append("lowercase letter")
    if not re.search(r"[A-Z]", v):
        errors.append("uppercase letter")
    if not re.search(r"\d", v):
        errors.append("number")

    if errors:
        raise ValueError(f"Password must contain at least one: {', '.join(errors)}")
    return v


class UserRegister(BaseModel):
    """Schema for user registration."""

    email: EmailStr
    password: str = Field(min_length=8, max_length=100)

    @field_validator("password")
    @classmethod
    def validate_password_strength(cls, v: str) -> str:
        return _validate_password_strength(v)


class UserLogin(BaseModel):
    """Schema for user login."""

    email: str  # Allow any string for login (supports migrated accounts with .local domains)
    password: str


class UserInfo(BaseModel):
    """Schema for user info in auth responses."""

    id: str
    email: str
    name: str | None = None
    show_combined_view: bool = True

    model_config = {"from_attributes": True}


class TokenResponse(BaseModel):
    """Schema for token response."""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user: UserInfo


class TokenRefresh(BaseModel):
    """Schema for token refresh."""

    refresh_token: str


class MessageResponse(BaseModel):
    """Schema for simple message response."""

    message: str


class UserPreferencesUpdate(BaseModel):
    """Schema for updating user preferences."""

    show_combined_view: bool | None = None
    name: str | None = Field(None, max_length=100)


class VerifyEmailRequest(BaseModel):
    """Schema for email verification."""

    token: str


class ResendVerificationRequest(BaseModel):
    """Schema for resending verification email."""

    email: EmailStr


class ChangePasswordRequest(BaseModel):
    """Schema for changing password while logged in."""

    current_password: str
    new_password: str = Field(min_length=8, max_length=100)

    @field_validator("new_password")
    @classmethod
    def validate_password_strength(cls, v: str) -> str:
        return _validate_password_strength(v)


class ForgotPasswordRequest(BaseModel):
    """Schema for requesting password reset."""

    email: EmailStr


class ResetPasswordRequest(BaseModel):
    """Schema for resetting password with token."""

    token: str
    new_password: str = Field(min_length=8, max_length=100)

    @field_validator("new_password")
    @classmethod
    def validate_password_strength(cls, v: str) -> str:
        return _validate_password_strength(v)
