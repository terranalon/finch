"""Snapshot response schemas."""

from pydantic import BaseModel, ConfigDict


class SnapshotPointResponse(BaseModel):
    """Single snapshot data point (after currency conversion)."""

    date: str
    value: float | None = None
    value_usd: float | None = None
    value_ils: float | None = None
    currency: str | None = None


class SnapshotCreateResponse(BaseModel):
    """Response for POST /api/snapshots/create.

    When run_async=True: {status, message, date}
    When run_async=False: {status, message, ...stats_fields}
    The stats fields vary, so we allow extras.
    """

    model_config = ConfigDict(extra="allow")

    status: str
    message: str
