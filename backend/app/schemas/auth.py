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


def _validate_username(v: str) -> str:
    """Validate username: 3-30 chars, alphanumeric + underscores, stored lowercase."""
    if not re.fullmatch(r"[A-Za-z0-9_]{3,30}", v):
        raise ValueError(
            "Username must be 3-30 characters and contain only letters, numbers, and underscores"
        )
    return v.lower()


class UserRegister(BaseModel):
    """Schema for user registration."""

    email: EmailStr
    username: str = Field(min_length=3, max_length=30)
    password: str = Field(min_length=8, max_length=100)

    @field_validator("username")
    @classmethod
    def validate_username(cls, v: str) -> str:
        return _validate_username(v)

    @field_validator("password")
    @classmethod
    def validate_password_strength(cls, v: str) -> str:
        return _validate_password_strength(v)


class UserLogin(BaseModel):
    """Schema for user login."""

    identifier: str  # Email or username
    password: str


class UserInfo(BaseModel):
    """Schema for user info in auth responses."""

    id: str
    email: str
    username: str | None = None
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
    username: str | None = Field(None, min_length=3, max_length=30)

    @field_validator("username")
    @classmethod
    def validate_username(cls, v: str | None) -> str | None:
        if v is not None:
            return _validate_username(v)
        return v


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
