"""Schemas for MFA endpoints."""

from pydantic import BaseModel, Field


class TotpSetupResponse(BaseModel):
    """Response for TOTP setup initiation."""

    secret: str
    qr_code_base64: str
    manual_entry_key: str


class TotpConfirmRequest(BaseModel):
    """Request to confirm TOTP setup."""

    secret: str
    code: str = Field(min_length=6, max_length=6)


class MfaEnabledResponse(BaseModel):
    """Response when MFA is enabled, includes recovery codes."""

    message: str
    recovery_codes: list[str] | None = None


class MfaDisableRequest(BaseModel):
    """Request to disable MFA (requires either mfa_code or recovery_code)."""

    mfa_code: str | None = None
    recovery_code: str | None = None


class RecoveryCodesRequest(BaseModel):
    """Request to regenerate recovery codes (requires MFA verification)."""

    mfa_code: str = Field(min_length=6, max_length=6)


class RecoveryCodesResponse(BaseModel):
    """Response with new recovery codes."""

    recovery_codes: list[str]


class MfaLoginResponse(BaseModel):
    """Response when MFA is required during login."""

    mfa_required: bool = True
    temp_token: str
    methods: list[str]


class MfaVerifyRequest(BaseModel):
    """Request to verify MFA code."""

    temp_token: str
    code: str
    method: str = Field(pattern="^(totp|email|recovery)$")


class SendEmailOtpRequest(BaseModel):
    """Request to send email OTP code."""

    temp_token: str


class MfaStatusResponse(BaseModel):
    """Response for GET /auth/mfa/status."""

    mfa_enabled: bool
    totp_enabled: bool
    email_otp_enabled: bool
    primary_method: str | None
    has_recovery_codes: bool


class SetPrimaryMethodRequest(BaseModel):
    """Request to set primary MFA method."""

    method: str = Field(pattern="^(totp|email)$")
