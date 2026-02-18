"""Service for assembling asset detail data."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.exceptions import NotFoundError
from app.models import Asset
from app.models.asset_daily_metrics import AssetDailyMetrics
from app.schemas.asset_detail import AssetDetailResponse, DailyMetricsResponse


class AssetDetailService:
    """Assembles asset detail from assets table + latest daily metrics."""

    @staticmethod
    def get_asset_detail(db: Session, *, asset_id: int) -> AssetDetailResponse:
        """Get full asset detail including latest daily metrics.

        Args:
            db: Database session
            asset_id: Asset primary key

        Returns:
            AssetDetailResponse with nested daily_metrics (or None if no data)

        Raises:
            NotFoundError: If asset_id doesn't exist
        """
        asset = db.get(Asset, asset_id)
        if asset is None:
            raise NotFoundError("Asset", asset_id)

        # Get latest daily metrics row (most recent date)
        stmt = (
            select(AssetDailyMetrics)
            .where(AssetDailyMetrics.asset_id == asset_id)
            .order_by(AssetDailyMetrics.date.desc())
            .limit(1)
        )
        latest_metrics = db.execute(stmt).scalar_one_or_none()

        metrics_response = None
        if latest_metrics is not None:
            metrics_response = DailyMetricsResponse.model_validate(latest_metrics)

        # Build from column data only (skip ORM relationships to avoid
        # Pydantic trying to validate InstrumentedList as DailyMetricsResponse)
        asset_data = {col.key: getattr(asset, col.key) for col in Asset.__table__.columns}
        asset_data["daily_metrics"] = metrics_response
        return AssetDetailResponse(**asset_data)
