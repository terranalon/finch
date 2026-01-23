"""Schemas for admin endpoints."""

from pydantic import BaseModel, Field


class AdminDisableMfaRequest(BaseModel):
    """Request schema for admin MFA disable."""

    reason: str = Field(..., min_length=5, max_length=500)
