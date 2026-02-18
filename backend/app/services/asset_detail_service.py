"""Service for assembling asset detail data."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.exceptions import NotFoundError
from app.models import Asset, AssetDailyMetrics
from app.schemas.asset_detail import AssetDetailResponse, DailyMetricsResponse


class AssetDetailService:
    """Assembles asset detail from assets table + latest daily metrics."""

    @staticmethod
    def get_asset_detail(db: Session, *, asset_id: int) -> AssetDetailResponse:
        """Get full asset detail including latest daily metrics.

        Raises NotFoundError if asset_id doesn't exist.
        """
        asset = db.get(Asset, asset_id)
        if asset is None:
            raise NotFoundError("Asset", asset_id)

        stmt = (
            select(AssetDailyMetrics)
            .where(AssetDailyMetrics.asset_id == asset_id)
            .order_by(AssetDailyMetrics.date.desc())
            .limit(1)
        )
        latest_metrics = db.execute(stmt).scalar_one_or_none()

        metrics_response = (
            DailyMetricsResponse.model_validate(latest_metrics)
            if latest_metrics is not None
            else None
        )

        # Fetch only the fields AssetDetailResponse declares, using Python attribute
        # names (avoids __table__.columns col.key returning DB column names for
        # aliased columns like meta_data -> "metadata")
        asset_data = {
            field: getattr(asset, field)
            for field in AssetDetailResponse.model_fields
            if field != "daily_metrics"
        }
        asset_data["daily_metrics"] = metrics_response
        return AssetDetailResponse(**asset_data)
