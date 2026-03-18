"""Snapshot response schemas."""

from pydantic import BaseModel, ConfigDict

from app.schemas.common import StatusResponse


class SnapshotPointResponse(BaseModel):
    """Single snapshot data point (after currency conversion)."""

    date: str
    value: float | None = None
    value_usd: float | None = None
    value_ils: float | None = None
    currency: str | None = None
    account_count: int | None = None


class SnapshotCreateResponse(StatusResponse):
    """Response for POST /api/snapshots.

    When run_async=True: {status, message, date}
    When run_async=False: {status, message, ...stats_fields}
    The stats fields vary, so we allow extras.
    """

    model_config = ConfigDict(extra="allow")
